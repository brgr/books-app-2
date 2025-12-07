from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pwdlib import PasswordHash
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

# Password hashing context
pwd_context = PasswordHash.recommended()

# HTTP Basic Auth
security = HTTPBasic()


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


def get_current_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """Dependency to get the current authenticated user."""
    user = authenticate_user(db, credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
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
