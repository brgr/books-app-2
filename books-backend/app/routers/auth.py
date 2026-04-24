from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import (
    REFRESH_TOKEN_COOKIE,
    authenticate_user,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    set_access_token_cookie,
    set_auth_cookies,
)
from app.book_events import project_user_book_state
from app.config import settings
from app.database import get_db
from app.models import Book, User, UserBook
from app.schemas import (
    AccessTokenResponse,
    RefreshRequest,
    TokenResponse,
    UserBooksExportResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
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

    set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_exp_minutes * 60,
        "refresh_expires_in": settings.jwt_refresh_token_exp_minutes * 60,
    }


@router.post("/auth/refresh", response_model=AccessTokenResponse)
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
    set_access_token_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_exp_minutes * 60,
    }


@router.post("/auth/logout")
def logout(response: Response):
    """Clear authentication cookies to log out the user."""
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/users/me", response_model=UserResponse)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current authenticated user info."""
    return current_user


@router.get("/users/me/export", response_model=UserBooksExportResponse)
def export_user_books(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Export the current user's books along with their reading state."""
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
