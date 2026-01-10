from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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

    # File uploads
    media_root: str = "media"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Create a global settings instance
settings = Settings()
