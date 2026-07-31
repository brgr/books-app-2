"""Orchestration layer for a user's shelves and their ordering."""

from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.book_events import build_user_book_response, project_user_book_state
from app.models import Book, ShelfName, User, UserBook
from app.schemas import ShelfItemReorderRequest
from app.shelves.shelves import SORT_ORDER_GAP, ensure_shelf_position


class Neighbour(NamedTuple):
    user_book: UserBook
    sort_order: Decimal


class ShelfError(Exception):
    """Base for shelf domain errors."""


class BookNotInLibraryError(ShelfError):
    """The moved book is not in the acting user's library (maps to 404)."""


class ShelfReorderError(ShelfError):
    """A reorder request references a book invalidly (maps to 400)."""


class ShelfService:
    """Shelf operations scoped to a single request's db session and user."""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    @property
    def _user_id(self) -> int:
        return self.user.id

    def list_books(
        self, shelf_name: ShelfName, page: int, page_size: int
    ) -> tuple[list[Book], int]:
        """Return one page of a shelf's books and the total."""
        books_query = (
            self.db.query(Book, UserBook)
            .join(UserBook, UserBook.book_id == Book.id)
            .filter(UserBook.user_id == self._user_id, UserBook.shelf == shelf_name)
        )

        total = books_query.count()
        book_pairs = (
            books_query.order_by(UserBook.sort_order.asc(), UserBook.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        books = []
        for book, user_book in book_pairs:
            project_user_book_state(self.db, user_book)
            book.user_book = build_user_book_response(self.db, user_book)
            books.append(book)
        return books, total

    def reorder(self, shelf_name: ShelfName, payload: ShelfItemReorderRequest) -> None:
        """Reposition a book on a shelf using fractional sort orders.

        Raises BookNotInLibraryError (404) or ShelfReorderError (400) on any
        ownership or reference violation.
        """
        moved_user_book = self._get_user_book(payload.moved_book_id)
        if not moved_user_book:
            raise BookNotInLibraryError("Book not in your library")

        ensure_shelf_position(self.db, moved_user_book)

        before = self._resolve_neighbour(shelf_name, payload.before_book_id)
        after = self._resolve_neighbour(shelf_name, payload.after_book_id)

        if before and after:
            if before.sort_order >= after.sort_order:
                self._rebalance_positions(shelf_name)
                self.db.flush()

            moved_user_book.sort_order = (
                before.sort_order + after.sort_order
            ) / Decimal("2")
        elif before:
            moved_user_book.sort_order = before.sort_order + SORT_ORDER_GAP
        elif after:
            moved_user_book.sort_order = after.sort_order - SORT_ORDER_GAP
        else:
            moved_user_book.sort_order = SORT_ORDER_GAP

        self.db.commit()

    def _rebalance_positions(self, shelf_name: ShelfName) -> None:
        """Respread the positions on one shelf, so fractional inserts have room again."""
        user_books = (
            self.db.query(UserBook)
            .filter(UserBook.user_id == self._user_id, UserBook.shelf == shelf_name)
            .order_by(UserBook.sort_order.asc(), UserBook.id.asc())
            .all()
        )

        for index, user_book in enumerate(user_books, start=1):
            user_book.sort_order = SORT_ORDER_GAP * Decimal(index)

    def _get_user_book(self, book_id: int) -> UserBook | None:
        return (
            self.db.query(UserBook)
            .filter(UserBook.user_id == self._user_id, UserBook.book_id == book_id)
            .first()
        )

    def _resolve_neighbour(
        self, shelf_name: ShelfName, book_id: int | None
    ) -> Neighbour | None:
        """Resolve a book the move is positioned against; it must be on this shelf."""
        if book_id is None:
            return None

        user_book = self._get_user_book(book_id)
        if not user_book:
            raise ShelfReorderError("Referenced book is not in your library")

        if user_book.shelf != shelf_name:
            raise ShelfReorderError("Referenced book is not on this shelf")

        sort_order = ensure_shelf_position(self.db, user_book)
        return Neighbour(user_book, sort_order)
