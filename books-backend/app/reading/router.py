from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.books.dependencies import get_library_book
from app.database import get_db
from app.models import Book, User
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
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set or update the shelf for a book in the current user's library."""
    try:
        return service.set_shelf(book.id, shelf_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.put("/books/{book_id}/rating", response_model=UserBookResponse)
def set_rating(
    book_id: int,
    rating_data: UserBookRatingUpdate,
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set a rating for a book in the current user's library."""
    response = service.set_rating(book_id, rating_data)

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not in your reading list",
        )

    return response


@router.delete("/books/{book_id}/rating", status_code=status.HTTP_204_NO_CONTENT)
def clear_rating(
    book_id: int,
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Clear the current user's rating for a book."""
    rating_cleared = service.clear_rating(book_id)

    if not rating_cleared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not in your reading list",
        )


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
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Get all events for a book for the current user, ordered by most recent first."""
    return [build_book_event_response(event) for event in service.get_events(book.id)]


@router.post("/books/{book_id}/progress", response_model=UserBookResponse)
def add_progress_event(
    progress: BookProgressUpdate,
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Record a progress event for the current user."""
    try:
        return service.add_progress(book.id, book.page_count, progress)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
