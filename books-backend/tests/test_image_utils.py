"""Tests for image utilities."""
import pytest

from app.image_utils import download_cover_image


@pytest.mark.external
async def test_download_cover_image_from_google_books():
    """Test downloading a cover image from Google Books."""
    url = "https://books.google.com/books/content?id=S7M1EQAAQBAJ&printsec=frontcover&img=1&zoom=0&edge=curl&source=gbs_api"

    result = await download_cover_image(url)

    assert result is not None
    assert result.startswith("/media/covers/")
    assert result.endswith((".jpg", ".png", ".webp", ".gif"))


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
