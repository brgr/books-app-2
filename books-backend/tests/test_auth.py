import pytest
from fastapi import status

from app.auth import create_user


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
    from base64 import b64encode

    # Wrong password
    credentials = f"{test_user['username']}:wrongpassword"
    encoded = b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {encoded}"}

    response = client.get("/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Non-existent user
    credentials = "nonexistent:password"
    encoded = b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {encoded}"}

    response = client.get("/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_single_user_limit(db_session, test_user_credentials):
    """Ensure only one user can be created."""
    create_user(db_session, test_user_credentials["username"], test_user_credentials["password"])

    with pytest.raises(ValueError):
        create_user(db_session, "anotheruser", "anotherpass123")
