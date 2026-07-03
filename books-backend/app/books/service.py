"""Orchestration layer for book operations."""

from sqlalchemy.orm import Session

from app.book_events import (
    ensure_added_event,
    project_user_book_state,
    record_cover_changed,
)
from app.book_lists import (
    ensure_list_item,
    get_or_create_default_lists,
    list_name_for_status,
)
from app.books.queries import get_user_book
from app.cover_upgrade import CoverUpgradeJob, start_job
from app.image_utils import download_cover_image
from app.models import Book, User, UserBook
from app.schemas import BookCreate, BookUpdate


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
        return self.attach_status(book, reproject=False)

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
        return self.attach_status(book, reproject=False)

    def list(self, page: int, page_size: int) -> tuple[list[Book], int]:
        """Return one page of books (with user status attached) and the total."""
        total = self.db.query(Book).count()
        books = (
            self.db.query(Book).offset((page - 1) * page_size).limit(page_size).all()
        )
        for book in books:
            # noinspection PyTypeChecker
            self.attach_status(book)
        # noinspection PyTypeChecker
        return books, total

    def delete(self, book: Book) -> None:
        self.db.delete(book)
        self.db.commit()

    def delete_all(self) -> None:
        """Delete all books and every user's reading state for them.

        Removing user_books first lets the ondelete=CASCADE on book_events and
        book_list_items fire at the DB level, avoiding orphaned rows that would
        otherwise re-link to unrelated books via SQLite primary-key reuse.
        """
        self.db.query(UserBook).delete(synchronize_session=False)
        self.db.query(Book).delete(synchronize_session=False)
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

    def attach_status(self, book: Book, *, reproject: bool = True) -> Book:
        """Attach the acting user's reading state to ``book.user_status``.

        When ``reproject`` is set, the user_book snapshot is first recomputed
        from its event stream (used on reads); cover-only writes skip it.
        """
        user_book = get_user_book(self.db, user_id=self._user_id, book_id=book.id)
        if user_book and reproject:
            project_user_book_state(self.db, user_book)
        book.user_status = user_book
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
        lists_by_name = get_or_create_default_lists(self.db, self._user_id)
        target_list_name = list_name_for_status(user_book.status)
        if target_list_name and target_list_name in lists_by_name:
            ensure_list_item(
                self.db,
                list_id=lists_by_name[target_list_name].id,
                user_book_id=user_book.id,
            )

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
