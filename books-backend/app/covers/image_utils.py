"""Utilities for downloading and storing book cover images."""

from __future__ import annotations

import hashlib
import re
from io import BytesIO

import httpx
from PIL import Image

from app.covers.cover_matching import covers_match
from app.covers.storage import store_cover_image

# Map content types to file extensions
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

# Google Books serves this fixed "image not available" PNG for metadata-only volumes that have no real image at the
# requested zoom level. It is a single book-independent asset; we match it by its exact size (a cheap pre-filter)
# and the SHA-256 of its decoded RGB pixels.
GOOGLE_BOOKS_PLACEHOLDER_SIZE = (300, 391)
GOOGLE_BOOKS_PLACEHOLDER_DIGEST = (
    "42b73c2339111d1350b2b78efafaf46dede1fd1fb0bb0486422e55ab76f022df"
)


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


async def fetch_cover_image(url: str) -> tuple[bytes, str] | None:
    """Fetch a cover, validating Google zoom variants against their thumbnail."""
    if not url or not url.startswith("http"):
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            content, extension = await _fetch_image(client, url)

            # A higher Google zoom can return a placeholder or a cropped image.
            # Therefore, we reuse the upgrade search's perceptual match check before
            # replacing the thumbnail with a higher-resolution image.
            fallback_url = _zoom_fallback_url(url)
            if fallback_url:
                try:
                    fb_content, fb_extension = await _fetch_image(client, fallback_url)

                    if not _is_google_books_placeholder(fb_content):
                        with (
                            Image.open(BytesIO(content)) as full,
                            Image.open(BytesIO(fb_content)) as thumbnail,
                        ):
                            matches = covers_match(full, thumbnail)

                        if _is_google_books_placeholder(content) or not matches:
                            content, extension = fb_content, fb_extension
                except (httpx.HTTPError, OSError, ValueError):
                    # An unavailable thumbnail must not prevent a valid full
                    # image from being saved.
                    pass

            # A successful HTTP response can still be empty or contain an error page.
            # Decode before writing anything, so we can catch errors early.
            with Image.open(BytesIO(content)) as image:
                image.load()

            return content, extension

    except httpx.HTTPError as e:
        print(f"Failed to download cover image from {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error downloading cover image: {e}")
        return None


async def download_cover_image(url: str) -> tuple[str, str | None] | None:
    """Download and store the same validated image used by the cover preview."""
    result = await fetch_cover_image(url)

    if result is None:
        return None

    try:
        return store_cover_image(*result)
    except Exception as e:
        print(f"Failed to store cover image: {e}")
        return None
