from datetime import datetime, timedelta, UTC

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
        headers=auth_headers,
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
        headers=auth_headers,
    )

    # Update to started
    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "notes": "Now reading"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "started"
    assert data["notes"] == "Now reading"


def test_set_finished_status(client, auth_headers, created_book):
    """Finishing requires a start event and sets finished_at."""
    book_id = created_book["id"]

    # Attempting to finish without starting should fail
    response = client.put(
        f"/books/{book_id}/status", json={"status": "finished"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot finish reading before starting" in response.json()["detail"]

    # Start then finish
    response = client.put(
        f"/books/{book_id}/status", json={"status": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/books/{book_id}/status", json={"status": "finished"}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "finished"
    assert "finished_at" in data
    assert data["finished_at"] is not None


def test_reading_status_on_nonexistent_book(client, auth_headers):
    """Test setting status on a book that doesn't exist."""
    response = client.put(
        "/books/99999/status", json={"status": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_book_list_includes_user_status(client, auth_headers, sample_book_data):
    """Test that book list includes user's reading status."""
    # Create a book
    response = client.post("/books", json=sample_book_data, headers=auth_headers)
    book_id = response.json()["id"]

    # Set reading status
    client.put(
        f"/books/{book_id}/status", json={"status": "started"}, headers=auth_headers
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
        f"/books/{book_id}/status", json={"status": "started"}, headers=auth_headers
    )
    client.put(
        f"/books/{book_id}/status",
        json={"status": "finished", "notes": "Excellent!"},
        headers=auth_headers,
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
        f"/books/{book_id}/status", json={"status": "started"}, headers=auth_headers
    )

    # Remove status
    response = client.delete(f"/books/{book_id}/status", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's removed - book should now have null status
    response = client.get(f"/books/{book_id}", headers=auth_headers)
    book = response.json()
    assert book["user_status"] is None


def test_cannot_revert_to_want_after_start(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.put(
        f"/books/{book_id}/status", json={"status": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot revert to 'want_to_read'" in response.json()["detail"]


def test_remove_nonexistent_reading_status(client, auth_headers, created_book):
    """Test removing a reading status that doesn't exist."""
    book_id = created_book["id"]

    # Creating a book auto-assigns a status; remove it first so we can test the 404 path.
    client.delete(f"/books/{book_id}/status", headers=auth_headers)

    response = client.delete(f"/books/{book_id}/status", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_reading_status_requires_auth(client, created_book):
    """Test that reading status endpoints require authentication."""
    book_id = created_book["id"]

    client.cookies.clear()
    response = client.put(f"/books/{book_id}/status", json={"status": "started"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_note_events_are_recorded(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "notes": "First note"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "notes": "Updated note"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "notes": ""},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    events_response = client.get(f"/books/{book_id}/events", headers=auth_headers)
    assert events_response.status_code == status.HTTP_200_OK
    event_types = [event["event_type"] for event in events_response.json()]

    assert "note_set" in event_types


def test_progress_requires_start(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.post(
        f"/books/{book_id}/progress", json={"page": 10}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot record progress before starting" in response.json()["detail"]


def test_set_started_with_custom_occurred_at(client, auth_headers, created_book):
    """Start reading can be backdated via occurred_at."""
    book_id = created_book["id"]
    backdated = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "occurred_at": backdated.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "started"
    returned = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
    if returned.tzinfo is None:
        returned = returned.replace(tzinfo=UTC)
    assert returned == backdated


def test_set_finished_with_custom_occurred_at(client, auth_headers, created_book):
    """Finish reading can be backdated via occurred_at."""
    book_id = created_book["id"]
    started_at = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    finished_at = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "occurred_at": started_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "finished", "occurred_at": finished_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "finished"
    returned = datetime.fromisoformat(data["finished_at"].replace("Z", "+00:00"))
    if returned.tzinfo is None:
        returned = returned.replace(tzinfo=UTC)
    assert returned == finished_at


def test_occurred_at_cannot_be_in_the_future(client, auth_headers, created_book):
    """Backdating must not accept future timestamps."""
    book_id = created_book["id"]
    future = datetime.now(UTC) + timedelta(days=2)

    response = client.put(
        f"/books/{book_id}/status",
        json={"status": "started", "occurred_at": future.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "future" in response.json()["detail"].lower()


def test_progress_clamps_to_page_count(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.put(
        f"/books/{book_id}/status", json={"status": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        f"/books/{book_id}/progress", json={"page": 9999}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_page"] == created_book["page_count"]

    events_response = client.get(f"/books/{book_id}/events", headers=auth_headers)
    assert events_response.status_code == status.HTTP_200_OK
    progress_events = [
        event
        for event in events_response.json()
        if event["event_type"] == "progress_set"
    ]
    assert progress_events
    assert progress_events[0]["page"] == created_book["page_count"]
