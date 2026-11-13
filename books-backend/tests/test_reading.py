from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status


def full_reading_date(value: datetime) -> dict[str, str]:
    return {"value": value.isoformat(), "precision": "day"}


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


def test_set_and_clear_rating(client, auth_headers, created_book):
    book_id = created_book["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/rating",
        json={"rating": 4.5},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["rating"] == 4.5

    events = client.get(f"/api/books/{book_id}/events", headers=auth_headers).json()
    rating_events = [event for event in events if event["event_type"] == "rating_set"]
    assert [event["rating"] for event in rating_events] == [4.5]

    response = client.delete(
        f"/api/books/{book_id}/rating",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    events = client.get(f"/api/books/{book_id}/events", headers=auth_headers).json()
    rating_events = [event for event in events if event["event_type"] == "rating_set"]
    assert [event["rating"] for event in rating_events] == [None, 4.5]

    response = client.get(f"/api/books/{book_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_book"]["rating"] is None


@pytest.mark.parametrize("rating", [0, 0.25, 5.5])
def test_set_rating_rejects_invalid_rating(client, auth_headers, created_book, rating):
    client.put(
        f"/api/books/{created_book['id']}/shelf",
        json={"shelf": "want_to_read"},
        headers=auth_headers,
    )
    response = client.put(
        f"/api/books/{created_book['id']}/rating",
        json={"rating": rating},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


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
        f"/api/books/{book_id}/progress",
        json={"unit": "page", "value": 10},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot record progress before starting" in response.json()["detail"]


def test_set_started_with_custom_occurred_at(client, auth_headers, created_book):
    """A full API reading date is stored and returned with day precision."""
    book_id = created_book["id"]
    backdated = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "reading_date": full_reading_date(backdated)},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shelf"] == "started"
    assert data["started_at"]["precision"] == "day"
    returned = datetime.fromisoformat(data["started_at"]["value"])
    if returned.tzinfo is None:
        returned = returned.replace(tzinfo=UTC)
    assert returned == backdated.replace(hour=0, minute=0, second=0, microsecond=0)


def test_set_shelf_accepts_partial_and_unknown_reading_dates(
    client, auth_headers, created_book
):
    book_id = created_book["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={
            "shelf": "started",
            "reading_date": {"value": "2026-04-18T12:00:00Z", "precision": "month"},
        },
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["started_at"] == {
        "value": "2026-04-01T00:00:00",
        "precision": "month",
    }

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={
            "shelf": "finished",
            "reading_date": {"value": None, "precision": "unknown"},
        },
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["finished_at"] == {"value": None, "precision": "unknown"}


def test_set_finished_with_custom_occurred_at(client, auth_headers, created_book):
    book_id = created_book["id"]
    started_at = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    finished_at = datetime(2026, 2, 1, 12, 0, 0, tzinfo=UTC)

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "reading_date": full_reading_date(started_at)},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "finished", "reading_date": full_reading_date(finished_at)},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["shelf"] == "finished"
    assert data["finished_at"]["precision"] == "day"
    returned = datetime.fromisoformat(data["finished_at"]["value"])
    if returned.tzinfo is None:
        returned = returned.replace(tzinfo=UTC)
    assert returned == finished_at.replace(hour=0, minute=0, second=0, microsecond=0)


def test_finish_can_precede_start_reading_date(client, auth_headers, created_book):
    """Reading-date chronology is distinct from the ordered event stream."""
    book_id = created_book["id"]
    started_at = datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
    # Note: The finished_at is before the started_at, which should trigger a validation error
    invalid_finished_at = datetime(2026, 1, 9, 12, 0, 0, tzinfo=UTC)

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "reading_date": full_reading_date(started_at)},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={
            "shelf": "finished",
            "reading_date": full_reading_date(invalid_finished_at),
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK


def test_occurred_at_cannot_be_in_the_future(client, auth_headers, created_book):
    """Backdating must not accept future timestamps."""
    book_id = created_book["id"]
    future = datetime.now(UTC) + timedelta(days=2)

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "started", "reading_date": full_reading_date(future)},
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
        f"/api/books/{book_id}/progress",
        json={"unit": "page", "value": 9999},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["progress"] == {"unit": "page", "value": created_book["page_count"]}

    events_response = client.get(f"/api/books/{book_id}/events", headers=auth_headers)
    assert events_response.status_code == status.HTTP_200_OK
    progress_events = [
        event
        for event in events_response.json()
        if event["event_type"] == "progress_set"
    ]
    assert progress_events
    assert progress_events[0]["progress"] == {
        "unit": "page",
        "value": created_book["page_count"],
    }


def _start_reading(client, auth_headers, book_id):
    response = client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("percent", [42.5, 100])
def test_progress_accepts_percent_only(client, auth_headers, created_book, percent):
    """Progress can be recorded as a percent without a page."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress",
        json={"unit": "percent", "value": percent},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["progress"] == {"unit": "percent", "value": percent}

    events = client.get(f"/api/books/{book_id}/events", headers=auth_headers).json()
    progress = [e for e in events if e["event_type"] == "progress_set"]
    assert progress[0]["progress"] == {"unit": "percent", "value": percent}


@pytest.mark.parametrize(
    "progress",
    [
        {"page": 10, "percent": 3.5},
        {"page": 0, "percent": 0},
        {"page": 0, "percent": 3.5},
        {"page": 10, "percent": 0},
        {"page": 10},
        {"percent": 42.5},
        {"unit": "unknown", "value": 10},
        {"unit": "page", "value": -1},
        {"unit": "page", "value": 1.5},
        {"unit": "percent", "value": -1},
        {"unit": "page", "value": 10, "percent": 3.5},
        {"unit": "percent", "value": 3.5, "page": 10},
    ],
)
def test_progress_rejects_invalid_payload(client, auth_headers, created_book, progress):
    """Reject invalid progress without changing the current position or history."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress",
        json={"unit": "page", "value": 5},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.post(
        f"/api/books/{book_id}/progress",
        json=progress,
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    data = client.get(f"/api/books/{book_id}", headers=auth_headers).json()
    assert data["user_book"]["progress"] == {"unit": "page", "value": 5}

    events = client.get(f"/api/books/{book_id}/events", headers=auth_headers).json()
    progress_events = [e for e in events if e["event_type"] == "progress_set"]
    assert [e["progress"] for e in progress_events] == [{"unit": "page", "value": 5}]


@pytest.mark.parametrize(
    "progress",
    [{"unit": "page", "value": 0}, {"unit": "percent", "value": 0}],
)
def test_progress_accepts_zero(client, auth_headers, created_book, progress):
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress", json=progress, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["progress"] == progress


def test_progress_percent_replaces_page(client, auth_headers, created_book):
    """The latest progress event wins; a later percent-only event clears the page."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    client.post(
        f"/api/books/{book_id}/progress",
        json={"unit": "page", "value": 10},
        headers=auth_headers,
    )
    response = client.post(
        f"/api/books/{book_id}/progress",
        json={"unit": "percent", "value": 50},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["progress"] == {"unit": "percent", "value": 50}


@pytest.mark.parametrize(
    "progress", [{}, {"unit": "page"}, {"value": 10}, {"unit": "page", "value": None}]
)
def test_progress_requires_unit_and_value(client, auth_headers, created_book, progress):
    """A progress request requires both a unit and a non-null value."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress", json=progress, headers=auth_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_progress_percent_out_of_range(client, auth_headers, created_book):
    """Percent must be between 0 and 100."""
    book_id = created_book["id"]
    _start_reading(client, auth_headers, book_id)

    response = client.post(
        f"/api/books/{book_id}/progress",
        json={"unit": "percent", "value": 150},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
