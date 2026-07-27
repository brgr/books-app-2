"""Orchestration layer for book operations."""

from sqlalchemy.orm import Session

from app.book_events import (
    build_user_book_response,
    ensure_added_event,
    project_user_book_state,
    record_cover_changed,
)
from app.books.queries import get_user_book
from app.cover_upgrade import CoverUpgradeJob, start_job
from app.image_utils import download_cover_image
from app.models import Book, User, UserBook
from app.schemas import BookCreate, BookUpdate
from app.shelves.shelves import ensure_shelf_position


# noinspection bad-argument-type
class BookService:
    """Book operations scoped to a single request's db session and user."""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    @property
    def _user_id(self) -> int:
        # noinspection PyTypeChecker
        return self.user.id

    async def create(self, book_data: BookCreate) -> Book:
        """Persist a new book, then add it to the acting user's library."""
        book = Book.from_create(book_data)
        remote_cover = await self._download_if_remote(book_data.cover_image_url)
        if remote_cover:
            book.cover_image_url, book.cover_thumbnail_url = remote_cover

        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)

        self._add_to_library(book)
        self.db.commit()
        return book

    async def update(self, book: Book, book_data: BookUpdate) -> Book:
        """Apply a partial update, resolving and journaling any cover change."""
        old_cover_image_url = book.cover_image_url
        old_cover_thumbnail_url = book.cover_thumbnail_url

        book.apply_update(book_data)

        cover_changed = "cover_image_url" in book_data.model_fields_set
        if cover_changed:
            remote_cover = await self._download_if_remote(book_data.cover_image_url)
            if remote_cover:
                book.cover_image_url, book.cover_thumbnail_url = remote_cover
            elif not book_data.cover_image_url:
                book.cover_thumbnail_url = None

        if cover_changed and book.cover_image_url != old_cover_image_url:
            self._record_cover_change(
                book, old_cover_image_url, old_cover_thumbnail_url
            )

        self.db.commit()
        self.db.refresh(book)
        return self.attach_user_book(book)

    def set_cover(self, book: Book, cover_url: str, thumbnail_url: str | None) -> Book:
        """Point the book at an already-stored cover, journaling the change."""
        old_cover_image_url = book.cover_image_url
        old_cover_thumbnail_url = book.cover_thumbnail_url
        book.cover_image_url = cover_url
        book.cover_thumbnail_url = thumbnail_url
        if cover_url != old_cover_image_url:
            self._record_cover_change(
                book, old_cover_image_url, old_cover_thumbnail_url
            )
        self.db.commit()
        self.db.refresh(book)
        return self.attach_user_book(book)

    def list(self, page: int, page_size: int) -> tuple[list[Book], int]:
        """Return one page of the user's library (with shelf entry attached) and the total."""
        library_books = (
            self.db.query(Book)
            .join(UserBook, UserBook.book_id == Book.id)
            .filter(UserBook.user_id == self._user_id)
        )

        offset = (page - 1) * page_size
        total = library_books.count()
        books = library_books.offset(offset).limit(page_size).all()

        for book in books:
            self.attach_user_book(book)

        return books, total

    def remove_from_library(self, book: Book) -> None:
        """Remove the book from the acting user's library.

        Deleting the UserBook cascades to its events and list items via the
        ORM relationship.
        """
        # noinspection PyTypeChecker
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book.id)

        if user_book:
            self.db.delete(user_book)
            self.db.commit()

    def clear_library(self) -> None:
        """Remove every book from the acting user's library."""
        self.db.query(UserBook).filter(UserBook.user_id == self._user_id).delete(
            synchronize_session=False
        )
        self.db.commit()

    def start_cover_upgrade(
        self, book: Book, current_cover_path: str
    ) -> CoverUpgradeJob:
        """Kick off the async higher-resolution cover search for this book."""
        return start_job(
            book_id=book.id,
            user_id=self._user_id,
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            current_cover_path=current_cover_path,
        )

    def attach_user_book(self, book: Book) -> Book:
        """Attach the acting user's shelf entry to ``book.user_book``.

        The snapshot columns are recomputed from the event stream and the
        event-derived reading dates are assembled into the DTO for serialization.
        """
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book.id)

        if user_book:
            project_user_book_state(self.db, user_book)
            book.user_book = build_user_book_response(self.db, user_book)
        else:
            book.user_book = None

        return book

    @staticmethod
    async def _download_if_remote(url: str | None) -> tuple[str, str | None] | None:
        """Download a remote (http) cover, returning (path, thumbnail) or None."""
        if url and url.startswith("http"):
            return await download_cover_image(url)
        return None

    def _add_to_library(self, book: Book) -> None:
        user_book = ensure_added_event(self.db, user_id=self._user_id, book_id=book.id)
        project_user_book_state(self.db, user_book)

        ensure_shelf_position(self.db, user_book)

    def _record_cover_change(
        self,
        book: Book,
        old_cover_image_url: str | None,
        old_cover_thumbnail_url: str | None,
    ) -> None:
        actor_user_book = ensure_added_event(
            self.db, user_id=self._user_id, book_id=book.id
        )
        record_cover_changed(
            self.db,
            user_book_id=actor_user_book.id,
            old_cover_image_url=old_cover_image_url,
            new_cover_image_url=book.cover_image_url,
            old_cover_thumbnail_url=old_cover_thumbnail_url,
            new_cover_thumbnail_url=book.cover_thumbnail_url,
        )
