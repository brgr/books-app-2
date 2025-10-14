from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import enum

Base = declarative_base()


class ReadingStatus(enum.Enum):
    WANT_TO_READ = "want_to_read"
    STARTED = "started"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationship to user's books
    user_books = relationship("UserBook", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}')>"


# TODO: Generated with Claude... still to update (more than one author e.g.)
class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    author = Column(String(100), nullable=False)
    isbn = Column(String(20), unique=True)
    description = Column(Text, nullable=True)
    published_date = Column(DateTime, nullable=True)
    page_count = Column(Integer, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationship to users who have this book
    user_books = relationship("UserBook", back_populates="book", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Book(title='{self.title}', author='{self.author}')>"


class UserBook(Base):
    __tablename__ = 'user_books'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    status = Column(Enum(ReadingStatus), nullable=False, default=ReadingStatus.WANT_TO_READ)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="user_books")
    book = relationship("Book", back_populates="user_books")

    def __repr__(self):
        return f"<UserBook(user_id={self.user_id}, book_id={self.book_id}, status='{self.status.value}')>"
