"""Operations over the single Shelf/ShelfPlacement model."""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.book_events import build_user_book_response
from app.models import Book, Shelf, ShelfKind, ShelfPlacement, User, UserBook
from app.schemas import CustomShelfNamePayload, ShelfReorderRequest, ShelfResponse
from app.shelves.refs import CustomShelfRef, ReadingShelfRef, ShelfRef
from app.shelves.shelves import (
    READING_SHELF_DISPLAY_NAMES,
    SORT_ORDER_GAP,
    find_shelf_placement,
    place_on_shelf,
)


class ShelfError(Exception):
    """Base for shelf domain errors."""


class ShelfNotFoundError(ShelfError):
    """No shelf of either kind answers to this ref."""


class BookNotInLibraryError(ShelfError):
    """The book is not in the acting user's library."""


class ShelfReorderError(ShelfError):
    """A reorder names a book that cannot be positioned against."""


class CustomShelfNameTakenError(ShelfError):
    """The user already has a shelf by this name."""


class ReadingShelfError(ShelfError):
    pass


class ShelfService:
    def __init__(self, db: Session, user: User):
        self.db, self.user = db, user

    @property
    def _user_id(self) -> int:
        return self.user.id

    def resolve(self, ref: ShelfRef) -> Shelf:
        if isinstance(ref, ReadingShelfRef):
            shelf = (
                self.db.query(Shelf)
                .filter_by(
                    user_id=self._user_id, kind=ShelfKind.READING, name=ref.shelf.value
                )
                .first()
            )
        else:  # CustomShelfRef
            shelf = (
                self.db.query(Shelf)
                .filter_by(id=ref.id, user_id=self._user_id, kind=ShelfKind.CUSTOM)
                .first()
            )

        if shelf is None:
            raise ShelfNotFoundError("Shelf not found")

        return shelf

    def _custom_shelf(self, ref: ShelfRef) -> Shelf:
        if isinstance(ref, ReadingShelfRef):
            raise ReadingShelfError(
                "Reading shelves cannot be changed; set a book's state via PUT /books/{book_id}/shelf."
            )

        return self.resolve(ref)

    def _ref(self, shelf: Shelf) -> str:
        if shelf.kind == ShelfKind.READING:
            return str(
                ReadingShelfRef(
                    next(
                        key
                        for key in READING_SHELF_DISPLAY_NAMES
                        if key.value == shelf.name
                    )
                )
            )

        return str(CustomShelfRef(shelf.id))

    def _to_response(self, shelf: Shelf, count: int | None = None) -> ShelfResponse:
        name = (
            READING_SHELF_DISPLAY_NAMES[
                next(
                    key
                    for key in READING_SHELF_DISPLAY_NAMES
                    if key.value == shelf.name
                )
            ]
            if shelf.kind == ShelfKind.READING
            else shelf.name
        )

        shelf_ref = self._ref(shelf)
        book_count = count if count is not None else len(shelf.placements)

        return ShelfResponse(ref=shelf_ref, display_name=name, book_count=book_count)

    def list_shelves(self) -> list[ShelfResponse]:
        shelves = (
            self.db.query(Shelf)
            .filter(Shelf.user_id == self._user_id)
            .order_by(Shelf.kind.asc(), Shelf.id.asc())
            .all()
        )
        count_rows = (
            self.db.query(ShelfPlacement.shelf_id, func.count(ShelfPlacement.id))
            .join(Shelf)
            .filter(Shelf.user_id == self._user_id)
            .group_by(ShelfPlacement.shelf_id)
            .all()
        )
        counts: dict[int, int] = {
            int(shelf_id): int(book_count) for shelf_id, book_count in count_rows
        }
        reading = [s for s in shelves if s.kind == ShelfKind.READING]
        reading.sort(
            key=lambda s: list(READING_SHELF_DISPLAY_NAMES).index(
                next(k for k in READING_SHELF_DISPLAY_NAMES if k.value == s.name)
            )
        )

        return [
            self._to_response(s, counts.get(s.id, 0))
            for s in reading + [s for s in shelves if s.kind == ShelfKind.CUSTOM]
        ]

    def list_book_custom_shelves(self, book_id: int) -> list[ShelfResponse]:
        """Return the custom shelves containing one of the user's library books."""
        user_book = self._get_user_book(book_id)
        if user_book is None:
            raise BookNotInLibraryError("Book not in your library")

        shelves = (
            self.db.query(Shelf)
            .join(ShelfPlacement)
            .filter(
                Shelf.user_id == self._user_id,
                Shelf.kind == ShelfKind.CUSTOM,
                ShelfPlacement.user_book_id == user_book.id,
            )
            .order_by(Shelf.id.asc())
            .all()
        )
        return [self._to_response(shelf) for shelf in shelves]

    def create_shelf(self, payload: CustomShelfNamePayload) -> ShelfResponse:
        shelf = Shelf(user_id=self._user_id, kind=ShelfKind.CUSTOM, name=payload.name)
        self.db.add(shelf)
        self._commit_unique_name(payload.name)
        return self._to_response(shelf)

    def update_shelf(
        self, ref: ShelfRef, payload: CustomShelfNamePayload
    ) -> ShelfResponse:
        shelf = self._custom_shelf(ref)
        shelf.name = payload.name
        self._commit_unique_name(payload.name)
        return self._to_response(shelf)

    def delete_shelf(self, ref: ShelfRef) -> None:
        self.db.delete(self._custom_shelf(ref))
        self.db.commit()

    def _commit_unique_name(self, name: str) -> None:
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise CustomShelfNameTakenError(
                f"You already have a shelf called '{name}'"
            ) from None

    def _get_user_book(self, book_id: int) -> UserBook | None:
        return (
            self.db.query(UserBook)
            .filter_by(user_id=self._user_id, book_id=book_id)
            .first()
        )

    def add_book(self, ref: ShelfRef, book_id: int) -> None:
        user_book = self._get_user_book(book_id)
        if user_book is None:
            raise BookNotInLibraryError("Book not in your library")

        place_on_shelf(self.db, self._custom_shelf(ref), user_book)
        self.db.commit()

    def remove_book(self, ref: ShelfRef, book_id: int) -> None:
        placement = find_shelf_placement(self.db, self._custom_shelf(ref), book_id)
        if placement is None:
            raise BookNotInLibraryError("Book is not on this shelf")

        self.db.delete(placement)
        self.db.commit()

    def list_books(
        self, shelf: Shelf, page: int, page_size: int
    ) -> tuple[list[Book], int]:
        query = (
            self.db.query(Book, UserBook)
            .join(UserBook, UserBook.book_id == Book.id)
            .join(ShelfPlacement, ShelfPlacement.user_book_id == UserBook.id)
            .filter(ShelfPlacement.shelf_id == shelf.id)
            .order_by(ShelfPlacement.sort_order.asc(), ShelfPlacement.id.asc())
        )
        total = query.count()

        books = []
        for book, user_book in (
            query.offset((page - 1) * page_size).limit(page_size).all()
        ):
            book.user_book = build_user_book_response(self.db, user_book)
            books.append(book)

        return books, total

    def reorder(self, shelf: Shelf, payload: ShelfReorderRequest) -> None:
        if self._get_user_book(payload.moved_book_id) is None:
            raise BookNotInLibraryError("Book not in your library")

        moved = find_shelf_placement(self.db, shelf, payload.moved_book_id)
        if moved is None:
            raise ShelfReorderError("Moved book is not on this shelf")

        before = self._neighbour(shelf, payload.before_book_id)
        after = self._neighbour(shelf, payload.after_book_id)
        if before and after:
            if before.sort_order >= after.sort_order:
                self._rebalance(shelf)
                self.db.flush()
            moved.sort_order = (before.sort_order + after.sort_order) / Decimal("2")
        elif before:
            moved.sort_order = before.sort_order + SORT_ORDER_GAP
        elif after:
            moved.sort_order = after.sort_order - SORT_ORDER_GAP
        else:
            moved.sort_order = SORT_ORDER_GAP

        self.db.commit()

    def _neighbour(self, shelf: Shelf, book_id: int | None) -> ShelfPlacement | None:
        if book_id is None:
            return None
        if self._get_user_book(book_id) is None:
            raise ShelfReorderError("Referenced book is not in your library")

        placement = find_shelf_placement(self.db, shelf, book_id)
        if placement is None:
            raise ShelfReorderError("Referenced book is not on this shelf")

        return placement

    def _rebalance(self, shelf: Shelf) -> None:
        for index, row in enumerate(
            self.db.query(ShelfPlacement)
            .filter_by(shelf_id=shelf.id)
            .order_by(ShelfPlacement.sort_order, ShelfPlacement.id),
            1,
        ):
            row.sort_order = SORT_ORDER_GAP * Decimal(index)
