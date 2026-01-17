from typing import Optional
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./books.db"

    # Application
    app_name: str = "Books API"
    debug: bool = False

    # CORS (if needed later)
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Google Books API (optional - search works without it but may have rate limits)
    google_books_api_key: Optional[str] = None

    # File uploads: user-generated assets (e.g., downloaded/posted book covers). A separate
    # static assets directory can be added later if needed; this is only for uploads.
    uploads_dir: str = "uploads"
    uploads_url_path: str = "uploads"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_exp_minutes: int = 60
    jwt_refresh_token_exp_minutes: int = 60 * 24 * 30

    # Cookie settings
    cookie_secure: bool = True  # Set to False for local network testing over HTTP (localhost works with True)
    cookie_samesite: str = "lax"  # "lax", "strict", or "none"
    cookie_domain: str | None = None  # None = current domain only

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

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
