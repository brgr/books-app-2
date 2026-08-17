"""Orchestration layer for a user's shelves, their contents and their ordering.

We have reading shelves and custom shelves.

* A **reading** shelf (``ReadingShelf``) is derived from the reading state via ``UserBook.reading_shelf``.
  It cannot be edited here, as that is the job of ``ReadingService``.
  Since a book is on exactly one reading shelf, the position of a book on it is stored on the
  ``UserBook.sort_order`` column.
  (Small note 2026-08-08: I'm a bit unsure if this is a good design choice. It was so until now, because we didn't yet have
  custom shelves. Now, however, we might want to switch this too, maybe. So far we haven't)
* A **custom** shelf (``CustomShelf``), on the other hand is assigned manually by the user.
  The user creates, renames and deletes it, and puts books on it when wanted.
  Every time a book is placed on a custom shelf, that's a ``CustomShelfPlacement``.
  It carries its own position, since a book may be on many.
"""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.book_events import build_user_book_response, project_user_book_state
from app.models import (
    Book,
    CustomShelf,
    CustomShelfPlacement,
    ReadingShelf,
    User,
    UserBook,
)
from app.schemas import (
    ShelfReorderRequest,
    CustomShelfNamePayload,
    ShelfResponse,
)
from app.shelves.shelves import (
    READING_SHELVES,
    READING_SHELF_DISPLAY_NAMES,
    SORT_ORDER_GAP,
    ensure_shelf_position,
    find_shelf_placement,
    place_on_custom_shelf,
)

# Either kind of shelf an operation can target
ShelfTarget = ReadingShelf | CustomShelf

# A row carrying a book's position on one shelf: the UserBook itself for a
# reading shelf, the CustomShelfPlacement for a custom one.
ShelfPlacement = UserBook | CustomShelfPlacement


def position_of(row: ShelfPlacement) -> Decimal:
    """Read a row's current position.

    Only ``UserBook`` has a nullable ``sort_order``, and any row reached through
    ``_position_of`` has been given one. Read through this rather than captured
    up front: ``_rebalance_positions`` rewrites positions in place, and a
    neighbor's value must reflect that.
    """
    assert row.sort_order is not None
    return row.sort_order


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
    """A reading shelf was asked to do something only custom shelves can do.

    Covers both lifecycle (rename, delete) and membership: a book's reading
    shelf follows its reading state, so it is set through the reading endpoints
    rather than by putting the book on a shelf. Maps to 400.
    """


class ShelfService:
    """Shelf operations scoped to a single request's db session and user."""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    @property
    def _user_id(self) -> int:
        return self.user.id

    # Resolving a ref

    def resolve(self, ref: str) -> ShelfTarget:
        """Turn a URL ref into the shelf it names.

        Reading shelves are addressed by ``ReadingShelf`` value and custom ones by
        id, which never collide: no reading-shelf name is a number.
        """
        if ref.isdigit():
            shelf = (
                self.db.query(CustomShelf)
                .filter(
                    CustomShelf.id == int(ref), CustomShelf.user_id == self._user_id
                )
                .first()
            )
            if shelf is None:
                raise ShelfNotFoundError("Shelf not found")
            return shelf

        try:
            return ReadingShelf(ref)
        except ValueError:
            raise ShelfNotFoundError("Shelf not found") from None

    def _custom_shelf(self, ref: str) -> CustomShelf:
        """Resolve a ref that must name a custom shelf."""
        shelf = self.resolve(ref)
        if isinstance(shelf, ReadingShelf):
            raise ReadingShelfError(
                f"'{shelf.value}' is a reading shelf and cannot be changed. "
                "A book's reading shelf follows its reading state; "
                "set it via PUT /books/{book_id}/shelf."
            )
        return shelf

    # Listing shelves

    def list_shelves(self) -> list[ShelfResponse]:
        """Every shelf the user has, reading shelves first and always present."""
        reading_shelf_counts = {
            name: count
            for name, count in self.db.query(
                UserBook.reading_shelf, func.count(UserBook.id)
            )
            .filter(UserBook.user_id == self._user_id)
            .group_by(UserBook.reading_shelf)
            .all()
        }

        custom_counts = {
            shelf_id: count
            for shelf_id, count in self.db.query(
                CustomShelfPlacement.shelf_id, func.count(CustomShelfPlacement.id)
            )
            .join(CustomShelf, CustomShelf.id == CustomShelfPlacement.shelf_id)
            .filter(CustomShelf.user_id == self._user_id)
            .group_by(CustomShelfPlacement.shelf_id)
            .all()
        }

        custom = (
            self.db.query(CustomShelf)
            .filter(CustomShelf.user_id == self._user_id)
            .order_by(CustomShelf.id.asc())
            .all()
        )

        reading_shelves = [
            ShelfResponse(
                ref=name.value,
                kind="default",
                display_name=READING_SHELF_DISPLAY_NAMES[name],
                book_count=reading_shelf_counts.get(name, 0),
            )
            for name in READING_SHELVES
        ]
        custom_shelves = [
            ShelfResponse(
                ref=str(shelf.id),
                kind="custom",
                display_name=shelf.name,
                book_count=custom_counts.get(shelf.id, 0),
            )
            for shelf in custom
        ]

        return reading_shelves + custom_shelves

    def _to_response(self, shelf: CustomShelf) -> ShelfResponse:
        return ShelfResponse(
            ref=str(shelf.id),
            kind="custom",
            display_name=shelf.name,
            book_count=len(shelf.placements),
        )

    # Shelf lifecycle

    def create_shelf(self, payload: CustomShelfNamePayload) -> ShelfResponse:
        shelf = CustomShelf(user_id=self._user_id, name=payload.name)
        self.db.add(shelf)
        self._commit_unique_name(payload.name)
        return self._to_response(shelf)

    def update_shelf(self, ref: str, payload: CustomShelfNamePayload) -> ShelfResponse:
        shelf = self._custom_shelf(ref)
        shelf.name = payload.name
        self._commit_unique_name(payload.name)
        return self._to_response(shelf)

    def delete_shelf(self, ref: str) -> None:
        """Delete a shelf. Its books stay in the library; only the placements go."""
        shelf = self._custom_shelf(ref)
        self.db.delete(shelf)
        self.db.commit()

    def _commit_unique_name(self, name: str) -> None:
        """Commit a create or rename, turning the name clash into a domain error."""
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise CustomShelfNameTakenError(
                f"You already have a shelf called '{name}'"
            ) from None

    # Membership

    def add_book(self, ref: str, book_id: int) -> None:
        shelf = self._custom_shelf(ref)
        user_book = self._get_user_book(book_id)
        if user_book is None:
            raise BookNotInLibraryError("Book not in your library")

        place_on_custom_shelf(self.db, shelf, user_book)
        self.db.commit()

    def remove_book(self, ref: str, book_id: int) -> None:
        shelf = self._custom_shelf(ref)
        placement = find_shelf_placement(self.db, shelf, book_id)
        if placement is None:
            raise BookNotInLibraryError("Book is not on this shelf")

        self.db.delete(placement)
        self.db.commit()

    # Contents

    def list_books(
        self, shelf: ShelfTarget, page: int, page_size: int
    ) -> tuple[list[Book], int]:
        """Return one page of a shelf's books and the total."""
        pairs_query = self.db.query(Book, UserBook).join(
            UserBook, UserBook.book_id == Book.id
        )
        if isinstance(shelf, ReadingShelf):
            pairs_query = pairs_query.filter(
                UserBook.user_id == self._user_id,
                UserBook.reading_shelf == shelf,
            ).order_by(UserBook.sort_order.asc(), UserBook.id.asc())
        else:
            pairs_query = (
                pairs_query.join(
                    CustomShelfPlacement,
                    CustomShelfPlacement.user_book_id == UserBook.id,
                )
                .filter(CustomShelfPlacement.shelf_id == shelf.id)
                .order_by(
                    CustomShelfPlacement.sort_order.asc(),
                    CustomShelfPlacement.id.asc(),
                )
            )

        total = pairs_query.count()
        book_pairs = pairs_query.offset((page - 1) * page_size).limit(page_size).all()

        books = []
        for book, user_book in book_pairs:
            project_user_book_state(self.db, user_book)
            book.user_book = build_user_book_response(self.db, user_book)
            books.append(book)
        return books, total

    # Ordering

    def reorder(self, shelf: ShelfTarget, payload: ShelfReorderRequest) -> None:
        """Reposition a book on a shelf using fractional sort orders.

        Raises BookNotInLibraryError (404) or ShelfReorderError (400) on any
        ownership or reference violation.
        """
        if self._get_user_book(payload.moved_book_id) is None:
            raise BookNotInLibraryError("Book not in your library")

        moved = self._position_of(shelf, payload.moved_book_id)
        if moved is None:
            raise ShelfReorderError("Moved book is not on this shelf")

        before = self._resolve_neighbour(shelf, payload.before_book_id)
        after = self._resolve_neighbour(shelf, payload.after_book_id)

        if before is not None and after is not None:
            if position_of(before) >= position_of(after):
                self._rebalance_positions(shelf)
                self.db.flush()

            moved.sort_order = (position_of(before) + position_of(after)) / Decimal("2")
        elif before is not None:
            moved.sort_order = position_of(before) + SORT_ORDER_GAP
        elif after is not None:
            moved.sort_order = position_of(after) - SORT_ORDER_GAP
        else:
            moved.sort_order = SORT_ORDER_GAP

        self.db.commit()

    def _positions(self, shelf: ShelfTarget) -> list[ShelfPlacement]:
        """Every position-carrying row on the shelf, in display order."""
        if isinstance(shelf, ReadingShelf):
            return list(
                self.db.query(UserBook)
                .filter(
                    UserBook.user_id == self._user_id,
                    UserBook.reading_shelf == shelf,
                )
                .order_by(UserBook.sort_order.asc(), UserBook.id.asc())
            )

        return list(
            self.db.query(CustomShelfPlacement)
            .filter(CustomShelfPlacement.shelf_id == shelf.id)
            .order_by(
                CustomShelfPlacement.sort_order.asc(), CustomShelfPlacement.id.asc()
            )
        )

    def _position_of(self, shelf: ShelfTarget, book_id: int) -> ShelfPlacement | None:
        """The book's position-carrying row on this shelf, or None if it is not on it."""
        if isinstance(shelf, ReadingShelf):
            user_book = (
                self.db.query(UserBook)
                .filter(
                    UserBook.user_id == self._user_id,
                    UserBook.reading_shelf == shelf,
                    UserBook.book_id == book_id,
                )
                .first()
            )

            if user_book is None:
                return None

            # A book reaches a reading shelf without necessarily having been
            # positioned on it, so give it a position on first sight.
            ensure_shelf_position(self.db, user_book)

            return user_book

        return find_shelf_placement(self.db, shelf, book_id)

    def _rebalance_positions(self, shelf: ShelfTarget) -> None:
        """Respread one shelf's positions, so fractional inserts have room again."""
        for index, row in enumerate(self._positions(shelf), start=1):
            row.sort_order = SORT_ORDER_GAP * Decimal(index)

    def _get_user_book(self, book_id: int) -> UserBook | None:
        return (
            self.db.query(UserBook)
            .filter(UserBook.user_id == self._user_id, UserBook.book_id == book_id)
            .first()
        )

    def _resolve_neighbour(
        self, shelf: ShelfTarget, book_id: int | None
    ) -> ShelfPlacement | None:
        """Resolve a book the move is positioned against; it must be on this shelf."""
        if book_id is None:
            return None

        if self._get_user_book(book_id) is None:
            raise ShelfReorderError("Referenced book is not in your library")

        row = self._position_of(shelf, book_id)
        if row is None:
            raise ShelfReorderError("Referenced book is not on this shelf")
        return row
