"""Find a higher-resolution version of a book's existing cover.

Runs asynchronously: a search job collects candidates from Google Books and
OpenLibrary, perceptually hashes each one, and keeps those that match the
current cover closely enough to be the same artwork at higher resolution.
Job state is in-memory (single-process assumption).
"""

import asyncio
import io
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx
import imagehash
from PIL import Image

from app.config import settings
from app.google_books import GoogleBooksRateLimitError, search_cover_images

# Hash distance bands (8x8 pHash, 64-bit).
EXACT_THRESHOLD = 6
LIKELY_THRESHOLD = 10
# Require the upgrade to be meaningfully larger.
MIN_SIZE_RATIO = 1.3
# Cap concurrent search jobs across the process.
SEARCH_SEMAPHORE = asyncio.Semaphore(3)
# Drop finished jobs after this long so the dict doesn't grow forever.
JOB_TTL_SECONDS = 60 * 30
# Per-image fetch timeout.
IMAGE_TIMEOUT = 15.0

JobStatus = Literal["running", "done", "failed"]
MatchQuality = Literal["exact", "likely"]


@dataclass
class CoverUpgradeCandidate:
    image_url: str
    thumbnail_url: str
    width: int
    height: int
    source: str
    phash_distance: int
    match_quality: MatchQuality
    size_ratio: float


@dataclass
class CoverUpgradeJob:
    id: str
    book_id: int
    user_id: int
    status: JobStatus = "running"
    results: list[CoverUpgradeCandidate] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None


_jobs: dict[str, CoverUpgradeJob] = {}
_running_tasks: set[asyncio.Task] = set()


def get_job(job_id: str) -> CoverUpgradeJob | None:
    _gc_jobs()
    return _jobs.get(job_id)


def _gc_jobs() -> None:
    now = time.time()
    stale = [
        jid
        for jid, j in _jobs.items()
        if j.finished_at is not None and now - j.finished_at > JOB_TTL_SECONDS
    ]
    for jid in stale:
        _jobs.pop(jid, None)


def start_job(
    *,
    book_id: int,
    user_id: int,
    title: str | None,
    author: str | None,
    isbn: str | None,
    current_cover_path: str,
) -> CoverUpgradeJob:
    job = CoverUpgradeJob(id=str(uuid.uuid4()), book_id=book_id, user_id=user_id)
    _jobs[job.id] = job
    task = asyncio.create_task(
        _run_job(
            job,
            title=title,
            author=author,
            isbn=isbn,
            current_cover_path=current_cover_path,
        )
    )
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)
    return job


async def _run_job(
    job: CoverUpgradeJob,
    *,
    title: str | None,
    author: str | None,
    isbn: str | None,
    current_cover_path: str,
) -> None:
    async with SEARCH_SEMAPHORE:
        try:
            current = _load_local_cover(current_cover_path)
            current_hash = imagehash.phash(current)
            current_width = current.size[0]

            candidates = await _gather_candidates(title=title, author=author, isbn=isbn)
            results = await _score_candidates(candidates, current_hash, current_width)
            results.sort(
                key=lambda c: (
                    0 if c.match_quality == "exact" else 1,
                    -c.size_ratio,
                    c.phash_distance,
                )
            )
            job.results = results
            job.status = "done"
        except Exception as e:  # noqa: BLE001 - surface to client
            job.status = "failed"
            job.error = f"{type(e).__name__}: {e}"
        finally:
            job.finished_at = time.time()


def _load_local_cover(url_path: str) -> Image.Image:
    rel = url_path.removeprefix(f"{settings.uploads_url_prefix}/")
    path = Path(settings.uploads_dir_path) / rel
    return Image.open(path).convert("RGB")


async def _gather_candidates(
    *, title: str | None, author: str | None, isbn: str | None
) -> list[dict]:
    """Pull candidates from Google Books + OpenLibrary, dedup by image URL."""
    seen: set[str] = set()
    out: list[dict] = []

    def _extend(items: list[dict], source: str) -> None:
        for it in items:
            url = it.get("image_url")
            if not url or url in seen:
                continue
            seen.add(url)
            out.append({**it, "source": source})

    # Google Books: title+author and ISBN.
    google_queries: list[dict] = []
    if title or author:
        google_queries.append({"title": title, "author": author})
    if isbn:
        google_queries.append({"isbn": isbn})
    for q in google_queries:
        try:
            _extend(await search_cover_images(**q, max_results=40), "google_books")
        except GoogleBooksRateLimitError:
            raise
        except Exception:
            # search_cover_images already swallows most errors and returns []
            pass

    # OpenLibrary: direct ISBN cover + edition search.
    if isbn:
        _extend(
            [
                {
                    "title": "",
                    "isbn": isbn,
                    "thumbnail": (
                        f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false"
                    ),
                    "image_url": (
                        f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
                    ),
                }
            ],
            "openlibrary",
        )
        _extend(await _openlibrary_search({"isbn": isbn, "limit": 5}), "openlibrary")

    if title or author:
        params: dict[str, str | int] = {"limit": 10}
        if title:
            params["title"] = title
        if author:
            params["author"] = author
        _extend(await _openlibrary_search(params), "openlibrary")

    return out


async def _openlibrary_search(params: dict) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("https://openlibrary.org/search.json", params=params)
            r.raise_for_status()
            docs = r.json().get("docs", [])
    except Exception:
        return []
    items: list[dict] = []
    for doc in docs:
        cid = doc.get("cover_i")
        if not cid:
            continue
        items.append(
            {
                "title": doc.get("title", ""),
                "isbn": (doc.get("isbn") or [None])[0],
                "thumbnail": f"https://covers.openlibrary.org/b/id/{cid}-M.jpg",
                "image_url": f"https://covers.openlibrary.org/b/id/{cid}-L.jpg",
            }
        )
    return items


async def _score_candidates(
    candidates: list[dict],
    current_hash: imagehash.ImageHash,
    current_width: int,
) -> list[CoverUpgradeCandidate]:
    async with httpx.AsyncClient(
        timeout=IMAGE_TIMEOUT, follow_redirects=True
    ) as client:
        images = await asyncio.gather(
            *(_fetch_image(client, c["image_url"]) for c in candidates)
        )

    results: list[CoverUpgradeCandidate] = []
    for cand, img in zip(candidates, images):
        if img is None:
            continue
        width, height = img.size
        if width <= current_width * MIN_SIZE_RATIO:
            continue
        dist = current_hash - imagehash.phash(img)
        if dist <= EXACT_THRESHOLD:
            quality: MatchQuality = "exact"
        elif dist <= LIKELY_THRESHOLD:
            quality = "likely"
        else:
            continue
        results.append(
            CoverUpgradeCandidate(
                image_url=cand["image_url"],
                thumbnail_url=cand.get("thumbnail") or cand["image_url"],
                width=width,
                height=height,
                source=cand["source"],
                phash_distance=dist,
                match_quality=quality,
                size_ratio=round(width / current_width, 2),
            )
        )
    return results


async def _fetch_image(client: httpx.AsyncClient, url: str) -> Image.Image | None:
    try:
        r = await client.get(url)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None
