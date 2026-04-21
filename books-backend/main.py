from datetime import datetime, UTC
from decimal import Decimal
from typing import Annotated, cast

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
    UploadFile,
    File,
    Response,
    Request,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    set_auth_cookies,
    set_access_token_cookie,
    clear_auth_cookies,
    REFRESH_TOKEN_COOKIE,
)
from app.book_events import (
    ensure_added_event,
    project_user_book_state,
    record_finished_reading,
    record_note_event,
    record_progress_event,
    record_started_reading,
)
from app.config import settings
from app.database import get_db
from app.google_books import search_google_books, GoogleBooksRateLimitError
from app.image_utils import download_cover_image, store_cover_image, CONTENT_TYPE_TO_EXT
from app.models import (
    User,
    Book,
    UserBook,
    BookEvent,
    BookEventCode,
    ReadingStatus,
    BookList,
    BookListItem,
)
from app.schemas import (
    AccessTokenResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    BookCreate,
    BookUpdate,
    BookResponse,
    PaginatedBooks,
    UserBookStatusUpdate,
    UserBookResponse,
    BookListResponse,
    BookListItemReorderRequest,
    GoogleBookResult,
    UserBooksExportResponse,
    BookEventResponse,
    BookProgressUpdate,
)

app = FastAPI(title=settings.app_name, debug=settings.debug)

DEFAULT_LIST_NAMES = ("To Read", "Finished")
SORT_ORDER_GAP = Decimal("1000")


def _list_name_for_status(status: ReadingStatus) -> str | None:
    if status in {ReadingStatus.WANT_TO_READ, ReadingStatus.STARTED, ReadingStatus.ABANDONED}:
        return "To Read"
    if status == ReadingStatus.FINISHED:
        return "Finished"
    return None


def _get_or_create_default_lists(db: Session, user_id: int) -> dict[str, BookList]:
    existing = (
        db.query(BookList).filter(BookList.user_id == user_id).all()
    )
    lists_by_name = {book_list.name: book_list for book_list in existing}
    for name in DEFAULT_LIST_NAMES:
        if name not in lists_by_name:
            book_list = BookList(user_id=user_id, name=name)
            db.add(book_list)
            db.flush()
            lists_by_name[name] = book_list
    return lists_by_name


def _ensure_list_item(db: Session, list_id: int, user_book_id: int) -> BookListItem:
    item = (
        db.query(BookListItem)
        .filter(
            BookListItem.list_id == list_id,
            BookListItem.user_book_id == user_book_id,
        )
        .first()
    )
    if item is not None:
        return item

    max_sort = (
        db.query(func.max(BookListItem.sort_order))
        .filter(BookListItem.list_id == list_id)
        .scalar()
    )
    next_sort = (max_sort or Decimal("0")) + SORT_ORDER_GAP
    item = BookListItem(list_id=list_id, user_book_id=user_book_id, sort_order=next_sort)
    db.add(item)
    db.flush()
    return item


def _rebalance_list_items(db: Session, list_id: int) -> None:
    items = (
        db.query(BookListItem)
        .filter(BookListItem.list_id == list_id)
        .order_by(BookListItem.sort_order.asc(), BookListItem.id.asc())
        .all()
    )
    for index, item in enumerate(items, start=1):
        item.sort_order = SORT_ORDER_GAP * Decimal(index)

# Add long-lived cache headers for immutable cover uploads.
@app.middleware("http")
async def add_cover_cache_headers(request: Request, call_next):
    response = await call_next(request)
    covers_prefix = f"{settings.uploads_url_prefix}/covers/"
    if request.url.path.startswith(covers_prefix) and response.status_code == 200:
        response.headers.setdefault(
            "Cache-Control", "public, max-age=31536000, immutable"
        )
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
settings.uploads_dir_path.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.uploads_url_prefix,
    StaticFiles(directory=settings.uploads_dir_path),
    name="uploads",
)


@app.post("/token", response_model=TokenResponse)
def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    """OAuth2 password flow: exchange credentials for a JWT access token.

    Sets HttpOnly cookies for browser clients. Also returns tokens in the
    response body for API clients and Swagger UI compatibility.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = str(user.username)
    access_token = create_access_token(username)
    refresh_token = create_refresh_token(username)

    # Set HttpOnly cookies for browser clients
    set_auth_cookies(response, access_token, refresh_token)

    # Also return tokens in body for API clients
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_exp_minutes * 60,
        "refresh_expires_in": settings.jwt_refresh_token_exp_minutes * 60,
    }


@app.post("/auth/refresh", response_model=AccessTokenResponse)
def exchange_refresh_token_for_new_access_token(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    payload: RefreshRequest | None = None,
):
    """Exchange a refresh token for a new access token.

    Accepts refresh token from either:
    1. HttpOnly cookie (preferred for browser clients)
    2. Request body (for API clients)
    """
    # Try cookie first, then request body
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token and payload:
        refresh_token = payload.refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = decode_refresh_token(refresh_token)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(str(user.username))

    # Set new access token cookie for browser clients
    set_access_token_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_exp_minutes * 60,
    }


@app.post("/auth/logout")
def logout(response: Response):
    """Clear authentication cookies to log out the user."""
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@app.get("/users/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current authenticated user info."""
    return current_user


@app.get("/users/me/export", response_model=UserBooksExportResponse)
def export_user_books(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Export the current user's books along with their reading state."""
    # TODO: derive reading state from book events instead of the legacy status fields.
    user_books = (
        db.query(UserBook, Book)
        .join(Book, UserBook.book_id == Book.id)
        .filter(UserBook.user_id == current_user.id)
        .order_by(Book.id.asc())
        .all()
    )

    books_payload = []
    for user_book, book in user_books:
        project_user_book_state(db, user_book)
        books_payload.append(
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "isbn": book.isbn,
                "description": book.description,
                "published_date": book.published_date,
                "page_count": book.page_count,
                "status": user_book.status,
                "notes": user_book.notes,
                "started_at": user_book.started_at,
                "finished_at": user_book.finished_at,
                "current_page": user_book.current_page,
            }
        )

    return {
        "exported_at": datetime.now(UTC),
        "user": current_user,
        "books": books_payload,
    }


@app.get("/")
async def root():
    return {"message": "Welcome to the Books API!"}


# Book list endpoints


@app.get("/lists", response_model=list[BookListResponse])
def list_book_lists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    lists_by_name = _get_or_create_default_lists(db, cast(int, current_user.id))
    db.commit()
    ordered = []
    for name in DEFAULT_LIST_NAMES:
        if name in lists_by_name:
            ordered.append(lists_by_name[name])
    # Include any non-default lists after the defaults
    for book_list in sorted(
        lists_by_name.values(), key=lambda entry: entry.id
    ):
        if book_list.name not in DEFAULT_LIST_NAMES:
            ordered.append(book_list)
    return ordered


@app.get("/lists/{list_id}/books", response_model=PaginatedBooks)
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


@app.post("/lists/{list_id}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
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

    moved_item = _ensure_list_item(db, list_id=list_id, user_book_id=moved_user_book.id)

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
        _rebalance_list_items(db, list_id)
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


# Books CRUD endpoints


@app.get("/books/search", response_model=list[GoogleBookResult])
async def search_books(
    q: str, current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Search for books using the Google Books API.

    Query parameter:
    - q: Search query string
    """
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


@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Create a new book."""
    data = book_data.model_dump()

    # Download cover image if it's an external URL
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

    # Creating a book implies adding it to the user's library (To Read by default).
    user_id = cast(int, current_user.id)
    user_book = ensure_added_event(db, user_id=user_id, book_id=cast(int, book.id))
    project_user_book_state(db, user_book)
    lists_by_name = _get_or_create_default_lists(db, user_id)
    target_list_name = _list_name_for_status(cast(ReadingStatus, user_book.status))
    if target_list_name and target_list_name in lists_by_name:
        _ensure_list_item(
            db,
            list_id=cast(int, lists_by_name[target_list_name].id),
            user_book_id=cast(int, user_book.id),
        )
    db.commit()

    return book


@app.get("/books", response_model=PaginatedBooks)
def list_books(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
):
    """List all books with pagination. Includes user's reading status for each book."""
    # Validate pagination parameters
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    # Get total count
    total = db.query(Book).count()

    # Get paginated books
    books = db.query(Book).offset((page - 1) * page_size).limit(page_size).all()

    # Attach user's reading status to each book
    for book in books:
        user_book: UserBook | None = (
            db.query(UserBook)
            .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
            .first()
        )
        if user_book:
            project_user_book_state(db, user_book)
        book.user_status = user_book

    # Calculate total pages
    pages = (total + page_size - 1) // page_size

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@app.get("/books/{book_id}", response_model=BookResponse)
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

    # Attach user's reading status
    user_book: UserBook | None = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
        .first()
    )
    if user_book:
        project_user_book_state(db, user_book)
    book.user_status = user_book

    return book


@app.put("/books/{book_id}", response_model=BookResponse)
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

    # Update only provided fields
    update_data = book_data.model_dump(exclude_unset=True)

    # Download cover image if it's an external URL
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

    db.commit()
    db.refresh(book)

    # Attach user's reading status
    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
        .first()
    )
    book.user_status = user_book

    return book


@app.delete("/books", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_books(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Delete all books."""
    db.query(Book).delete()
    db.commit()
    return None


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@app.post("/books/{book_id}/cover", response_model=BookResponse)
async def upload_book_cover(
    book_id: int,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Upload a cover image for a book."""
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    # Validate file type
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

    # Update book with cover URLs
    book.cover_image_url = cover_url
    book.cover_thumbnail_url = thumbnail_url
    db.commit()
    db.refresh(book)

    # Attach user's reading status
    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book.id)
        .first()
    )
    book.user_status = user_book

    return book


# Reading status endpoints


@app.put("/books/{book_id}/status", response_model=UserBookResponse)
def set_reading_status(
    book_id: int,
    status_data: UserBookStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Set or update the reading status for a book for the current user."""
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    user_id = cast(int, current_user.id)

    try:
        user_book = ensure_added_event(db, user_id=user_id, book_id=book_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    project_user_book_state(db, user_book)

    user_book_id = cast(int, user_book.id)

    try:
        if (
            status_data.status == ReadingStatus.WANT_TO_READ
            and user_book.status != ReadingStatus.WANT_TO_READ
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revert to 'want_to_read' after reading has started",
            )

        if (
            status_data.status == ReadingStatus.STARTED
            and user_book.status != ReadingStatus.STARTED
        ):
            record_started_reading(db, user_book_id=user_book_id)
        elif (
            status_data.status == ReadingStatus.FINISHED
            and user_book.status != ReadingStatus.FINISHED
        ):
            record_finished_reading(db, user_book_id=user_book_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    notes_provided = "notes" in status_data.model_fields_set
    if notes_provided:
        normalized_notes = status_data.notes
        if normalized_notes == "":
            normalized_notes = None

        if normalized_notes != user_book.notes:
            record_note_event(
                db,
                user_book_id=user_book_id,
                code=BookEventCode.NOTE_SET,
                note=normalized_notes,
            )
            user_book.notes = normalized_notes

    project_user_book_state(db, user_book)

    lists_by_name = _get_or_create_default_lists(db, user_id)
    target_list_name = _list_name_for_status(cast(ReadingStatus, user_book.status))
    target_list_id = (
        lists_by_name[target_list_name].id if target_list_name in lists_by_name else None
    )
    if target_list_id is not None:
        _ensure_list_item(db, list_id=cast(int, target_list_id), user_book_id=user_book_id)

    for list_name, book_list in lists_by_name.items():
        if book_list.id != target_list_id:
            (
                db.query(BookListItem)
                .filter(
                    BookListItem.list_id == book_list.id,
                    BookListItem.user_book_id == user_book_id,
                )
                .delete()
            )
    db.commit()
    db.refresh(user_book)
    return user_book


@app.delete("/books/{book_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def remove_reading_status(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove a book from the current user's reading list."""
    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book_id)
        .first()
    )

    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not in your reading list",
        )

    db.delete(user_book)
    db.commit()
    return None


@app.get("/books/{book_id}/events", response_model=list[BookEventResponse])
def get_book_events(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get all events for a book for the current user, ordered by most recent first."""
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    # Get user's relationship with this book
    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book_id)
        .first()
    )

    if not user_book:
        return []

    # Get all events for this user_book, ordered by occurred_at desc
    events = (
        db.query(BookEvent)
        .options(joinedload(BookEvent.note_entry), joinedload(BookEvent.progress_entry))
        .filter(BookEvent.user_book_id == user_book.id)
        .order_by(BookEvent.occurred_at.desc(), BookEvent.id.desc())
        .all()
    )

    return [
        BookEventResponse(
            id=event.id,
            event_type=event.event_type.code,
            occurred_at=event.occurred_at,
            note=event.note_entry.note if event.note_entry else None,
            page=event.progress_entry.page if event.progress_entry else None,
        )
        for event in events
    ]


@app.post("/books/{book_id}/progress", response_model=UserBookResponse)
def add_progress_event(
    book_id: int,
    progress: BookProgressUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Record a progress event for the current user."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )

    user_book = (
        db.query(UserBook)
        .filter(UserBook.user_id == current_user.id, UserBook.book_id == book_id)
        .first()
    )
    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record progress before starting reading",
        )

    project_user_book_state(db, user_book)
    if user_book.status != ReadingStatus.STARTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record progress before starting reading",
        )

    page = progress.page
    if book.page_count is not None and page > book.page_count:
        page = book.page_count

    record_progress_event(db, user_book_id=user_book.id, page=page)
    user_book.current_page = page
    db.commit()
    db.refresh(user_book)
    return user_book
