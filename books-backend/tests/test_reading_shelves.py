import pytest
from fastapi import status


def _create_book(client, auth_headers, sample_book_data, title_suffix, isbn_suffix):
    payload = sample_book_data.copy()
    payload["title"] = f"{sample_book_data['title']} {title_suffix}"
    payload["isbn"] = f"{sample_book_data['isbn']}{isbn_suffix}"
    response = client.post("/api/books", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


@pytest.mark.parametrize("edge", ["top", "bottom"])
def test_reorder_to_true_shelf_edge(client, auth_headers, sample_book_data, edge):
    # Create books and add them to the "want_to_read" shelf
    ids = [
        _create_book(client, auth_headers, sample_book_data, str(i), str(i))
        for i in range(4)
    ]

    # Move the second book (book ID ids[1]) to the edge
    response = client.post(
        "/api/shelves/reading:want_to_read/items/reorder",
        json={"moved_book_id": ids[1], "edge": edge},
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Ensure the order of books in the shelf is as expected after the reorder
    remaining = [ids[3], ids[2], ids[0]]
    expected = [ids[1], *remaining] if edge == "top" else [*remaining, ids[1]]
    result = client.get("/api/shelves/reading:want_to_read/books", headers=auth_headers)
    assert [book["id"] for book in result.json()["items"]] == expected


# This test simulates a request the frontend might make when not all books are loaded in the UI
def test_drag_after_loaded_boundary_uses_unloaded_successor(
    client, auth_headers, sample_book_data
):
    book_a = _create_book(client, auth_headers, sample_book_data, "A", "0")
    book_b = _create_book(client, auth_headers, sample_book_data, "B", "1")
    book_c = _create_book(client, auth_headers, sample_book_data, "C", "2")
    book_d = _create_book(client, auth_headers, sample_book_data, "D", "3")

    # Initial order: D, C, B, A. Move A before D => A, D, C, B
    response = client.post(
        "/api/shelves/reading:want_to_read/items/reorder",
        json={"moved_book_id": book_a, "after_book_id": book_d},
        headers=auth_headers,
    )
    assert response.status_code == 204

    # Say in the frontend only A, D, C are loaded and the user moves A after C;
    # the backend must find unseen B and keep A before it, producing D, C, A, B
    response = client.post(
        "/api/shelves/reading:want_to_read/items/reorder",
        json={"moved_book_id": book_a, "before_book_id": book_c},
        headers=auth_headers,
    )
    assert response.status_code == 204

    result = client.get("/api/shelves/reading:want_to_read/books", headers=auth_headers)
    assert [book["id"] for book in result.json()["items"]] == [
        book_d,
        book_c,
        book_a,
        book_b,
    ]


def test_shelves_default_and_books_ordering(client, auth_headers, sample_book_data):
    book_one_id = _create_book(client, auth_headers, sample_book_data, "One", "1")
    book_two_id = _create_book(client, auth_headers, sample_book_data, "Two", "2")

    response = client.put(
        f"/api/books/{book_one_id}/shelf",
        json={"shelf": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/api/books/{book_two_id}/shelf",
        json={"shelf": "started"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    response = client.put(
        f"/api/books/{book_two_id}/shelf",
        json={"shelf": "finished"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    want_to_read_response = client.get(
        "/api/shelves/reading:want_to_read/books", headers=auth_headers
    )
    assert want_to_read_response.status_code == status.HTTP_200_OK
    want_to_read_items = want_to_read_response.json()["items"]
    assert any(item["id"] == book_one_id for item in want_to_read_items)

    finished_response = client.get(
        "/api/shelves/reading:finished/books", headers=auth_headers
    )
    assert finished_response.status_code == status.HTTP_200_OK
    finished_items = finished_response.json()["items"]
    assert any(item["id"] == book_two_id for item in finished_items)


def test_an_invalid_shelf_ref_has_a_helpful_error(client, auth_headers):
    """Malformed refs are rejected before any shelf lookup happens."""
    invalid_refs = {
        "sommerbuecher": "Shelf ref must be 'reading:<shelf>' or 'custom:<positive id>'",
        "7": "Shelf ref must be 'reading:<shelf>' or 'custom:<positive id>'",
        "want_to_read": "Shelf ref must be 'reading:<shelf>' or 'custom:<positive id>'",
        "custom:abc": "Custom shelf id must be a positive decimal integer",
        "reading:unknown": (
            "Unknown reading shelf 'unknown'. Expected one of: "
            "want_to_read, started, paused, finished, abandoned"
        ),
    }
    for shelf, detail in invalid_refs.items():
        response = client.get(f"/api/shelves/{shelf}/books", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["detail"] == detail

    reorder = client.post(
        "/api/shelves/custom:7/items/reorder",
        json={"moved_book_id": 1, "before_book_id": None, "after_book_id": None},
        headers=auth_headers,
    )

    assert reorder.status_code == status.HTTP_404_NOT_FOUND


def test_shelf_reorder_updates_order(client, auth_headers, sample_book_data):
    book_one_id = _create_book(client, auth_headers, sample_book_data, "Alpha", "3")
    book_two_id = _create_book(client, auth_headers, sample_book_data, "Beta", "4")

    response = client.put(
        f"/api/books/{book_one_id}/shelf",
        json={"shelf": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    response = client.put(
        f"/api/books/{book_two_id}/shelf",
        json={"shelf": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    # Initial order: Beta, Alpha. Move Alpha before Beta.
    reorder_response = client.post(
        "/api/shelves/reading:want_to_read/items/reorder",
        json={
            "moved_book_id": book_one_id,
            "before_book_id": None,
            "after_book_id": book_two_id,
        },
        headers=auth_headers,
    )
    assert reorder_response.status_code == status.HTTP_204_NO_CONTENT

    want_to_read_response = client.get(
        "/api/shelves/reading:want_to_read/books", headers=auth_headers
    )
    assert want_to_read_response.status_code == status.HTTP_200_OK
    ordered_ids = [item["id"] for item in want_to_read_response.json()["items"]]
    assert ordered_ids == [book_one_id, book_two_id]


def test_shelf_reorder_between_two_items(client, auth_headers, sample_book_data):
    """Move a book between two others (both before and after specified)."""
    book_a_id = _create_book(client, auth_headers, sample_book_data, "A", "10")
    book_b_id = _create_book(client, auth_headers, sample_book_data, "B", "11")
    book_c_id = _create_book(client, auth_headers, sample_book_data, "C", "12")

    for book_id in (book_a_id, book_b_id, book_c_id):
        client.put(
            f"/api/books/{book_id}/shelf",
            json={"shelf": "want_to_read"},
            headers=auth_headers,
        )

    # Initial order: C, B, A. Move A between C and B.
    reorder_response = client.post(
        "/api/shelves/reading:want_to_read/items/reorder",
        json={
            "moved_book_id": book_a_id,
            "before_book_id": book_c_id,
            "after_book_id": book_b_id,
        },
        headers=auth_headers,
    )
    assert reorder_response.status_code == status.HTTP_204_NO_CONTENT

    books_response = client.get(
        "/api/shelves/reading:want_to_read/books", headers=auth_headers
    )
    ordered_ids = [item["id"] for item in books_response.json()["items"]]
    assert ordered_ids == [book_c_id, book_a_id, book_b_id]


def test_shelf_reorder_with_inverted_neighbours_rebalances(
    client, auth_headers, sample_book_data
):
    """Neighbors given in the wrong order force a rebalance before the insert.

    When ``before`` sits at or past ``after``, there's no space left to slot
    the moved book into, so the shelf respreads its positions and the book
    lands at the midpoint of the respread neighbors.
    """
    book_a_id = _create_book(client, auth_headers, sample_book_data, "A", "20")
    book_b_id = _create_book(client, auth_headers, sample_book_data, "B", "21")
    book_c_id = _create_book(client, auth_headers, sample_book_data, "C", "22")

    for book_id in (book_a_id, book_b_id, book_c_id):
        client.put(
            f"/api/books/{book_id}/shelf",
            json={"shelf": "want_to_read"},
            headers=auth_headers,
        )

    # Initial order: C, B, A. Ask for A between B and C (i.e. inverted)
    reorder_response = client.post(
        "/api/shelves/reading:want_to_read/items/reorder",
        json={
            "moved_book_id": book_a_id,
            "before_book_id": book_b_id,
            "after_book_id": book_c_id,
        },
        headers=auth_headers,
    )
    assert reorder_response.status_code == status.HTTP_204_NO_CONTENT

    books_response = client.get(
        "/api/shelves/reading:want_to_read/books", headers=auth_headers
    )
    ordered_ids = [item["id"] for item in books_response.json()["items"]]
    assert ordered_ids == [book_c_id, book_a_id, book_b_id]


def test_create_book_adds_to_top_of_want_to_read_shelf(
    client, auth_headers, sample_book_data
):
    existing_ids = [
        _create_book(client, auth_headers, sample_book_data, str(i), str(i))
        for i in range(3)
    ]
    reorder = client.post(
        "/api/shelves/reading:want_to_read/items/reorder",
        json={"moved_book_id": existing_ids[0], "edge": "top"},
        headers=auth_headers,
    )
    assert reorder.status_code == status.HTTP_204_NO_CONTENT

    create_response = client.post(
        "/api/books", json=sample_book_data, headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    book_id = create_response.json()["id"]

    want_to_read_response = client.get(
        "/api/shelves/reading:want_to_read/books", headers=auth_headers
    )
    assert want_to_read_response.status_code == status.HTTP_200_OK
    ordered_ids = [item["id"] for item in want_to_read_response.json()["items"]]
    assert ordered_ids == [book_id, existing_ids[0], existing_ids[2], existing_ids[1]]
