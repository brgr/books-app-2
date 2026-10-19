import httpx
import pytest

from app.google_books import (
    GoogleBooksRateLimitError,
    GoogleBooksSearchError,
    search_cover_images,
    search_google_books,
)


async def test_cover_search_preserves_full_resolution_selection(monkeypatch):
    """Preview the thumbnail while retaining the higher zoom for selection."""

    async def fake_get(self, url, params=None):
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={
                "items": [
                    {
                        "id": "volume",
                        "volumeInfo": {
                            "title": "The Heart of Enterprise",
                            "imageLinks": {
                                "thumbnail": "http://books.google.com/books/content?id=volume&img=1&zoom=1&edge=curl",
                            },
                        },
                    }
                ],
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    results = await search_cover_images(title="The Heart of Enterprise")

    assert len(results) == 1
    assert results[0]["thumbnail"].endswith("zoom=1")
    assert results[0]["image_url"] == (
        "https://books.google.com/books/content?id=volume&img=1&zoom=2"
    )


async def test_search_retries_upstream_503_then_returns_books(monkeypatch):
    statuses = iter([503, 503, 503, 200])
    delays = []

    async def fake_get(self, url, params=None):
        status = next(statuses)
        return httpx.Response(
            status,
            request=httpx.Request("GET", url),
            json={"items": [{"volumeInfo": {"title": "Waste Wars"}}]}
            if status == 200
            else {},
        )

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr("app.google_books.asyncio.sleep", fake_sleep)
    results = await search_google_books("waste wars alexander clapp")

    assert [book["title"] for book in results] == ["Waste Wars"]
    assert len(delays) == 3
    assert 0.25 <= delays[0] <= 0.35
    assert 0.5 <= delays[1] <= 0.6
    assert 1.0 <= delays[2] <= 1.1


@pytest.mark.parametrize("status,expected_attempts", [(503, 4), (403, 1)])
async def test_search_does_not_report_upstream_failure_as_no_results(
    monkeypatch, status, expected_attempts
):
    attempts = 0

    async def fake_get(self, url, params=None):
        nonlocal attempts
        attempts += 1
        return httpx.Response(status, request=httpx.Request("GET", url), json={})

    async def fake_sleep(delay):
        pass

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr("app.google_books.asyncio.sleep", fake_sleep)

    with pytest.raises(GoogleBooksSearchError) as exc:
        await search_google_books("Waste Wars")
    assert exc.value.transient is (status == 503)
    assert attempts == expected_attempts


async def test_search_returns_empty_only_for_successful_empty_response(monkeypatch):
    async def fake_get(self, url, params=None):
        return httpx.Response(
            200, request=httpx.Request("GET", url), json={"totalItems": 0}
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await search_google_books("unknown book") == []


async def test_search_does_not_retry_rate_limits(monkeypatch):
    attempts = 0

    async def fake_get(self, url, params=None):
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            429, request=httpx.Request("GET", url), headers={"Retry-After": "20"}
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    with pytest.raises(GoogleBooksRateLimitError) as exc:
        await search_google_books("Waste Wars")
    assert exc.value.retry_after == "20"
    assert attempts == 1


@pytest.mark.parametrize(
    "transient,expected_status,detail",
    [
        (True, 503, "Google Books is temporarily unavailable. Please try again."),
        (False, 502, "Google Books search failed. Please try again later."),
    ],
)
def test_search_endpoint_reports_upstream_failure(
    client, auth_headers, monkeypatch, transient, expected_status, detail
):
    from app.books import router

    async def failed_search(query):
        raise GoogleBooksSearchError(transient=transient)

    monkeypatch.setattr(router, "search_google_books", failed_search)
    response = client.get(
        "/api/books/search", params={"q": "Waste Wars"}, headers=auth_headers
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": detail}


def test_preview_uses_validated_cover(client, auth_headers, monkeypatch):
    from app.books import router

    async def fake_fetch(url):
        return b"validated-image", "png"

    monkeypatch.setattr(router, "fetch_cover_image", fake_fetch)
    response = client.get(
        "/api/books/cover-preview",
        params={"url": "https://books.google.com/books/content?id=X&zoom=2"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.content == b"validated-image"
    assert response.headers["content-type"] == "image/png"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/cover.png",
        "https://books.google.com.example.com/books/content?id=X",
        "https://books.google.com/other",
    ],
)
def test_preview_rejects_non_google_cover_urls(client, auth_headers, url):
    response = client.get(
        "/api/books/cover-preview", params={"url": url}, headers=auth_headers
    )
    assert response.status_code == 400
