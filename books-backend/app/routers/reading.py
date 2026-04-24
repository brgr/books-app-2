from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.book_events import (
    ensure_added_event,
    project_user_book_state,
    record_finished_reading,
    record_note_event,
    record_progress_event,
    record_started_reading,
)
from app.book_lists import (
    ensure_list_item,
    get_or_create_default_lists,
    list_name_for_status,
)
from app.database import get_db
from app.models import (
    Book,
    BookEvent,
    BookEventCode,
    BookListItem,
    ReadingStatus,
    User,
    UserBook,
)
from app.schemas import (
    BookEventResponse,
    BookProgressUpdate,
    UserBookResponse,
    UserBookStatusUpdate,
)

router = APIRouter()


@router.put("/books/{book_id}/status", response_model=UserBookResponse)
def set_reading_status(
    book_id: int,
    status_data: UserBookStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Set or update the reading status for a book for the current user."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    user_id = cast(int, current_user.id)

    try:
        user_book = ensure_added_event(db, user_id=user_id, book_id=book_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    project_user_book_state(db, user_book)

    user_book_id = cast(int, user_book.id)

    try:
        if (
            status_data.status == ReadingStatus.WANT_TO_READ
            and user_book.status != ReadingStatus.WANT_TO_READ
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revert to 'want_to_read' after reading has started",
            )

        if (
            status_data.status == ReadingStatus.STARTED
            and user_book.status != ReadingStatus.STARTED
        ):
            record_started_reading(db, user_book_id=user_book_id)
        elif (
            status_data.status == ReadingStatus.FINISHED
            and user_book.status != ReadingStatus.FINISHED
        ):
            record_finished_reading(db, user_book_id=user_book_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    notes_provided = "notes" in status_data.model_fields_set
    if notes_provided:
        normalized_notes = status_data.notes
        if normalized_notes == "":
            normalized_notes = None

        if normalized_notes != user_book.notes:
            record_note_event(
                db,
                user_book_id=user_book_id,
                code=BookEventCode.NOTE_SET,
                note=normalized_notes,
            )
            user_book.notes = normalized_notes

    project_user_book_state(db, user_book)

    lists_by_name = get_or_create_default_lists(db, user_id)
    target_list_name = list_name_for_status(cast(ReadingStatus, user_book.status))
    target_list_id = (
        lists_by_name[target_list_name].id if target_list_name in lists_by_name else None
    )
    if target_list_id is not None:
        ensure_list_item(db, list_id=cast(int, target_list_id), user_book_id=user_book_id)

    for list_name, book_list in lists_by_name.items():
        if book_list.id != target_list_id:
            (
                db.query(BookListItem)
                .filter(
                    BookListItem.list_id == book_list.id,
                    BookListItem.user_book_id == user_book_id,
                )
                .delete()
            )
    db.commit()
    db.refresh(user_book)
    return user_book


@router.delete("/books/{book_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def remove_reading_status(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove a book from the current user's reading list."""
    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book_id)
        .first()
    )

    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not in your reading list",
        )

    db.delete(user_book)
    db.commit()
    return None


@router.get("/books/{book_id}/events", response_model=list[BookEventResponse])
def get_book_events(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get all events for a book for the current user, ordered by most recent first."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book_id)
        .first()
    )

    if not user_book:
        return []

    events = (
        db.query(BookEvent)
        .options(joinedload(BookEvent.note_entry), joinedload(BookEvent.progress_entry))
        .filter(BookEvent.user_book_id == user_book.id)
        .order_by(BookEvent.occurred_at.desc(), BookEvent.id.desc())
        .all()
    )

    return [
        BookEventResponse(
            id=event.id,
            event_type=event.event_type.code,
            occurred_at=event.occurred_at,
            note=event.note_entry.note if event.note_entry else None,
            page=event.progress_entry.page if event.progress_entry else None,
        )
        for event in events
    ]


@router.post("/books/{book_id}/progress", response_model=UserBookResponse)
def add_progress_event(
    book_id: int,
    progress: BookProgressUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Record a progress event for the current user."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book_id)
        .first()
    )
    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record progress before starting reading",
        )

    project_user_book_state(db, user_book)
    if user_book.status != ReadingStatus.STARTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record progress before starting reading",
        )

    page = progress.page
    if book.page_count is not None and page > book.page_count:
        page = book.page_count

    record_progress_event(db, user_book_id=user_book.id, page=page)
    user_book.current_page = page
    db.commit()
    db.refresh(user_book)
    return user_book
