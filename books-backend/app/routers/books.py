from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
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
from app.database import get_db
from app.google_books import (
    GoogleBooksRateLimitError,
    search_cover_images,
    search_google_books,
)
from app.cover_upgrade import get_job, start_job
from app.image_utils import CONTENT_TYPE_TO_EXT, download_cover_image, store_cover_image
from app.models import Book, ReadingStatus, User, UserBook
from app.schemas import (
    BookCreate,
    BookResponse,
    BookUpdate,
    CoverSearchResult,
    CoverUpgradeCandidateResponse,
    CoverUpgradeJobResponse,
    GoogleBookResult,
    PaginatedBooks,
)

router = APIRouter()


@router.get("/books/search", response_model=list[GoogleBookResult])
async def search_books(
    q: str, current_user: Annotated[User, Depends(get_current_user)]
):
    """Search for books using the Google Books API."""
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty",
        )

    try:
        results = await search_google_books(q)
    except GoogleBooksRateLimitError as e:
        headers = {}
        if e.retry_after:
            headers["Retry-After"] = e.retry_after
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Google Books rate limit exceeded. "
                "Try again later or set GOOGLE_BOOKS_API_KEY."
            ),
            headers=headers,
        )
    return results


@router.get("/books/search-covers", response_model=list[CoverSearchResult])
async def search_covers(
    current_user: Annotated[User, Depends(get_current_user)],
    title: str | None = None,
    author: str | None = None,
    isbn: str | None = None,
):
    """Search Google Books for candidate cover images by title/author/isbn."""
    if not any([title, author, isbn]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of title, author, or isbn",
        )
    try:
        return await search_cover_images(title=title, author=author, isbn=isbn)
    except GoogleBooksRateLimitError as e:
        headers = {}
        if e.retry_after:
            headers["Retry-After"] = e.retry_after
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Google Books rate limit exceeded.",
            headers=headers,
        )


@router.post(
    "/books/{book_id}/cover-upgrade-search",
    response_model=CoverUpgradeJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_cover_upgrade_search(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Kick off an async search for higher-resolution versions of this cover."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
        .first()
    )
    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    cover_path = cast(str | None, book.cover_image_url)
    if not cover_path or cover_path.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book has no local cover to upgrade",
        )
    job = start_job(
        book_id=book_id,
        user_id=cast(int, current_user.id),
        title=cast(str | None, book.title),
        author=cast(str | None, book.author),
        isbn=cast(str | None, book.isbn),
        current_cover_path=cover_path,
    )
    return CoverUpgradeJobResponse(job_id=job.id, status=job.status)


@router.get(
    "/books/{book_id}/cover-upgrade-search/{job_id}",
    response_model=CoverUpgradeJobResponse,
)
async def get_cover_upgrade_search(
    book_id: int,
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    job = get_job(job_id)
    if not job or job.book_id != book_id or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return CoverUpgradeJobResponse(
        job_id=job.id,
        status=job.status,
        results=[CoverUpgradeCandidateResponse.model_validate(c) for c in job.results],
        error=job.error,
    )


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Create a new book."""
    data = book_data.model_dump()

    cover_url = data.get("cover_image_url")
    if cover_url and cover_url.startswith("http"):
        download_result = await download_cover_image(cover_url)
        if download_result:
            cover_path, thumbnail_path = download_result
            data["cover_image_url"] = cover_path
            data["cover_thumbnail_url"] = thumbnail_path

    book = Book(**data)
    db.add(book)
    db.commit()
    db.refresh(book)

    user_id = cast(int, current_user.id)
    user_book = ensure_added_event(db, user_id=user_id, book_id=cast(int, book.id))
    project_user_book_state(db, user_book)
    lists_by_name = get_or_create_default_lists(db, user_id)
    target_list_name = list_name_for_status(cast(ReadingStatus, user_book.status))
    if target_list_name and target_list_name in lists_by_name:
        ensure_list_item(
            db,
            list_id=cast(int, lists_by_name[target_list_name].id),
            user_book_id=cast(int, user_book.id),
        )
    db.commit()

    return book


@router.get("/books", response_model=PaginatedBooks)
def list_books(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
):
    """List all books with pagination. Includes user's reading status for each book."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    total = db.query(Book).count()
    books = db.query(Book).offset((page - 1) * page_size).limit(page_size).all()

    for book in books:
        user_book: UserBook | None = (
            db.query(UserBook)
            .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
            .first()
        )
        if user_book:
            project_user_book_state(db, user_book)
        book.user_status = user_book

    pages = (total + page_size - 1) // page_size

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/books/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get a single book by ID. Includes user's reading status."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    user_book: UserBook | None = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
        .first()
    )
    if user_book:
        project_user_book_state(db, user_book)
    book.user_status = user_book

    return book


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Update a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    update_data = book_data.model_dump(exclude_unset=True)

    old_cover_image_url = cast(str | None, book.cover_image_url)
    old_cover_thumbnail_url = cast(str | None, book.cover_thumbnail_url)
    cover_url = update_data.get("cover_image_url")
    if "cover_image_url" in update_data:
        cover_url = update_data.get("cover_image_url")
        if cover_url and cover_url.startswith("http"):
            download_result = await download_cover_image(cover_url)
            if download_result:
                cover_path, thumbnail_path = download_result
                update_data["cover_image_url"] = cover_path
                update_data["cover_thumbnail_url"] = thumbnail_path
        elif not cover_url:
            update_data["cover_thumbnail_url"] = None

    for key, value in update_data.items():
        setattr(book, key, value)

    if "cover_image_url" in update_data and book.cover_image_url != old_cover_image_url:
        actor_user_book = ensure_added_event(
            db, user_id=cast(int, current_user.id), book_id=cast(int, book.id)
        )
        record_cover_changed(
            db,
            user_book_id=cast(int, actor_user_book.id),
            old_cover_image_url=old_cover_image_url,
            new_cover_image_url=cast(str | None, book.cover_image_url),
            old_cover_thumbnail_url=old_cover_thumbnail_url,
            new_cover_thumbnail_url=cast(str | None, book.cover_thumbnail_url),
        )

    db.commit()
    db.refresh(book)

    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
        .first()
    )
    book.user_status = user_book

    return book


@router.delete("/books", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_books(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Delete all books, along with every user's reading state for them.

    Removing user_books first lets the ondelete=CASCADE on book_events and
    book_list_items fire at the DB level, avoiding orphaned rows that would
    otherwise re-link to unrelated books via SQLite primary-key reuse.
    """
    db.query(UserBook).delete(synchronize_session=False)
    db.query(Book).delete(synchronize_session=False)
    db.commit()
    return None


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Delete a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    db.delete(book)
    db.commit()
    return None


@router.post("/books/{book_id}/cover", response_model=BookResponse)
async def upload_book_cover(
    book_id: int,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Upload a cover image for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
        )

    filename = file.filename or ""
    file_extension = filename.rsplit(".", 1)[-1] if "." in filename else None
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:
        extension = CONTENT_TYPE_TO_EXT.get(file.content_type or "", file_extension)
        cover_url, thumbnail_url = store_cover_image(content, extension)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    old_cover_image_url = cast(str | None, book.cover_image_url)
    old_cover_thumbnail_url = cast(str | None, book.cover_thumbnail_url)
    book.cover_image_url = cover_url
    book.cover_thumbnail_url = thumbnail_url
    if cover_url != old_cover_image_url:
        actor_user_book = ensure_added_event(
            db, user_id=cast(int, current_user.id), book_id=cast(int, book.id)
        )
        record_cover_changed(
            db,
            user_book_id=cast(int, actor_user_book.id),
            old_cover_image_url=old_cover_image_url,
            new_cover_image_url=cover_url,
            old_cover_thumbnail_url=old_cover_thumbnail_url,
            new_cover_thumbnail_url=thumbnail_url,
        )
    db.commit()
    db.refresh(book)

    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
        .first()
    )
    book.user_status = user_book

    return book
