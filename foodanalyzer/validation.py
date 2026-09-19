"""Upload validation: content type,magic bytes and size limits

The users input is checked using the first bytes of the provided file are compared with jpeg and png signatures

"""

from __future__ import annotations

from pathlib import Path

from foodanalyzer.config import get_settings
from foodanalyzer.errors import (
    FileTooLargeError,
    UnsupportedMediaTypeError,
    ValidationError,
)

# (extension, mime, signature-prefix)
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def sniff_image_type(data: bytes) -> str | None:
    """Return ``"image/png"`` / ``"image/jpeg"`` from magic bytes, else ``None``."""
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    return None


def validate_upload(
    data: bytes,
    *,
    filename: str | None,
    declared_content_type: str | None = None,
    max_size_bytes: int | None = None,
) -> str:
    """Validate  in-memory upload.

    Returns the detected type on success or raises a
    ValidationError otherwise.
    """
    if not data:
        raise ValidationError("Uploaded file is empty.")

    limit = max_size_bytes if max_size_bytes is not None else get_settings().max_image_size_bytes
    if len(data) > limit:
        raise FileTooLargeError(
            f"File is {len(data) / 1_048_576:.2f} MB; the limit is {limit / 1_048_576:.2f} MB."
        )

    detected = sniff_image_type(data)
    if detected is None:
        raise UnsupportedMediaTypeError(
            "File is not a valid JPEG or PNG (magic-byte check failed)."
        )

    if declared_content_type:
        ct = declared_content_type.split(";", 1)[0].strip().lower()
        if ct and ct not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedMediaTypeError(
                f"Declared content type {ct!r} is not an accepted image type."
            )

    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix and suffix not in ALLOWED_EXTENSIONS:
            raise UnsupportedMediaTypeError(
                f"File extension {suffix!r} is not an accepted image type."
            )

    return detected


def validate_image_file(path: str | Path, *, max_size_bytes: int | None = None) -> str:
    """Validate an image already on disk (used by the CLI)."""
    p = Path(path)
    if not p.is_file():
        raise ValidationError(f"Image not found: {p}")
    data = p.read_bytes()
    return validate_upload(
        data,
        filename=p.name,
        declared_content_type=None,
        max_size_bytes=max_size_bytes,
    )
