"""Upload validation rules."""

from __future__ import annotations

import pytest

from foodanalyzer.errors import (
    FileTooLargeError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from foodanalyzer.validation import sniff_image_type, validate_image_file, validate_upload


def test_sniff_png(png_bytes):
    assert sniff_image_type(png_bytes) == "image/png"


def test_sniff_jpeg(jpeg_bytes):
    assert sniff_image_type(jpeg_bytes) == "image/jpeg"


def test_sniff_unknown():
    assert sniff_image_type(b"GIF89a....") is None


def test_validate_accepts_png(png_bytes):
    assert validate_upload(png_bytes, filename="x.png", declared_content_type="image/png") == "image/png"


def test_validate_rejects_empty():
    with pytest.raises(ValidationError):
        validate_upload(b"", filename="x.png")


def test_validate_rejects_non_image():
    with pytest.raises(UnsupportedMediaTypeError):
        validate_upload(b"not an image at all", filename="x.png")


def test_validate_rejects_oversize(png_bytes):
    with pytest.raises(FileTooLargeError):
        validate_upload(png_bytes, filename="x.png", max_size_bytes=4)


def test_validate_rejects_bad_extension(png_bytes):
    with pytest.raises(UnsupportedMediaTypeError):
        validate_upload(png_bytes, filename="x.gif")


def test_validate_rejects_content_type_mismatch(png_bytes):
    with pytest.raises(UnsupportedMediaTypeError):
        validate_upload(png_bytes, filename="x.png", declared_content_type="application/pdf")


def test_validate_image_file_missing(tmp_path):
    with pytest.raises(ValidationError):
        validate_image_file(tmp_path / "nope.png")


def test_validate_image_file_ok(meal_png):
    assert validate_image_file(meal_png) == "image/png"
