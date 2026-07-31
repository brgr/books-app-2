from fastapi import status


def _create_book(client, auth_headers, sample_book_data, title_suffix, isbn_suffix):
    payload = sample_book_data.copy()
    payload["title"] = f"{sample_book_data['title']} {title_suffix}"
    payload["isbn"] = f"{sample_book_data['isbn']}{isbn_suffix}"
    response = client.post("/api/books", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


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
        "/api/shelves/want_to_read/books", headers=auth_headers
    )
    assert want_to_read_response.status_code == status.HTTP_200_OK
    want_to_read_items = want_to_read_response.json()["items"]
    assert any(item["id"] == book_one_id for item in want_to_read_items)

    finished_response = client.get("/api/shelves/finished/books", headers=auth_headers)
    assert finished_response.status_code == status.HTTP_200_OK
    finished_items = finished_response.json()["items"]
    assert any(item["id"] == book_two_id for item in finished_items)


def test_only_built_in_shelf_names_are_accepted(client, auth_headers):
    """Anything but the built-in shelves is refused at the path, before any lookup."""
    for shelf in ("sommerbuecher", "7"):
        response = client.get(f"/api/shelves/{shelf}/books", headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        error = response.json()["detail"][0]
        assert error["loc"] == ["path", "shelf_name"]
        assert "want_to_read" in error["msg"]

    reorder = client.post(
        "/api/shelves/7/items/reorder",
        json={"moved_book_id": 1, "before_book_id": None, "after_book_id": None},
        headers=auth_headers,
    )

    assert reorder.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


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

    reorder_response = client.post(
        "/api/shelves/want_to_read/items/reorder",
        json={
            "moved_book_id": book_two_id,
            "before_book_id": None,
            "after_book_id": book_one_id,
        },
        headers=auth_headers,
    )
    assert reorder_response.status_code == status.HTTP_204_NO_CONTENT

    want_to_read_response = client.get(
        "/api/shelves/want_to_read/books", headers=auth_headers
    )
    assert want_to_read_response.status_code == status.HTTP_200_OK
    ordered_ids = [item["id"] for item in want_to_read_response.json()["items"]]
    assert ordered_ids[0] == book_two_id


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

    # Initial order: A, B, C. Move C between A and B.
    reorder_response = client.post(
        "/api/shelves/want_to_read/items/reorder",
        json={
            "moved_book_id": book_c_id,
            "before_book_id": book_a_id,
            "after_book_id": book_b_id,
        },
        headers=auth_headers,
    )
    assert reorder_response.status_code == status.HTTP_204_NO_CONTENT

    books_response = client.get("/api/shelves/want_to_read/books", headers=auth_headers)
    ordered_ids = [item["id"] for item in books_response.json()["items"]]
    assert ordered_ids == [book_a_id, book_c_id, book_b_id]


def test_create_book_adds_to_want_to_read_shelf(client, auth_headers, sample_book_data):
    create_response = client.post(
        "/api/books", json=sample_book_data, headers=auth_headers
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    book_id = create_response.json()["id"]

    want_to_read_response = client.get(
        "/api/shelves/want_to_read/books", headers=auth_headers
    )
    assert want_to_read_response.status_code == status.HTTP_200_OK
    ordered_ids = [item["id"] for item in want_to_read_response.json()["items"]]
    assert book_id in ordered_ids
