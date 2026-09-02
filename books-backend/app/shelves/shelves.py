"""Shared shelf vocabulary and placement helpers."""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ReadingShelf, Shelf, ShelfKind, ShelfPlacement, UserBook

SORT_ORDER_GAP = Decimal("1000")

# TODO: Why do we have a separate display name mapping? I don't think we use that in the frontend? (for display)
#  And if we do... we shouldn't!
READING_SHELF_DISPLAY_NAMES: dict[ReadingShelf, str] = {
    ReadingShelf.WANT_TO_READ: "Want to Read",
    ReadingShelf.STARTED: "Currently Reading",
    ReadingShelf.PAUSED: "Paused",
    ReadingShelf.FINISHED: "Finished",
    ReadingShelf.ABANDONED: "Abandoned",
}
READING_SHELVES = tuple(READING_SHELF_DISPLAY_NAMES)


def create_reading_shelves(db: Session, user_id: int) -> list[Shelf]:
    """Create the system-owned reading shelves for a newly persisted user.

    The caller owns the surrounding transaction, so user creation and shelf
    initialization remain atomic.
    """
    shelves = [
        Shelf(user_id=user_id, kind=ShelfKind.READING, name=state.value)
        for state in READING_SHELVES
    ]
    db.add_all(shelves)

    return shelves


def find_shelf_placement(
    db: Session, shelf: Shelf, book_id: int
) -> ShelfPlacement | None:
    return (
        db.query(ShelfPlacement)
        .join(UserBook, UserBook.id == ShelfPlacement.user_book_id)
        .filter(ShelfPlacement.shelf_id == shelf.id, UserBook.book_id == book_id)
        .first()
    )


def place_on_shelf(db: Session, shelf: Shelf, user_book: UserBook) -> ShelfPlacement:
    """Add a placement at the end, preserving an existing placement's order."""
    existing = find_shelf_placement(db, shelf, user_book.book_id)
    if existing is not None:
        return existing

    max_sort = (
        db.query(func.max(ShelfPlacement.sort_order))
        .filter(ShelfPlacement.shelf_id == shelf.id)
        .scalar()
    )
    placement = ShelfPlacement(
        shelf_id=shelf.id,
        user_book_id=user_book.id,
        sort_order=(max_sort or Decimal("0")) + SORT_ORDER_GAP,
    )

    db.add(placement)
    db.flush()

    return placement
