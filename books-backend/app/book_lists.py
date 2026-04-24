from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import BookList, BookListItem, ReadingStatus

DEFAULT_LIST_NAMES = ("To Read", "Finished")
SORT_ORDER_GAP = Decimal("1000")


def list_name_for_status(status: ReadingStatus) -> str | None:
    if status in {ReadingStatus.WANT_TO_READ, ReadingStatus.STARTED, ReadingStatus.ABANDONED}:
        return "To Read"
    if status == ReadingStatus.FINISHED:
        return "Finished"
    return None


def get_or_create_default_lists(db: Session, user_id: int) -> dict[str, BookList]:
    existing = db.query(BookList).filter(BookList.user_id == user_id).all()
    lists_by_name = {book_list.name: book_list for book_list in existing}
    for name in DEFAULT_LIST_NAMES:
        if name not in lists_by_name:
            book_list = BookList(user_id=user_id, name=name)
            db.add(book_list)
            db.flush()
            lists_by_name[name] = book_list
    return lists_by_name


def ensure_list_item(db: Session, list_id: int, user_book_id: int) -> BookListItem:
    item = (
        db.query(BookListItem)
        .filter(
            BookListItem.list_id == list_id,
            BookListItem.user_book_id == user_book_id,
        )
        .first()
    )
    if item is not None:
        return item

    max_sort = (
        db.query(func.max(BookListItem.sort_order))
        .filter(BookListItem.list_id == list_id)
        .scalar()
    )
    next_sort = (max_sort or Decimal("0")) + SORT_ORDER_GAP
    item = BookListItem(list_id=list_id, user_book_id=user_book_id, sort_order=next_sort)
    db.add(item)
    db.flush()
    return item


def rebalance_list_items(db: Session, list_id: int) -> None:
    items = (
        db.query(BookListItem)
        .filter(BookListItem.list_id == list_id)
        .order_by(BookListItem.sort_order.asc(), BookListItem.id.asc())
        .all()
    )
    for index, item in enumerate(items, start=1):
        item.sort_order = SORT_ORDER_GAP * Decimal(index)
