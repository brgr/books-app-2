"""Tests for cover-change events (per user_book, like other reading events)."""

import io
from pathlib import Path

from app.models import (
    Book,
    BookEvent,
    BookEventCode,
    BookEventCover,
    BookEventType,
    UserBook,
)


def _make_book(db_session, **overrides):
    defaults = dict(
        title="Test Book",
        author="Test Author",
        cover_image_url="/uploads/covers/old.jpg",
        cover_thumbnail_url="/uploads/covers/thumbnails/old.jpg",
    )
    defaults.update(overrides)
    book = Book(**defaults)
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


def _patch_cover_download(monkeypatch, new_path="/uploads/covers/new.jpg",
                          new_thumb="/uploads/covers/thumbnails/new.jpg"):
    async def fake_download(url):
        return (new_path, new_thumb)

    monkeypatch.setattr("app.routers.books.download_cover_image", fake_download)


def _patch_cover_store(monkeypatch, new_path="/uploads/covers/uploaded.jpg",
                       new_thumb="/uploads/covers/thumbnails/uploaded.jpg"):
    def fake_store(content, extension):
        return (new_path, new_thumb)

    monkeypatch.setattr("app.routers.books.store_cover_image", fake_store)


def _cover_events_for_user_book(db_session, user_book_id):
    return (
        db_session.query(BookEvent)
        .join(BookEventType, BookEvent.event_type_id == BookEventType.id)
        .filter(
            BookEvent.user_book_id == user_book_id,
            BookEventType.code == BookEventCode.COVER_CHANGED.value,
        )
        .order_by(BookEvent.occurred_at.asc(), BookEvent.id.asc())
        .all()
    )


def test_cover_changed_event_type_is_seeded(db_session):
    codes = {code for (code,) in db_session.query(BookEventType.code).all()}
    assert BookEventCode.COVER_CHANGED.value in codes


def test_put_book_with_new_cover_records_event_on_user_book(
    client, auth_headers, db_session, monkeypatch
):
    book = _make_book(db_session)
    _patch_cover_download(monkeypatch)

    response = client.put(
        f"/books/{book.id}",
        json={"cover_image_url": "https://example.com/new-cover.jpg"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    user_book = db_session.query(UserBook).filter_by(book_id=book.id).one()
    events = _cover_events_for_user_book(db_session, user_book.id)
    assert len(events) == 1
    payload = (
        db_session.query(BookEventCover)
        .filter_by(event_id=events[0].id)
        .one()
    )
    assert payload.old_cover_image_url == "/uploads/covers/old.jpg"
    assert payload.new_cover_image_url == "/uploads/covers/new.jpg"
    assert payload.old_cover_thumbnail_url == "/uploads/covers/thumbnails/old.jpg"
    assert payload.new_cover_thumbnail_url == "/uploads/covers/thumbnails/new.jpg"


def test_put_book_with_unchanged_cover_records_nothing(
    client, auth_headers, db_session, monkeypatch
):
    book = _make_book(db_session)

    response = client.put(
        f"/books/{book.id}",
        json={"title": "Renamed"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    assert db_session.query(BookEventCover).count() == 0


def test_put_book_with_same_cover_url_records_nothing(
    client, auth_headers, db_session, monkeypatch
):
    book = _make_book(db_session, cover_image_url="/uploads/covers/keep.jpg",
                      cover_thumbnail_url="/uploads/covers/thumbnails/keep.jpg")

    response = client.put(
        f"/books/{book.id}",
        json={"cover_image_url": "/uploads/covers/keep.jpg"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    assert db_session.query(BookEventCover).count() == 0


def test_put_book_clearing_cover_records_event(
    client, auth_headers, db_session, monkeypatch
):
    book = _make_book(db_session)

    response = client.put(
        f"/books/{book.id}",
        json={"cover_image_url": None},
        headers=auth_headers,
    )
    assert response.status_code == 200

    user_book = db_session.query(UserBook).filter_by(book_id=book.id).one()
    events = _cover_events_for_user_book(db_session, user_book.id)
    assert len(events) == 1
    payload = (
        db_session.query(BookEventCover).filter_by(event_id=events[0].id).one()
    )
    assert payload.old_cover_image_url == "/uploads/covers/old.jpg"
    assert payload.new_cover_image_url is None
    assert payload.new_cover_thumbnail_url is None


def test_upload_cover_records_event(
    client, auth_headers, db_session, monkeypatch
):
    book = _make_book(db_session)
    _patch_cover_store(monkeypatch)

    response = client.post(
        f"/books/{book.id}/cover",
        headers=auth_headers,
        files={"file": ("cover.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")},
    )
    assert response.status_code == 200

    user_book = db_session.query(UserBook).filter_by(book_id=book.id).one()
    events = _cover_events_for_user_book(db_session, user_book.id)
    assert len(events) == 1
    payload = (
        db_session.query(BookEventCover).filter_by(event_id=events[0].id).one()
    )
    assert payload.old_cover_image_url == "/uploads/covers/old.jpg"
    assert payload.new_cover_image_url == "/uploads/covers/uploaded.jpg"


def test_two_consecutive_changes_record_two_events(
    client, auth_headers, db_session, monkeypatch
):
    book = _make_book(db_session)

    _patch_cover_download(monkeypatch, new_path="/uploads/covers/v2.jpg",
                          new_thumb="/uploads/covers/thumbnails/v2.jpg")
    r1 = client.put(
        f"/books/{book.id}",
        json={"cover_image_url": "https://example.com/v2.jpg"},
        headers=auth_headers,
    )
    assert r1.status_code == 200

    _patch_cover_download(monkeypatch, new_path="/uploads/covers/v3.jpg",
                          new_thumb="/uploads/covers/thumbnails/v3.jpg")
    r2 = client.put(
        f"/books/{book.id}",
        json={"cover_image_url": "https://example.com/v3.jpg"},
        headers=auth_headers,
    )
    assert r2.status_code == 200

    user_book = db_session.query(UserBook).filter_by(book_id=book.id).one()
    events = _cover_events_for_user_book(db_session, user_book.id)
    assert len(events) == 2
    payloads = [
        db_session.query(BookEventCover).filter_by(event_id=e.id).one()
        for e in events
    ]
    assert payloads[0].new_cover_image_url == "/uploads/covers/v2.jpg"
    assert payloads[1].old_cover_image_url == "/uploads/covers/v2.jpg"
    assert payloads[1].new_cover_image_url == "/uploads/covers/v3.jpg"


def test_old_cover_file_is_preserved_on_change(
    client, auth_headers, db_session, monkeypatch
):
    uploads_root = Path("uploads/covers")
    uploads_root.mkdir(parents=True, exist_ok=True)
    old_filename = "test_preserve_cover.jpg"
    old_path = uploads_root / old_filename
    old_path.write_bytes(b"original-cover-bytes")

    try:
        book = _make_book(
            db_session,
            cover_image_url=f"/uploads/covers/{old_filename}",
            cover_thumbnail_url=None,
        )
        _patch_cover_download(monkeypatch)

        response = client.put(
            f"/books/{book.id}",
            json={"cover_image_url": "https://example.com/replacement.jpg"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        assert old_path.exists(), "Old cover file should not be deleted"
    finally:
        if old_path.exists():
            old_path.unlink()


def test_get_book_events_includes_cover_changes_for_user(
    client, auth_headers, db_session, monkeypatch
):
    """Cover-change events should appear in the user's event timeline."""
    book = _make_book(db_session)

    _patch_cover_download(monkeypatch, new_path="/uploads/covers/v2.jpg",
                          new_thumb="/uploads/covers/thumbnails/v2.jpg")
    r = client.put(
        f"/books/{book.id}",
        json={"cover_image_url": "https://example.com/v2.jpg"},
        headers=auth_headers,
    )
    assert r.status_code == 200

    response = client.get(f"/books/{book.id}/events", headers=auth_headers)
    assert response.status_code == 200
    events = response.json()
    cover_events = [
        e for e in events if e["event_type"] == BookEventCode.COVER_CHANGED.value
    ]
    assert len(cover_events) == 1
    assert cover_events[0]["new_cover_image_url"] == "/uploads/covers/v2.jpg"
    assert cover_events[0]["old_cover_image_url"] == "/uploads/covers/old.jpg"
