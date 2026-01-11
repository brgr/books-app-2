from typing import Optional
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./books.db"

    # Application
    app_name: str = "Books API"
    debug: bool = False

    # CORS (if needed later)
    allowed_origins: list[str] = ["*"]

    # Google Books API (optional - search works without it but may have rate limits)
    google_books_api_key: Optional[str] = None

    # File uploads: user-generated assets (e.g., downloaded/posted book covers). A separate
    # static assets directory can be added later if needed; this is only for uploads.
    uploads_dir: str = "uploads"
    uploads_url_path: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def uploads_dir_path(self) -> Path:
        """Path on disk where uploads are stored."""
        return Path(self.uploads_dir)

    @property
    def uploads_url_prefix(self) -> str:
        """URL prefix under which uploads are served."""
        return "/" + self.uploads_url_path.strip("/")


# Create a global settings instance
settings = Settings()
