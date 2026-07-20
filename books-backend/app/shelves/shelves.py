from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Shelf, ShelfName, UserBook

SORT_ORDER_GAP = Decimal("1000")

SHELF_DISPLAY_NAMES: dict[ShelfName, str] = {
    ShelfName.WANT_TO_READ: "Want to Read",
    ShelfName.STARTED: "Currently Reading",
    ShelfName.FINISHED: "Finished",
    ShelfName.ABANDONED: "Abandoned",
}

DEFAULT_SHELVES = tuple(SHELF_DISPLAY_NAMES.keys())


def _load_shelves(db: Session, user_id: int) -> dict[ShelfName, Shelf]:
    shelves = db.query(Shelf).filter(Shelf.user_id == user_id).all()
    return {shelf.name: shelf for shelf in shelves}


def get_or_create_default_shelves(db: Session, user_id: int) -> dict[ShelfName, Shelf]:
    """Return the user's default shelves, minting them on first use.

    Nothing creates these up front, so the first two requests for a new user can race to
    insert them. The unique constraint settles that: whoever loses adopts the winner's
    rows rather than failing the request.

    Note: I'd say in theory, we should just create the shelves on user creation. However,
    right now user creation just happens pretty much manually and isn't really part of the
    app logic that much (as it's basically just meant for single user).
    In the future, we can improve this.
    """
    shelves_by_name = _load_shelves(db, user_id)
    missing = [name for name in DEFAULT_SHELVES if name not in shelves_by_name]
    if not missing:
        return shelves_by_name

    try:
        for name in missing:
            db.add(Shelf(user_id=user_id, name=name))
        db.commit()
    except IntegrityError:
        db.rollback()

    return _load_shelves(db, user_id)


def move_to_end_of_shelf(db: Session, user_book: UserBook) -> None:
    max_sort = (
        db.query(func.max(UserBook.sort_order))
        .filter(
            UserBook.user_id == user_book.user_id,
            UserBook.shelf == user_book.shelf,
            UserBook.id != user_book.id,
        )
        .scalar()
    )
    user_book.sort_order = (max_sort or Decimal("0")) + SORT_ORDER_GAP
    db.flush()


def ensure_shelf_position(db: Session, user_book: UserBook) -> Decimal:
    """Give a book a shelf position if it has none, appending it to the end."""
    if user_book.sort_order is not None:
        return user_book.sort_order

    move_to_end_of_shelf(db, user_book)
    assert user_book.sort_order is not None
    return user_book.sort_order
