"""Shelf vocabulary and the hand-arranged positions books hold on a shelf.

Both kinds of shelf let the user arrange books by hand, but they keep that
arrangement in different places: a built-in shelf on ``UserBook.sort_order``,
a custom shelf on ``ShelfItem.sort_order``. See ``app.shelves.service`` for why.
"""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Shelf, ShelfItem, ShelfName, UserBook

SORT_ORDER_GAP = Decimal("1000")

SHELF_DISPLAY_NAMES: dict[ShelfName, str] = {
    ShelfName.WANT_TO_READ: "Want to Read",
    ShelfName.STARTED: "Currently Reading",
    ShelfName.FINISHED: "Finished",
    ShelfName.ABANDONED: "Abandoned",
}

DEFAULT_SHELVES = tuple(SHELF_DISPLAY_NAMES.keys())


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
    """Give a book a built-in shelf position if it has none, appending it to the end."""
    if user_book.sort_order is not None:
        return user_book.sort_order

    move_to_end_of_shelf(db, user_book)
    assert user_book.sort_order is not None
    return user_book.sort_order


def find_shelf_item(db: Session, shelf: Shelf, book_id: int) -> ShelfItem | None:
    """The book's placement on a custom shelf, or None if it is not on it."""
    return (
        db.query(ShelfItem)
        .join(UserBook, UserBook.id == ShelfItem.user_book_id)
        .filter(ShelfItem.shelf_id == shelf.id, UserBook.book_id == book_id)
        .first()
    )


def place_on_custom_shelf(db: Session, shelf: Shelf, user_book: UserBook) -> ShelfItem:
    """Put a book at the end of a custom shelf, or return its existing placement.

    Adding a book already on the shelf leaves its position alone, so a repeated
    add is a no-op rather than a move to the end.
    """
    existing = find_shelf_item(db, shelf, user_book.book_id)
    if existing is not None:
        return existing

    max_sort = (
        db.query(func.max(ShelfItem.sort_order))
        .filter(ShelfItem.shelf_id == shelf.id)
        .scalar()
    )
    item = ShelfItem(
        shelf_id=shelf.id,
        user_book_id=user_book.id,
        sort_order=(max_sort or Decimal("0")) + SORT_ORDER_GAP,
    )
    db.add(item)
    db.flush()
    return item
