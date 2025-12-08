from fastapi import status


def test_create_book(client, auth_headers, sample_book_data):
    """Test creating a book."""
    response = client.post("/books", json=sample_book_data, headers=auth_headers)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == sample_book_data["title"]
    assert data["author"] == sample_book_data["author"]
    assert data["isbn"] == sample_book_data["isbn"]
    assert "id" in data


def test_create_book_requires_auth(client, sample_book_data):
    """Test that creating a book requires authentication."""
    response = client.post("/books", json=sample_book_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_books(client, auth_headers, sample_book_data):
    """Test listing books."""
    # Create a few books
    for i in range(3):
        book_data = sample_book_data.copy()
        book_data["title"] = f"Test Book {i}"
        book_data["isbn"] = f"123456789{i}"
        client.post("/books", json=book_data, headers=auth_headers)

    # List books
    response = client.get("/books", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_books_pagination(client, auth_headers, sample_book_data):
    """Test book listing pagination."""
    # Create 5 books
    for i in range(5):
        book_data = sample_book_data.copy()
        book_data["title"] = f"Test Book {i}"
        book_data["isbn"] = f"123456789{i}"
        client.post("/books", json=book_data, headers=auth_headers)

    # Get first page with 2 items
    response = client.get("/books?page=1&page_size=2", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3

    # Get second page
    response = client.get("/books?page=2&page_size=2", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2


def test_get_book(client, auth_headers, sample_book_data):
    """Test getting a single book."""
    # Create a book
    create_response = client.post("/books", json=sample_book_data, headers=auth_headers)
    book_id = create_response.json()["id"]

    # Get the book
    response = client.get(f"/books/{book_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == book_id
    assert data["title"] == sample_book_data["title"]


def test_get_nonexistent_book(client, auth_headers):
    """Test getting a book that doesn't exist."""
    response = client.get("/books/99999", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_book(client, auth_headers, sample_book_data):
    """Test updating a book."""
    # Create a book
    create_response = client.post("/books", json=sample_book_data, headers=auth_headers)
    book_id = create_response.json()["id"]

    # Update the book
    update_data = {
        "title": "Updated Title",
        "page_count": 350
    }
    response = client.put(f"/books/{book_id}", json=update_data, headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["page_count"] == 350
    assert data["author"] == sample_book_data["author"]  # Unchanged field


def test_update_nonexistent_book(client, auth_headers):
    """Test updating a book that doesn't exist."""
    response = client.put("/books/99999", json={"title": "New Title"}, headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_book(client, auth_headers, sample_book_data):
    """Test deleting a book."""
    # Create a book
    create_response = client.post("/books", json=sample_book_data, headers=auth_headers)
    book_id = create_response.json()["id"]

    # Delete the book
    response = client.delete(f"/books/{book_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's gone
    response = client.get(f"/books/{book_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_nonexistent_book(client, auth_headers):
    """Test deleting a book that doesn't exist."""
    response = client.delete("/books/99999", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_book_validation(client, auth_headers):
    """Test book data validation."""
    # Missing required field
    response = client.post("/books", json={
        "author": "Test Author"
        # Missing title
    }, headers=auth_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Invalid page count (negative)
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "page_count": -10
    }, headers=auth_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
