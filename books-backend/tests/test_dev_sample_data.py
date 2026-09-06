import pytest

from app.book_events import current_reading_shelf, derive_reading_date_values
from app.models import (
    Book,
    BookEvent,
    BookEventImportSource,
    Import,
    ReadingShelf,
    User,
    UserBook,
)
from scripts.dev_with_sample_data import build_parser
from scripts.sample_books import create_sample_books


def test_add_900_books_preserves_existing_library(db_session, test_user):
    user = db_session.query(User).one()
    create_sample_books(db_session, user.id, 1, ReadingShelf.FINISHED)
    db_session.commit()
    original = db_session.query(UserBook).one()
    original_id = original.id

    create_sample_books(db_session, user.id, 900, ReadingShelf.WANT_TO_READ)
    db_session.commit()

    assert db_session.query(Import).count() == 0
    assert db_session.query(BookEventImportSource).count() == 0
    assert db_session.query(BookEvent).count() == 903
    assert db_session.query(Book).count() == 901
    assert current_reading_shelf(db_session, original_id) == ReadingShelf.FINISHED
    added = db_session.query(UserBook).filter(UserBook.id != original_id).all()
    assert len(added) == 900
    assert all(
        current_reading_shelf(db_session, book.id) == ReadingShelf.WANT_TO_READ
        for book in added
    )


@pytest.mark.parametrize("shelf", list(ReadingShelf))
def test_generated_books_have_consistent_reading_state(db_session, test_user, shelf):
    user = db_session.query(User).one()
    create_sample_books(db_session, user.id, 2, shelf)
    db_session.commit()

    for book in db_session.query(UserBook).all():
        assert current_reading_shelf(db_session, book.id) == shelf
        started, finished = derive_reading_date_values(db_session, book.id)
        assert (started is not None) == (shelf != ReadingShelf.WANT_TO_READ)
        assert (finished is not None) == (shelf == ReadingShelf.FINISHED)


def test_negative_count_rejected():
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--sample-books", "-1"])
    assert exc.value.code == 2
