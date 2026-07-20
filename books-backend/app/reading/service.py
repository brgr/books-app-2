"""Orchestration layer for a user's reading state and timeline."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.book_events import (
    apply_progress_event,
    build_user_book_response,
    ensure_added_event,
    project_user_book_state,
    record_finished_reading,
    record_note_event,
    record_started_reading,
)
from app.books.queries import get_user_book
from app.models import (
    BookEvent,
    BookEventCode,
    ShelfName,
    User,
    UserBook,
)
from app.schemas import BookProgressUpdate, UserBookResponse, UserBookShelfUpdate
from app.shelves.shelves import ensure_shelf_position, move_to_end_of_shelf


# noinspection bad-argument-type
class ReadingService:
    """Reading-state operations scoped to a single request's db session and user."""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    @property
    def _user_id(self) -> int:
        # noinspection PyTypeChecker
        return self.user.id

    def set_shelf(
        self, book_id: int, shelf_data: UserBookShelfUpdate
    ) -> UserBookResponse:
        """Set or update the acting user's shelf for a book.

        Raises ValueError on any domain-rule violation (illegal transition, a
        future ``occurred_at``, etc.); the router maps these to HTTP 400.
        """
        user_book = ensure_added_event(self.db, user_id=self._user_id, book_id=book_id)
        project_user_book_state(self.db, user_book)
        previous_shelf = user_book.shelf

        occurred_at = self._normalize_occurred_at(shelf_data.occurred_at)
        self._apply_shelf_transition(user_book, shelf_data.shelf, occurred_at)
        self._apply_notes(user_book, shelf_data)

        project_user_book_state(self.db, user_book)
        self._sync_shelf_position(user_book, previous_shelf)

        self.db.commit()
        self.db.refresh(user_book)

        return build_user_book_response(self.db, user_book)

    def remove_from_library(self, book_id: int) -> bool:
        """Remove the book from the user's library. Returns False if absent."""
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book_id)
        if not user_book:
            return False
        self.db.delete(user_book)
        self.db.commit()
        return True

    def get_events(self, book_id: int) -> list[BookEvent]:
        """Return the user's events for a book, most recent first (empty if none)."""
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book_id)
        if not user_book:
            return []

        # noinspection PyTypeChecker
        return (
            self.db.query(BookEvent)
            .options(
                joinedload(BookEvent.note_entry),
                joinedload(BookEvent.progress_entry),
                joinedload(BookEvent.cover_entry),
                joinedload(BookEvent.import_source),
            )
            .filter(BookEvent.user_book_id == user_book.id)
            .order_by(BookEvent.occurred_at.desc(), BookEvent.id.desc())
            .all()
        )

    def add_progress(
        self, book_id: int, max_page: int | None, progress: BookProgressUpdate
    ) -> UserBookResponse:
        """Record a progress event, requiring an in-progress reading cycle.

        Raises ValueError (mapped to HTTP 400) if the book has not been started.
        """
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book_id)
        if not user_book:
            raise ValueError("Cannot record progress before starting reading")

        project_user_book_state(self.db, user_book)
        if user_book.shelf != ShelfName.STARTED:
            raise ValueError("Cannot record progress before starting reading")

        user_book = apply_progress_event(
            self.db,
            user_book,
            page=progress.page,
            percent=progress.percent,
            max_page=max_page,
        )
        return build_user_book_response(self.db, user_book)

    @staticmethod
    def _normalize_occurred_at(occurred_at: datetime | None) -> datetime | None:
        if occurred_at is None:
            return None
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        if occurred_at > datetime.now(UTC):
            raise ValueError("occurred_at cannot be in the future")
        return occurred_at

    def _apply_shelf_transition(
        self,
        user_book: UserBook,
        target_shelf: ShelfName,
        occurred_at: datetime | None,
    ) -> None:
        user_book_id = user_book.id
        if (
            target_shelf == ShelfName.WANT_TO_READ
            and user_book.shelf != ShelfName.WANT_TO_READ
        ):
            raise ValueError(
                "Cannot revert to 'want_to_read' after reading has started"
            )

        if target_shelf == ShelfName.STARTED and user_book.shelf != ShelfName.STARTED:
            record_started_reading(
                self.db, user_book_id=user_book_id, occurred_at=occurred_at
            )
        elif (
            target_shelf == ShelfName.FINISHED and user_book.shelf != ShelfName.FINISHED
        ):
            record_finished_reading(
                self.db, user_book_id=user_book_id, occurred_at=occurred_at
            )

    def _apply_notes(
        self, user_book: UserBook, shelf_data: UserBookShelfUpdate
    ) -> None:
        if "notes" not in shelf_data.model_fields_set:
            return
        normalized_notes = shelf_data.notes
        if normalized_notes == "":
            normalized_notes = None
        if normalized_notes != user_book.notes:
            record_note_event(
                self.db,
                user_book_id=user_book.id,
                code=BookEventCode.NOTE_SET,
                note=normalized_notes,
            )
            user_book.notes = normalized_notes

    def _sync_shelf_position(
        self, user_book: UserBook, previous_shelf: ShelfName
    ) -> None:
        """Keep the book's position sensible after a shelf change."""
        if previous_shelf != user_book.shelf:
            move_to_end_of_shelf(self.db, user_book)
        else:
            ensure_shelf_position(self.db, user_book)
