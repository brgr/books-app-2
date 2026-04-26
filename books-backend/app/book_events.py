"""Event helper functions for book event sourcing (initial three-event slice)."""

from datetime import datetime, UTC
from typing import Optional, cast

from sqlalchemy.orm import Session

from app.models import (
    BookEvent,
    BookEventCode,
    BookEventCover,
    BookEventImportSource,
    BookEventNote,
    BookEventProgress,
    BookEventType,
    ReadingStatus,
    UserBook,
)


def _get_event_type(session: Session, code: BookEventCode) -> BookEventType:
    event_type: BookEventType | None = (
        session.query(BookEventType).filter(BookEventType.code == code.value).first()
    )
    if event_type is not None:
        return event_type
    raise ValueError(f"Event type '{code.value}' not seeded")


def _latest_event(
    session: Session, user_book_id: int, code: BookEventCode
) -> Optional[BookEvent]:
    return (
        session.query(BookEvent)
        .join(BookEventType, BookEvent.event_type_id == BookEventType.id)
        .filter(
            BookEvent.user_book_id == user_book_id, BookEventType.code == code.value
        )
        .order_by(BookEvent.occurred_at.desc(), BookEvent.id.desc())
        .first()
    )


def _is_after(candidate: BookEvent, other: Optional[BookEvent]) -> bool:
    if other is None:
        return True
    if candidate.occurred_at > other.occurred_at:
        return True
    if candidate.occurred_at < other.occurred_at:
        return False
    return str(candidate.id) > str(other.id)


def record_added_to_library(
    session: Session,
    user_id: int,
    book_id: int,
    occurred_at: Optional[datetime] = None,
    import_id: Optional[int] = None,
) -> BookEvent:
    """Create the user_book record if needed and append the first add event.

    Raises ValueError if an add event already exists for this user_book.
    """
    user_book = _ensure_user_book(session, user_id=user_id, book_id=book_id)

    existing_add = _latest_event(
        session, cast(int, user_book.id), BookEventCode.ADDED_TO_LIBRARY
    )
    if existing_add:
        raise ValueError("Book already added to library for this user")

    event_type = _get_event_type(session, BookEventCode.ADDED_TO_LIBRARY)
    event = BookEvent(
        user_book_id=user_book.id,
        event_type_id=event_type.id,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    if import_id is not None:
        session.add(BookEventImportSource(event_id=event.id, import_id=import_id))
        session.flush()
    return event


def _ensure_user_book(session: Session, user_id: int, book_id: int) -> UserBook:
    user_book: UserBook | None = (
        session.query(UserBook)
        .filter(UserBook.user_id == user_id, UserBook.book_id == book_id)
        .first()
    )
    if user_book is not None:
        return user_book

    user_book = UserBook(
        user_id=user_id, book_id=book_id, status=ReadingStatus.WANT_TO_READ
    )
    session.add(user_book)
    session.flush()
    return user_book


def ensure_added_event(
    session: Session,
    user_id: int,
    book_id: int,
    import_id: Optional[int] = None,
) -> UserBook:
    """Guarantee a user_book row and its initial add event exist."""
    user_book: UserBook | None = (
        session.query(UserBook)
        .filter(UserBook.user_id == user_id, UserBook.book_id == book_id)
        .first()
    )

    if user_book is None:
        record_added_to_library(
            session, user_id=user_id, book_id=book_id, import_id=import_id
        )
        user_book = (
            session.query(UserBook)
            .filter(UserBook.user_id == user_id, UserBook.book_id == book_id)
            .first()
        )
        if user_book is None:
            raise ValueError("Failed to create user_book for add event")
        return user_book

    existing_add = _latest_event(session, user_book.id, BookEventCode.ADDED_TO_LIBRARY)
    if not existing_add:
        record_added_to_library(
            session, user_id=user_id, book_id=book_id, import_id=import_id
        )
    return user_book


def record_started_reading(
    session: Session,
    user_book_id: int,
    occurred_at: Optional[datetime] = None,
) -> BookEvent:
    """Append a start event if the book is not currently being read.

    Requires that the book was added and is not already in an open reading cycle.
    """
    add_event = _latest_event(session, user_book_id, BookEventCode.ADDED_TO_LIBRARY)
    if not add_event:
        raise ValueError("Cannot start reading before adding to library")

    latest_start = _latest_event(session, user_book_id, BookEventCode.STARTED_READING)
    latest_finish = _latest_event(session, user_book_id, BookEventCode.FINISHED_READING)

    if latest_start and not (latest_finish and _is_after(latest_finish, latest_start)):
        raise ValueError(
            "Cannot start reading while a reading cycle is already in progress"
        )

    event_type = _get_event_type(session, BookEventCode.STARTED_READING)
    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=event_type.id,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    return event


def record_finished_reading(
    session: Session,
    user_book_id: int,
    occurred_at: Optional[datetime] = None,
) -> BookEvent:
    """Append a finish event if there is an open reading cycle."""
    add_event = _latest_event(session, user_book_id, BookEventCode.ADDED_TO_LIBRARY)
    if not add_event:
        raise ValueError("Cannot finish reading before adding to library")

    latest_start = _latest_event(session, user_book_id, BookEventCode.STARTED_READING)
    latest_finish = _latest_event(session, user_book_id, BookEventCode.FINISHED_READING)

    if not latest_start:
        raise ValueError("Cannot finish reading before starting")

    if latest_finish and _is_after(latest_finish, latest_start):
        raise ValueError("Cannot finish reading twice without a new start")

    event_type = _get_event_type(session, BookEventCode.FINISHED_READING)
    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=event_type.id,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    return event


def record_note_event(
    session: Session,
    user_book_id: int,
    code: BookEventCode,
    note: Optional[str],
    occurred_at: Optional[datetime] = None,
) -> BookEvent:
    """Append a note event for the user_book."""
    event_type = _get_event_type(session, code)
    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=event_type.id,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    session.add(BookEventNote(event_id=event.id, note=note))
    session.flush()
    return event


def record_progress_event(
    session: Session,
    user_book_id: int,
    page: int,
    occurred_at: Optional[datetime] = None,
) -> BookEvent:
    """Append a progress event for the user_book."""
    event_type = _get_event_type(session, BookEventCode.PROGRESS_SET)
    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=event_type.id,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    session.add(BookEventProgress(event_id=event.id, page=page))
    session.flush()
    return event


def record_cover_changed(
    session: Session,
    user_book_id: int,
    old_cover_image_url: Optional[str],
    new_cover_image_url: Optional[str],
    old_cover_thumbnail_url: Optional[str],
    new_cover_thumbnail_url: Optional[str],
    occurred_at: Optional[datetime] = None,
) -> BookEvent:
    """Append a cover-changed event to the user's reading timeline.

    Caller must check the cover URL actually changed before calling.
    """
    event_type = _get_event_type(session, BookEventCode.COVER_CHANGED)
    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=event_type.id,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    session.add(
        BookEventCover(
            event_id=event.id,
            old_cover_image_url=old_cover_image_url,
            new_cover_image_url=new_cover_image_url,
            old_cover_thumbnail_url=old_cover_thumbnail_url,
            new_cover_thumbnail_url=new_cover_thumbnail_url,
        )
    )
    session.flush()
    return event


def project_user_book_state(session: Session, user_book: UserBook) -> UserBook:
    """Project the current reading state from the event stream onto the user_book snapshot fields."""
    user_book_id = cast(int, user_book.id)
    latest_start = _latest_event(session, user_book_id, BookEventCode.STARTED_READING)
    latest_finish = _latest_event(session, user_book_id, BookEventCode.FINISHED_READING)
    latest_progress = _latest_event(session, user_book_id, BookEventCode.PROGRESS_SET)

    if latest_finish and _is_after(latest_finish, latest_start):
        user_book.status = ReadingStatus.FINISHED
        user_book.finished_at = latest_finish.occurred_at
    elif latest_start:
        user_book.status = ReadingStatus.STARTED
        user_book.finished_at = None
    else:
        user_book.status = ReadingStatus.WANT_TO_READ
        user_book.finished_at = None

    user_book.started_at = latest_start.occurred_at if latest_start else None
    if latest_progress:
        progress_entry = (
            session.query(BookEventProgress)
            .filter(BookEventProgress.event_id == latest_progress.id)
            .first()
        )
        user_book.current_page = progress_entry.page if progress_entry else None
    else:
        user_book.current_page = None
    session.flush()

    return user_book
