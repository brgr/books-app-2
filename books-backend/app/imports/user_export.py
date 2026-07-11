"""Assemble a user's book export payload (query + reading-state projection)."""

from sqlalchemy.orm import Session

from app.book_events import derive_reading_dates, project_user_book_state
from app.models import Book, User, UserBook
from app.schemas import ExportBookEntry


def build_user_books_export(db: Session, user: User) -> list[ExportBookEntry]:
    """Return the current reading state for every book the user owns."""
    user_books = (
        db.query(UserBook, Book)
        .join(Book, UserBook.book_id == Book.id)
        .filter(UserBook.user_id == user.id)
        .order_by(Book.id.asc())
        .all()
    )

    entries = []
    for user_book, book in user_books:
        project_user_book_state(db, user_book)
        started_at, finished_at = derive_reading_dates(db, user_book.id)
        entries.append(
            ExportBookEntry.from_orm_pair(
                book, user_book, started_at=started_at, finished_at=finished_at
            )
        )
    return entries
