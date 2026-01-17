from datetime import datetime, timedelta, UTC

import jwt
import pytest
from fastapi import status

from app.auth import create_user
from app.config import settings


def test_get_current_user(client, test_user, auth_headers):
    """Test getting current user info."""
    response = client.get("/users/me", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == test_user["username"]
    assert "id" in data


def test_authentication_required(client, test_user):
    """Test that endpoints require authentication."""
    # Try without auth
    response = client.get("/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_credentials(client, test_user):
    """Test authentication with invalid credentials."""
    # Wrong password
    response = client.post(
        "/token",
        data={"username": test_user["username"], "password": "wrongpassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Non-existent user
    response = client.post(
        "/token",
        data={"username": "nonexistent", "password": "password"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_token(client, test_user):
    """Test refreshing an access token."""
    login_response = client.post("/token", data=test_user)
    assert login_response.status_code == status.HTTP_200_OK
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == status.HTTP_200_OK
    data = refresh_response.json()
    assert "access_token" in data


def test_refresh_token_reuse(client, test_user):
    """Refresh tokens can be reused until expiry (no rotation yet)."""
    login_response = client.post("/token", data=test_user)
    refresh_token = login_response.json()["refresh_token"]

    first = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    second = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK


def test_refresh_token_not_valid_for_access(client, test_user):
    """Refresh tokens should not authorize protected endpoints."""
    login_response = client.post("/token", data=test_user)
    refresh_token = login_response.json()["refresh_token"]

    response = client.get("/users/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_expired_tokens_rejected(client, test_user):
    """Expired tokens should be rejected for both access and refresh."""
    expired = datetime.now(UTC) - timedelta(minutes=1)
    access_token = jwt.encode(
        {"sub": test_user["username"], "typ": "access", "exp": expired},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    refresh_token = jwt.encode(
        {"sub": test_user["username"], "typ": "refresh", "exp": expired},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    access_response = client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})
    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert access_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_single_user_limit(db_session, test_user_credentials):
    """Ensure only one user can be created."""
    create_user(db_session, test_user_credentials["username"], test_user_credentials["password"])

    with pytest.raises(ValueError):
        create_user(db_session, "anotheruser", "anotherpass123")
