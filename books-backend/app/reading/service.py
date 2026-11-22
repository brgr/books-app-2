"""Reading-state operations: the state is the user's reading-shelf placement."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.book_events import (
    apply_progress_event,
    build_user_book_response,
    current_reading_shelf,
    move_reading_shelf_placement,
    project_user_book_state,
    record_finished_reading,
    record_note_event,
    record_rating_event,
    record_reading_event,
    record_started_reading,
)
from app.models import (
    Book,
    BookEvent,
    BookEventCode,
    ReadingDate,
    ReadingShelf,
)
from app.schemas import (
    BookProgressUpdate,
    ReadingDateValue,
    UserBookNotesUpdate,
    UserBookRatingUpdate,
    UserBookResponse,
    UserBookShelfUpdate,
)


class ReadingService:
    def __init__(self, db: Session):
        self.db = db

    # TODO: We should separate the API for reading and custom shelves. For custom shelves, we don't "set" a shelf,
    #  but we add or remove a book from that shelf. For reading, in the API, we might want to talk about
    #  reading state instead; and use a different API endpoint, even though the DB model differs only slightly.
    def set_shelf(
        self, book: Book, shelf_data: UserBookShelfUpdate
    ) -> UserBookResponse:
        previous = current_reading_shelf(self.db, book.id)
        reading_date = self._reading_date_from_input(shelf_data.reading_date)
        self._apply_transition(book, previous, shelf_data.shelf, reading_date)

        if shelf_data.shelf != previous:
            move_reading_shelf_placement(self.db, book, shelf_data.shelf)

        project_user_book_state(self.db, book)
        self.db.commit()
        self.db.refresh(book)

        return build_user_book_response(self.db, book)

    def set_notes(
        self, book: Book, notes_data: UserBookNotesUpdate
    ) -> UserBookResponse:
        notes = notes_data.notes or None
        if notes != book.notes:
            record_note_event(self.db, book.id, BookEventCode.NOTE_SET, notes)
            book.notes = notes

        self.db.commit()
        self.db.refresh(book)

        return build_user_book_response(self.db, book)

    def set_rating(
        self, book: Book, rating_data: UserBookRatingUpdate
    ) -> UserBookResponse:
        if book.rating != rating_data.rating:
            record_rating_event(self.db, book.id, rating_data.rating)
            book.rating = rating_data.rating

        self.db.commit()
        self.db.refresh(book)

        return build_user_book_response(self.db, book)

    def clear_rating(self, book: Book) -> None:
        if book.rating is not None:
            record_rating_event(self.db, book.id, None)
            book.rating = None

        self.db.commit()

    def get_events(self, book: Book) -> list[BookEvent]:
        return (
            self.db.query(BookEvent)
            .options(
                joinedload(BookEvent.note_entry),
                joinedload(BookEvent.rating_entry),
                joinedload(BookEvent.progress_entry),
                joinedload(BookEvent.cover_entry),
                joinedload(BookEvent.import_source),
                joinedload(BookEvent.reading_date_entry),
            )
            .filter(BookEvent.book_id == book.id)
            .order_by(BookEvent.occurred_at.desc(), BookEvent.id.desc())
            .all()
        )

    def add_progress(
        self, book: Book, progress: BookProgressUpdate
    ) -> UserBookResponse:
        if current_reading_shelf(self.db, book.id) != ReadingShelf.STARTED:
            raise ValueError("Cannot record progress before starting reading")

        return build_user_book_response(
            self.db,
            apply_progress_event(
                self.db,
                book,
                page=progress.value if progress.unit == "page" else None,
                percent=progress.value if progress.unit == "percent" else None,
                max_page=book.page_count,
            ),
        )

    # TODO: This will probably change in the future, when we actually support imprecise reading dates in the frontend
    # TODO: Should it really be possible that this is "None"?
    @staticmethod
    def _reading_date_from_input(value: ReadingDateValue | None) -> ReadingDate:
        """Use the requested reading date, defaulting to today's full date."""
        if value is None:
            return ReadingDate.from_datetime(datetime.now(UTC))

        reading_date = value.to_domain()
        if reading_date.value:
            date_value = reading_date.value

            if date_value.tzinfo is None:
                date_value = date_value.replace(tzinfo=UTC)
            if date_value > datetime.now(UTC):
                raise ValueError("reading_date cannot be in the future")

        return reading_date

    def _apply_transition(
        self,
        book: Book,
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
            record_started_reading(self.db, book.id, reading_date)
        elif source == ReadingShelf.STARTED and target == ReadingShelf.PAUSED:
            record_reading_event(self.db, book.id, BookEventCode.PAUSED_READING)
        elif source == ReadingShelf.PAUSED and target == ReadingShelf.STARTED:
            record_reading_event(self.db, book.id, BookEventCode.RESUMED_READING)
        elif source == ReadingShelf.STARTED and target == ReadingShelf.FINISHED:
            record_finished_reading(self.db, book.id, reading_date)
        elif (
            source in {ReadingShelf.STARTED, ReadingShelf.PAUSED}
            and target == ReadingShelf.ABANDONED
        ):
            record_reading_event(self.db, book.id, BookEventCode.ABANDONED_READING)
        elif (
            source in {ReadingShelf.FINISHED, ReadingShelf.ABANDONED}
            and target == ReadingShelf.STARTED
        ):
            record_started_reading(self.db, book.id, reading_date)
        else:
            raise ValueError(f"Cannot move from '{source.value}' to '{target.value}'")
