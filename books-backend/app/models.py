from decimal import Decimal
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Enum,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.orm import declarative_base, mapped_column, relationship, Mapped
from datetime import datetime, UTC
from typing import TYPE_CHECKING
import enum
import uuid

if TYPE_CHECKING:
    from app.schemas import BookCreate, BookUpdate, UserBookResponse

Base = declarative_base()


class ShelfName(enum.Enum):
    """The book's shelf. Fixed and built-in for now; no user-created shelves yet."""

    WANT_TO_READ = "want_to_read"
    STARTED = "started"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class BookEventCode(enum.Enum):
    ADDED_TO_LIBRARY = "added_to_library"
    STARTED_READING = "started_reading"
    FINISHED_READING = "finished_reading"
    NOTE_SET = "note_set"
    PROGRESS_SET = "progress_set"
    COVER_CHANGED = "cover_changed"


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
    shelf: Mapped[ShelfName] = mapped_column(
        Enum(ShelfName), nullable=False, default=ShelfName.WANT_TO_READ
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # Hand-arranged position on whichever shelf the book is on. Null until the
    # book is first placed; app.shelves assigns and rebalances it.
    sort_order: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="user_books")
    book: Mapped["Book"] = relationship(back_populates="user_books")
    events: Mapped[list["BookEvent"]] = relationship(
        back_populates="user_book", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserBook(user_id={self.user_id}, book_id={self.book_id}, shelf='{self.shelf.value}')>"


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

    user_book: Mapped["UserBook"] = relationship(back_populates="events")
    event_type: Mapped["BookEventType"] = relationship()
    note_entry: Mapped["BookEventNote | None"] = relationship(
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


class BookEventNote(Base):
    __tablename__ = "book_event_notes"

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped["BookEvent"] = relationship(back_populates="note_entry")

    def __repr__(self):
        return f"<BookEventNote(event_id='{self.event_id}')>"


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


class Shelf(Base):
    """A row per built-in shelf per user. Gives each shelf a stable id for the
    API. Membership is derived from ``UserBook.shelf``, not stored here."""

    __tablename__ = "shelves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[ShelfName] = mapped_column(Enum(ShelfName), nullable=False)

    user: Mapped["User"] = relationship(back_populates="shelves")

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_shelves_user_name"),)

    @property
    def display_name(self) -> str:
        from app.shelves.shelves import SHELF_DISPLAY_NAMES

        return SHELF_DISPLAY_NAMES[self.name]

    def __repr__(self):
        return f"<Shelf(user_id={self.user_id}, name='{self.name}')>"
