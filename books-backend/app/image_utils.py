"""Utilities for downloading and storing book cover images."""

from __future__ import annotations

import hashlib
import re
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageOps

from app.config import settings

# Map content types to file extensions
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

THUMBNAIL_SIZE = (300, 450)

# Google Books serves this fixed "image not available" PNG for metadata-only volumes that have no real image at the
# requested zoom level. It is a single book-independent asset; we match it by its exact size (a cheap pre-filter)
# and the SHA-256 of its decoded RGB pixels.
GOOGLE_BOOKS_PLACEHOLDER_SIZE = (300, 391)
GOOGLE_BOOKS_PLACEHOLDER_DIGEST = (
    "42b73c2339111d1350b2b78efafaf46dede1fd1fb0bb0486422e55ab76f022df"
)


def _normalize_extension(extension: str | None) -> str:
    if not extension:
        return "jpg"
    normalized = extension.lower().lstrip(".")
    if normalized == "jpeg":
        normalized = "jpg"
    if normalized not in {"jpg", "png", "webp", "gif"}:
        return "jpg"
    return normalized


def _ensure_cover_dirs() -> tuple[Path, Path]:
    covers_dir = settings.uploads_dir_path / "covers"
    thumbnails_dir = covers_dir / "thumbnails"
    covers_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    return covers_dir, thumbnails_dir


def _create_thumbnail(content: bytes, cover_id: uuid.UUID) -> str | None:
    _, thumbnails_dir = _ensure_cover_dirs()
    try:
        image = Image.open(BytesIO(content))
        image = ImageOps.exif_transpose(image)

        if image.mode in {"RGBA", "P"}:
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        thumb = ImageOps.contain(image, THUMBNAIL_SIZE, method=Image.Resampling.LANCZOS)
        thumb_filename = f"{cover_id}_thumb.jpg"
        thumb_path = thumbnails_dir / thumb_filename
        thumb.save(
            thumb_path, format="JPEG", quality=85, optimize=True, progressive=True
        )
        return f"{settings.uploads_url_prefix}/covers/thumbnails/{thumb_filename}"
    except Exception as exc:
        print(f"Failed to generate cover thumbnail: {exc}")
        return None


def store_cover_image(content: bytes, extension: str | None) -> tuple[str, str | None]:
    """Store the full cover image and a resized thumbnail."""
    covers_dir, _ = _ensure_cover_dirs()
    cover_id = uuid.uuid4()
    normalized_extension = _normalize_extension(extension)
    cover_filename = f"{cover_id}.{normalized_extension}"
    file_path = covers_dir / cover_filename
    file_path.write_bytes(content)
    cover_url = f"{settings.uploads_url_prefix}/covers/{cover_filename}"
    thumbnail_url = _create_thumbnail(content, cover_id)
    return cover_url, thumbnail_url


def _is_google_books_placeholder(content: bytes) -> bool:
    """Detect Google Books' gray "image not available" placeholder image.

    Metadata-only volumes have only a small thumbnail; requesting a larger
    zoom silently returns this fixed-size PNG rather than an actual cover.
    """
    try:
        with Image.open(BytesIO(content)) as image:
            if image.size != GOOGLE_BOOKS_PLACEHOLDER_SIZE:
                return False
            digest = hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
            return digest == GOOGLE_BOOKS_PLACEHOLDER_DIGEST
    except (OSError, ValueError):
        return False


def _zoom_fallback_url(url: str) -> str | None:
    """Return a zoom=1 variant of a Google Books content URL, if applicable.

    Used to recover the real (lower-resolution) cover when a higher zoom
    returned the placeholder.
    """
    if "books.google" not in url:
        return None
    match = re.search(r"zoom=(\d+)", url)
    if not match or int(match.group(1)) <= 1:
        return None
    return re.sub(r"zoom=\d+", "zoom=1", url)


async def _fetch_image(client: httpx.AsyncClient, url: str) -> tuple[bytes, str]:
    """Fetch image bytes and infer a file extension from the response/URL."""
    headers = {"User-Agent": "BooksApp/1.0"}
    response = await client.get(url, headers=headers)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    extension = CONTENT_TYPE_TO_EXT.get(content_type)

    if not extension:
        # Try to infer from URL if content-type is generic
        if "jpeg" in url or "jpg" in url:
            extension = "jpg"
        elif "png" in url:
            extension = "png"
        elif "webp" in url:
            extension = "webp"
        elif "gif" in url:
            extension = "gif"
        else:
            extension = "jpg"  # Default to jpg

    return response.content, extension


async def download_cover_image(url: str) -> tuple[str, str | None] | None:
    """
    Download an image from a URL and save it locally with a thumbnail.

    Args:
        url: The URL of the image to download

    Returns:
        Tuple of (cover_image_url, cover_thumbnail_url) or None if download failed
    """
    if not url or not url.startswith("http"):
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            content, extension = await _fetch_image(client, url)

            # A Google Books volume that has no cover returns the "image not available" placeholder at higher zoom
            # levels. Fall back to the zoom=1 thumbnail, which holds the real (smaller) cover.
            if _is_google_books_placeholder(content):
                fallback_url = _zoom_fallback_url(url)
                if fallback_url:
                    fb_content, fb_extension = await _fetch_image(client, fallback_url)
                    if not _is_google_books_placeholder(fb_content):
                        content, extension = fb_content, fb_extension

            return store_cover_image(content, extension)

    except httpx.HTTPError as e:
        print(f"Failed to download cover image from {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error downloading cover image: {e}")
        return None
