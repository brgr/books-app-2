"""Utilities for downloading and storing book cover images."""
import uuid
from pathlib import Path

import httpx

from app.config import settings

# Map content types to file extensions
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


async def download_cover_image(url: str) -> str | None:
    """
    Download an image from a URL and save it locally.

    Args:
        url: The URL of the image to download

    Returns:
        The local path (e.g., "/uploads/covers/{uuid}.jpg") or None if download failed
    """
    if not url or not url.startswith("http"):
        return None

    try:
        headers = {"User-Agent": "BooksApp/1.0"}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
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
                else:
                    extension = "jpg"  # Default to jpg

            # Ensure upload directory exists
            covers_dir = Path(settings.uploads_dir) / "covers"
            covers_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename and save
            unique_filename = f"{uuid.uuid4()}.{extension}"
            file_path = covers_dir / unique_filename

            file_path.write_bytes(response.content)

            return f"/{settings.uploads_dir}/covers/{unique_filename}"

    except httpx.HTTPError as e:
        print(f"Failed to download cover image from {url}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error downloading cover image: {e}")
        return None
