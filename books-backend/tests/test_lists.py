from fastapi import status


def _create_book(client, auth_headers, sample_book_data, title_suffix, isbn_suffix):
    payload = sample_book_data.copy()
    payload["title"] = f"{sample_book_data['title']} {title_suffix}"
    payload["isbn"] = f"{sample_book_data['isbn']}{isbn_suffix}"
    response = client.post("/books", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _get_list_id(lists, name):
    for entry in lists:
        if entry["name"] == name:
            return entry["id"]
    return None


def test_lists_default_and_books_ordering(client, auth_headers, sample_book_data):
    book_one_id = _create_book(client, auth_headers, sample_book_data, "One", "1")
    book_two_id = _create_book(client, auth_headers, sample_book_data, "Two", "2")

    response = client.put(
        f"/books/{book_one_id}/status",
        json={"status": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    response = client.put(
        f"/books/{book_two_id}/status",
        json={"status": "started"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    response = client.put(
        f"/books/{book_two_id}/status",
        json={"status": "finished"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    lists_response = client.get("/lists", headers=auth_headers)
    assert lists_response.status_code == status.HTTP_200_OK
    lists = lists_response.json()
    to_read_id = _get_list_id(lists, "To Read")
    finished_id = _get_list_id(lists, "Finished")
    assert to_read_id is not None
    assert finished_id is not None

    to_read_response = client.get(f"/lists/{to_read_id}/books", headers=auth_headers)
    assert to_read_response.status_code == status.HTTP_200_OK
    to_read_items = to_read_response.json()["items"]
    assert any(item["id"] == book_one_id for item in to_read_items)

    finished_response = client.get(f"/lists/{finished_id}/books", headers=auth_headers)
    assert finished_response.status_code == status.HTTP_200_OK
    finished_items = finished_response.json()["items"]
    assert any(item["id"] == book_two_id for item in finished_items)


def test_list_reorder_updates_order(client, auth_headers, sample_book_data):
    book_one_id = _create_book(client, auth_headers, sample_book_data, "Alpha", "3")
    book_two_id = _create_book(client, auth_headers, sample_book_data, "Beta", "4")

    response = client.put(
        f"/books/{book_one_id}/status",
        json={"status": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    response = client.put(
        f"/books/{book_two_id}/status",
        json={"status": "want_to_read"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK

    lists_response = client.get("/lists", headers=auth_headers)
    assert lists_response.status_code == status.HTTP_200_OK
    to_read_id = _get_list_id(lists_response.json(), "To Read")
    assert to_read_id is not None

    reorder_response = client.post(
        f"/lists/{to_read_id}/items/reorder",
        json={
            "moved_book_id": book_two_id,
            "before_book_id": None,
            "after_book_id": book_one_id,
        },
        headers=auth_headers,
    )
    assert reorder_response.status_code == status.HTTP_204_NO_CONTENT

    to_read_response = client.get(f"/lists/{to_read_id}/books", headers=auth_headers)
    assert to_read_response.status_code == status.HTTP_200_OK
    ordered_ids = [item["id"] for item in to_read_response.json()["items"]]
    assert ordered_ids[0] == book_two_id


def test_create_book_adds_to_to_read_list(client, auth_headers, sample_book_data):
    create_response = client.post("/books", json=sample_book_data, headers=auth_headers)
    assert create_response.status_code == status.HTTP_201_CREATED
    book_id = create_response.json()["id"]

    lists_response = client.get("/lists", headers=auth_headers)
    assert lists_response.status_code == status.HTTP_200_OK
    to_read_id = _get_list_id(lists_response.json(), "To Read")
    assert to_read_id is not None

    to_read_response = client.get(f"/lists/{to_read_id}/books", headers=auth_headers)
    assert to_read_response.status_code == status.HTTP_200_OK
    ordered_ids = [item["id"] for item in to_read_response.json()["items"]]
    assert book_id in ordered_ids
