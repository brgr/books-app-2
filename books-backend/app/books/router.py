from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.books.queries import get_book_by_id, get_user_book
from app.books.service import BookService
from app.cover_upgrade import get_job
from app.database import get_db
from app.google_books import (
    GoogleBooksRateLimitError,
    search_cover_images,
    search_google_books,
)
from app.image_utils import CONTENT_TYPE_TO_EXT, store_cover_image
from app.models import Book, User
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


def get_book_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookService:
    return BookService(db, current_user)


def get_library_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Book:
    """Load a book from the acting user's library, or 404 if it isn't in it."""
    book = get_book_by_id(db, book_id)

    # noinspection PyTypeChecker
    if not book or not get_user_book(db, user_id=current_user.id, book_id=book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    return book


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
    service: Annotated[BookService, Depends(get_book_service)],
):
    """Kick off an async search for higher-resolution versions of this cover."""
    book = get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    user_book = get_user_book(db, user_id=current_user.id, book_id=book.id)
    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    cover_path = book.cover_image_url
    if not cover_path or cover_path.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book has no local cover to upgrade",
        )
    job = service.start_cover_upgrade(book, cover_path)
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
    service: Annotated[BookService, Depends(get_book_service)],
):
    """Create a new book."""
    return await service.create(book_data)


@router.get("/books", response_model=PaginatedBooks)
def list_books(
    service: Annotated[BookService, Depends(get_book_service)],
    page: int = 1,
    page_size: int = 20,
):
    """List all books with pagination. Includes user's reading status for each book."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    books, total = service.list(page, page_size)
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
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[BookService, Depends(get_book_service)],
):
    """Get a single book from the user's library. Includes reading status."""
    return service.attach_status(book)


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[BookService, Depends(get_book_service)],
):
    """Update a book."""
    book = get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return await service.update(book, book_data)


@router.delete("/books", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_books(
    service: Annotated[BookService, Depends(get_book_service)],
):
    """Delete all books, along with every user's reading state for them."""
    service.delete_all()
    return None


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book: Annotated[Book, Depends(get_library_book)],
    service: Annotated[BookService, Depends(get_book_service)],
):
    """Remove a book from the current user's library."""
    service.remove_from_library(book)
    return None


@router.post("/books/{book_id}/cover", response_model=BookResponse)
async def upload_book_cover(
    book_id: int,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[BookService, Depends(get_book_service)],
):
    """Upload a cover image for a book."""
    book = get_book_by_id(db, book_id)
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

    return service.set_cover(book, cover_url, thumbnail_url)
