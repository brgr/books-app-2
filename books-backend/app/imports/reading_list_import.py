import csv
import io
import zipfile
from datetime import datetime

from sqlalchemy.orm import Session

from app.book_events import (
    ensure_added_event,
    record_finished_reading,
    record_started_reading,
)
from app.image_utils import store_cover_image
from app.models import Book, Import, ShelfName, UserBook
from app.shelves.shelves import ensure_shelf_position


class ImportReadingListError(ValueError):
    """Raised when the import payload is structurally invalid."""


def _parse_author(raw: str) -> str:
    """Convert 'Last, First' to 'First Last'. Pass through single names."""
    if "," in raw:
        parts = raw.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return raw.strip()


def _derive_shelf(row: dict) -> ShelfName:
    if row.get("Finished Reading"):
        return ShelfName.FINISHED
    if row.get("Did Not Finish"):
        return ShelfName.ABANDONED
    if row.get("Started Reading"):
        return ShelfName.STARTED
    return ShelfName.WANT_TO_READ


def _parse_date(val: str) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d")
    except ValueError:
        return None


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
            imported += 1
            continue

        derived_shelf = _derive_shelf(row)
        started_at = _parse_date((row.get("Started Reading") or "").strip())
        finished_at = _parse_date((row.get("Finished Reading") or "").strip())
        notes = (row.get("Notes") or "").strip() or None
        current_page_raw = (row.get("Current Page") or "").strip()
        current_page = int(current_page_raw) if current_page_raw else None

        user_book = UserBook(
            user_id=user_id,
            book_id=book_id,
            shelf=derived_shelf,
            notes=notes,
            current_page=current_page,
        )
        db.add(user_book)
        db.flush()

        ensure_added_event(db, user_id=user_id, book_id=book_id, import_id=import_id)
        if derived_shelf in (ShelfName.STARTED, ShelfName.FINISHED):
            record_started_reading(
                db,
                user_book_id=user_book.id,
                occurred_at=started_at,
            )
        if derived_shelf == ShelfName.FINISHED:
            record_finished_reading(
                db,
                user_book_id=user_book.id,
                occurred_at=finished_at,
            )

        ensure_shelf_position(db, user_book)

        # The export's "Lists" column is ignored: a book sits on exactly one
        # built-in shelf, the one its ShelfName puts it on.

        imported += 1

    import_record.imported_count = imported
    import_record.skipped_count = skipped
    db.commit()
    return {"imported": imported, "skipped": skipped}
