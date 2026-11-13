from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.books.queries import get_book_by_id, get_user_book
from app.database import get_db
from app.models import Book, User, UserBook


def get_library_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Book:
    """Load a book from the acting user's library, or 404 if it isn't in it."""
    book = get_book_by_id(db, book_id)

    if not book or not get_user_book(db, user_id=current_user.id, book_id=book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    return book


def get_library_user_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserBook:
    """Load the acting user's library entry for a book, or 404 if there is none."""
    user_book = get_user_book(db, user_id=current_user.id, book_id=book_id)

    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    return user_book
