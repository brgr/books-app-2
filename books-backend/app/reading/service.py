"""Reading-state operations: the state is the user's reading-shelf placement."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.book_events import (
    apply_progress_event,
    build_user_book_response,
    current_reading_shelf,
    ensure_added_event,
    move_reading_shelf_placement,
    project_user_book_state,
    record_finished_reading,
    record_note_event,
    record_reading_event,
    record_started_reading,
)
from app.books.queries import get_user_book
from app.models import (
    BookEvent,
    BookEventCode,
    ReadingDate,
    ReadingShelf,
    User,
    UserBook,
)
from app.schemas import BookProgressUpdate, UserBookResponse, UserBookShelfUpdate


class ReadingService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    @property
    def _user_id(self) -> int:
        return self.user.id

    # TODO: We should separate the API for reading and custom shelves. For custom shelves, we don't "set" a shelf,
    #  but we add or remove a book from that shelf. For reading, in the API, we might want to talk about
    #  reading state instead; and use a different API endpoint, even though the DB model differs only slightly.
    def set_shelf(
        self, book_id: int, shelf_data: UserBookShelfUpdate
    ) -> UserBookResponse:
        user_book = ensure_added_event(self.db, self._user_id, book_id)
        previous = current_reading_shelf(self.db, user_book.id)
        reading_date = self._reading_date_from_legacy_input(shelf_data.occurred_at)
        self._apply_transition(user_book, previous, shelf_data.shelf, reading_date)
        self._apply_notes(user_book, shelf_data)

        if shelf_data.shelf != previous:
            move_reading_shelf_placement(self.db, user_book, shelf_data.shelf)

        project_user_book_state(self.db, user_book)
        self.db.commit()
        self.db.refresh(user_book)

        return build_user_book_response(self.db, user_book)

    def remove_from_library(self, book_id: int) -> bool:
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book_id)
        if not user_book:
            return False

        self.db.delete(user_book)
        self.db.commit()
        return True

    def get_events(self, book_id: int) -> list[BookEvent]:
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book_id)
        if not user_book:
            return []

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
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book_id)

        if (
            not user_book
            or current_reading_shelf(self.db, user_book.id) != ReadingShelf.STARTED
        ):
            raise ValueError("Cannot record progress before starting reading")

        return build_user_book_response(
            self.db,
            apply_progress_event(
                self.db,
                user_book,
                page=progress.page,
                percent=progress.percent,
                max_page=max_page,
            ),
        )

    # TODO: Adapt this once we change the API accordingly. Also, we shouldn't even expect a None, then.
    @staticmethod
    def _reading_date_from_legacy_input(value: datetime | None) -> ReadingDate:
        """Adapt the current API's date field to the reading-date domain.

        The API still calls this field ``occurred_at``. Until the API is changed,
        it denotes the user-stated reading date, not the timestamp of
        the state-change event.
        """
        if value is None:
            return ReadingDate.from_datetime(datetime.now(UTC))
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        if value > datetime.now(UTC):
            raise ValueError("occurred_at cannot be in the future")
        return ReadingDate.from_datetime(value)

    def _apply_transition(
        self,
        user_book: UserBook,
        source: ReadingShelf,
        target: ReadingShelf,
        reading_date: ReadingDate,
    ) -> None:
        if target == source:
            return
        if target == ReadingShelf.WANT_TO_READ:
            raise ValueError(
                "Cannot revert to 'want_to_read' after reading has started"
            )

        if source == ReadingShelf.WANT_TO_READ and target == ReadingShelf.FINISHED:
            raise ValueError("Cannot finish reading before starting")

        if source == ReadingShelf.WANT_TO_READ and target == ReadingShelf.STARTED:
            record_started_reading(self.db, user_book.id, reading_date)
        elif source == ReadingShelf.STARTED and target == ReadingShelf.PAUSED:
            record_reading_event(self.db, user_book.id, BookEventCode.PAUSED_READING)
        elif source == ReadingShelf.PAUSED and target == ReadingShelf.STARTED:
            record_reading_event(self.db, user_book.id, BookEventCode.RESUMED_READING)
        elif source == ReadingShelf.STARTED and target == ReadingShelf.FINISHED:
            record_finished_reading(self.db, user_book.id, reading_date)
        elif (
            source in {ReadingShelf.STARTED, ReadingShelf.PAUSED}
            and target == ReadingShelf.ABANDONED
        ):
            record_reading_event(self.db, user_book.id, BookEventCode.ABANDONED_READING)
        elif (
            source in {ReadingShelf.FINISHED, ReadingShelf.ABANDONED}
            and target == ReadingShelf.STARTED
        ):
            record_started_reading(self.db, user_book.id, reading_date)
        else:
            raise ValueError(f"Cannot move from '{source.value}' to '{target.value}'")

    def _apply_notes(self, user_book: UserBook, data: UserBookShelfUpdate) -> None:
        if "notes" not in data.model_fields_set:
            return
        note = data.notes or None
        if note != user_book.notes:
            record_note_event(self.db, user_book.id, BookEventCode.NOTE_SET, note)
            user_book.notes = note
