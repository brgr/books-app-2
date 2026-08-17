"""Shelf vocabulary and the hand-arranged positions books hold on a shelf.

Both kinds of shelf let the user arrange books by hand, but they keep that
arrangement in different places: a reading shelf on ``UserBook.sort_order``,
a custom shelf on ``CustomShelfPlacement.sort_order``. See ``app.shelves.service`` for why.
"""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CustomShelf, CustomShelfPlacement, ReadingShelf, UserBook

SORT_ORDER_GAP = Decimal("1000")

READING_SHELF_DISPLAY_NAMES: dict[ReadingShelf, str] = {
    ReadingShelf.WANT_TO_READ: "Want to Read",
    ReadingShelf.STARTED: "Currently Reading",
    ReadingShelf.FINISHED: "Finished",
    ReadingShelf.ABANDONED: "Abandoned",
}

READING_SHELVES = tuple(READING_SHELF_DISPLAY_NAMES.keys())


def move_to_end_of_shelf(db: Session, user_book: UserBook) -> None:
    max_sort = (
        db.query(func.max(UserBook.sort_order))
        .filter(
            UserBook.user_id == user_book.user_id,
            UserBook.reading_shelf == user_book.reading_shelf,
            UserBook.id != user_book.id,
        )
        .scalar()
    )
    user_book.sort_order = (max_sort or Decimal("0")) + SORT_ORDER_GAP
    db.flush()


def ensure_shelf_position(db: Session, user_book: UserBook) -> Decimal:
    """Give a book a reading-shelf position if it has none, appending it to the end."""
    if user_book.sort_order is not None:
        return user_book.sort_order

    move_to_end_of_shelf(db, user_book)
    assert user_book.sort_order is not None
    return user_book.sort_order


def find_shelf_placement(
    db: Session, shelf: CustomShelf, book_id: int
) -> CustomShelfPlacement | None:
    """The book's placement on a custom shelf, or None if it is not on it."""
    return (
        db.query(CustomShelfPlacement)
        .join(UserBook, UserBook.id == CustomShelfPlacement.user_book_id)
        .filter(
            CustomShelfPlacement.shelf_id == shelf.id,
            UserBook.book_id == book_id,
        )
        .first()
    )


def place_on_custom_shelf(
    db: Session, shelf: CustomShelf, user_book: UserBook
) -> CustomShelfPlacement:
    """Put a book at the end of a custom shelf, or return its existing placement.

    Adding a book already on the shelf leaves its position alone, so a repeated
    add is a no-op rather than a move to the end.
    """
    existing = find_shelf_placement(db, shelf, user_book.book_id)
    if existing is not None:
        return existing

    max_sort = (
        db.query(func.max(CustomShelfPlacement.sort_order))
        .filter(CustomShelfPlacement.shelf_id == shelf.id)
        .scalar()
    )
    placement = CustomShelfPlacement(
        shelf_id=shelf.id,
        user_book_id=user_book.id,
        sort_order=(max_sort or Decimal("0")) + SORT_ORDER_GAP,
    )
    db.add(placement)
    db.flush()
    return placement
