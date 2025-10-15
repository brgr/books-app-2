"""Google Books API integration for book search."""
import httpx
from typing import Optional
from app.config import settings


async def search_google_books(query: str, max_results: int = 10) -> list[dict]:
    """
    Search for books using the Google Books API.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)

    Returns:
        List of book dictionaries with normalized data
    """
    if not query or not query.strip():
        return []

    # Build the API URL
    base_url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query.strip(),
        "maxResults": min(max_results, 40),  # API limit is 40
    }

    # Add API key if configured
    if settings.google_books_api_key:
        params["key"] = settings.google_books_api_key

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

        # Parse and normalize the results
        books = []
        for item in data.get("items", []):
            book = _normalize_book_data(item)
            if book:
                books.append(book)

        return books

    except httpx.HTTPError as e:
        # Log the error but don't crash - return empty results
        print(f"Google Books API error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error searching Google Books: {e}")
        return []


def _normalize_book_data(item: dict) -> Optional[dict]:
    """
    Normalize a single book item from Google Books API response.

    Args:
        item: A single volume item from the API response

    Returns:
        Normalized book dictionary or None if invalid
    """
    try:
        volume_info = item.get("volumeInfo", {})

        # Title is required
        title = volume_info.get("title")
        if not title:
            return None

        # Get authors (can be multiple)
        authors = volume_info.get("authors", [])
        author = ", ".join(authors) if authors else "Unknown Author"

        # Get ISBNs - prefer ISBN_13, fall back to ISBN_10
        isbn = None
        for identifier in volume_info.get("industryIdentifiers", []):
            if identifier.get("type") == "ISBN_13":
                isbn = identifier.get("identifier")
                break
            elif identifier.get("type") == "ISBN_10" and not isbn:
                isbn = identifier.get("identifier")

        # Get description
        description = volume_info.get("description")

        # Get published date
        published_date = volume_info.get("publishedDate")

        # Get page count
        page_count = volume_info.get("pageCount")

        # Get thumbnail image
        thumbnail = None
        image_links = volume_info.get("imageLinks", {})
        if image_links:
            # Get thumbnail (prefer thumbnail over smallThumbnail)
            thumbnail = (
                image_links.get("thumbnail") or
                image_links.get("smallThumbnail")
            )

            if thumbnail:
                # Upgrade to HTTPS if needed
                if thumbnail.startswith("http:"):
                    thumbnail = thumbnail.replace("http:", "https:")

                # Replace zoom parameter with zoom=0 for highest resolution
                # Google Books uses zoom=1 (default) or zoom=5 (small), zoom=0 gives highest res
                if "zoom=" in thumbnail:
                    import re
                    thumbnail = re.sub(r'zoom=\d+', 'zoom=0', thumbnail)

        # Get Google Books ID
        google_books_id = item.get("id")

        return {
            "title": title,
            "author": author,
            "isbn": isbn,
            "description": description,
            "published_date": published_date,
            "page_count": page_count,
            "thumbnail": thumbnail,
            "google_books_id": google_books_id,
        }

    except Exception as e:
        print(f"Error normalizing book data: {e}")
        return None
