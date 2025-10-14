import pytest
from fastapi import status


@pytest.fixture
def created_book(client, auth_headers, sample_book_data):
    """Create a book for testing."""
    response = client.post("/books", json=sample_book_data, headers=auth_headers)
    return response.json()


def test_set_reading_status(client, auth_headers, created_book):
    """Test setting a reading status for a book."""
    book_id = created_book["id"]

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "notes": "Great book so far!"},
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "started"
    assert data["notes"] == "Great book so far!"
    assert data["book_id"] == book_id
    assert "started_at" in data
    assert data["started_at"] is not None


def test_update_reading_status(client, auth_headers, created_book):
    """Test updating an existing reading status."""
    book_id = created_book["id"]

    # Set initial status
    client.put(
        f"/books/{book_id}/status",
        json={"status": "want_to_read"},
        headers=auth_headers
    )

    # Update to started
    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "notes": "Now reading"},
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "started"
    assert data["notes"] == "Now reading"


def test_set_finished_status(client, auth_headers, created_book):
    """Test setting finished status sets finished_at timestamp."""
    book_id = created_book["id"]

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "finished"},
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "finished"
    assert "finished_at" in data
    assert data["finished_at"] is not None


def test_reading_status_on_nonexistent_book(client, auth_headers):
    """Test setting status on a book that doesn't exist."""
    response = client.put(
        "/books/99999/status",
        json={"status": "started"},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_book_list_includes_user_status(client, auth_headers, sample_book_data):
    """Test that book list includes user's reading status."""
    # Create a book
    response = client.post("/books", json=sample_book_data, headers=auth_headers)
    book_id = response.json()["id"]

    # Set reading status
    client.put(
        f"/books/{book_id}/status",
        json={"status": "started"},
        headers=auth_headers
    )

    # List books
    response = client.get("/books", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    books = response.json()["items"]

    book = next(b for b in books if b["id"] == book_id)
    assert book["user_status"] is not None
    assert book["user_status"]["status"] == "started"


def test_get_book_includes_user_status(client, auth_headers, created_book):
    """Test that getting a single book includes user's reading status."""
    book_id = created_book["id"]

    # Set reading status
    client.put(
        f"/books/{book_id}/status",
        json={"status": "finished", "notes": "Excellent!"},
        headers=auth_headers
    )

    # Get the book
    response = client.get(f"/books/{book_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    book = response.json()

    assert book["user_status"] is not None
    assert book["user_status"]["status"] == "finished"
    assert book["user_status"]["notes"] == "Excellent!"


def test_remove_reading_status(client, auth_headers, created_book):
    """Test removing a book from reading list."""
    book_id = created_book["id"]

    # Set reading status
    client.put(
        f"/books/{book_id}/status",
        json={"status": "started"},
        headers=auth_headers
    )

    # Remove status
    response = client.delete(f"/books/{book_id}/status", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's removed - book should now have null status
    response = client.get(f"/books/{book_id}", headers=auth_headers)
    book = response.json()
    assert book["user_status"] is None


def test_remove_nonexistent_reading_status(client, auth_headers, created_book):
    """Test removing a reading status that doesn't exist."""
    book_id = created_book["id"]

    response = client.delete(f"/books/{book_id}/status", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_reading_status_requires_auth(client, created_book):
    """Test that reading status endpoints require authentication."""
    book_id = created_book["id"]

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_different_users_have_separate_statuses(client, sample_book_data):
    """Test that different users can have different statuses for the same book."""
    # Create first user and book
    user1_creds = {"username": "user1", "password": "pass123"}
    client.post("/register", json=user1_creds)

    from base64 import b64encode
    user1_auth = b64encode(f"{user1_creds['username']}:{user1_creds['password']}".encode()).decode()
    user1_headers = {"Authorization": f"Basic {user1_auth}"}

    book_response = client.post("/books", json=sample_book_data, headers=user1_headers)
    book_id = book_response.json()["id"]

    # User1 sets status to "started"
    client.put(f"/books/{book_id}/status", json={"status": "started"}, headers=user1_headers)

    # Create second user
    user2_creds = {"username": "user2", "password": "pass123"}
    client.post("/register", json=user2_creds)

    user2_auth = b64encode(f"{user2_creds['username']}:{user2_creds['password']}".encode()).decode()
    user2_headers = {"Authorization": f"Basic {user2_auth}"}

    # User2 sets status to "finished"
    client.put(f"/books/{book_id}/status", json={"status": "finished"}, headers=user2_headers)

    # Verify each user sees their own status
    response1 = client.get(f"/books/{book_id}", headers=user1_headers)
    assert response1.json()["user_status"]["status"] == "started"

    response2 = client.get(f"/books/{book_id}", headers=user2_headers)
    assert response2.json()["user_status"]["status"] == "finished"
