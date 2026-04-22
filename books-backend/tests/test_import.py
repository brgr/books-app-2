import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import status

from app.models import Book, UserBook, ReadingStatus, BookList, BookListItem

FIXTURES = Path(__file__).parent / "fixtures"


def _make_zip(rows: list[dict], images: dict[str, bytes] | None = None) -> bytes:
    """Build an in-memory ZIP with a data.csv and optional images/ entries."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        csv_buf = io.StringIO()
        fieldnames = [
            "Reading List ID", "Google Books ID", "Apple Books ID",
            "Open Library Edition ID", "ISBN-13", "Title", "Subtitle",
            "Authors", "Page Count", "Publication Date", "Publisher",
            "Description", "Subjects", "Language Code", "Started Reading",
            "Paused", "Finished Reading", "Did Not Finish", "Current Page",
            "Current Percentage", "Rating", "Notes", "Lists",
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
        "/import/reading-list",
        headers=auth_headers,
        files={"file": ("export.zip", zip_bytes, "application/zip")},
    )


# --- Basic import ---


def test_import_creates_books(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {
            "Reading List ID": "AAA",
            "Title": "Test Book",
            "Authors": "Doe, John",
            "ISBN-13": "9781234567890",
            "Page Count": "300",
            "Description": "A great book",
        },
    ])

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
    zip_bytes = _make_zip([
        {"Reading List ID": "AAA", "Title": "Book One", "Authors": "Smith, Jane"},
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.status == ReadingStatus.WANT_TO_READ


# --- Status mapping ---


def test_import_status_finished(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {
            "Reading List ID": "AAA",
            "Title": "Done Book",
            "Authors": "A, B",
            "Started Reading": "2025-01-01",
            "Finished Reading": "2025-02-01",
        },
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.status == ReadingStatus.FINISHED


def test_import_status_abandoned(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {
            "Reading List ID": "AAA",
            "Title": "Gave Up",
            "Authors": "A, B",
            "Did Not Finish": "true",
        },
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.status == ReadingStatus.ABANDONED


def test_import_status_started(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {
            "Reading List ID": "AAA",
            "Title": "Reading Now",
            "Authors": "A, B",
            "Started Reading": "2025-03-01",
        },
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.status == ReadingStatus.STARTED


# --- Notes and progress ---


def test_import_notes_and_current_page(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {
            "Reading List ID": "AAA",
            "Title": "Noted",
            "Authors": "A, B",
            "Notes": "Very insightful",
            "Current Page": "42",
            "Started Reading": "2025-01-01",
        },
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    ub = db_session.query(UserBook).one()
    assert ub.notes == "Very insightful"
    assert ub.current_page == 42


# --- Lists ---


def test_import_creates_lists(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {
            "Reading List ID": "AAA",
            "Title": "Listed Book",
            "Authors": "A, B",
            "Lists": "Sci-Fi (5); Philosophy (3)",
        },
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    lists = db_session.query(BookList).all()
    list_names = {bl.name for bl in lists}
    assert "Sci-Fi" in list_names
    assert "Philosophy" in list_names

    items = db_session.query(BookListItem).all()
    assert len(items) >= 2


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
    zip_bytes = _make_zip([
        {"Reading List ID": "AAA", "Title": "", "Authors": "A, B"},
        {"Reading List ID": "BBB", "Title": "Valid", "Authors": "A, B"},
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["imported"] == 1


def test_import_author_single_name(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {"Reading List ID": "AAA", "Title": "Book", "Authors": "Plato"},
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    book = db_session.query(Book).one()
    assert book.author == "Plato"


def test_import_duplicate_isbn_is_skipped(client, auth_headers, db_session):
    zip_bytes = _make_zip([
        {"Reading List ID": "AAA", "Title": "Book A", "Authors": "A, B", "ISBN-13": "9781234567890"},
        {"Reading List ID": "BBB", "Title": "Book B", "Authors": "C, D", "ISBN-13": "9781234567890"},
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"imported": 1, "skipped": 1}
    assert db_session.query(Book).count() == 1
    assert db_session.query(UserBook).count() == 1


def test_import_started_books_appear_first_in_to_read(client, auth_headers, db_session):
    """STARTED books must sort before WANT_TO_READ ones in the 'To Read' list.

    The frontend filters the visible page for STARTED books to populate the
    'Currently Reading' section. If they're buried on page 20 they disappear.
    """
    rows = []
    for i in range(30):
        rows.append({"Reading List ID": f"Q{i}", "Title": f"Queued {i}", "Authors": "A, B"})
    rows.insert(
        25,
        {
            "Reading List ID": "READING",
            "Title": "Currently Reading Book",
            "Authors": "A, B",
            "Started Reading": "2026-04-01",
        },
    )

    resp = _upload_zip(client, auth_headers, _make_zip(rows))
    assert resp.status_code == status.HTTP_200_OK

    to_read = db_session.query(BookList).filter(BookList.name == "To Read").one()
    items = (
        db_session.query(BookListItem)
        .filter(BookListItem.list_id == to_read.id)
        .order_by(BookListItem.sort_order)
        .all()
    )
    first_title = items[0].user_book.book.title
    assert first_title == "Currently Reading Book"


def test_import_puts_books_in_default_shelves(client, auth_headers, db_session):
    """Imported books must appear in the default 'To Read' / 'Finished' lists.

    The frontend loads the main shelf by querying these lists, so books not in
    them show up as 'No books yet' even though rows exist in user_books.
    """
    zip_bytes = _make_zip([
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
    ])

    resp = _upload_zip(client, auth_headers, zip_bytes)
    assert resp.status_code == status.HTTP_200_OK

    to_read = db_session.query(BookList).filter(BookList.name == "To Read").one()
    finished = db_session.query(BookList).filter(BookList.name == "Finished").one()

    to_read_titles = {
        item.user_book.book.title
        for item in db_session.query(BookListItem).filter(BookListItem.list_id == to_read.id).all()
    }
    finished_titles = {
        item.user_book.book.title
        for item in db_session.query(BookListItem).filter(BookListItem.list_id == finished.id).all()
    }

    assert to_read_titles == {"Queued", "Reading"}
    assert finished_titles == {"Done"}


def test_import_rejects_non_zip(client, auth_headers):
    resp = client.post(
        "/import/reading-list",
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
        1 for r in unique_rows
        if r["Started Reading"] and not r["Finished Reading"] and not r["Did Not Finish"]
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
        db_session.query(UserBook)
        .filter(UserBook.status == ReadingStatus.FINISHED)
        .count()
        == expected_finished
    )
    assert (
        db_session.query(UserBook)
        .filter(UserBook.status == ReadingStatus.STARTED)
        .count()
        == expected_started
    )
    assert (
        db_session.query(UserBook)
        .filter(UserBook.status == ReadingStatus.ABANDONED)
        .count()
        == expected_abandoned
    )
    assert (
        db_session.query(UserBook)
        .filter(UserBook.notes.isnot(None))
        .count()
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
        .filter(UserBook.status == ReadingStatus.STARTED)
        .all()
    )

    titles_by_author = {book.title: ub for book, ub in started}
    assert set(titles_by_author) == {
        "Der Ekel",
        "UNIX and Linux System Administration Handbook, 5/e",
    }

    ekel = next(ub for book, ub in started if book.title == "Der Ekel")
    assert ekel.started_at == datetime(2026, 4, 13)

    unix = next(
        ub for book, ub in started
        if book.title == "UNIX and Linux System Administration Handbook, 5/e"
    )
    assert unix.started_at == datetime(2026, 4, 18)


def test_import_real_export_creates_lists(client, auth_headers, db_session):
    """The real export includes named lists that should become BookList rows.

    Lists from rows whose ISBN duplicates an earlier row are dropped, since the
    whole row is skipped.
    """
    csv_path = FIXTURES / "reading_list_sample.csv"
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))

    import re

    def _list_names(row: dict) -> set[str]:
        return {
            re.sub(r"\s*\(\d+\)\s*$", "", seg).strip()
            for seg in (row["Lists"] or "").split(";")
            if seg.strip()
        }

    seen_isbns: set[str] = set()
    expected_lists: set[str] = set()
    for row in rows:
        isbn = row["ISBN-13"].strip()
        if isbn and isbn in seen_isbns:
            continue
        if isbn:
            seen_isbns.add(isbn)
        expected_lists |= _list_names(row)

    resp = _upload_zip(client, auth_headers, _zip_from_csv(csv_path))
    assert resp.status_code == status.HTTP_200_OK

    created = {bl.name for bl in db_session.query(BookList).all()}
    assert expected_lists == created - {"To Read", "Finished"}
    assert len(expected_lists) > 5  # sanity check against empty match
