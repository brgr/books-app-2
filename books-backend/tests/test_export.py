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
        response = client.post("/api/books", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        created_books.append(response.json())

    shelf_updates = ["finished", "started", "want_to_read"]
    expected_shelf_by_id = {}

    for book, new_shelf in zip(reversed(created_books), shelf_updates):
        notes = f"Note for {book['title']}"
        if new_shelf == "finished":
            start_response = client.put(
                f"/api/books/{book['id']}/shelf",
                json={"shelf": "started"},
                headers=auth_headers,
            )
            assert start_response.status_code == status.HTTP_200_OK

            response = client.put(
                f"/api/books/{book['id']}/shelf",
                json={"shelf": "finished", "notes": notes},
                headers=auth_headers,
            )
            assert response.status_code == status.HTTP_200_OK
        else:
            response = client.put(
                f"/api/books/{book['id']}/shelf",
                json={"shelf": new_shelf, "notes": notes},
                headers=auth_headers,
            )
            assert response.status_code == status.HTTP_200_OK
        expected_shelf_by_id[book["id"]] = {"shelf": new_shelf, "notes": notes}

    response = client.get("/api/users/me/export", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()

    assert payload["schema_version"] == "v1"
    assert payload["user"]["username"] == test_user["username"]
    assert len(payload["books"]) == len(created_books)

    exported_titles = [book["title"] for book in payload["books"]]
    expected_titles = [book["title"] for book in created_books]
    assert exported_titles == expected_titles

    for book in payload["books"]:
        expected = expected_shelf_by_id[book["id"]]
        assert book["shelf"] == expected["shelf"]
        assert book["notes"] == expected["notes"]
