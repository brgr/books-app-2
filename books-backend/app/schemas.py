from datetime import datetime
from typing import Annotated, Literal, Optional, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models import (
    Book,
    BookEvent,
    BookEventCode,
    ReadingDate,
    ReadingDatePrecision,
    ReadingShelf,
    UserBook,
)


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
    user_book: Optional["UserBookResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# UserBook schemas
class ReadingDateValue(BaseModel):
    """A calendar date together with how precisely the user knows it."""

    value: Optional[datetime] = None
    precision: ReadingDatePrecision

    @model_validator(mode="after")
    def validate_value(self) -> "ReadingDateValue":
        # Keep validation and normalization rules in the domain model so the
        # HTTP contract cannot represent an invalid reading date.
        reading_date = ReadingDate(self.value, self.precision)
        self.value = reading_date.value
        return self

    def to_domain(self) -> ReadingDate:
        return ReadingDate(self.value, self.precision)

    @classmethod
    def from_domain(cls, reading_date: ReadingDate) -> "ReadingDateValue":
        return cls(value=reading_date.value, precision=reading_date.precision)


class UserBookBase(BaseModel):
    shelf: ReadingShelf
    notes: Optional[str] = None


class UserBookCreate(UserBookBase):
    pass


class UserBookUpdate(BaseModel):
    shelf: Optional[ReadingShelf] = None
    notes: Optional[str] = None


class UserBookShelfUpdate(BaseModel):
    """Schema for updating just the shelf via PUT endpoint."""

    shelf: ReadingShelf
    notes: Optional[str] = None
    reading_date: Optional[ReadingDateValue] = None


class UserBookResponse(UserBookBase):
    id: int
    user_id: int
    book_id: int
    started_at: Optional[ReadingDateValue] = None
    finished_at: Optional[ReadingDateValue] = None
    current_page: Optional[int] = None
    current_percent: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_user_book(
        cls,
        user_book: UserBook,
        shelf: ReadingShelf,
        started_at: Optional[ReadingDate],
        finished_at: Optional[ReadingDate],
    ) -> "UserBookResponse":
        """Build the response from a user_book plus its event-derived dates.

        Reading dates are not stored on ``UserBook``; the caller derives them
        from the event stream and passes them in.
        """
        # noinspection PyTypeChecker
        return cls(
            id=user_book.id,
            user_id=user_book.user_id,
            book_id=user_book.book_id,
            shelf=shelf,
            notes=user_book.notes,
            started_at=ReadingDateValue.from_domain(started_at) if started_at else None,
            finished_at=ReadingDateValue.from_domain(finished_at)
            if finished_at
            else None,
            current_page=user_book.current_page,
            current_percent=user_book.current_percent,
        )


# Shelf schemas
class ShelfReorderRequest(BaseModel):
    moved_book_id: int
    before_book_id: Optional[int] = None
    after_book_id: Optional[int] = None


class CustomShelfNamePayload(BaseModel):
    """Body of both shelf create and shelf rename."""

    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]


class CustomShelfBookAdd(BaseModel):
    book_id: int


class ShelfResponse(BaseModel):
    """One shelf.

    ``ref`` is how the shelf is addressed in a URL: ``reading:<ReadingShelf
    value>`` or ``custom:<id>``. Its tag identifies the shelf kind.
    """

    ref: str
    display_name: str
    book_count: int


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
    shelf: ReadingShelf
    notes: Optional[str] = None
    started_at: Optional[ReadingDateValue] = None
    finished_at: Optional[ReadingDateValue] = None
    current_page: Optional[int] = None
    current_percent: Optional[float] = None

    @classmethod
    def from_orm_pair(
        cls,
        book: Book,
        user_book: UserBook,
        shelf: ReadingShelf,
        started_at: Optional[ReadingDate],
        finished_at: Optional[ReadingDate],
    ) -> "ExportBookEntry":
        # noinspection PyTypeChecker
        return cls(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            description=book.description,
            published_date=book.published_date,
            page_count=book.page_count,
            shelf=shelf,
            notes=user_book.notes,
            started_at=ReadingDateValue.from_domain(started_at) if started_at else None,
            finished_at=ReadingDateValue.from_domain(finished_at)
            if finished_at
            else None,
            current_page=user_book.current_page,
            current_percent=user_book.current_percent,
        )


class UserBooksExportResponse(BaseModel):
    # A small note: In theory, we should have bumped this already. Since, in practice,
    # this isn't really used yet; we didn't yet bump it.
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
    reading_date: Optional[ReadingDateValue] = None
    note: Optional[str] = None
    page: Optional[int] = None
    percent: Optional[float] = None
    old_cover_image_url: Optional[str] = None
    new_cover_image_url: Optional[str] = None
    old_cover_thumbnail_url: Optional[str] = None
    new_cover_thumbnail_url: Optional[str] = None
    import_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_event(cls, event: BookEvent) -> "BookEventResponse":
        """Flatten a BookEvent and its detail rows into a response object."""
        reading_date = (
            ReadingDateValue.from_domain(
                ReadingDate(
                    event.reading_date_entry.value,
                    event.reading_date_entry.precision,
                )
            )
            if event.reading_date_entry
            else None
        )

        return cls(
            id=str(event.id),
            event_type=cast(BookEventCode, event.event_type.code),
            occurred_at=event.occurred_at,
            reading_date=reading_date,
            note=event.note_entry.note if event.note_entry else None,
            page=event.progress_entry.page if event.progress_entry else None,
            percent=event.progress_entry.percent if event.progress_entry else None,
            old_cover_image_url=event.cover_entry.old_cover_image_url
            if event.cover_entry
            else None,
            new_cover_image_url=event.cover_entry.new_cover_image_url
            if event.cover_entry
            else None,
            old_cover_thumbnail_url=event.cover_entry.old_cover_thumbnail_url
            if event.cover_entry
            else None,
            new_cover_thumbnail_url=event.cover_entry.new_cover_thumbnail_url
            if event.cover_entry
            else None,
            import_id=event.import_source.import_id if event.import_source else None,
        )


class BookProgressUpdate(BaseModel):
    page: Optional[int] = Field(default=None, ge=0)
    percent: Optional[float] = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _require_page_or_percent(self) -> "BookProgressUpdate":
        if self.page is None and self.percent is None:
            raise ValueError("Must provide page or percent")
        return self


class ImportResponse(BaseModel):
    id: int
    filename: Optional[str] = None
    occurred_at: datetime
    imported_count: int
    skipped_count: int

    model_config = ConfigDict(from_attributes=True)
