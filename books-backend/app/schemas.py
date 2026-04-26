from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Literal, Optional
from app.models import ReadingStatus, BookEventCode


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Book schemas
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=100)
    isbn: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    published_date: Optional[datetime] = None
    page_count: Optional[int] = Field(None, ge=0)
    cover_image_url: Optional[str] = Field(None, max_length=500)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    isbn: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    published_date: Optional[datetime] = None
    page_count: Optional[int] = Field(None, ge=0)
    cover_image_url: Optional[str] = Field(None, max_length=500)


class BookResponse(BookBase):
    id: int
    cover_thumbnail_url: Optional[str] = None
    user_status: Optional["UserBookResponse"] = (
        None  # Include user's reading status if available
    )

    model_config = ConfigDict(from_attributes=True)


# UserBook (reading status) schemas
class UserBookBase(BaseModel):
    status: ReadingStatus
    notes: Optional[str] = None


class UserBookCreate(UserBookBase):
    pass


class UserBookUpdate(BaseModel):
    status: Optional[ReadingStatus] = None
    notes: Optional[str] = None


class UserBookStatusUpdate(BaseModel):
    """Simpler schema for updating just status via PUT endpoint."""

    status: ReadingStatus
    notes: Optional[str] = None
    occurred_at: Optional[datetime] = None


class UserBookResponse(UserBookBase):
    id: int
    user_id: int
    book_id: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    current_page: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# Book list schemas
class BookListResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class BookListItemReorderRequest(BaseModel):
    moved_book_id: int
    before_book_id: Optional[int] = None
    after_book_id: Optional[int] = None


# Pagination
class PaginatedBooks(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Google Books search result
class GoogleBookResult(BaseModel):
    """Result from Google Books API search."""

    title: str
    author: str
    isbn: Optional[str] = None
    description: Optional[str] = None
    published_date: Optional[str] = None
    page_count: Optional[int] = None
    thumbnail: Optional[str] = None
    google_books_id: Optional[str] = None


class CoverSearchResult(BaseModel):
    """A candidate cover image returned by the cover picker."""

    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    thumbnail: str
    image_url: str
    google_books_id: Optional[str] = None


class CoverUpgradeCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_url: str
    thumbnail_url: str
    width: int
    height: int
    source: str
    phash_distance: int
    match_quality: Literal["exact", "likely"]
    size_ratio: float


class CoverUpgradeJobResponse(BaseModel):
    job_id: str
    status: Literal["running", "done", "failed"]
    results: list[CoverUpgradeCandidateResponse] = []
    error: Optional[str] = None


# Export schemas
class ExportBookEntry(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None
    description: Optional[str] = None
    published_date: Optional[datetime] = None
    page_count: Optional[int] = None
    status: ReadingStatus
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    current_page: Optional[int] = None


class UserBooksExportResponse(BaseModel):
    schema_version: str = "v1"
    exported_at: datetime
    user: UserResponse
    books: list[ExportBookEntry]


# Book event schemas
class BookEventResponse(BaseModel):
    """Response schema for a book event."""

    id: str
    event_type: BookEventCode
    occurred_at: datetime
    note: Optional[str] = None
    page: Optional[int] = None
    old_cover_image_url: Optional[str] = None
    new_cover_image_url: Optional[str] = None
    old_cover_thumbnail_url: Optional[str] = None
    new_cover_thumbnail_url: Optional[str] = None
    import_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class BookProgressUpdate(BaseModel):
    page: int = Field(..., ge=0)
