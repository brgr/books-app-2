from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.models import ReadingStatus


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Book schemas
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=100)
    isbn: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    published_date: Optional[datetime] = None
    page_count: Optional[int] = Field(None, ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    isbn: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    published_date: Optional[datetime] = None
    page_count: Optional[int] = Field(None, ge=0)


class BookResponse(BookBase):
    id: int
    created_at: datetime
    updated_at: datetime
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
    created_at: datetime
    updated_at: datetime

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
