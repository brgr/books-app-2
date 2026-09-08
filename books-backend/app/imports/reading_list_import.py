import csv
import io
import re
import zipfile
from datetime import datetime

from sqlalchemy.orm import Session

from app.book_events import (
    ensure_added_event,
    move_reading_shelf_placement,
    project_user_book_state,
    record_finished_reading,
    record_progress_event,
    record_rating_event,
    record_reading_event,
    record_started_reading,
)
from app.covers.image_utils import store_cover_image
from app.models import (
    Book,
    BookEventCode,
    Import,
    ReadingDate,
    ReadingDatePrecision,
    ReadingShelf,
    Shelf,
    ShelfKind,
    UserBook,
)
from app.shelves.shelves import place_on_shelf


class ImportReadingListError(ValueError):
    """Raised when the import payload is structurally invalid."""


def _parse_author(raw: str) -> str:
    """Convert 'Last, First' to 'First Last'. Pass through single names."""
    if "," in raw:
        parts = raw.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return raw.strip()


def _derive_shelf(row: dict) -> ReadingShelf:
    if row.get("Did Not Finish"):
        return ReadingShelf.ABANDONED
    if row.get("Finished Reading"):
        return ReadingShelf.FINISHED
    if row.get("Paused"):
        return ReadingShelf.PAUSED
    if row.get("Started Reading"):
        return ReadingShelf.STARTED
    return ReadingShelf.WANT_TO_READ


def _parse_date(val: str) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d")
    except ValueError:
        return None


def _reading_date_or_unknown(value: datetime | None) -> ReadingDate:
    if value is None:
        return ReadingDate.unknown()
    return ReadingDate.from_datetime(value)


def _parse_reading_date(value: str) -> ReadingDate:
    """Parse Reading List dates while retaining their stated precision."""
    value = value.strip()

    if not value or value == "Unknown":
        return ReadingDate.unknown()

    for fmt, precision in (
        ("%Y-%m-%d", ReadingDatePrecision.DAY),
        ("%Y-%m", ReadingDatePrecision.MONTH),
        ("%Y", ReadingDatePrecision.YEAR),
    ):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue

        return ReadingDate(parsed, precision)

    return ReadingDate.unknown()


def _import_lists(db: Session, user_book: UserBook, raw: str) -> None:
    for entry in raw.split(";"):
        # Entries end with a signed list position; parentheses can also be
        # part of the name, e.g. "Short Book (< ~200 Pages) (31)".
        name = re.sub(r"\s+\(-?\d+\)$", "", entry.strip()).strip()

        if not name:
            continue

        shelf = (
            db.query(Shelf)
            .filter_by(user_id=user_book.user_id, kind=ShelfKind.CUSTOM, name=name)
            .first()
        )

        if shelf is None:
            shelf = Shelf(user_id=user_book.user_id, kind=ShelfKind.CUSTOM, name=name)
            db.add(shelf)
            db.flush()

        place_on_shelf(db, shelf, user_book)


def import_reading_list_from_bytes(
    db: Session, user_id: int, content: bytes, filename: str | None = None
) -> dict[str, int]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ImportReadingListError("Uploaded file is not a valid ZIP") from exc

    try:
        csv_data = zf.read("data.csv").decode("utf-8")
    except KeyError as exc:
        raise ImportReadingListError("ZIP does not contain data.csv") from exc

    image_names = {
        n.split("/")[-1]
        for n in zf.namelist()
        if n.startswith("images/") and "/" in n and n != "images/"
    }

    rows = list(csv.DictReader(io.StringIO(csv_data)))
    import_record = Import(user_id=user_id, filename=filename)
    db.add(import_record)
    db.flush()
    import_id = import_record.id
    imported = 0
    skipped = 0

    for row in rows:
        title = (row.get("Title") or "").strip()
        if not title:
            continue

        author = _parse_author(row.get("Authors") or "Unknown")
        isbn = (row.get("ISBN-13") or "").strip() or None
        description = (row.get("Description") or "").strip() or None
        page_count_raw = (row.get("Page Count") or "").strip()
        page_count = int(page_count_raw) if page_count_raw else None
        pub_date = _parse_date((row.get("Publication Date") or "").strip())

        book = None
        if isbn:
            book = db.query(Book).filter(Book.isbn == isbn).first()
        if book is not None:
            already_in_library = (
                db.query(UserBook)
                .filter(UserBook.user_id == user_id, UserBook.book_id == book.id)
                .first()
            )
            if already_in_library:
                _import_lists(db, already_in_library, row.get("Lists") or "")
                skipped += 1
                continue
        else:
            book = Book(
                title=title,
                author=author,
                isbn=isbn,
                description=description,
                page_count=page_count,
                published_date=pub_date,
            )
            db.add(book)
            db.flush()

        reading_list_id = (row.get("Reading List ID") or "").strip()
        if reading_list_id:
            for img_name in image_names:
                if img_name.startswith(reading_list_id):
                    try:
                        img_data = zf.read(f"images/{img_name}")
                        ext = img_name.rsplit(".", 1)[-1] if "." in img_name else None
                        cover_url, thumbnail_url = store_cover_image(img_data, ext)
                        book.cover_image_url = cover_url
                        book.cover_thumbnail_url = thumbnail_url
                    except Exception:
                        pass
                    break

        book_id = book.id
        existing_ub = (
            db.query(UserBook)
            .filter(UserBook.user_id == user_id, UserBook.book_id == book_id)
            .first()
        )
        if existing_ub:
            _import_lists(db, existing_ub, row.get("Lists") or "")
            imported += 1
            continue

        derived_shelf = _derive_shelf(row)
        started_at = _parse_reading_date(row.get("Started Reading") or "")
        paused_at = _parse_date((row.get("Paused") or "").strip())
        finished_at = _parse_reading_date(row.get("Finished Reading") or "")
        notes = (row.get("Notes") or "").strip() or None
        rating_raw = (row.get("Rating") or "").strip()
        rating = float(rating_raw) if rating_raw else None
        current_page_raw = (row.get("Current Page") or "").strip()
        current_page = int(current_page_raw) if current_page_raw else None
        current_percent_raw = (row.get("Current Percentage") or "").strip()
        current_percent = float(current_percent_raw) if current_percent_raw else None

        user_book = UserBook(
            user_id=user_id,
            book_id=book_id,
            notes=notes,
            rating=rating,
            current_page=current_page,
            current_percent=current_percent,
        )
        db.add(user_book)
        db.flush()

        ensure_added_event(db, user_id=user_id, book_id=book_id, import_id=import_id)
        if derived_shelf in (
            ReadingShelf.STARTED,
            ReadingShelf.PAUSED,
            ReadingShelf.FINISHED,
            ReadingShelf.ABANDONED,
        ):
            record_started_reading(
                db,
                user_book_id=user_book.id,
                reading_date=started_at,
            )
        if derived_shelf == ReadingShelf.PAUSED:
            record_reading_event(
                db,
                user_book.id,
                BookEventCode.PAUSED_READING,
                occurred_at=paused_at,
            )
        if derived_shelf == ReadingShelf.FINISHED:
            record_finished_reading(
                db,
                user_book_id=user_book.id,
                reading_date=finished_at,
            )
        if derived_shelf == ReadingShelf.ABANDONED:
            record_reading_event(db, user_book.id, BookEventCode.ABANDONED_READING)
        if current_page is not None:
            record_progress_event(
                db,
                user_book.id,
                page=current_page,
                percent=current_percent,
            )
        elif current_percent is not None:
            record_progress_event(db, user_book.id, percent=current_percent)
        if rating is not None:
            record_rating_event(db, user_book.id, rating=rating, import_id=import_id)

        move_reading_shelf_placement(db, user_book, derived_shelf)
        project_user_book_state(db, user_book)

        _import_lists(db, user_book, row.get("Lists") or "")

        imported += 1

    import_record.imported_count = imported
    import_record.skipped_count = skipped
    db.commit()
    return {"imported": imported, "skipped": skipped}
