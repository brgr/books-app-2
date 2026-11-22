"""Assemble a user's book export payload (query + reading-state projection)."""

from sqlalchemy.orm import Session

from app.book_events import (
    current_reading_shelf,
    derive_reading_date_values,
    project_user_book_state,
)
from app.models import Book, User
from app.schemas import ExportBookEntry


def build_user_books_export(db: Session, user: User) -> list[ExportBookEntry]:
    """Return the current reading state for every book the user owns."""
    books = db.query(Book).filter(Book.user_id == user.id).order_by(Book.id.asc()).all()

    entries = []
    for book in books:
        project_user_book_state(db, book)
        started_at, finished_at = derive_reading_date_values(db, book.id)
        reading_shelf = current_reading_shelf(db, book.id)

        book_entry = ExportBookEntry.from_book(
            book,
            reading_shelf,
            started_at=started_at,
            finished_at=finished_at,
        )

        entries.append(book_entry)

    return entries
