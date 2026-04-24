from decimal import Decimal
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.book_events import project_user_book_state
from app.book_lists import (
    DEFAULT_LIST_NAMES,
    SORT_ORDER_GAP,
    ensure_list_item,
    get_or_create_default_lists,
    rebalance_list_items,
)
from app.database import get_db
from app.models import Book, BookList, BookListItem, User, UserBook
from app.schemas import BookListItemReorderRequest, BookListResponse, PaginatedBooks

router = APIRouter()


@router.get("/lists", response_model=list[BookListResponse])
def list_book_lists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    lists_by_name = get_or_create_default_lists(db, cast(int, current_user.id))
    db.commit()
    ordered = []
    for name in DEFAULT_LIST_NAMES:
        if name in lists_by_name:
            ordered.append(lists_by_name[name])
    for book_list in sorted(lists_by_name.values(), key=lambda entry: entry.id):
        if book_list.name not in DEFAULT_LIST_NAMES:
            ordered.append(book_list)
    return ordered


@router.get("/lists/{list_id}/books", response_model=PaginatedBooks)
def list_books_in_list(
    list_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    book_list = (
        db.query(BookList)
        .filter(BookList.id == list_id, BookList.user_id == current_user.id)
        .first()
    )
    if not book_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")

    total = (
        db.query(BookListItem)
        .join(UserBook, BookListItem.user_book_id == UserBook.id)
        .filter(BookListItem.list_id == list_id, UserBook.user_id == current_user.id)
        .count()
    )

    rows = (
        db.query(Book, UserBook)
        .join(UserBook, UserBook.book_id == Book.id)
        .join(BookListItem, BookListItem.user_book_id == UserBook.id)
        .filter(BookListItem.list_id == list_id, UserBook.user_id == current_user.id)
        .order_by(BookListItem.sort_order.asc(), BookListItem.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    books = []
    for book, user_book in rows:
        project_user_book_state(db, user_book)
        book.user_status = user_book
        books.append(book)

    pages = (total + page_size - 1) // page_size

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("/lists/{list_id}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_list_item(
    list_id: int,
    payload: BookListItemReorderRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    book_list = (
        db.query(BookList)
        .filter(BookList.id == list_id, BookList.user_id == current_user.id)
        .first()
    )
    if not book_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")

    moved_user_book = (
        db.query(UserBook)
        .filter(
            UserBook.user_id == current_user.id,
            UserBook.book_id == payload.moved_book_id,
        )
        .first()
    )
    if not moved_user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not in your library"
        )

    moved_item = ensure_list_item(db, list_id=list_id, user_book_id=moved_user_book.id)

    def _resolve_item(book_id: int | None) -> BookListItem | None:
        if book_id is None:
            return None
        user_book = (
            db.query(UserBook)
            .filter(UserBook.user_id == current_user.id, UserBook.book_id == book_id)
            .first()
        )
        if not user_book:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referenced book is not in your library",
            )
        item = (
            db.query(BookListItem)
            .filter(
                BookListItem.list_id == list_id,
                BookListItem.user_book_id == user_book.id,
            )
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referenced book is not in this list",
            )
        return item

    before_item = _resolve_item(payload.before_book_id)
    after_item = _resolve_item(payload.after_book_id)

    if before_item and after_item and before_item.sort_order >= after_item.sort_order:
        rebalance_list_items(db, list_id)
        db.flush()
        before_item = _resolve_item(payload.before_book_id)
        after_item = _resolve_item(payload.after_book_id)

    if before_item and after_item:
        moved_item.sort_order = (before_item.sort_order + after_item.sort_order) / Decimal("2")
    elif before_item:
        moved_item.sort_order = before_item.sort_order + SORT_ORDER_GAP
    elif after_item:
        moved_item.sort_order = after_item.sort_order - SORT_ORDER_GAP
    else:
        moved_item.sort_order = SORT_ORDER_GAP

    db.commit()
    return None
