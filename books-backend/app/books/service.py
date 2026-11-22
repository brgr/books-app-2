"""Orchestration layer for book operations."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.book_events import (
    build_user_book_response,
    ensure_added_event,
    project_user_book_state,
    record_cover_changed,
)
from app.covers.cover_upgrade import CoverUpgradeJob, start_job
from app.covers.image_utils import download_cover_image
from app.models import Book, User
from app.schemas import BookCreate, BookUpdate


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
        book = Book.from_create(book_data, self._user_id)
        remote_cover = await self._download_if_remote(book_data.cover_image_url)
        if remote_cover:
            book.cover_image_url, book.cover_thumbnail_url = remote_cover

        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)

        self._add_to_library(book)
        self.db.commit()
        return self.attach_user_book(book)

    async def update(self, book: Book, book_data: BookUpdate) -> Book:
        """Apply a partial update, resolving and journaling any cover change."""
        old_cover_image_url = book.cover_image_url
        old_cover_thumbnail_url = book.cover_thumbnail_url

        cover_changed = "cover_image_url" in book_data.model_fields_set
        remote_cover = None

        if cover_changed:
            remote_cover = await self._download_if_remote(book_data.cover_image_url)

            if (
                book_data.cover_image_url
                and book_data.cover_image_url.startswith("http")
                and not remote_cover
            ):
                # We found an URL that looks like a remote image, but we couldn't download it (in this case, it was
                # a book cover URL from Athesia). Before, it wouldn't give a useful error message, so this
                # now should be a bit more helpful.
                raise HTTPException(
                    status_code=422,
                    detail="Could not download a valid cover image from that URL. Try another image URL or upload a file.",
                )

        book.apply_update(book_data)

        if cover_changed:
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
        books = self.db.query(Book).filter(Book.user_id == self._user_id)

        offset = (page - 1) * page_size
        total = books.count()
        page_books = books.offset(offset).limit(page_size).all()

        for book in page_books:
            self.attach_user_book(book)

        return page_books, total

    def remove_from_library(self, book: Book) -> None:
        """Delete the book from the user's library.

        Deleting the Book cascades to its events and shelf placements via the ORM
        relationships.
        """
        self.db.delete(book)
        self.db.commit()

    def clear_library(self) -> None:
        """Delete every book in the user's library."""
        # The database cascades from books to events and shelf placements
        self.db.query(Book).filter(Book.user_id == self._user_id).delete(
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
        project_user_book_state(self.db, book)
        book.user_book = build_user_book_response(self.db, book)

        return book

    @staticmethod
    async def _download_if_remote(url: str | None) -> tuple[str, str | None] | None:
        """Download a remote (http) cover, returning (path, thumbnail) or None."""
        if url and url.startswith("http"):
            return await download_cover_image(url)
        return None

    def _add_to_library(self, book: Book) -> None:
        ensure_added_event(self.db, user_id=self._user_id, book_id=book.id)
        project_user_book_state(self.db, book)

    def _record_cover_change(
        self,
        book: Book,
        old_cover_image_url: str | None,
        old_cover_thumbnail_url: str | None,
    ) -> None:
        ensure_added_event(self.db, user_id=self._user_id, book_id=book.id)
        record_cover_changed(
            self.db,
            book_id=book.id,
            old_cover_image_url=old_cover_image_url,
            new_cover_image_url=book.cover_image_url,
            old_cover_thumbnail_url=old_cover_thumbnail_url,
            new_cover_thumbnail_url=book.cover_thumbnail_url,
        )
