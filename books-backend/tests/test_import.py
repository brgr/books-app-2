import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import status

from app.book_events import derive_reading_dates
from app.models import (
    Book,
    BookEvent,
    BookEventCode,
    BookEventImportSource,
    BookEventType,
    Import,
    Shelf,
    ShelfName,
    UserBook,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _make_zip(rows: list[dict], images: dict[str, bytes] | None = None) -> bytes:
    """Build an in-memory ZIP with a data.csv and optional images/ entries."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        csv_buf = io.StringIO()
        fieldnames = [
            "Reading List ID",
            "Google Books ID",
            "Apple Books ID",
            "Open Library Edition ID",
            "ISBN-13",
            "Title",
            "Subtitle",
            "Authors",
            "Page Count",
            "Publication Date",
            "Publisher",
            "Description",
            "Subjects",
            "Language Code",
            "Started Reading",
            "Paused",
            "Finished Reading",
            "Did Not Finish",
            "Current Page",
            "Current Percentage",
            "Rating",
            "Notes",
            "Lists",
        ]
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            full_row = {f: "" for f in fieldnames}
            full_row.update(row)
            writer.writerow(full_row)
        zf.writestr("data.csv", csv_buf.getvalue())

        if images:
            for name, content in images.items():
                zf.writestr(f"images/{name}", content)
    return buf.getvalue()


def _upload_zip(client, auth_headers, zip_bytes: bytes):
    return client.post(
        "/api/import/reading-list",
        headers=auth_headers,
        files={"file": ("export.zip", zip_bytes, "application/zip")},
    )


# --- Basic import ---


def test_import_creates_books(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {
                "Reading List ID": "AAA",
                "Title": "Test Book",
                "Authors": "Doe, John",
                "ISBN-13": "9781234567890",
                "Page Count": "300",
                "Description": "A great book",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["imported"] == 1

    book = db_session.query(Book).one()
    assert book.title == "Test Book"
    assert book.author == "John Doe"
    assert book.isbn == "9781234567890"
    assert book.page_count == 300
    assert book.description == "A great book"


def test_import_creates_user_book(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {"Reading List ID": "AAA", "Title": "Book One", "Authors": "Smith, Jane"},
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.shelf == ShelfName.WANT_TO_READ


# --- Status mapping ---


def test_import_status_finished(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {
                "Reading List ID": "AAA",
                "Title": "Done Book",
                "Authors": "A, B",
                "Started Reading": "2025-01-01",
                "Finished Reading": "2025-02-01",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.shelf == ShelfName.FINISHED


def test_import_status_abandoned(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {
                "Reading List ID": "AAA",
                "Title": "Gave Up",
                "Authors": "A, B",
                "Did Not Finish": "true",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.shelf == ShelfName.ABANDONED


def test_import_status_started(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {
                "Reading List ID": "AAA",
                "Title": "Reading Now",
                "Authors": "A, B",
                "Started Reading": "2025-03-01",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.shelf == ShelfName.STARTED


# --- Notes and progress ---


def test_import_notes_and_current_page(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {
                "Reading List ID": "AAA",
                "Title": "Noted",
                "Authors": "A, B",
                "Notes": "Very insightful",
                "Current Page": "42",
                "Started Reading": "2025-01-01",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.notes == "Very insightful"
    assert ub.current_page == 42


# --- Cover images ---


def test_import_cover_image(client, auth_headers, db_session):
    from PIL import Image

    img_buf = io.BytesIO()
    Image.new("RGB", (100, 150), color="red").save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    zip_bytes = _make_zip(
        [{"Reading List ID": "COVER-ID", "Title": "With Cover", "Authors": "A, B"}],
        images={"COVER-ID.png": img_bytes},
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    book = db_session.query(Book).one()
    assert book.cover_image_url is not None
    assert "covers" in book.cover_image_url


# --- Multiple books ---


def test_import_multiple_books(client, auth_headers, db_session):
    rows = [
        {"Reading List ID": f"ID-{i}", "Title": f"Book {i}", "Authors": "A, B"}
        for i in range(5)
    ]
    zip_bytes = _make_zip(rows)

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["imported"] == 5
    assert db_session.query(Book).count() == 5


# --- Edge cases ---


def test_import_skips_books_without_title(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {"Reading List ID": "AAA", "Title": "", "Authors": "A, B"},
            {"Reading List ID": "BBB", "Title": "Valid", "Authors": "A, B"},
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["imported"] == 1


def test_import_author_single_name(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {"Reading List ID": "AAA", "Title": "Book", "Authors": "Plato"},
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    book = db_session.query(Book).one()
    assert book.author == "Plato"


def test_import_duplicate_isbn_is_skipped(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {
                "Reading List ID": "AAA",
                "Title": "Book A",
                "Authors": "A, B",
                "ISBN-13": "9781234567890",
            },
            {
                "Reading List ID": "BBB",
                "Title": "Book B",
                "Authors": "C, D",
                "ISBN-13": "9781234567890",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"imported": 1, "skipped": 1}
    assert db_session.query(Book).count() == 1
    assert db_session.query(UserBook).count() == 1


def test_import_puts_books_in_default_shelves(client, auth_headers, db_session):
    """Imported books must appear on the default built-in shelves.

    The frontend loads the main shelf by querying these shelves, so books not on
    them show up as 'No books yet' even though rows exist in user_books.
    """
    zip_bytes = _make_zip(
        [
            {"Reading List ID": "A1", "Title": "Queued", "Authors": "A, B"},
            {
                "Reading List ID": "A2",
                "Title": "Reading",
                "Authors": "A, B",
                "Started Reading": "2026-04-01",
            },
            {
                "Reading List ID": "A3",
                "Title": "Done",
                "Authors": "A, B",
                "Started Reading": "2026-03-01",
                "Finished Reading": "2026-04-01",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    def titles_on(shelf: ShelfName) -> set[str]:
        return {
            book.title
            for book in db_session.query(Book)
            .join(UserBook, UserBook.book_id == Book.id)
            .filter(UserBook.shelf == shelf)
            .all()
        }

    assert titles_on(ShelfName.WANT_TO_READ) == {"Queued"}
    assert titles_on(ShelfName.STARTED) == {"Reading"}
    assert titles_on(ShelfName.FINISHED) == {"Done"}


# --- Import provenance ---


def test_import_creates_import_record(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {"Reading List ID": "AAA", "Title": "Book One", "Authors": "A, B"},
            {"Reading List ID": "BBB", "Title": "Book Two", "Authors": "C, D"},
        ]
    )

    resp = client.post(
        "/api/import/reading-list",
        headers=auth_headers,
        files={"file": ("my-export.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == status.HTTP_200_OK

    imports = db_session.query(Import).all()
    assert len(imports) == 1
    imp = imports[0]
    assert imp.filename == "my-export.zip"
    assert imp.imported_count == 2
    assert imp.skipped_count == 0
    assert imp.occurred_at is not None


def test_import_links_added_events_to_import(client, auth_headers, db_session):
    zip_bytes = _make_zip(
        [
            {"Reading List ID": "AAA", "Title": "Book One", "Authors": "A, B"},
            {"Reading List ID": "BBB", "Title": "Book Two", "Authors": "C, D"},
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    imp = db_session.query(Import).one()
    add_events = (
        db_session.query(BookEvent)
        .join(BookEventType, BookEvent.event_type_id == BookEventType.id)
        .filter(BookEventType.code == BookEventCode.ADDED_TO_LIBRARY.value)
        .all()
    )
    assert len(add_events) == 2
    for event in add_events:
        source = (
            db_session.query(BookEventImportSource)
            .filter(BookEventImportSource.event_id == event.id)
            .one()
        )
        assert source.import_id == imp.id


def test_import_does_not_link_started_or_finished_events(
    client, auth_headers, db_session
):
    """Only added_to_library events carry the import provenance."""
    zip_bytes = _make_zip(
        [
            {
                "Reading List ID": "AAA",
                "Title": "Done",
                "Authors": "A, B",
                "Started Reading": "2025-01-01",
                "Finished Reading": "2025-02-01",
            },
        ]
    )

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    non_add_events = (
        db_session.query(BookEvent)
        .join(BookEventType, BookEvent.event_type_id == BookEventType.id)
        .filter(BookEventType.code != BookEventCode.ADDED_TO_LIBRARY.value)
        .all()
    )
    assert len(non_add_events) >= 2
    for event in non_add_events:
        source = (
            db_session.query(BookEventImportSource)
            .filter(BookEventImportSource.event_id == event.id)
            .first()
        )
        assert source is None


def test_import_rejects_non_zip(client, auth_headers):
    resp = client.post(
        "/api/import/reading-list",
        headers=auth_headers,
        files={"file": ("export.txt", b"not a zip", "text/plain")},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --- Regression tests against real Reading List export ---


def _zip_from_csv(csv_path: Path) -> bytes:
    """Wrap a CSV file into a ZIP in the Reading List export format."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.csv", csv_path.read_bytes())
    return buf.getvalue()


def test_import_real_export_counts_match_csv(client, auth_headers, db_session):
    """Import the full real export and verify counts/statuses match the CSV."""
    csv_path = FIXTURES / "reading_list_sample.csv"
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))

    # Some rows share an ISBN (same book listed twice); they should be deduped.
    seen_isbns: set[str] = set()
    unique_rows: list[dict] = []
    skipped_duplicates = 0
    for r in rows:
        isbn = r["ISBN-13"].strip()
        if isbn and isbn in seen_isbns:
            skipped_duplicates += 1
            continue
        if isbn:
            seen_isbns.add(isbn)
        unique_rows.append(r)

    expected_imported = len(unique_rows)
    expected_finished = sum(1 for r in unique_rows if r["Finished Reading"])
    expected_started = sum(
        1
        for r in unique_rows
        if r["Started Reading"]
        and not r["Finished Reading"]
        and not r["Did Not Finish"]
    )
    expected_abandoned = sum(
        1 for r in unique_rows if r["Did Not Finish"] and not r["Finished Reading"]
    )
    expected_with_notes = sum(1 for r in unique_rows if r["Notes"])

    resp = _upload_zip(client, auth_headers, _zip_from_csv(csv_path))
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["imported"] == expected_imported
    assert body["skipped"] == skipped_duplicates

    assert db_session.query(Book).count() == expected_imported
    assert db_session.query(UserBook).count() == expected_imported

    assert (
        db_session.query(UserBook).filter(UserBook.shelf == ShelfName.FINISHED).count()
        == expected_finished
    )
    assert (
        db_session.query(UserBook).filter(UserBook.shelf == ShelfName.STARTED).count()
        == expected_started
    )
    assert (
        db_session.query(UserBook).filter(UserBook.shelf == ShelfName.ABANDONED).count()
        == expected_abandoned
    )
    assert (
        db_session.query(UserBook).filter(UserBook.notes.isnot(None)).count()
        == expected_with_notes
    )


def test_import_real_export_parses_known_book(client, auth_headers, db_session):
    """Spot-check a well-known book from the real export."""
    csv_path = FIXTURES / "reading_list_sample.csv"
    resp = _upload_zip(client, auth_headers, _zip_from_csv(csv_path))
    assert resp.status_code == status.HTTP_200_OK

    book = db_session.query(Book).filter(Book.title == "Das Orangenmädchen").one()
    assert book.author == "Jostein Gaarder"
    assert book.isbn == "9783423133968"
    assert book.page_count == 187


def test_import_real_export_currently_reading(client, auth_headers, db_session):
    """The two books currently being read in the real export should import as STARTED."""
    csv_path = FIXTURES / "reading_list_sample.csv"
    resp = _upload_zip(client, auth_headers, _zip_from_csv(csv_path))
    assert resp.status_code == status.HTTP_200_OK

    started = (
        db_session.query(Book, UserBook)
        .join(UserBook, UserBook.book_id == Book.id)
        .filter(UserBook.shelf == ShelfName.STARTED)
        .all()
    )

    titles_by_author = {book.title: ub for book, ub in started}
    assert set(titles_by_author) == {
        "Der Ekel",
        "UNIX and Linux System Administration Handbook, 5/e",
    }

    # started_at is now derived from the event stream, not a stored column.
    ekel = next(ub for book, ub in started if book.title == "Der Ekel")
    assert derive_reading_dates(db_session, ekel.id)[0] == datetime(2026, 4, 13)

    unix = next(
        ub
        for book, ub in started
        if book.title == "UNIX and Linux System Administration Handbook, 5/e"
    )
    assert derive_reading_dates(db_session, unix.id)[0] == datetime(2026, 4, 18)


def test_import_real_export_creates_no_custom_shelves(client, auth_headers, db_session):
    """The real export names many lists; none of them become shelves."""
    csv_path = FIXTURES / "reading_list_sample.csv"
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))

    named_in_export = {row["Lists"].strip() for row in rows if row["Lists"].strip()}
    assert len(named_in_export) > 5  # sanity check: the fixture does name lists

    resp = _upload_zip(client, auth_headers, _zip_from_csv(csv_path))
    assert resp.status_code == status.HTTP_200_OK

    assert db_session.query(Shelf).count() == 0

    # Every imported book still got a position (sort_order) on the shelf its status puts it on.
    positions = [ub.sort_order for ub in db_session.query(UserBook).all()]
    assert positions and all(position is not None for position in positions)
