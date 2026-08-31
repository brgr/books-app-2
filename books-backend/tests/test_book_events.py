from datetime import datetime, UTC

import pytest
from app.auth.security import create_user
from app.book_events import (
    record_added_to_library,
    record_finished_reading,
    record_started_reading,
    derive_reading_date_values,
)
from app.models import (
    Book,
    BookEvent,
    BookEventCode,
    BookEventType,
    ReadingDate,
    ReadingDatePrecision,
    UserBook,
)


def _create_user_and_book(db_session):
    user = create_user(db_session, "alice", "secret123")
    book = Book(title="Sample", author="Author")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return user, book


def _today() -> ReadingDate:
    return ReadingDate.from_datetime(datetime.now(UTC))


def test_event_type_seeding_is_idempotent(db_session):
    codes = {code for (code,) in db_session.query(BookEventType.code).all()}
    assert codes == {c.value for c in BookEventCode}


def test_added_to_library_only_once(db_session):
    user, book = _create_user_and_book(db_session)

    first_event = record_added_to_library(db_session, user.id, book.id)
    assert first_event.event_type.code == BookEventCode.ADDED_TO_LIBRARY.value

    with pytest.raises(ValueError):
        record_added_to_library(db_session, user.id, book.id)

    count = db_session.query(BookEvent).count()
    assert count == 1


def test_start_requires_add(db_session):
    user, book = _create_user_and_book(db_session)
    user_book = UserBook(user_id=user.id, book_id=book.id)
    db_session.add(user_book)
    db_session.flush()

    with pytest.raises(ValueError):
        record_started_reading(db_session, user_book.id, _today())  # type: ignore[arg-type]


def test_start_twice_without_finish_is_rejected(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()  # type: ignore[assignment]

    record_started_reading(db_session, user_book_id, _today())
    with pytest.raises(ValueError):
        record_started_reading(db_session, user_book_id, _today())


def test_finish_requires_start(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()  # type: ignore[assignment]

    with pytest.raises(ValueError):
        record_finished_reading(db_session, user_book_id, _today())

    record_started_reading(db_session, user_book_id, _today())
    record_finished_reading(db_session, user_book_id, _today())

    with pytest.raises(ValueError):
        record_finished_reading(db_session, user_book_id, _today())


def test_reread_cycle_allowed(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()  # type: ignore[assignment]

    record_started_reading(db_session, user_book_id, _today())
    record_finished_reading(db_session, user_book_id, _today())

    record_started_reading(db_session, user_book_id, _today())
    record_finished_reading(db_session, user_book_id, _today())

    events = db_session.query(BookEvent).all()
    assert len(events) == 5  # add + start/finish twice


def test_cascade_on_user_book_delete(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book = db_session.query(UserBook).first()

    record_started_reading(db_session, user_book.id, _today())
    record_finished_reading(db_session, user_book.id, _today())

    db_session.delete(user_book)
    db_session.flush()

    remaining_events = db_session.query(BookEvent).count()
    assert remaining_events == 0


def test_timeline_ordering(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(
        db_session, user.id, book.id, occurred_at=datetime(2024, 1, 1, tzinfo=UTC)
    )
    user_book_id = db_session.query(UserBook.id).scalar()

    record_started_reading(
        db_session,
        user_book_id,
        ReadingDate.from_datetime(datetime(2024, 1, 2, tzinfo=UTC)),
    )
    record_finished_reading(
        db_session,
        user_book_id,
        ReadingDate.from_datetime(datetime(2024, 1, 3, tzinfo=UTC)),
    )

    ordered = (
        db_session.query(BookEvent)
        .order_by(BookEvent.occurred_at.desc(), BookEvent.id.desc())
        .all()
    )
    assert [e.event_type.code for e in ordered] == [
        BookEventCode.FINISHED_READING.value,
        BookEventCode.STARTED_READING.value,
        BookEventCode.ADDED_TO_LIBRARY.value,
    ]


def test_reading_date_normalizes_partial_calendar_values():
    assert ReadingDate(
        datetime(2026, 4, 18, 14, 30), ReadingDatePrecision.DAY
    ).value == datetime(2026, 4, 18)
    assert ReadingDate(
        datetime(2026, 4, 18), ReadingDatePrecision.MONTH
    ).value == datetime(2026, 4, 1)
    assert ReadingDate(
        datetime(2026, 4, 18), ReadingDatePrecision.YEAR
    ).value == datetime(2026, 1, 1)
    assert ReadingDate.unknown().value is None


def test_reading_events_persist_partial_and_unknown_dates(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()

    start_event = record_started_reading(
        db_session,
        user_book_id,
        reading_date=ReadingDate(datetime(2026, 4, 18), ReadingDatePrecision.MONTH),
    )
    finish_event = record_finished_reading(
        db_session, user_book_id, reading_date=ReadingDate.unknown()
    )

    started, finished = derive_reading_date_values(db_session, user_book_id)
    assert started == ReadingDate(datetime(2026, 4, 1), ReadingDatePrecision.MONTH)
    assert finished == ReadingDate.unknown()
    assert start_event.occurred_at.date() == datetime.now(UTC).date()
    assert finish_event.occurred_at.date() == datetime.now(UTC).date()


def test_missing_reading_date_payload_is_a_data_integrity_error(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()
    event = record_started_reading(db_session, user_book_id, _today())

    db_session.delete(event.reading_date_entry)
    db_session.flush()
    db_session.expire_all()

    with pytest.raises(RuntimeError, match="no reading-date payload"):
        derive_reading_date_values(db_session, user_book_id)
