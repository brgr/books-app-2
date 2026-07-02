from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Book, UserBook


def get_book_by_id(db: Session, book_id: int) -> Book | None:
    """Fetch a book by id, or None if it doesn't exist."""
    # PyCharm mis-infers db.get() as type[Book]; see JetBrains PY-63874
    # noinspection PyTypeChecker
    return db.get(Book, book_id)


def get_user_book(db: Session, *, user_id: int, book_id: int) -> UserBook | None:
    """Fetch the given user's reading state for a book, if any."""
    return db.scalars(
        select(UserBook).where(UserBook.user_id == user_id, UserBook.book_id == book_id)
    ).first()
