from datetime import datetime, timedelta, UTC

import pytest
from fastapi import status


@pytest.fixture
def created_book(client, auth_headers, sample_book_data):
    """Create a book for testing."""
    response = client.post("/api/books", json=sample_book_data, headers=auth_headers)
    return response.json()


def test_set_shelf(client, auth_headers, created_book):
    """Test setting a shelf for a book."""
    book_id = created_book["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "notes": "Great book so far!"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shelf"] == "started"
    assert data["notes"] == "Great book so far!"
    assert data["book_id"] == book_id
    assert "started_at" in data
    assert data["started_at"] is not None


def test_update_shelf(client, auth_headers, created_book):
    """Test updating an existing shelf assignment."""
    book_id = created_book["id"]

    # Set the initial shelf
    client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "want_to_read"},
        headers=auth_headers,
    )

    # Update to started
    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "notes": "Now reading"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shelf"] == "started"
    assert data["notes"] == "Now reading"


def test_set_finished_shelf(client, auth_headers, created_book):
    """Finishing requires a start event and sets finished_at."""
    book_id = created_book["id"]

    # Attempting to finish without starting should fail
    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "finished"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot finish reading before starting" in response.json()["detail"]

    # Start then finish
    response = client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "finished"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shelf"] == "finished"
    assert "finished_at" in data
    assert data["finished_at"] is not None


def test_set_shelf_on_nonexistent_book(client, auth_headers):
    """Test setting a shelf on a book that doesn't exist."""
    response = client.put(
        "/api/books/99999/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_book_list_includes_user_book(client, auth_headers, sample_book_data):
    """Test that the book list includes the user's shelf entry."""
    # Create a book
    response = client.post("/api/books", json=sample_book_data, headers=auth_headers)
    book_id = response.json()["id"]

    # Put it on a shelf
    client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )

    # List books
    response = client.get("/api/books", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    books = response.json()["items"]

    book = next(b for b in books if b["id"] == book_id)
    assert book["user_book"] is not None
    assert book["user_book"]["shelf"] == "started"


def test_get_book_includes_user_book(client, auth_headers, created_book):
    """Test that getting a single book includes the user's shelf entry."""
    book_id = created_book["id"]

    # Put it on a shelf
    client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "finished", "notes": "Excellent!"},
        headers=auth_headers,
    )

    # Get the book
    response = client.get(f"/api/books/{book_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    book = response.json()

    assert book["user_book"] is not None
    assert book["user_book"]["shelf"] == "finished"
    assert book["user_book"]["notes"] == "Excellent!"


def test_remove_from_library(client, auth_headers, created_book):
    """Test removing a book from the library."""
    book_id = created_book["id"]

    # Put it on a shelf
    client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )

    # Remove it from the library
    response = client.delete(f"/api/books/{book_id}/shelf", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's removed - the book is no longer in the user's library
    response = client.get(f"/api/books/{book_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_cannot_revert_to_want_after_start(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot revert to 'want_to_read'" in response.json()["detail"]


def test_remove_nonexistent_shelf_entry(client, auth_headers, created_book):
    """Test removing a shelf entry that doesn't exist."""
    book_id = created_book["id"]

    # Creating a book auto-assigns a shelf; remove it first so we can test the 404 path.
    client.delete(f"/api/books/{book_id}/shelf", headers=auth_headers)

    response = client.delete(f"/api/books/{book_id}/shelf", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_shelf_endpoints_require_auth(client, created_book):
    """Test that the shelf endpoints require authentication."""
    book_id = created_book["id"]

    client.cookies.clear()
    response = client.put(f"/api/books/{book_id}/shelf", json={"shelf": "started"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_note_events_are_recorded(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "notes": "First note"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "notes": "Updated note"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "notes": ""},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    events_response = client.get(f"/api/books/{book_id}/events", headers=auth_headers)
    assert events_response.status_code == status.HTTP_200_OK
    event_types = [event["event_type"] for event in events_response.json()]

    assert "note_set" in event_types


def test_progress_requires_start(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.post(
        f"/api/books/{book_id}/progress", json={"page": 10}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot record progress before starting" in response.json()["detail"]


def test_set_started_with_custom_occurred_at(client, auth_headers, created_book):
    """Start reading can be backdated via occurred_at."""
    book_id = created_book["id"]
    backdated = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "occurred_at": backdated.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shelf"] == "started"
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
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "occurred_at": started_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "finished", "occurred_at": finished_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shelf"] == "finished"
    returned = datetime.fromisoformat(data["finished_at"].replace("Z", "+00:00"))
    if returned.tzinfo is None:
        returned = returned.replace(tzinfo=UTC)
    assert returned == finished_at


def test_occurred_at_cannot_be_in_the_future(client, auth_headers, created_book):
    """Backdating must not accept future timestamps."""
    book_id = created_book["id"]
    future = datetime.now(UTC) + timedelta(days=2)

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "occurred_at": future.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "future" in response.json()["detail"].lower()


def test_progress_clamps_to_page_count(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        f"/api/books/{book_id}/progress", json={"page": 9999}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_page"] == created_book["page_count"]

    events_response = client.get(f"/api/books/{book_id}/events", headers=auth_headers)
    assert events_response.status_code == status.HTTP_200_OK
    progress_events = [
        event
        for event in events_response.json()
        if event["event_type"] == "progress_set"
    ]
    assert progress_events
    assert progress_events[0]["page"] == created_book["page_count"]


def _start_reading(client, auth_headers, book_id):
    response = client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK


def test_progress_accepts_percent_only(client, auth_headers, created_book):
    """Progress can be recorded as a percent without a page."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress", json={"percent": 42.5}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_percent"] == 42.5
    assert data["current_page"] is None

    events = client.get(f"/api/books/{book_id}/events", headers=auth_headers).json()
    progress = [e for e in events if e["event_type"] == "progress_set"]
    assert progress[0]["percent"] == 42.5
    assert progress[0]["page"] is None


def test_progress_accepts_page_and_percent(client, auth_headers, created_book):
    """Page and percent can be recorded together and are stored independently."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress",
        json={"page": 10, "percent": 3.5},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_page"] == 10
    assert data["current_percent"] == 3.5


def test_progress_percent_replaces_page(client, auth_headers, created_book):
    """The latest progress event wins; a later percent-only event clears the page."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    client.post(
        f"/api/books/{book_id}/progress", json={"page": 10}, headers=auth_headers
    )
    response = client.post(
        f"/api/books/{book_id}/progress", json={"percent": 50}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_percent"] == 50
    assert data["current_page"] is None


def test_progress_requires_page_or_percent(client, auth_headers, created_book):
    """A progress request with neither page nor percent is rejected."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress", json={}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_progress_percent_out_of_range(client, auth_headers, created_book):
    """Percent must be between 0 and 100."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress", json={"percent": 150}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
