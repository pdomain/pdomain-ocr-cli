from __future__ import annotations

from pathlib import Path

import pytest

from pdomain_ocr_cli._image_limits import (
    MAX_IMAGE_BYTES,
    MAX_IMAGE_PIXELS,
    ImageLimitError,
    validate_byte_size,
    validate_pixel_count,
)


def test_validate_byte_size_accepts_exact_limit() -> None:
    path = Path("page.png")
    assert validate_byte_size(path, MAX_IMAGE_BYTES) is None


def test_validate_byte_size_rejects_one_byte_over_limit() -> None:
    path = Path("page.png")
    with pytest.raises(
        ImageLimitError,
        match=rf"page\.png: {MAX_IMAGE_BYTES + 1} bytes exceeds .*{MAX_IMAGE_BYTES}",
    ):
        validate_byte_size(path, MAX_IMAGE_BYTES + 1)


def test_validate_pixel_count_accepts_exact_limit() -> None:
    path = Path("page.png")
    assert validate_pixel_count(path, (10_000, 10_000)) is None


def test_validate_pixel_count_rejects_one_pixel_over_limit() -> None:
    path = Path("page.png")
    with pytest.raises(
        ImageLimitError,
        match=rf"page\.png: 100000001 pixels exceeds .*{MAX_IMAGE_PIXELS}",
    ):
        validate_pixel_count(path, (100_000_001, 1))
