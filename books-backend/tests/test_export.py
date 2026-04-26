from fastapi import status


def test_user_books_export_sorted_by_id(
    client, auth_headers, sample_book_data, test_user
):
    """Ensure the export endpoint returns books sorted by their IDs."""
    created_books = []
    titles = ["Zulu Book", "Alpha Book", "Gamma Book"]

    for idx, title in enumerate(titles):
        payload = sample_book_data.copy()
        payload["title"] = title
        payload["isbn"] = f"ISBN-{idx}"
        response = client.post("/books", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        created_books.append(response.json())

    status_updates = ["finished", "started", "want_to_read"]
    expected_status_by_id = {}

    for book, new_status in zip(reversed(created_books), status_updates):
        notes = f"Note for {book['title']}"
        if new_status == "finished":
            start_response = client.put(
                f"/books/{book['id']}/status",
                json={"status": "started"},
                headers=auth_headers,
            )
            assert start_response.status_code == status.HTTP_200_OK

            response = client.put(
                f"/books/{book['id']}/status",
                json={"status": "finished", "notes": notes},
                headers=auth_headers,
            )
            assert response.status_code == status.HTTP_200_OK
        else:
            response = client.put(
                f"/books/{book['id']}/status",
                json={"status": new_status, "notes": notes},
                headers=auth_headers,
            )
            assert response.status_code == status.HTTP_200_OK
        expected_status_by_id[book["id"]] = {"status": new_status, "notes": notes}

    response = client.get("/users/me/export", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()

    assert payload["schema_version"] == "v1"
    assert payload["user"]["username"] == test_user["username"]
    assert len(payload["books"]) == len(created_books)

    exported_titles = [book["title"] for book in payload["books"]]
    expected_titles = [book["title"] for book in created_books]
    assert exported_titles == expected_titles

    for book in payload["books"]:
        expected = expected_status_by_id[book["id"]]
        assert book["status"] == expected["status"]
        assert book["notes"] == expected["notes"]
