from fastapi import status


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
