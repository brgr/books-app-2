from sqlalchemy.orm import Session

from app.models import Book


def get_book_by_id(db: Session, book_id: int) -> Book | None:
    """Fetch a book by id, or None if it doesn't exist."""
    # PyCharm mis-infers db.get() as type[Book]; see JetBrains PY-63874
    # noinspection PyTypeChecker
    return db.get(Book, book_id)
