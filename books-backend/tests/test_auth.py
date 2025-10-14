import pytest
from fastapi import status


def test_register_user(client):
    """Test user registration."""
    response = client.post("/register", json={
        "username": "newuser",
        "password": "securepass123"
    })

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "newuser"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_username(client, test_user):
    """Test registering with an existing username fails."""
    response = client.post("/register", json={
        "username": test_user["username"],
        "password": "differentpass"
    })

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"].lower()


def test_register_invalid_data(client):
    """Test registration with invalid data."""
    # Too short username
    response = client.post("/register", json={
        "username": "ab",
        "password": "validpass123"
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Too short password
    response = client.post("/register", json={
        "username": "validuser",
        "password": "short"
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


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
