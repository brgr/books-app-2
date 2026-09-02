"""User-created shelves: CRUD, membership and ordering.

The reading shelves are covered by ``test_reading_shelves``.
The tests here test custom shelves and the rules that keep the two kinds apart.
"""

from fastapi import status


def _create_book(client, auth_headers, sample_book_data, title_suffix, isbn_suffix):
    payload = sample_book_data.copy()

    payload["title"] = f"{sample_book_data['title']} {title_suffix}"
    payload["isbn"] = f"{sample_book_data['isbn']}{isbn_suffix}"

    response = client.post("/api/books", json=payload, headers=auth_headers)

    assert response.status_code == status.HTTP_201_CREATED

    return response.json()["id"]


def _create_shelf(client, auth_headers, name):
    response = client.post("/api/shelves", json={"name": name}, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["ref"]


# Listing


def test_list_shelves_returns_reading_and_custom(client, auth_headers):
    response = client.get("/api/shelves", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    shelves = response.json()
    assert [shelf["ref"] for shelf in shelves] == [
        "reading:want_to_read",
        "reading:started",
        "reading:paused",
        "reading:finished",
        "reading:abandoned",
    ]
    assert all("kind" not in shelf for shelf in shelves)
    assert shelves[0]["display_name"] == "Want to Read"

    _create_shelf(client, auth_headers, "Beach reads")

    shelves = client.get("/api/shelves", headers=auth_headers).json()
    assert len(shelves) == 6

    custom = shelves[-1]
    assert custom["display_name"] == "Beach reads"
    assert custom["ref"].startswith("custom:")
    assert custom["ref"].removeprefix("custom:").isdigit()


def test_list_shelves_reports_book_counts(client, auth_headers, sample_book_data):
    book_id = _create_book(client, auth_headers, sample_book_data, "Counted", "1")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    client.post(
        f"/api/shelves/{shelf_ref}/books",
        json={"book_id": book_id},
        headers=auth_headers,
    )

    shelves = {
        shelf["ref"]: shelf
        for shelf in client.get("/api/shelves", headers=auth_headers).json()
    }
    assert shelves[shelf_ref]["book_count"] == 1
    # The book stays on its reading shelf as well; the two are independent.
    assert shelves["reading:want_to_read"]["book_count"] == 1


def test_shelves_are_scoped_to_their_owner(client, auth_headers, db_session):
    """``create_user`` allows only one account, so the second is built directly."""
    from app.auth.security import hash_password
    from app.models import User

    shelf_ref = _create_shelf(client, auth_headers, "Private")

    db_session.add(
        User(username="other", hashed_password=hash_password("otherpass123"))
    )
    db_session.commit()
    other_token = client.post(
        "/api/token", data={"username": "other", "password": "otherpass123"}
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    shelves = client.get("/api/shelves", headers=other_headers).json()
    assert all("kind" not in shelf for shelf in shelves)

    response = client.get(f"/api/shelves/{shelf_ref}/books", headers=other_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# Create / update / delete


def test_create_shelf(client, auth_headers):
    response = client.post(
        "/api/shelves", json={"name": "Sommerbücher"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED

    body = response.json()
    assert body["display_name"] == "Sommerbücher"
    assert "kind" not in body
    assert body["book_count"] == 0


def test_create_shelf_rejects_duplicate_name(client, auth_headers):
    _create_shelf(client, auth_headers, "Beach reads")

    response = client.post(
        "/api/shelves", json={"name": "Beach reads"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_and_rename_reject_paused_books_name(client, auth_headers):
    response = client.post(
        "/api/shelves", json={"name": "paused books"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    shelf_ref = _create_shelf(client, auth_headers, "On hold")
    response = client.patch(
        f"/api/shelves/{shelf_ref}",
        json={"name": "Paused Books"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_shelf_rejects_blank_name(client, auth_headers):
    response = client.post("/api/shelves", json={"name": "   "}, headers=auth_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_rename_shelf(client, auth_headers):
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    response = client.patch(
        f"/api/shelves/{shelf_ref}", json={"name": "Summer reads"}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["display_name"] == "Summer reads"


def test_delete_shelf(client, auth_headers, sample_book_data):
    book_id = _create_book(client, auth_headers, sample_book_data, "Kept", "1")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")
    client.post(
        f"/api/shelves/{shelf_ref}/books",
        json={"book_id": book_id},
        headers=auth_headers,
    )

    response = client.delete(f"/api/shelves/{shelf_ref}", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert (
        client.get(f"/api/shelves/{shelf_ref}/books", headers=auth_headers).status_code
        == status.HTTP_404_NOT_FOUND
    )
    # Deleting a shelf must not take its books out of the library
    assert (
        client.get(f"/api/books/{book_id}", headers=auth_headers).status_code
        == status.HTTP_200_OK
    )


def test_unknown_shelf_ref_is_not_found(client, auth_headers):
    assert (
        client.get("/api/shelves/custom:9999/books", headers=auth_headers).status_code
        == status.HTTP_404_NOT_FOUND
    )
    assert (
        client.delete("/api/shelves/custom:9999", headers=auth_headers).status_code
        == status.HTTP_404_NOT_FOUND
    )


# Reading shelves are not user-owned objects


def test_reading_shelves_reject_lifecycle_changes(client, auth_headers):
    assert (
        client.patch(
            "/api/shelves/reading:finished",
            json={"name": "Done"},
            headers=auth_headers,
        ).status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        client.delete("/api/shelves/reading:finished", headers=auth_headers).status_code
        == status.HTTP_400_BAD_REQUEST
    )


def test_reading_shelf_membership_is_derived_not_assigned(
    client, auth_headers, sample_book_data
):
    """Membership of a reading shelf follows reading state, so it is read-only here."""
    book_id = _create_book(client, auth_headers, sample_book_data, "Derived", "1")

    response = client.post(
        "/api/shelves/reading:finished/books",
        json={"book_id": book_id},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "/shelf" in response.json()["detail"]

    response = client.delete(
        f"/api/shelves/reading:want_to_read/books/{book_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Membership


def test_add_and_remove_books(client, auth_headers, sample_book_data):
    book_id = _create_book(client, auth_headers, sample_book_data, "Member", "1")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    response = client.post(
        f"/api/shelves/{shelf_ref}/books",
        json={"book_id": book_id},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    books = client.get(f"/api/shelves/{shelf_ref}/books", headers=auth_headers).json()
    assert [item["id"] for item in books["items"]] == [book_id]
    assert books["total"] == 1

    # The shelf view carries the same reading-state payload as any other listing
    assert books["items"][0]["user_book"]["shelf"] == "want_to_read"

    response = client.delete(
        f"/api/shelves/{shelf_ref}/books/{book_id}", headers=auth_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    books = client.get(f"/api/shelves/{shelf_ref}/books", headers=auth_headers).json()
    assert books["items"] == []


def test_adding_a_book_twice_is_idempotent(client, auth_headers, sample_book_data):
    book_id = _create_book(client, auth_headers, sample_book_data, "Twice", "1")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    for _ in range(2):
        response = client.post(
            f"/api/shelves/{shelf_ref}/books",
            json={"book_id": book_id},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    books = client.get(f"/api/shelves/{shelf_ref}/books", headers=auth_headers).json()
    assert books["total"] == 1


def test_a_book_can_sit_on_several_custom_shelves(
    client, auth_headers, sample_book_data
):
    book_id = _create_book(client, auth_headers, sample_book_data, "Shared", "1")
    first_ref = _create_shelf(client, auth_headers, "Beach reads")
    second_ref = _create_shelf(client, auth_headers, "Favourites")

    for shelf_ref in (first_ref, second_ref):
        client.post(
            f"/api/shelves/{shelf_ref}/books",
            json={"book_id": book_id},
            headers=auth_headers,
        )

    for shelf_ref in (first_ref, second_ref):
        books = client.get(
            f"/api/shelves/{shelf_ref}/books", headers=auth_headers
        ).json()
        assert [item["id"] for item in books["items"]] == [book_id]


def test_list_book_custom_shelves(client, auth_headers, sample_book_data):
    book_id = _create_book(client, auth_headers, sample_book_data, "Listed", "1")
    first_ref = _create_shelf(client, auth_headers, "Beach reads")
    second_ref = _create_shelf(client, auth_headers, "Favourites")

    client.post(
        f"/api/shelves/{first_ref}/books",
        json={"book_id": book_id},
        headers=auth_headers,
    )
    client.post(
        f"/api/shelves/{second_ref}/books",
        json={"book_id": book_id},
        headers=auth_headers,
    )

    response = client.get(f"/api/books/{book_id}/custom-shelves", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert [shelf["ref"] for shelf in response.json()] == [first_ref, second_ref]


def test_adding_a_book_outside_the_library_is_not_found(client, auth_headers):
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    response = client.post(
        f"/api/shelves/{shelf_ref}/books", json={"book_id": 9999}, headers=auth_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_removing_a_book_from_the_library_clears_its_shelf_entries(
    client, auth_headers, sample_book_data
):
    book_id = _create_book(client, auth_headers, sample_book_data, "Gone", "1")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")
    client.post(
        f"/api/shelves/{shelf_ref}/books",
        json={"book_id": book_id},
        headers=auth_headers,
    )

    assert (
        client.delete(f"/api/books/{book_id}", headers=auth_headers).status_code
        == status.HTTP_204_NO_CONTENT
    )

    books = client.get(f"/api/shelves/{shelf_ref}/books", headers=auth_headers).json()
    assert books["items"] == []


# Ordering


def test_custom_shelf_keeps_its_own_order(client, auth_headers, sample_book_data):
    """Position on a custom shelf is independent of position on a reading shelf."""
    book_a = _create_book(client, auth_headers, sample_book_data, "A", "1")
    book_b = _create_book(client, auth_headers, sample_book_data, "B", "2")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    for book_id in (book_a, book_b):
        client.post(
            f"/api/shelves/{shelf_ref}/books",
            json={"book_id": book_id},
            headers=auth_headers,
        )

    reorder = client.post(
        f"/api/shelves/{shelf_ref}/items/reorder",
        json={
            "moved_book_id": book_b,
            "before_book_id": None,
            "after_book_id": book_a,
        },
        headers=auth_headers,
    )
    assert reorder.status_code == status.HTTP_204_NO_CONTENT

    books = client.get(f"/api/shelves/{shelf_ref}/books", headers=auth_headers).json()
    assert [item["id"] for item in books["items"]] == [book_b, book_a]

    # The reading shelf both books also sit on is untouched.
    reading_shelf = client.get(
        "/api/shelves/reading:want_to_read/books", headers=auth_headers
    ).json()
    assert [item["id"] for item in reading_shelf["items"]] == [book_a, book_b]


def test_reorder_between_two_books_on_a_custom_shelf(
    client, auth_headers, sample_book_data
):
    book_a = _create_book(client, auth_headers, sample_book_data, "A", "1")
    book_b = _create_book(client, auth_headers, sample_book_data, "B", "2")
    book_c = _create_book(client, auth_headers, sample_book_data, "C", "3")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    for book_id in (book_a, book_b, book_c):
        client.post(
            f"/api/shelves/{shelf_ref}/books",
            json={"book_id": book_id},
            headers=auth_headers,
        )

    reorder = client.post(
        f"/api/shelves/{shelf_ref}/items/reorder",
        json={
            "moved_book_id": book_c,
            "before_book_id": book_a,
            "after_book_id": book_b,
        },
        headers=auth_headers,
    )
    assert reorder.status_code == status.HTTP_204_NO_CONTENT

    books = client.get(f"/api/shelves/{shelf_ref}/books", headers=auth_headers).json()
    assert [item["id"] for item in books["items"]] == [book_a, book_c, book_b]


def test_reorder_against_a_book_not_on_the_shelf_is_rejected(
    client, auth_headers, sample_book_data
):
    book_on = _create_book(client, auth_headers, sample_book_data, "On", "1")
    book_off = _create_book(client, auth_headers, sample_book_data, "Off", "2")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")
    client.post(
        f"/api/shelves/{shelf_ref}/books",
        json={"book_id": book_on},
        headers=auth_headers,
    )

    response = client.post(
        f"/api/shelves/{shelf_ref}/items/reorder",
        json={
            "moved_book_id": book_on,
            "before_book_id": book_off,
            "after_book_id": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_reorder_of_a_book_not_on_the_shelf_is_rejected(
    client, auth_headers, sample_book_data
):
    book_off = _create_book(client, auth_headers, sample_book_data, "Off", "1")
    shelf_ref = _create_shelf(client, auth_headers, "Beach reads")

    response = client.post(
        f"/api/shelves/{shelf_ref}/items/reorder",
        json={
            "moved_book_id": book_off,
            "before_book_id": None,
            "after_book_id": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
