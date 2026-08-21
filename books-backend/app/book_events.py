"""Event helper functions for book event sourcing (initial three-event slice)."""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    BookEvent,
    BookEventCode,
    BookEventCover,
    BookEventImportSource,
    BookEventNote,
    BookEventProgress,
    BookEventType,
    ReadingShelf,
    Shelf,
    ShelfKind,
    ShelfPlacement,
    UserBook,
)
from app.schemas import UserBookResponse
from app.shelves.shelves import place_on_shelf


def _get_event_type(session: Session, code: BookEventCode) -> BookEventType:
    # noinspection PyTypeChecker
    event_type: BookEventType | None = (
        session.query(BookEventType).filter(BookEventType.code == code.value).first()
    )
    if event_type is not None:
        return event_type
    raise ValueError(f"Event type '{code.value}' not seeded")


def _latest_event(
    session: Session, user_book_id: int, code: BookEventCode
) -> Optional[BookEvent]:
    # noinspection PyTypeChecker
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

    # noinspection PyTypeChecker
    existing_add = _latest_event(session, user_book.id, BookEventCode.ADDED_TO_LIBRARY)
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

    user_book = UserBook(user_id=user_id, book_id=book_id)
    session.add(user_book)
    session.flush()
    wanted = (
        session.query(Shelf)
        .filter_by(
            user_id=user_id,
            kind=ShelfKind.READING,
            name=ReadingShelf.WANT_TO_READ.value,
        )
        .one()
    )

    place_on_shelf(session, wanted, user_book)

    return user_book


def ensure_added_event(
    session: Session,
    user_id: int,
    book_id: int,
    import_id: Optional[int] = None,
) -> UserBook:
    """Guarantee a user_book row and its initial add event exist."""
    # noinspection PyTypeChecker
    user_book: UserBook | None = (
        session.query(UserBook)
        .filter(UserBook.user_id == user_id, UserBook.book_id == book_id)
        .first()
    )

    if user_book is None:
        record_added_to_library(
            session, user_id=user_id, book_id=book_id, import_id=import_id
        )
        # noinspection PyTypeChecker
        user_book = (
            session.query(UserBook)
            .filter(UserBook.user_id == user_id, UserBook.book_id == book_id)
            .first()
        )
        if user_book is None:
            raise ValueError("Failed to create user_book for add event")
        return user_book

    # noinspection PyTypeChecker
    existing_add = _latest_event(session, user_book.id, BookEventCode.ADDED_TO_LIBRARY)
    if not existing_add:
        record_added_to_library(
            session, user_id=user_id, book_id=book_id, import_id=import_id
        )
    # Imports may have created a legacy-style UserBook row first. Ensure it has
    # exactly one initial reading placement as well.
    has_reading_placement = (
        session.query(ShelfPlacement)
        .join(Shelf)
        .filter(
            ShelfPlacement.user_book_id == user_book.id, Shelf.kind == ShelfKind.READING
        )
        .first()
    )

    if has_reading_placement is None:
        shelf = (
            session.query(Shelf)
            .filter_by(
                user_id=user_id,
                kind=ShelfKind.READING,
                name=ReadingShelf.WANT_TO_READ.value,
            )
            .one()
        )
        place_on_shelf(session, shelf, user_book)

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
    latest_abandoned = _latest_event(
        session, user_book_id, BookEventCode.ABANDONED_READING
    )
    latest_terminal = latest_finish
    if latest_abandoned and (
        latest_terminal is None or _is_after(latest_abandoned, latest_terminal)
    ):
        latest_terminal = latest_abandoned

    # Validate against the event stream rather than the reading placement: an
    # import constructs its historical events before projecting that placement.
    if latest_start and not (
        latest_terminal and _is_after(latest_terminal, latest_start)
    ):
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

    # Validate against the event stream rather than the reading placement: an
    # import constructs its historical events before projecting that placement.
    if not latest_start:
        raise ValueError("Cannot finish reading before starting")
    if latest_finish and _is_after(latest_finish, latest_start):
        raise ValueError("Cannot finish reading twice without a new start")

    event_occurred_at = occurred_at or datetime.now(UTC)
    if event_occurred_at.tzinfo is None:
        event_occurred_at = event_occurred_at.replace(tzinfo=UTC)

    start_occurred_at = latest_start.occurred_at
    if start_occurred_at.tzinfo is None:
        start_occurred_at = start_occurred_at.replace(tzinfo=UTC)

    if event_occurred_at < start_occurred_at:
        raise ValueError("Cannot finish reading before the current start date")

    event_type = _get_event_type(session, BookEventCode.FINISHED_READING)
    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=event_type.id,
        occurred_at=event_occurred_at,
    )
    session.add(event)
    session.flush()
    return event


def record_reading_event(
    session: Session,
    user_book_id: int,
    code: BookEventCode,
    occurred_at: Optional[datetime] = None,
) -> BookEvent:
    """Append one of the pause/resume/abandon state events."""
    if code not in {
        BookEventCode.PAUSED_READING,
        BookEventCode.RESUMED_READING,
        BookEventCode.ABANDONED_READING,
    }:
        raise ValueError("Not a reading-state event")

    if not _latest_event(session, user_book_id, BookEventCode.ADDED_TO_LIBRARY):
        raise ValueError("Cannot change reading state before adding to library")

    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=_get_event_type(session, code).id,
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
    page: Optional[int] = None,
    percent: Optional[float] = None,
    occurred_at: Optional[datetime] = None,
) -> BookEvent:
    """Append a progress event for the user_book.

    Progress may be expressed as a page, a percent, or both. Page and percent
    are stored independently; neither is derived from the other.
    """
    if page is None and percent is None:
        raise ValueError("Progress event requires a page or a percent")

    event_type = _get_event_type(session, BookEventCode.PROGRESS_SET)
    event = BookEvent(
        user_book_id=user_book_id,
        event_type_id=event_type.id,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    session.add(BookEventProgress(event_id=event.id, page=page, percent=percent))
    session.flush()
    return event


def apply_progress_event(
    session: Session,
    user_book: UserBook,
    page: Optional[int] = None,
    percent: Optional[float] = None,
    max_page: Optional[int] = None,
) -> UserBook:
    """Record a progress event and update the user_book's current position.

    ``page`` is clamped to ``max_page`` (the book's length) when provided.
    Commits and returns the refreshed user_book.
    """
    if page is not None and max_page is not None and page > max_page:
        page = max_page

    record_progress_event(
        session, user_book_id=user_book.id, page=page, percent=percent
    )
    user_book.current_page = page
    user_book.current_percent = percent
    session.commit()
    session.refresh(user_book)
    return user_book


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


def derive_reading_dates(
    session: Session, user_book_id: int
) -> tuple[datetime | None, datetime | None]:
    """Derive ``(started_at, finished_at)`` for a user_book from its event stream.

    ``started_at`` is the latest start event's ``occurred_at`` (None if never started).
    ``finished_at`` is the latest finish event's ``occurred_at`` only when that finish is after the latest start
    (None otherwise), matching an open vs. closed reading cycle.
    """
    latest_start = _latest_event(session, user_book_id, BookEventCode.STARTED_READING)
    latest_finish = _latest_event(session, user_book_id, BookEventCode.FINISHED_READING)

    started_at = latest_start.occurred_at if latest_start else None
    if latest_finish and _is_after(latest_finish, latest_start):
        finished_at = latest_finish.occurred_at
    else:
        finished_at = None
    # noinspection PyTypeChecker
    return started_at, finished_at


def current_reading_shelf(session: Session, user_book_id: int) -> ReadingShelf:
    """Read the current state from the book's sole reading-shelf placement."""
    placement = (
        session.query(ShelfPlacement)
        .join(Shelf)
        .filter(
            ShelfPlacement.user_book_id == user_book_id,
            Shelf.kind == ShelfKind.READING,
        )
        .one()
    )

    return ReadingShelf(placement.shelf.name)


def move_reading_shelf_placement(
    session: Session, user_book: UserBook, state: ReadingShelf
) -> None:
    """Move a book's sole reading placement to ``state`` without touching custom ones."""
    current = (
        session.query(ShelfPlacement)
        .join(Shelf)
        .filter(
            ShelfPlacement.user_book_id == user_book.id, Shelf.kind == ShelfKind.READING
        )
        .one_or_none()
    )
    if current is not None and current.shelf.name == state.value:
        return

    if current is not None:
        session.delete(current)
        session.flush()

    shelf = (
        session.query(Shelf)
        .filter_by(user_id=user_book.user_id, kind=ShelfKind.READING, name=state.value)
        .one()
    )

    place_on_shelf(session, shelf, user_book)


def project_user_book_state(session: Session, user_book: UserBook) -> UserBook:
    """Project the current reading state from the event stream onto the user_book snapshot fields.

    Reading dates are *not* stored on the user_book. Instead, they are derived on demand via
    ``derive_reading_dates`` for serialization. This only projects the persisted snapshot columns
    (shelf, current page/percent).
    """
    # noinspection PyTypeChecker
    user_book_id: int = user_book.id
    latest_progress = _latest_event(session, user_book_id, BookEventCode.PROGRESS_SET)

    if latest_progress:
        progress_entry = (
            session.query(BookEventProgress)
            .filter(BookEventProgress.event_id == latest_progress.id)
            .first()
        )
        user_book.current_page = progress_entry.page if progress_entry else None
        user_book.current_percent = progress_entry.percent if progress_entry else None
    else:
        user_book.current_page = None
        user_book.current_percent = None

    return user_book


def build_user_book_response(session: Session, user_book: UserBook) -> UserBookResponse:
    """Assemble the reading-state response DTO for a user_book.

    Combines the persisted snapshot columns with the event-derived reading
    dates. This is the single seam that produces the read model; the ORM
    ``UserBook`` itself carries no date attributes.
    """
    # noinspection PyTypeChecker
    started_at, finished_at = derive_reading_dates(session, user_book.id)
    return UserBookResponse.from_user_book(
        user_book, current_reading_shelf(session, user_book.id), started_at, finished_at
    )
