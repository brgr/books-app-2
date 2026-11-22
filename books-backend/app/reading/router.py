from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.books.dependencies import get_library_book
from app.database import get_db
from app.models import Book
from app.reading.service import ReadingService
from app.schemas import (
    BookEventResponse,
    BookNotesUpdate,
    BookProgressUpdate,
    BookRatingUpdate,
    BookResponse,
    BookShelfUpdate,
    build_book_event_response,
)

router = APIRouter()


def get_reading_service(db: Annotated[Session, Depends(get_db)]) -> ReadingService:
    return ReadingService(db)


@router.put("/books/{book_id}/shelf", response_model=BookResponse)
def set_shelf(
    shelf_data: BookShelfUpdate,
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set or update the shelf for a book in the current user's library."""
    try:
        return service.set_shelf(book, shelf_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.put("/books/{book_id}/notes", response_model=BookResponse)
def set_notes(
    notes_data: BookNotesUpdate,
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set or clear the current user's notes for a book."""
    return service.set_notes(book, notes_data)


@router.put("/books/{book_id}/rating", response_model=BookResponse)
def set_rating(
    rating_data: BookRatingUpdate,
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Set a rating for a book in the current user's library."""
    return service.set_rating(book, rating_data)


@router.delete("/books/{book_id}/rating", status_code=status.HTTP_204_NO_CONTENT)
def clear_rating(
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Clear the current user's rating for a book."""
    service.clear_rating(book)


@router.get("/books/{book_id}/events", response_model=list[BookEventResponse])
def get_book_events(
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Get all events for a book for the current user, ordered by most recent first."""
    return [build_book_event_response(event) for event in service.get_events(book)]


@router.post("/books/{book_id}/progress", response_model=BookResponse)
def add_progress_event(
    progress: BookProgressUpdate,
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[ReadingService, Depends(get_reading_service)],
):
    """Record a progress event for the current user."""
    try:
        return service.add_progress(book, progress)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
