"""Pure admission-control checks for untrusted image inputs.

Two independent, side-effect-free checks gate every candidate image before
it is decoded for OCR: a compressed-size ceiling (checked from ``stat()``,
before Pillow ever opens the file) and a decoded-pixel-count ceiling
(checked from the Pillow header, before the image enters a batch). Both
checks are pure functions — the caller performs the filesystem/Pillow I/O
and passes the resulting values in — so they're trivially unit-testable at
their exact boundaries.

The CLI owns these limits; see ``docs/specs/2026-07-21-image-resource-limits-design.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

MAX_IMAGE_BYTES = 100 * 1024 * 1024
MAX_IMAGE_PIXELS = 100_000_000
# What the default --batch-pages of 4 could already hold at the per-image cap,
# about 1.2 GB decoded. Only larger --batch-pages values are affected.
MAX_CHUNK_PIXELS = 4 * MAX_IMAGE_PIXELS


class ImageLimitError(ValueError):
    """Raised when a candidate image exceeds a configured resource limit."""


def validate_byte_size(path: Path, size_bytes: int) -> None:
    """Reject ``path`` if its compressed size exceeds ``MAX_IMAGE_BYTES``.

    Callers must run this before opening the file with Pillow, so an
    oversized file is never handed to an image decoder.
    """
    if size_bytes > MAX_IMAGE_BYTES:
        raise ImageLimitError(
            f"{path}: {size_bytes} bytes exceeds the {MAX_IMAGE_BYTES}-byte limit"
        )


def validate_pixel_count(path: Path, dimensions: tuple[int, int]) -> None:
    """Reject ``path`` if its decoded pixel count exceeds ``MAX_IMAGE_PIXELS``.

    Callers must run this before the image enters a decode batch, using
    dimensions read from the Pillow header (no full pixel decode needed).
    """
    pixels = dimensions[0] * dimensions[1]
    if pixels > MAX_IMAGE_PIXELS:
        raise ImageLimitError(f"{path}: {pixels} pixels exceeds the {MAX_IMAGE_PIXELS}-pixel limit")


def exceeds_chunk_budget(chunk_pixels: int, dimensions: tuple[int, int]) -> bool:
    """True when adding the image would overrun the chunk; a first image always fits."""
    return chunk_pixels > 0 and chunk_pixels + dimensions[0] * dimensions[1] > MAX_CHUNK_PIXELS
