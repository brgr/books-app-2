from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.books.dependencies import get_library_user_book
from app.database import get_db
from app.models import User, UserBook
from app.reading.service import ReadingService
from app.schemas import (
    BookEventResponse,
    BookProgressUpdate,
    UserBookRatingUpdate,
    UserBookResponse,
    UserBookShelfUpdate,
    build_book_event_response,
)

router = APIRouter()


def get_reading_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReadingService:
    return ReadingService(db, current_user)


@router.put("/books/{book_id}/shelf", response_model=UserBookResponse)
def set_shelf(
    shelf_data: UserBookShelfUpdate,
    user_book: Annotated[UserBook, Depends(get_library_user_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set or update the shelf for a book in the current user's library."""
    try:
        return service.set_shelf(user_book, shelf_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.put("/books/{book_id}/rating", response_model=UserBookResponse)
def set_rating(
    rating_data: UserBookRatingUpdate,
    user_book: Annotated[UserBook, Depends(get_library_user_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set a rating for a book in the current user's library."""
    return service.set_rating(user_book, rating_data)


@router.delete("/books/{book_id}/rating", status_code=status.HTTP_204_NO_CONTENT)
def clear_rating(
    user_book: Annotated[UserBook, Depends(get_library_user_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Clear the current user's rating for a book."""
    service.clear_rating(user_book)


@router.delete("/books/{book_id}/shelf", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_library(
    book_id: int,
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Remove a book from the current user's library."""
    if not service.remove_from_library(book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not in your reading list",
        )


@router.get("/books/{book_id}/events", response_model=list[BookEventResponse])
def get_book_events(
    user_book: Annotated[UserBook, Depends(get_library_user_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Get all events for a book for the current user, ordered by most recent first."""
    return [build_book_event_response(event) for event in service.get_events(user_book)]


@router.post("/books/{book_id}/progress", response_model=UserBookResponse)
def add_progress_event(
    progress: BookProgressUpdate,
    user_book: Annotated[UserBook, Depends(get_library_user_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Record a progress event for the current user."""
    try:
        return service.add_progress(user_book, progress)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
