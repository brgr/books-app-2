"""Orchestration layer for a user's book lists and their ordering."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.book_events import project_user_book_state
from app.book_lists.book_lists import (
    DEFAULT_LIST_NAMES,
    SORT_ORDER_GAP,
    ensure_list_item,
    get_or_create_default_lists,
    rebalance_list_items,
)
from app.models import Book, BookList, BookListItem, User, UserBook
from app.schemas import BookListItemReorderRequest


class BookListError(Exception):
    """Base for book-list domain errors."""


class ListNotFoundError(BookListError):
    """The requested list does not exist for the acting user (maps to 404)."""


class BookNotInLibraryError(BookListError):
    """The moved book is not in the acting user's library (maps to 404)."""


class ListReorderError(BookListError):
    """A reorder request references a book invalidly (maps to 400)."""


class BookListService:
    """Book-list operations scoped to a single request's db session and user."""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    @property
    def _user_id(self) -> int:
        # noinspection PyTypeChecker
        return self.user.id

    def get_lists(self) -> list[BookList]:
        """Return the user's lists, default lists first then the rest by id."""
        lists_by_name = get_or_create_default_lists(self.db, self._user_id)
        self.db.commit()
        book_lists = [
            lists_by_name[name] for name in DEFAULT_LIST_NAMES if name in lists_by_name
        ]

        for book_list in sorted(lists_by_name.values(), key=lambda entry: entry.id):
            if book_list.name not in DEFAULT_LIST_NAMES:
                book_lists.append(book_list)

        return book_lists

    def list_books(
        self, list_id: int, page: int, page_size: int
    ) -> tuple[list[Book], int]:
        """Return one page of a list's books (status attached) and the total.

        Raises ListNotFoundError if the list is not owned by the acting user.
        """
        self._get_owned_list(list_id)

        total = (
            self.db.query(BookListItem)
            .join(UserBook, BookListItem.user_book_id == UserBook.id)
            .filter(BookListItem.list_id == list_id, UserBook.user_id == self._user_id)
            .count()
        )

        book_pairs = (
            self.db.query(Book, UserBook)
            .join(UserBook, UserBook.book_id == Book.id)
            .join(BookListItem, BookListItem.user_book_id == UserBook.id)
            .filter(BookListItem.list_id == list_id, UserBook.user_id == self._user_id)
            .order_by(BookListItem.sort_order.asc(), BookListItem.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        books = []
        for book, user_book in book_pairs:
            project_user_book_state(self.db, user_book)
            book.user_status = user_book
            books.append(book)
        return books, total

    def reorder(self, list_id: int, payload: BookListItemReorderRequest) -> None:
        """Reposition a book within a list using fractional sort orders.

        Raises ListNotFoundError / BookNotInLibraryError (404) or
        ListReorderError (400) on any ownership or reference violation.
        """
        self._get_owned_list(list_id)

        moved_user_book = self._get_user_book(payload.moved_book_id)
        if not moved_user_book:
            raise BookNotInLibraryError("Book not in your library")

        # noinspection PyTypeChecker
        moved_item = ensure_list_item(
            self.db, list_id=list_id, user_book_id=moved_user_book.id
        )

        before_item = self._resolve_item(list_id, payload.before_book_id)
        after_item = self._resolve_item(list_id, payload.after_book_id)

        if (
            before_item
            and after_item
            and before_item.sort_order >= after_item.sort_order
        ):
            rebalance_list_items(self.db, list_id)
            self.db.flush()
            before_item = self._resolve_item(list_id, payload.before_book_id)
            after_item = self._resolve_item(list_id, payload.after_book_id)

        if before_item and after_item:
            moved_item.sort_order = (
                before_item.sort_order + after_item.sort_order
            ) / Decimal("2")
        elif before_item:
            moved_item.sort_order = before_item.sort_order + SORT_ORDER_GAP
        elif after_item:
            moved_item.sort_order = after_item.sort_order - SORT_ORDER_GAP
        else:
            moved_item.sort_order = SORT_ORDER_GAP

        self.db.commit()

    def _get_owned_list(self, list_id: int) -> BookList:
        book_list = (
            self.db.query(BookList)
            .filter(BookList.id == list_id, BookList.user_id == self._user_id)
            .first()
        )

        if not book_list:
            raise ListNotFoundError("List not found")

        # noinspection PyTypeChecker
        return book_list

    def _get_user_book(self, book_id: int) -> UserBook | None:
        # noinspection PyTypeChecker
        return (
            self.db.query(UserBook)
            .filter(UserBook.user_id == self._user_id, UserBook.book_id == book_id)
            .first()
        )

    def _resolve_item(self, list_id: int, book_id: int | None) -> BookListItem | None:
        if book_id is None:
            return None

        user_book = self._get_user_book(book_id)
        if not user_book:
            raise ListReorderError("Referenced book is not in your library")

        item = (
            self.db.query(BookListItem)
            .filter(
                BookListItem.list_id == list_id,
                BookListItem.user_book_id == user_book.id,
            )
            .first()
        )

        if not item:
            raise ListReorderError("Referenced book is not in this list")

        # noinspection PyTypeChecker
        return item
