from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.books.queries import get_book_by_id
from app.database import get_db
from app.models import User
from app.reading_service import ReadingService
from app.schemas import (
    BookEventResponse,
    BookProgressUpdate,
    UserBookResponse,
    UserBookStatusUpdate,
)

router = APIRouter()


def get_reading_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReadingService:
    return ReadingService(db, current_user)


@router.put("/books/{book_id}/status", response_model=UserBookResponse)
def set_reading_status(
    book_id: int,
    status_data: UserBookStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set or update the reading status for a book for the current user."""
    if not get_book_by_id(db, book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    try:
        return service.set_status(book_id, status_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.delete("/books/{book_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def remove_reading_status(
    book_id: int,
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Remove a book from the current user's reading list."""
    if not service.remove_status(book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not in your reading list",
        )


@router.get("/books/{book_id}/events", response_model=list[BookEventResponse])
def get_book_events(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Get all events for a book for the current user, ordered by most recent first."""
    if not get_book_by_id(db, book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    return [
        BookEventResponse.from_event(event) for event in service.get_events(book_id)
    ]


@router.post("/books/{book_id}/progress", response_model=UserBookResponse)
def add_progress_event(
    book_id: int,
    progress: BookProgressUpdate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Record a progress event for the current user."""
    book = get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    try:
        return service.add_progress(book_id, book.page_count, progress)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
