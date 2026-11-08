import pytest
from fastapi import status


@pytest.mark.parametrize("page_count", [300, 0, None])
def test_start_initializes_progress_at_zero(
    client, auth_headers, sample_book_data, page_count
):
    book_id = client.post(
        "/api/books",
        json={**sample_book_data, "page_count": page_count},
        headers=auth_headers,
    ).json()["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    expected_page = 0 if page_count is not None else None
    expected_percent = None if page_count is not None else 0
    assert response.json()["current_page"] == expected_page
    assert response.json()["current_percent"] == expected_percent
    saved = client.get(f"/api/books/{book_id}", headers=auth_headers).json()[
        "user_book"
    ]
    assert saved["current_page"] == expected_page
    assert saved["current_percent"] == expected_percent


@pytest.mark.parametrize("previous_shelf", ["paused", "finished", "abandoned"])
def test_resume_preserves_progress_and_new_cycle_resets_it(
    client, auth_headers, sample_book_data, previous_shelf
):
    book_id = client.post(
        "/api/books", json=sample_book_data, headers=auth_headers
    ).json()["id"]
    client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )
    response = client.post(
        f"/api/books/{book_id}/progress",
        json={"unit": "percent", "value": 42.5},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": previous_shelf},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_id}/shelf", json={"shelf": "started"}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_page"] == (
        None if previous_shelf == "paused" else 0
    )
    assert response.json()["current_percent"] == (
        42.5 if previous_shelf == "paused" else None
    )


def test_only_a_currently_reading_book_can_be_paused(
    client, auth_headers, sample_book_data
):
    book_id = client.post(
        "/api/books", json=sample_book_data, headers=auth_headers
    ).json()["id"]

    response = client.put(
        f"/api/books/{book_id}/shelf",
        json={"shelf": "paused"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Cannot move from 'want_to_read' to 'paused'"


def test_pause_resume_and_abandon_move_the_single_reading_placement(
    client, auth_headers, sample_book_data
):
    book_id = client.post(
        "/api/books", json=sample_book_data, headers=auth_headers
    ).json()["id"]

    for shelf in ("started", "paused", "started", "abandoned", "started"):
        response = client.put(
            f"/api/books/{book_id}/shelf", json={"shelf": shelf}, headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["shelf"] == shelf

    events = client.get(f"/api/books/{book_id}/events", headers=auth_headers).json()
    assert {event["event_type"] for event in events} >= {
        "started_reading",
        "paused_reading",
        "resumed_reading",
        "abandoned_reading",
    }
