"""Shared perceptual comparison for cover selection and upgrades."""

from typing import Literal

import imagehash
from PIL import Image

EXACT_THRESHOLD = 6
LIKELY_THRESHOLD = 10
MatchQuality = Literal["exact", "likely"]


def cover_match_quality(distance: int) -> MatchQuality | None:
    """Classify the distance between two 64-bit (8x8) perceptual hashes."""
    if distance <= EXACT_THRESHOLD:
        return "exact"
    if distance <= LIKELY_THRESHOLD:
        return "likely"

    return None


def covers_match(first: Image.Image, second: Image.Image) -> bool:
    quality = cover_match_quality(
        imagehash.phash(first.convert("RGB")) - imagehash.phash(second.convert("RGB"))
    )

    return quality is not None
