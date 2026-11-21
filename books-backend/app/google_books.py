"""Google Books API integration for book search."""

import asyncio
import logging
import random
import re
from json import JSONDecodeError

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SEARCH_MAX_ATTEMPTS = 4


def _build_cover_query(
    title: str | None, author: str | None, isbn: str | None
) -> str | None:
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
    title: str | None = None,
    author: str | None = None,
    isbn: str | None = None,
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
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Google Books cover search error: status=%s", e.response.status_code
        )
        return []
    except httpx.HTTPError as e:
        # Avoid logging the request URL, which contains the API key.
        logger.warning("Google Books cover search error: %s", type(e).__name__)
        return []
    except (JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Invalid Google Books cover search response: %r", e)
        return []

    if not isinstance(data, dict) or not isinstance(data.get("items", []), list):
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

        result_isbn: str | None = None
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
    def __init__(self, retry_after: str | None = None):
        self.retry_after = retry_after
        super().__init__("Google Books API rate limit exceeded")


class GoogleBooksSearchError(Exception):
    """The upstream search failed; this is not an empty result set."""

    def __init__(self, *, transient: bool = True):
        self.transient = transient
        super().__init__("Google Books search failed")


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

    # Retry transient server failures (but don't retry rate limits or client errors)
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(SEARCH_MAX_ATTEMPTS):
            try:
                response = await client.get(base_url, params=params)

                if response.status_code == 429:
                    raise GoogleBooksRateLimitError(response.headers.get("Retry-After"))

                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                logger.warning(
                    "Google Books API error: status=%s body=%s",
                    status,
                    e.response.text.strip(),
                )

                if (
                    status not in (500, 502, 503, 504)
                    or attempt == SEARCH_MAX_ATTEMPTS - 1
                ):
                    raise GoogleBooksSearchError(
                        transient=status in (500, 502, 503, 504)
                    ) from e
            except httpx.HTTPError as e:
                # Avoid logging the request URL, which contains the API key.
                logger.warning("Google Books API error: %s", type(e).__name__)

                raise GoogleBooksSearchError from e
            except (JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning("Invalid Google Books search response: %r", e)

                raise GoogleBooksSearchError from e
            else:
                if not isinstance(data, dict) or not isinstance(
                    data.get("items", []), list
                ):
                    raise GoogleBooksSearchError(transient=False)

                books = []

                for item in data.get("items", []):
                    book = _normalize_book_data(item)
                    if book:
                        books.append(book)

                return books

            await asyncio.sleep(0.25 * 2**attempt + random.uniform(0, 0.1))

    raise GoogleBooksSearchError


def _normalize_book_data(item: dict) -> dict | None:
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
        author = ", ".join(authors) if authors else None

        # Get ISBNs - prefer ISBN_13, fall back to ISBN_10
        isbn = None
        for identifier in volume_info.get("industryIdentifiers", []):
            if identifier.get("type") == "ISBN_13":
                isbn = identifier.get("identifier")
                break

            if identifier.get("type") == "ISBN_10" and not isbn:
                isbn = identifier.get("identifier")

        # Get description
        description = volume_info.get("description")

        # Get published date
        published_date = volume_info.get("publishedDate")

        # Get page count
        page_count = volume_info.get("pageCount")

        # Google serves each cover in several sizes.
        # In search results, we return the small zoom=1 cover; when we save the book, we save the large zoom=0 cover
        # instead.
        # Sometimes, a book doesn't have a large scan (at which point it gets a "image not available" placeholder).
        # fetch_cover_image notices that and saves the zoom=1 one instead.
        thumbnail = None
        image_url = None
        image_links = volume_info.get("imageLinks") or {}
        raw = image_links.get("thumbnail") or image_links.get("smallThumbnail")
        if raw:
            thumbnail = _upgrade_thumbnail(raw, zoom=1)
            image_url = _upgrade_thumbnail(raw, zoom=0)

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
            "image_url": image_url,
            "google_books_id": google_books_id,
        }

    except (AttributeError, TypeError):
        # External metadata may have nulls or incorrect field types.
        logger.warning("Error normalizing book data", exc_info=True)
        return None
