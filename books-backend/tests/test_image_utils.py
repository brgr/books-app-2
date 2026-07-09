"""Tests for image utilities."""

from io import BytesIO
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.image_utils import (
    GOOGLE_BOOKS_PLACEHOLDER_SIZE,
    _is_google_books_placeholder,
    _zoom_fallback_url,
    download_cover_image,
)

# The genuine Google Books "image not available" placeholder, captured once.
PLACEHOLDER_BYTES = (
    Path(__file__).parent / "fixtures" / "google_books_placeholder.png"
).read_bytes()


def _png_bytes(size: tuple[int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, (200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(size: tuple[int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def test_is_google_books_placeholder():
    assert _is_google_books_placeholder(PLACEHOLDER_BYTES)
    # A real cover at the placeholder's exact size must NOT be treated as the
    # placeholder — the pixel-content check distinguishes them.
    assert not _is_google_books_placeholder(_png_bytes(GOOGLE_BOOKS_PLACEHOLDER_SIZE))
    assert not _is_google_books_placeholder(_jpeg_bytes(GOOGLE_BOOKS_PLACEHOLDER_SIZE))
    assert not _is_google_books_placeholder(_png_bytes((300, 450)))
    assert not _is_google_books_placeholder(b"not an image")


def test_zoom_fallback_url():
    base = "https://books.google.com/books/content?id=X&img=1&zoom=2&source=gbs_api"
    assert _zoom_fallback_url(base) == base.replace("zoom=2", "zoom=1")
    # Already zoom=1, non-Google, or no zoom param -> no fallback.
    assert _zoom_fallback_url(base.replace("zoom=2", "zoom=1")) is None
    assert _zoom_fallback_url("https://example.com/cover.jpg?zoom=2") is None
    assert _zoom_fallback_url("https://books.google.com/books/content?id=X") is None


async def test_download_falls_back_to_zoom1_on_placeholder(monkeypatch):
    """A placeholder at zoom=2 should trigger a retry at zoom=1."""
    placeholder = PLACEHOLDER_BYTES
    real_cover = _jpeg_bytes((128, 205))
    requested: list[str] = []

    async def fake_get(self, url, headers=None):
        requested.append(url)
        request = httpx.Request("GET", url)
        if "zoom=1" in url:
            return httpx.Response(
                200,
                content=real_cover,
                headers={"content-type": "image/jpeg"},
                request=request,
            )
        return httpx.Response(
            200,
            content=placeholder,
            headers={"content-type": "image/png"},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    url = "https://books.google.com/books/content?id=X&img=1&zoom=2&source=gbs_api"
    result = await download_cover_image(url)

    assert result is not None
    cover_url, _ = result
    assert cover_url.endswith(".jpg")  # stored the JPEG cover, not the PNG placeholder
    assert any("zoom=1" in u for u in requested)


@pytest.mark.external
async def test_download_cover_image_from_google_books():
    """Test downloading a cover image from Google Books."""
    url = "https://books.google.com/books/content?id=S7M1EQAAQBAJ&printsec=frontcover&img=1&zoom=0&edge=curl&source=gbs_api"

    result = await download_cover_image(url)

    assert result is not None
    cover_url, thumbnail_url = result
    assert cover_url.startswith("/uploads/covers/")
    assert cover_url.endswith((".jpg", ".png", ".webp", ".gif"))
    assert thumbnail_url is not None
    assert thumbnail_url.startswith("/uploads/covers/thumbnails/")


async def test_download_cover_image_invalid_url():
    """Test that invalid URLs return None."""
    result = await download_cover_image("")
    assert result is None

    result = await download_cover_image("not-a-url")
    assert result is None


async def test_download_cover_image_nonexistent_url():
    """Test that nonexistent URLs return None."""
    result = await download_cover_image("https://example.com/nonexistent-image.jpg")
    assert result is None
