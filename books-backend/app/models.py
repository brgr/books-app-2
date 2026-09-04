import enum
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

if TYPE_CHECKING:
    from app.schemas import BookCreate, BookUpdate, UserBookResponse

Base = declarative_base()


class ReadingShelf(enum.Enum):
    """Fixed reading shelves."""

    WANT_TO_READ = "want_to_read"
    STARTED = "started"
    PAUSED = "paused"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class BookEventCode(enum.Enum):
    ADDED_TO_LIBRARY = "added_to_library"
    STARTED_READING = "started_reading"
    PAUSED_READING = "paused_reading"
    RESUMED_READING = "resumed_reading"
    FINISHED_READING = "finished_reading"
    ABANDONED_READING = "abandoned_reading"
    NOTE_SET = "note_set"
    RATING_SET = "rating_set"
    PROGRESS_SET = "progress_set"
    COVER_CHANGED = "cover_changed"


class ReadingDatePrecision(enum.Enum):
    """How much of a reading date is known."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ReadingDate:
    """A reading date whose calendar precision may be full, partial, or unknown.

    Known values are stored at the first instant of their known period; e.g., April 2026
    will be stored as April 1st, 2026.  The separate precision field then tells it that
    the reading date is only known to the month or year (in the example, the reading date
    is only known to the month).
    """

    value: datetime | None
    precision: ReadingDatePrecision

    def __post_init__(self) -> None:
        if self.precision == ReadingDatePrecision.UNKNOWN:
            if self.value is not None:
                raise ValueError("An unknown reading date cannot have a value")
            return
        if self.value is None:
            raise ValueError("A known reading date requires a value")

        normalized = self.value.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.precision == ReadingDatePrecision.MONTH:
            normalized = normalized.replace(day=1)
        elif self.precision == ReadingDatePrecision.YEAR:
            normalized = normalized.replace(month=1, day=1)
        object.__setattr__(self, "value", normalized)

    @classmethod
    def unknown(cls) -> "ReadingDate":
        return cls(None, ReadingDatePrecision.UNKNOWN)

    @classmethod
    def from_datetime(cls, value: datetime) -> "ReadingDate":
        """Build a day-precision date from a legacy full timestamp."""
        return cls(value, ReadingDatePrecision.DAY)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationship to user's books
    user_books: Mapped[list["UserBook"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    shelves: Mapped[list["Shelf"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(username='{self.username}')>"


class Book(Base):
    __tablename__ = "books"
    # Permit the non-Mapped ``user_book`` annotation below; it's a transient
    # instance attribute the service layer sets, not a mapped column.
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship to users who have this book
    user_books: Mapped[list["UserBook"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )

    user_book: "UserBookResponse | None" = None

    @classmethod
    def from_create(cls, data: "BookCreate") -> "Book":
        """Build a Book from a validated BookCreate payload."""
        return cls(
            title=data.title,
            author=data.author,
            isbn=data.isbn,
            description=data.description,
            published_date=data.published_date,
            page_count=data.page_count,
            cover_image_url=data.cover_image_url,
        )

    def apply_update(self, data: "BookUpdate") -> None:
        """Assign only the explicitly-set fields from a partial update payload.

        Mirrors ``from_create``'s explicit mapping (rather than a blind
        ``setattr`` loop, which would silently accept unknown fields) so
        schema/model drift surfaces here. Uses ``model_fields_set`` for PATCH
        semantics: absent fields are left untouched, fields set to ``None`` are
        cleared. ``cover_image_url`` is assigned raw here; the service layer
        resolves any download/thumbnail side effects afterwards.
        """
        fields = data.model_fields_set
        if "title" in fields and data.title is not None:
            self.title = data.title
        if "author" in fields and data.author is not None:
            self.author = data.author
        if "isbn" in fields:
            self.isbn = data.isbn
        if "description" in fields:
            self.description = data.description
        if "published_date" in fields:
            self.published_date = data.published_date
        if "page_count" in fields:
            self.page_count = data.page_count
        if "cover_image_url" in fields:
            self.cover_image_url = data.cover_image_url

    def __repr__(self):
        return f"<Book(title='{self.title}', author='{self.author}')>"


class UserBook(Base):
    __tablename__ = "user_books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    current_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="user_books")
    book: Mapped["Book"] = relationship(back_populates="user_books")
    events: Mapped[list["BookEvent"]] = relationship(
        back_populates="user_book", cascade="all, delete-orphan"
    )
    shelf_placements: Mapped[list["ShelfPlacement"]] = relationship(
        back_populates="user_book", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserBook(user_id={self.user_id}, book_id={self.book_id})>"


class BookEventType(Base):
    __tablename__ = "book_event_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<BookEventType(code='{self.code}')>"


class BookEvent(Base):
    __tablename__ = "book_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_books.id", ondelete="CASCADE"), nullable=False
    )
    event_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("book_event_types.id"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    reading_date_entry: Mapped["BookEventReadingDate | None"] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )

    user_book: Mapped["UserBook"] = relationship(back_populates="events")
    event_type: Mapped["BookEventType"] = relationship()
    note_entry: Mapped["BookEventNote | None"] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    rating_entry: Mapped["BookEventRating | None"] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    progress_entry: Mapped["BookEventProgress | None"] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    cover_entry: Mapped["BookEventCover | None"] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    import_source: Mapped["BookEventImportSource | None"] = relationship(
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("id", name="uq_book_events_id"),)

    def __repr__(self):
        return (
            f"<BookEvent(id='{self.id}', user_book_id={self.user_book_id}, "
            f"event_type_id={self.event_type_id}, occurred_at={self.occurred_at})>"
        )


class BookEventReadingDate(Base):
    """Imprecise date payload for a reading-state event."""

    __tablename__ = "book_event_reading_dates"

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    precision: Mapped[ReadingDatePrecision] = mapped_column(
        Enum(ReadingDatePrecision, name="reading_date_precision"), nullable=False
    )

    event: Mapped["BookEvent"] = relationship(back_populates="reading_date_entry")

    def __repr__(self):
        return (
            f"<BookEventReadingDate(event_id='{self.event_id}', "
            f"precision={self.precision.value})>"
        )


class BookEventNote(Base):
    __tablename__ = "book_event_notes"

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped["BookEvent"] = relationship(back_populates="note_entry")

    def __repr__(self):
        return f"<BookEventNote(event_id='{self.event_id}')>"


class BookEventRating(Base):
    """The rating assigned by a rating-set event; null means it was cleared."""

    __tablename__ = "book_event_ratings"

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)

    event: Mapped["BookEvent"] = relationship(back_populates="rating_entry")

    def __repr__(self):
        return f"<BookEventRating(event_id='{self.event_id}', rating={self.rating})>"


class BookEventProgress(Base):
    __tablename__ = "book_event_progress"

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    event: Mapped["BookEvent"] = relationship(back_populates="progress_entry")

    def __repr__(self):
        return (
            f"<BookEventProgress(event_id='{self.event_id}', "
            f"page={self.page}, percent={self.percent})>"
        )


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<Import(id={self.id}, user_id={self.user_id}, "
            f"filename='{self.filename}', imported_count={self.imported_count})>"
        )


class BookEventImportSource(Base):
    __tablename__ = "book_event_import_sources"

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    import_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("imports.id", ondelete="CASCADE"), nullable=False
    )

    event: Mapped["BookEvent"] = relationship(back_populates="import_source")
    import_record: Mapped["Import"] = relationship()

    def __repr__(self):
        return (
            f"<BookEventImportSource(event_id='{self.event_id}', "
            f"import_id={self.import_id})>"
        )


class BookEventCover(Base):
    __tablename__ = "book_event_covers"

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    old_cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    new_cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    old_cover_thumbnail_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    new_cover_thumbnail_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    event: Mapped["BookEvent"] = relationship(back_populates="cover_entry")

    def __repr__(self):
        return f"<BookEventCover(event_id='{self.event_id}')>"


class ShelfKind(enum.Enum):
    READING = "reading"
    CUSTOM = "custom"


class Shelf(Base):
    """An ordered shelf, either a reading shelf or a custom (user-created) shelf."""

    __tablename__ = "shelves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[ShelfKind] = mapped_column(
        Enum(ShelfKind, name="shelf_kind"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    user: Mapped["User"] = relationship(back_populates="shelves")
    placements: Mapped[list["ShelfPlacement"]] = relationship(
        back_populates="shelf", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "kind", "name", name="uq_shelves_user_kind_name"),
    )

    def __repr__(self):
        return f"<Shelf(user_id={self.user_id}, kind='{self.kind.value}', name='{self.name}')>"


class ShelfPlacement(Base):
    """A book's placement and position on one shelf."""

    __tablename__ = "shelf_placements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shelf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shelves.id", ondelete="CASCADE"), nullable=False
    )
    user_book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_books.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)

    shelf: Mapped["Shelf"] = relationship(back_populates="placements")
    user_book: Mapped["UserBook"] = relationship(back_populates="shelf_placements")

    __table_args__ = (
        UniqueConstraint(
            "shelf_id",
            "user_book_id",
            name="uq_shelf_placements_shelf_user_book",
        ),
        Index("ix_shelf_placements_shelf_sort", "shelf_id", "sort_order"),
    )

    def __repr__(self):
        return f"<ShelfPlacement(shelf_id={self.shelf_id}, user_book_id={self.user_book_id})>"
