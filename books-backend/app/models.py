from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Enum,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import enum
import uuid

Base = declarative_base()


class ReadingStatus(enum.Enum):
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Relationship to user's books
    user_books = relationship(
        "UserBook", back_populates="user", cascade="all, delete-orphan"
    )
    lists = relationship(
        "BookList", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(username='{self.username}')>"


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    author = Column(String(100), nullable=False)
    isbn = Column(String(20), unique=True)
    description = Column(Text, nullable=True)
    published_date = Column(DateTime, nullable=True)
    page_count = Column(Integer, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    cover_thumbnail_url = Column(String(500), nullable=True)

    # Relationship to users who have this book
    user_books = relationship(
        "UserBook", back_populates="book", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Book(title='{self.title}', author='{self.author}')>"


class UserBook(Base):
    __tablename__ = "user_books"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    status = Column(
        Enum(ReadingStatus), nullable=False, default=ReadingStatus.WANT_TO_READ
    )
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    current_page = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="user_books")
    book = relationship("Book", back_populates="user_books")
    events = relationship(
        "BookEvent", back_populates="user_book", cascade="all, delete-orphan"
    )
    list_items = relationship(
        "BookListItem", back_populates="user_book", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserBook(user_id={self.user_id}, book_id={self.book_id}, status='{self.status.value}')>"


class BookEventType(Base):
    __tablename__ = "book_event_types"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<BookEventType(code='{self.code}')>"


class BookEvent(Base):
    __tablename__ = "book_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_book_id = Column(
        Integer, ForeignKey("user_books.id", ondelete="CASCADE"), nullable=False
    )
    event_type_id = Column(Integer, ForeignKey("book_event_types.id"), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    user_book = relationship("UserBook", back_populates="events")
    event_type = relationship("BookEventType")
    note_entry = relationship(
        "BookEventNote",
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )
    progress_entry = relationship(
        "BookEventProgress",
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

    event_id = Column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    note = Column(Text, nullable=True)

    event = relationship("BookEvent", back_populates="note_entry")

    def __repr__(self):
        return f"<BookEventNote(event_id='{self.event_id}')>"


class BookEventProgress(Base):
    __tablename__ = "book_event_progress"

    event_id = Column(
        String(36), ForeignKey("book_events.id", ondelete="CASCADE"), primary_key=True
    )
    page = Column(Integer, nullable=False)

    event = relationship("BookEvent", back_populates="progress_entry")

    def __repr__(self):
        return f"<BookEventProgress(event_id='{self.event_id}', page={self.page})>"


class BookList(Base):
    __tablename__ = "book_lists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    user = relationship("User", back_populates="lists")
    items = relationship(
        "BookListItem", back_populates="list", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_book_lists_user_name"),)

    def __repr__(self):
        return f"<BookList(user_id={self.user_id}, name='{self.name}')>"


class BookListItem(Base):
    __tablename__ = "book_list_items"

    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("book_lists.id", ondelete="CASCADE"), nullable=False)
    user_book_id = Column(
        Integer, ForeignKey("user_books.id", ondelete="CASCADE"), nullable=False
    )
    sort_order = Column(Numeric(20, 10), nullable=False)

    list = relationship("BookList", back_populates="items")
    user_book = relationship("UserBook", back_populates="list_items")

    __table_args__ = (
        UniqueConstraint("list_id", "user_book_id", name="uq_book_list_items_list_user_book"),
    )

    def __repr__(self):
        return (
            f"<BookListItem(list_id={self.list_id}, user_book_id={self.user_book_id}, "
            f"sort_order={self.sort_order})>"
        )
