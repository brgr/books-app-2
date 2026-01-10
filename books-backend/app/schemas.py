from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.models import ReadingStatus, BookEventCode


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


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
    user_status: Optional["UserBookResponse"] = None  # Include user's reading status if available

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


class UserBookResponse(UserBookBase):
    id: int
    user_id: int
    book_id: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)
