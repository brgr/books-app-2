"""Google Books API integration for book search."""
import re
import httpx
from typing import Optional
from app.config import settings


def _build_cover_query(
    title: Optional[str], author: Optional[str], isbn: Optional[str]
) -> Optional[str]:
    """Build a Google Books query that uses field qualifiers for better recall."""
    if isbn:
        digits = re.sub(r"[^0-9Xx]", "", isbn)
        if digits:
            return f"isbn:{digits}"
    parts: list[str] = []
    if title and title.strip():
        parts.append(f'intitle:"{title.strip()}"')
    if author and author.strip():
        parts.append(f'inauthor:"{author.strip()}"')
    if not parts:
        return None
    return "+".join(parts)


def _upgrade_thumbnail(url: str, zoom: int = 2) -> str:
    """Upgrade a Google Books thumbnail URL to a larger, https variant."""
    if url.startswith("http:"):
        url = "https:" + url[5:]
    url = url.replace("&edge=curl", "").replace("?edge=curl&", "?")
    if "zoom=" in url:
        url = re.sub(r"zoom=\d+", f"zoom={zoom}", url)
    else:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}zoom={zoom}"
    return url


async def search_cover_images(
    title: Optional[str] = None,
    author: Optional[str] = None,
    isbn: Optional[str] = None,
    max_results: int = 40,
) -> list[dict]:
    """Search Google Books for candidate cover images.

    Uses field qualifiers (intitle/inauthor/isbn) for materially better
    recall than free text. Returns deduped results with an upgraded
    higher-resolution thumbnail URL.
    """
    query = _build_cover_query(title, author, isbn)
    if not query:
        return []

    base_url = "https://www.googleapis.com/books/v1/volumes"
    params: dict[str, str | int] = {
        "q": query,
        "maxResults": min(max_results, 40),
        "printType": "books",
        "projection": "full",
    }
    if settings.google_books_api_key:
        params["key"] = settings.google_books_api_key

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(base_url, params=params)
            if response.status_code == 429:
                raise GoogleBooksRateLimitError(response.headers.get("Retry-After"))
            response.raise_for_status()
            data = response.json()
    except GoogleBooksRateLimitError:
        raise
    except httpx.HTTPError as e:
        print(f"Google Books cover search error: {e!r}")
        return []

    seen: set[str] = set()
    results: list[dict] = []
    for item in data.get("items", []):
        volume_info = item.get("volumeInfo", {}) or {}
        image_links = volume_info.get("imageLinks") or {}
        raw = (
            image_links.get("extraLarge")
            or image_links.get("large")
            or image_links.get("medium")
            or image_links.get("thumbnail")
            or image_links.get("smallThumbnail")
        )
        if not raw:
            continue
        thumb = _upgrade_thumbnail(raw, zoom=1)
        full = _upgrade_thumbnail(raw, zoom=2)
        dedupe_key = re.sub(r"[?&]zoom=\d+", "", full)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        result_isbn: Optional[str] = None
        for ident in volume_info.get("industryIdentifiers", []) or []:
            if ident.get("type") == "ISBN_13":
                result_isbn = ident.get("identifier")
                break
            if ident.get("type") == "ISBN_10" and not result_isbn:
                result_isbn = ident.get("identifier")

        results.append(
            {
                "title": volume_info.get("title") or "",
                "author": ", ".join(volume_info.get("authors", []) or []) or None,
                "isbn": result_isbn,
                "thumbnail": thumb,
                "image_url": full,
                "google_books_id": item.get("id"),
            }
        )
    return results


class GoogleBooksRateLimitError(Exception):
    def __init__(self, retry_after: Optional[str] = None):
        self.retry_after = retry_after
        super().__init__("Google Books API rate limit exceeded")


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
            if response.status_code == 429:
                raise GoogleBooksRateLimitError(response.headers.get("Retry-After"))
            response.raise_for_status()
            data = response.json()

        # Parse and normalize the results
        books = []
        for item in data.get("items", []):
            book = _normalize_book_data(item)
            if book:
                books.append(book)

        return books

    except GoogleBooksRateLimitError:
        raise
    except httpx.HTTPStatusError as e:
        # Log response details to surface errors like bad API keys or quota issues.
        status = e.response.status_code
        body = (e.response.text or "").strip()
        print(f"Google Books API error: status={status} body={body}")
        return []
    except httpx.HTTPError as e:
        # Network or protocol error.
        print(f"Google Books API error: {e!r}")
        return []
    except Exception as e:
        print(f"Unexpected error searching Google Books: {e!r}")
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
