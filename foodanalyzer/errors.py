"""Exception hierarchy for the SE layer.

api and cli use these exceptions. 
Provided ai moduleuses ProviderError that is wrapped by these exceptions

"""

from __future__ import annotations


class FoodAnalyzerError(Exception):
    """Standard class for every exception in the api and cli"""

    #: HTTP status the API should use when this bubbles up.
    http_status: int = 500
    #: Short machine-readable slug for the JSON error body.
    code: str = "internal_error"


class ValidationError(FoodAnalyzerError):
    """The upload failed a validation (type, size, missing field)"""

    http_status = 422
    code = "validation_error"


class UnsupportedMediaTypeError(ValidationError):
    """The uploaded file is not a jpeg or png"""

    http_status = 415
    code = "unsupported_media_type"


class FileTooLargeError(ValidationError):
    """The uploaded file exceeds MAX_IMAGE_SIZE_MB"""

    http_status = 413
    code = "file_too_large"


class IngredientIdentificationError(FoodAnalyzerError):
    """The VLM call failed after some retries."""

    http_status = 502
    code = "vlm_unavailable"


class NutritionLookupError(FoodAnalyzerError):
    """A nutrition provider call failed after some retries."""

    http_status = 502
    code = "nutrition_unavailable"


class StorageError(FoodAnalyzerError):
    """The history log could not be read or written."""

    http_status = 503
    code = "storage_unavailable"
