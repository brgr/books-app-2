from datetime import datetime, UTC

import pytest
from app.auth import create_user
from app.book_events import (
    record_added_to_library,
    record_finished_reading,
    record_started_reading,
)
from app.models import Book, BookEvent, BookEventCode, BookEventType, UserBook


def _create_user_and_book(db_session):
    user = create_user(db_session, "alice", "secret123")
    book = Book(title="Sample", author="Author")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return user, book


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
        record_started_reading(db_session, user_book.id)  # type: ignore[arg-type]


def test_start_twice_without_finish_is_rejected(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()  # type: ignore[assignment]

    record_started_reading(db_session, user_book_id)
    with pytest.raises(ValueError):
        record_started_reading(db_session, user_book_id)


def test_finish_requires_start(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()  # type: ignore[assignment]

    with pytest.raises(ValueError):
        record_finished_reading(db_session, user_book_id)

    record_started_reading(db_session, user_book_id)
    record_finished_reading(db_session, user_book_id)

    with pytest.raises(ValueError):
        record_finished_reading(db_session, user_book_id)


def test_reread_cycle_allowed(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book_id = db_session.query(UserBook.id).scalar()  # type: ignore[assignment]

    record_started_reading(db_session, user_book_id)
    record_finished_reading(db_session, user_book_id)

    record_started_reading(db_session, user_book_id)
    record_finished_reading(db_session, user_book_id)

    events = db_session.query(BookEvent).all()
    assert len(events) == 5  # add + start/finish twice


def test_cascade_on_user_book_delete(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id)
    user_book = db_session.query(UserBook).first()

    record_started_reading(db_session, user_book.id)
    record_finished_reading(db_session, user_book.id)

    db_session.delete(user_book)
    db_session.flush()

    remaining_events = db_session.query(BookEvent).count()
    assert remaining_events == 0


def test_timeline_ordering(db_session):
    user, book = _create_user_and_book(db_session)
    record_added_to_library(db_session, user.id, book.id, occurred_at=datetime(2024, 1, 1, tzinfo=UTC))
    user_book_id = db_session.query(UserBook.id).scalar()

    record_started_reading(db_session, user_book_id, occurred_at=datetime(2024, 1, 2, tzinfo=UTC))
    record_finished_reading(db_session, user_book_id, occurred_at=datetime(2024, 1, 3, tzinfo=UTC))

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
