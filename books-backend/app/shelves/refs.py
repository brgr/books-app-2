"""Typed, canonical references for shelves exposed by the API."""

from dataclasses import dataclass

from app.models import ReadingShelf


class InvalidShelfRefError(ValueError):
    """A shelf ref is malformed or names an unknown reading shelf."""


@dataclass(frozen=True)
class ReadingShelfRef:
    shelf: ReadingShelf

    def __str__(self) -> str:
        return f"reading:{self.shelf.value}"


@dataclass(frozen=True)
class CustomShelfRef:
    id: int

    def __post_init__(self) -> None:
        if self.id < 1:
            raise ValueError("Custom shelf ids must be positive")

    def __str__(self) -> str:
        return f"custom:{self.id}"


ShelfRef = ReadingShelfRef | CustomShelfRef

_READING_SHELF_VALUES = ", ".join(shelf.value for shelf in ReadingShelf)


def parse_shelf_ref(value: str) -> ShelfRef:
    """Parse a URL ref into its typed, canonical shelf reference."""
    kind, separator, target = value.partition(":")
    if not separator or not target:
        raise InvalidShelfRefError(
            "Shelf ref must be 'reading:<shelf>' or 'custom:<positive id>'"
        )

    if kind == "reading":
        try:
            return ReadingShelfRef(ReadingShelf(target))
        except ValueError:
            raise InvalidShelfRefError(
                f"Unknown reading shelf '{target}'. Expected one of: "
                f"{_READING_SHELF_VALUES}"
            ) from None

    if kind == "custom":
        if not target.isascii() or not target.isdecimal() or target.startswith("0"):
            raise InvalidShelfRefError(
                "Custom shelf id must be a positive decimal integer"
            )
        return CustomShelfRef(int(target))

    raise InvalidShelfRefError("Shelf ref must start with 'reading:' or 'custom:'")
