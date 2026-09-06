"""Generate development books directly using the backend's event helpers."""

from sqlalchemy.orm import Session

from app.book_events import (
    ensure_added_event,
    move_reading_shelf_placement,
    record_finished_reading,
    record_reading_event,
    record_started_reading,
)
from app.models import Book, BookEventCode, ReadingDate, ReadingShelf


def create_sample_books(
    db: Session, user_id: int, count: int, shelf: ReadingShelf
) -> None:
    """Add sample books and reading history."""
    if count < 0:
        raise ValueError("Sample book count must be zero or greater")

    for index in range(1, count + 1):
        book = Book(
            title=f"Sample Book {index:04d}",
            author=f"Sample Author {(index - 1) % 30 + 1:02d}",
            page_count=100 + (index * 37) % 600,
            description=f"Generated development book {index} for testing a large library.",
        )

        db.add(book)
        db.flush()

        user_book = ensure_added_event(db, user_id=user_id, book_id=book.id)

        if shelf != ReadingShelf.WANT_TO_READ:
            record_started_reading(db, user_book.id, ReadingDate.unknown())
        if shelf == ReadingShelf.FINISHED:
            record_finished_reading(db, user_book.id, ReadingDate.unknown())
        elif shelf == ReadingShelf.PAUSED:
            record_reading_event(db, user_book.id, BookEventCode.PAUSED_READING)
        elif shelf == ReadingShelf.ABANDONED:
            record_reading_event(db, user_book.id, BookEventCode.ABANDONED_READING)

        move_reading_shelf_placement(db, user_book, shelf)
