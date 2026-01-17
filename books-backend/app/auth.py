from datetime import datetime, timedelta, UTC
from typing import Annotated, Literal

import jwt
from jwt import ExpiredSignatureError, PyJWTError
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

# Cookie names
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"

# Password hashing context
pwd_context = PasswordHash.recommended()

# OAuth2 Password flow with Bearer tokens (kept for Swagger UI compatibility)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_username(db: Session, username: str) -> User | None:
    """Get a user by username."""
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Authenticate a user by username and password."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not isinstance(user.hashed_password, str):
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(subject: str) -> str:
    """Create a signed JWT for the given subject."""
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_exp_minutes
    )
    payload = {"sub": subject, "typ": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create a signed refresh JWT for the given subject."""
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_refresh_token_exp_minutes
    )
    payload = {"sub": subject, "typ": "refresh", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HttpOnly authentication cookies on the response."""
    # SameSite must be a valid literal type
    samesite: Literal["lax", "strict", "none"] = "lax"
    if settings.cookie_samesite.lower() in ("lax", "strict", "none"):
        samesite = settings.cookie_samesite.lower()  # type: ignore[assignment]

    # Access token cookie
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=settings.jwt_access_token_exp_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite,
        domain=settings.cookie_domain,
        path="/",
    )

    # Refresh token cookie
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=settings.jwt_refresh_token_exp_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def set_access_token_cookie(response: Response, access_token: str) -> None:
    """Set only the access token cookie (used during refresh)."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    if settings.cookie_samesite.lower() in ("lax", "strict", "none"):
        samesite = settings.cookie_samesite.lower()  # type: ignore[assignment]

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=settings.jwt_access_token_exp_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE, path="/", domain=settings.cookie_domain
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE, path="/", domain=settings.cookie_domain
    )


def _decode_token(token: str) -> dict:
    """Decode a JWT and return its payload."""
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def decode_access_token(token: str) -> str:
    """Decode an access JWT and return the subject."""
    payload = _decode_token(token)
    if payload.get("typ") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject


def decode_refresh_token(token: str) -> str:
    """Decode a refresh JWT and return the subject."""
    payload = _decode_token(token)
    if payload.get("typ") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject


def get_current_user(
    request: Request,
    bearer_token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Dependency to get the current authenticated user.

    Checks for authentication in the following order:
    1. HttpOnly cookie (preferred for browser clients)
    2. Authorization header (for API clients and Swagger UI)
    """
    # Try cookie first
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)

    # Fall back to Authorization header
    if not token:
        token = bearer_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = decode_access_token(token)
    user = get_user_by_username(db, username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def create_user(db: Session, username: str, password: str) -> User:
    """Create the single allowed user account. For now, we basically don't allow further users."""
    existing_users = db.query(func.count(User.id)).scalar()
    if existing_users and existing_users > 0:
        raise ValueError("A user already exists.")

    hashed_password = hash_password(password)
    user = User(username=username, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
