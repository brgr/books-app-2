import shutil
import uuid
from datetime import datetime, UTC
from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
)
from app.book_events import (
    ensure_added_event,
    project_user_book_state,
    record_finished_reading,
    record_started_reading,
)
from app.config import settings
from app.database import get_db
from app.google_books import search_google_books
from app.image_utils import download_cover_image
from app.models import User, Book, UserBook, BookEvent
from app.schemas import (
    AccessTokenResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    BookCreate, BookUpdate, BookResponse, PaginatedBooks,
    UserBookStatusUpdate, UserBookResponse,
    GoogleBookResult,
    UserBooksExportResponse,
    BookEventResponse,
)

app = FastAPI(title=settings.app_name, debug=settings.debug)

# Configure CORS
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
COVERS_DIR = settings.uploads_dir_path / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for uploaded images
app.mount(settings.uploads_url_prefix, StaticFiles(directory=settings.uploads_dir_path), name="uploads")


@app.post("/token", response_model=TokenResponse)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    """OAuth2 password flow: exchange credentials for a JWT access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = str(user.username)
    token = create_access_token(username)
    refresh_token = create_refresh_token(username)
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_exp_minutes * 60,
        "refresh_expires_in": settings.jwt_refresh_token_exp_minutes * 60,
    }


@app.post("/auth/refresh", response_model=AccessTokenResponse)
def exchange_refresh_token_for_new_access_token(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]):
    """Exchange a refresh token for a new access token."""
    username = decode_refresh_token(payload.refresh_token)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(str(user.username))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_exp_minutes * 60,
    }


@app.get("/users/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current authenticated user info."""
    return current_user


@app.get("/users/me/export", response_model=UserBooksExportResponse)
def export_user_books(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
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
        books_payload.append({
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
            "finished_at": user_book.finished_at
        })

    return {
        "exported_at": datetime.now(UTC),
        "user": current_user,
        "books": books_payload
    }


@app.get("/")
async def root():
    return {"message": "Welcome to the Books API!"}


# Books CRUD endpoints

@app.get("/books/search", response_model=list[GoogleBookResult])
async def search_books(
        q: str,
        current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Search for books using the Google Books API.

    Query parameter:
    - q: Search query string
    """
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )

    results = await search_google_books(q)
    return results


@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
        book_data: BookCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Create a new book."""
    data = book_data.model_dump()

    # Download cover image if it's an external URL
    cover_url = data.get("cover_image_url")
    if cover_url and cover_url.startswith("http"):
        local_path = await download_cover_image(cover_url)
        if local_path:
            data["cover_image_url"] = local_path

    book = Book(**data)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.get("/books", response_model=PaginatedBooks)
def list_books(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
        page: int = 1,
        page_size: int = 20
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
        user_book: UserBook | None = db.query(UserBook).filter(
            UserBook.user_id == current_user.id,
            UserBook.book_id == book.id
        ).first()
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
        "pages": pages
    }


@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(
        book_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Get a single book by ID. Includes user's reading status."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Attach user's reading status
    user_book: UserBook | None = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book.id
    ).first()
    if user_book:
        project_user_book_state(db, user_book)
    book.user_status = user_book

    return book


@app.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
        book_id: int,
        book_data: BookUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Update a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Update only provided fields
    update_data = book_data.model_dump(exclude_unset=True)

    # Download cover image if it's an external URL
    cover_url = update_data.get("cover_image_url")
    if cover_url and cover_url.startswith("http"):
        local_path = await download_cover_image(cover_url)
        if local_path:
            update_data["cover_image_url"] = local_path

    for key, value in update_data.items():
        setattr(book, key, value)

    db.commit()
    db.refresh(book)

    # Attach user's reading status
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book.id
    ).first()
    book.user_status = user_book

    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
        book_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Delete a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    db.delete(book)
    db.commit()
    return None


@app.post("/books/{book_id}/cover", response_model=BookResponse)
async def upload_book_cover(
        book_id: int,
        file: Annotated[UploadFile, File(...)],
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Upload a cover image for a book."""
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )

    # Generate unique filename
    filename = file.filename or ""
    file_extension = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = COVERS_DIR / unique_filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            # noinspection PyTypeChecker
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Update book with cover URL
    book.cover_image_url = f"{settings.uploads_url_prefix}/covers/{unique_filename}"
    db.commit()
    db.refresh(book)

    # Attach user's reading status
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book.id
    ).first()
    book.user_status = user_book

    return book


# Reading status endpoints

@app.put("/books/{book_id}/status", response_model=UserBookResponse)
def set_reading_status(
        book_id: int,
        status_data: UserBookStatusUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Set or update the reading status for a book for the current user."""
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    from app.models import ReadingStatus

    user_id = cast(int, current_user.id)

    try:
        user_book = ensure_added_event(db, user_id=user_id, book_id=book_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Reset notes if explicitly provided
    if status_data.notes is not None:
        user_book.notes = status_data.notes

    project_user_book_state(db, user_book)
    if status_data.status == ReadingStatus.WANT_TO_READ and user_book.status != ReadingStatus.WANT_TO_READ:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revert to 'want_to_read' after reading has started",
        )

    user_book_id = cast(int, user_book.id)

    try:
        if status_data.status == ReadingStatus.STARTED:
            record_started_reading(db, user_book_id=user_book_id)
        elif status_data.status == ReadingStatus.FINISHED:
            record_finished_reading(db, user_book_id=user_book_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    project_user_book_state(db, user_book)
    db.commit()
    db.refresh(user_book)
    return user_book


@app.delete("/books/{book_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def remove_reading_status(
        book_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Remove a book from the current user's reading list."""
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book_id
    ).first()

    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not in your reading list"
        )

    db.delete(user_book)
    db.commit()
    return None


@app.get("/books/{book_id}/events", response_model=list[BookEventResponse])
def get_book_events(
        book_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
):
    """Get all events for a book for the current user, ordered by most recent first."""
    # Check if book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    # Get user's relationship with this book
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book_id
    ).first()

    if not user_book:
        return []

    # Get all events for this user_book, ordered by occurred_at desc
    events = (
        db.query(BookEvent)
        .filter(BookEvent.user_book_id == user_book.id)
        .order_by(BookEvent.occurred_at.desc(), BookEvent.id.desc())
        .all()
    )

    return [
        BookEventResponse(
            id=event.id,
            event_type=event.event_type.code,
            occurred_at=event.occurred_at,
        )
        for event in events
    ]
