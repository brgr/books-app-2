"""Store book cover images and generate thumbnails."""

import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from app.config import settings

THUMBNAIL_SIZE = (300, 450)


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
