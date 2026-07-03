"""Orchestration layer for a user's reading state and timeline."""

from datetime import datetime, UTC

from sqlalchemy.orm import Session, joinedload

from app.book_events import (
    apply_progress_event,
    ensure_added_event,
    project_user_book_state,
    record_finished_reading,
    record_note_event,
    record_started_reading,
)
from app.book_lists import (
    ensure_list_item,
    get_or_create_default_lists,
    list_name_for_status,
)
from app.book_queries import get_user_book
from app.models import (
    BookEvent,
    BookEventCode,
    BookListItem,
    ReadingStatus,
    User,
    UserBook,
)
from app.schemas import BookProgressUpdate, UserBookStatusUpdate


class ReadingService:
    """Reading-state operations scoped to a single request's db session and user."""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    @property
    def _user_id(self) -> int:
        # noinspection PyTypeChecker
        return self.user.id

    def set_status(self, book_id: int, status_data: UserBookStatusUpdate) -> UserBook:
        """Set or update the acting user's reading status for a book.

        Raises ValueError on any domain-rule violation (illegal transition, a
        future ``occurred_at``, etc.); the router maps these to HTTP 400.
        """
        user_book = ensure_added_event(self.db, user_id=self._user_id, book_id=book_id)
        project_user_book_state(self.db, user_book)

        occurred_at = self._normalize_occurred_at(status_data.occurred_at)
        self._apply_status_transition(user_book, status_data.status, occurred_at)
        self._apply_notes(user_book, status_data)

        project_user_book_state(self.db, user_book)
        self._sync_default_lists(user_book)

        self.db.commit()
        self.db.refresh(user_book)
        return user_book

    def remove_status(self, book_id: int) -> bool:
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
    ) -> UserBook:
        """Record a progress event, requiring an in-progress reading cycle.

        Raises ValueError (mapped to HTTP 400) if the book has not been started.
        """
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book_id)
        if not user_book:
            raise ValueError("Cannot record progress before starting reading")

        project_user_book_state(self.db, user_book)
        if user_book.status != ReadingStatus.STARTED:
            raise ValueError("Cannot record progress before starting reading")

        return apply_progress_event(
            self.db,
            user_book,
            page=progress.page,
            percent=progress.percent,
            max_page=max_page,
        )

    @staticmethod
    def _normalize_occurred_at(occurred_at: datetime | None) -> datetime | None:
        if occurred_at is None:
            return None
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        if occurred_at > datetime.now(UTC):
            raise ValueError("occurred_at cannot be in the future")
        return occurred_at

    def _apply_status_transition(
        self,
        user_book: UserBook,
        target_status: ReadingStatus,
        occurred_at: datetime | None,
    ) -> None:
        user_book_id = user_book.id
        if (
            target_status == ReadingStatus.WANT_TO_READ
            and user_book.status != ReadingStatus.WANT_TO_READ
        ):
            raise ValueError(
                "Cannot revert to 'want_to_read' after reading has started"
            )

        if (
            target_status == ReadingStatus.STARTED
            and user_book.status != ReadingStatus.STARTED
        ):
            record_started_reading(
                self.db, user_book_id=user_book_id, occurred_at=occurred_at
            )
        elif (
            target_status == ReadingStatus.FINISHED
            and user_book.status != ReadingStatus.FINISHED
        ):
            record_finished_reading(
                self.db, user_book_id=user_book_id, occurred_at=occurred_at
            )

    def _apply_notes(
        self, user_book: UserBook, status_data: UserBookStatusUpdate
    ) -> None:
        if "notes" not in status_data.model_fields_set:
            return
        normalized_notes = status_data.notes
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

    def _sync_default_lists(self, user_book: UserBook) -> None:
        """Place the user_book in the list matching its status, removing it from others."""
        user_book_id = user_book.id
        lists_by_name = get_or_create_default_lists(self.db, self._user_id)
        target_list_name = list_name_for_status(user_book.status)
        target_list_id = (
            lists_by_name[target_list_name].id
            if target_list_name in lists_by_name
            else None
        )
        if target_list_id is not None:
            ensure_list_item(self.db, list_id=target_list_id, user_book_id=user_book_id)

        for book_list in lists_by_name.values():
            if book_list.id != target_list_id:
                (
                    self.db.query(BookListItem)
                    .filter(
                        BookListItem.list_id == book_list.id,
                        BookListItem.user_book_id == user_book_id,
                    )
                    .delete()
                )
