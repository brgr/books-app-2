import pytest

from app.models import ReadingShelf
from app.shelves.refs import (
    CustomShelfRef,
    InvalidShelfRefError,
    ReadingShelfRef,
    parse_shelf_ref,
)


def test_parse_shelf_ref_returns_typed_canonical_refs():
    reading_ref = parse_shelf_ref("reading:started")
    custom_ref = parse_shelf_ref("custom:42")

    assert reading_ref == ReadingShelfRef(ReadingShelf.STARTED)
    assert str(reading_ref) == "reading:started"
    assert custom_ref == CustomShelfRef(42)
    assert str(custom_ref) == "custom:42"


@pytest.mark.parametrize(
    ("value", "detail"),
    [
        ("started", "Shelf ref must be 'reading:<shelf>' or 'custom:<positive id>'"),
        (
            "reading:later",
            "Unknown reading shelf 'later'. Expected one of: "
            "want_to_read, started, finished, abandoned",
        ),
        ("custom:0042", "Custom shelf id must be a positive decimal integer"),
    ],
)
def test_parse_shelf_ref_rejects_invalid_values(value, detail):
    with pytest.raises(InvalidShelfRefError, match=detail):
        parse_shelf_ref(value)
