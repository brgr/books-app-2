"""Tests for cover-upgrade search endpoints and the cover_upgrade module."""

import time

import imagehash
import pytest
from PIL import Image

from app import cover_upgrade
from app.cover_upgrade import (
    CoverUpgradeJob,
    JOB_TTL_SECONDS,
    _gc_jobs,
    _run_job,
    _score_candidates,
    get_job,
)
from app.models import Book, UserBook


def _make_image(
    size: tuple[int, int], color: tuple[int, int, int] = (123, 45, 67)
) -> Image.Image:
    """Build a deterministic image. Same color → same pHash regardless of size."""
    return Image.new("RGB", size, color)


def _create_book_with_local_cover(
    db, *, cover_path: str, title="T", author="A", isbn="111"
):
    book = Book(title=title, author=author, isbn=isbn, cover_image_url=cover_path)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def _add_to_library(db, *, user_id, book_id):
    ub = UserBook(user_id=user_id, book_id=book_id)
    db.add(ub)
    db.commit()


def _user_id(db, username: str) -> int:
    from app.models import User

    return db.query(User).filter(User.username == username).first().id


@pytest.fixture
def local_cover(tmp_path, monkeypatch):
    """Write a small local cover and point settings at the tmp uploads dir."""
    monkeypatch.setattr(
        cover_upgrade.settings, "uploads_dir", str(tmp_path), raising=False
    )
    # uploads_dir_path / uploads_url_prefix are properties — they read uploads_dir/uploads_url_path.
    img = _make_image((100, 150))
    cover_file = tmp_path / "cover.jpg"
    img.save(cover_file, "JPEG")
    return "/uploads/cover.jpg"


# ---------- Router tests ----------


def test_start_cover_upgrade_404_for_unknown_book(client, auth_headers):
    r = client.post("/books/999/cover-upgrade-search", headers=auth_headers)
    assert r.status_code == 404


def test_start_cover_upgrade_404_when_book_not_in_library(
    client, auth_headers, db_session, local_cover
):
    book = _create_book_with_local_cover(db_session, cover_path=local_cover)
    # Note: book exists but no UserBook row for current user.
    r = client.post(f"/books/{book.id}/cover-upgrade-search", headers=auth_headers)
    assert r.status_code == 404


def test_start_cover_upgrade_400_when_no_local_cover(client, auth_headers, db_session):
    book = Book(title="T", author="A", cover_image_url=None)
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    _add_to_library(
        db_session, user_id=_user_id(db_session, "testuser"), book_id=book.id
    )
    r = client.post(f"/books/{book.id}/cover-upgrade-search", headers=auth_headers)
    assert r.status_code == 400


def test_start_cover_upgrade_400_for_external_cover(client, auth_headers, db_session):
    book = Book(title="T", author="A", cover_image_url="http://example.com/c.jpg")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    _add_to_library(
        db_session, user_id=_user_id(db_session, "testuser"), book_id=book.id
    )
    r = client.post(f"/books/{book.id}/cover-upgrade-search", headers=auth_headers)
    assert r.status_code == 400


def test_start_and_get_cover_upgrade_job(
    client, auth_headers, db_session, local_cover, monkeypatch
):
    # Make the job no-op so we can deterministically inspect status transitions.
    async def fake_run(job, **_):
        job.status = "done"
        job.finished_at = time.time()

    monkeypatch.setattr(cover_upgrade, "_run_job", fake_run)

    book = _create_book_with_local_cover(db_session, cover_path=local_cover)
    _add_to_library(
        db_session, user_id=_user_id(db_session, "testuser"), book_id=book.id
    )

    r = client.post(f"/books/{book.id}/cover-upgrade-search", headers=auth_headers)
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    # Poll once — fake_run completes immediately.
    r2 = client.get(
        f"/books/{book.id}/cover-upgrade-search/{job_id}", headers=auth_headers
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["job_id"] == job_id
    assert body["status"] == "done"


def test_get_job_404_for_wrong_book_id(
    client, auth_headers, db_session, local_cover, monkeypatch
):
    async def fake_run(job, **_):
        job.status = "done"
        job.finished_at = time.time()

    monkeypatch.setattr(cover_upgrade, "_run_job", fake_run)

    book = _create_book_with_local_cover(db_session, cover_path=local_cover)
    _add_to_library(
        db_session, user_id=_user_id(db_session, "testuser"), book_id=book.id
    )
    r = client.post(f"/books/{book.id}/cover-upgrade-search", headers=auth_headers)
    job_id = r.json()["job_id"]

    r2 = client.get(f"/books/9999/cover-upgrade-search/{job_id}", headers=auth_headers)
    assert r2.status_code == 404


def test_get_job_404_for_other_users_job(
    client, auth_headers, db_session, local_cover, monkeypatch
):
    """A job created by user A must not be visible to user B."""

    async def fake_run(job, **_):
        job.status = "done"
        job.finished_at = time.time()

    monkeypatch.setattr(cover_upgrade, "_run_job", fake_run)

    book = _create_book_with_local_cover(db_session, cover_path=local_cover)
    _add_to_library(
        db_session, user_id=_user_id(db_session, "testuser"), book_id=book.id
    )

    r = client.post(f"/books/{book.id}/cover-upgrade-search", headers=auth_headers)
    job_id = r.json()["job_id"]

    # The harness only allows one user, so simulate cross-user isolation by
    # rewriting the in-memory job's user_id to a different value.
    cover_upgrade._jobs[job_id].user_id = 99999

    r2 = client.get(
        f"/books/{book.id}/cover-upgrade-search/{job_id}", headers=auth_headers
    )
    assert r2.status_code == 404


# ---------- Module-level tests ----------


@pytest.mark.asyncio
async def test_score_candidates_filters_by_size_ratio(monkeypatch):
    current = _make_image((100, 150))
    current_hash = imagehash.phash(current)

    candidates = [
        {"image_url": "u1", "thumbnail": None, "source": "google_books"},  # too small
        {"image_url": "u2", "thumbnail": None, "source": "google_books"},  # big enough
    ]

    async def fake_fetch(client, url):
        if url == "u1":
            return _make_image((110, 165))  # ratio 1.1 < 1.3
        return _make_image((200, 300))

    monkeypatch.setattr(cover_upgrade, "_fetch_image", fake_fetch)

    results = await _score_candidates(candidates, current_hash, current.size[0])
    urls = [r.image_url for r in results]
    assert urls == ["u2"]


@pytest.mark.asyncio
async def test_score_candidates_drops_unrelated_images(monkeypatch):
    current = _make_image((100, 150), color=(255, 0, 0))
    current_hash = imagehash.phash(current)

    candidates = [
        {"image_url": "match", "thumbnail": None, "source": "x"},
        {"image_url": "noise", "thumbnail": None, "source": "x"},
    ]

    async def fake_fetch(client, url):
        if url == "match":
            return _make_image((200, 300), color=(255, 0, 0))
        # Random noise → distinct phash
        img = Image.effect_noise((200, 300), 100).convert("RGB")
        return img

    monkeypatch.setattr(cover_upgrade, "_fetch_image", fake_fetch)

    results = await _score_candidates(candidates, current_hash, current.size[0])
    assert [r.image_url for r in results] == ["match"]
    assert results[0].match_quality in ("exact", "likely")


@pytest.mark.asyncio
async def test_run_job_transitions_to_done(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cover_upgrade.settings, "uploads_dir", str(tmp_path), raising=False
    )
    cover = tmp_path / "c.jpg"
    _make_image((100, 150)).save(cover, "JPEG")

    async def fake_gather(**_):
        return []

    monkeypatch.setattr(cover_upgrade, "_gather_candidates", fake_gather)

    job = CoverUpgradeJob(id="j1", book_id=1, user_id=1)
    await _run_job(
        job, title="t", author="a", isbn=None, current_cover_path="/uploads/c.jpg"
    )
    assert job.status == "done"
    assert job.finished_at is not None
    assert job.results == []


@pytest.mark.asyncio
async def test_run_job_transitions_to_failed_on_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(
        cover_upgrade.settings, "uploads_dir", str(tmp_path), raising=False
    )
    cover = tmp_path / "c.jpg"
    _make_image((100, 150)).save(cover, "JPEG")

    async def boom(**_):
        raise RuntimeError("network is down")

    monkeypatch.setattr(cover_upgrade, "_gather_candidates", boom)

    job = CoverUpgradeJob(id="j2", book_id=1, user_id=1)
    await _run_job(
        job, title="t", author="a", isbn=None, current_cover_path="/uploads/c.jpg"
    )
    assert job.status == "failed"
    assert "network is down" in (job.error or "")


def test_gc_drops_old_finished_jobs():
    cover_upgrade._jobs.clear()
    old = CoverUpgradeJob(id="old", book_id=1, user_id=1, status="done")
    old.finished_at = time.time() - JOB_TTL_SECONDS - 1
    fresh = CoverUpgradeJob(id="fresh", book_id=1, user_id=1, status="done")
    fresh.finished_at = time.time()
    cover_upgrade._jobs["old"] = old
    cover_upgrade._jobs["fresh"] = fresh

    _gc_jobs()

    assert "old" not in cover_upgrade._jobs
    assert "fresh" in cover_upgrade._jobs
    assert get_job("old") is None
    assert get_job("fresh") is fresh
