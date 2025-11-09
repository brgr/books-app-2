from typing import Annotated
import os
import uuid
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import get_db, engine
from app.auth import get_current_user
from app.models import Base, User, Book, UserBook
from app.schemas import (
    UserResponse,
    BookCreate, BookUpdate, BookResponse, PaginatedBooks,
    UserBookStatusUpdate, UserBookResponse,
    GoogleBookResult
)
from app.config import settings
from app.google_books import search_google_books
from datetime import datetime, UTC

# Ensure database schema exists (useful for fresh local setups)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, debug=settings.debug)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/covers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
@app.get("/users/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current authenticated user info."""
    return current_user


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
def create_book(
    book_data: BookCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new book."""
    book = Book(**book_data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.get("/books", response_model=PaginatedBooks)
def list_books(
    page: int = 1,
    page_size: int = 20,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None
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
        user_book = db.query(UserBook).filter(
            UserBook.user_id == current_user.id,
            UserBook.book_id == book.id
        ).first()
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
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book.id
    ).first()
    book.user_status = user_book

    return book


@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(
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
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Update book with cover URL
    book.cover_image_url = f"/uploads/covers/{unique_filename}"
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

    # Check if user already has this book
    user_book = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.book_id == book_id
    ).first()

    if user_book:
        # Update existing status
        user_book.status = status_data.status
        if status_data.notes is not None:
            user_book.notes = status_data.notes

        # Auto-set timestamps based on status
        from app.models import ReadingStatus
        if status_data.status == ReadingStatus.STARTED and not user_book.started_at:
            user_book.started_at = datetime.now(UTC)
        elif status_data.status == ReadingStatus.FINISHED and not user_book.finished_at:
            user_book.finished_at = datetime.now(UTC)
    else:
        # Create new user book entry
        user_book = UserBook(
            user_id=current_user.id,
            book_id=book_id,
            status=status_data.status,
            notes=status_data.notes
        )

        # Auto-set timestamps based on status
        from app.models import ReadingStatus
        if status_data.status == ReadingStatus.STARTED:
            user_book.started_at = datetime.now(UTC)
        elif status_data.status == ReadingStatus.FINISHED:
            user_book.finished_at = datetime.now(UTC)

        db.add(user_book)

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
