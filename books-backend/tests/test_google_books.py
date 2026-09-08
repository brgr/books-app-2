import httpx
import pytest

from app.google_books import search_cover_images


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
