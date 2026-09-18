"""Retry/logging wrapper around the provided ``ai`` entry points.

Business logic never imports ``ai`` directly for the VLM call — it goes
through :func:`identify_ingredients` here so retries, logging and error
translation happen in exactly one place.
"""

from __future__ import annotations

from ai import identify_ingredients as _ai_identify_ingredients
from ai.nutrition import NutritionProvider, get_nutrition_provider
from ai.providers.base import ProviderError, VLMProvider
from ai.schemas import Ingredient

from foodanalyzer.config import Settings, get_settings
from foodanalyzer.errors import IngredientIdentificationError
from foodanalyzer.logging_config import get_logger
from foodanalyzer.services.nutrition_cache import CachingNutritionProvider
from foodanalyzer.services.retry import RetryPolicy, retry_call

_log = get_logger(__name__)


def identify_ingredients(
    image_path: str,
    *,
    vlm: VLMProvider | None = None,
    policy: RetryPolicy | None = None,
) -> list[Ingredient]:
    """Identify ingredients in ``image_path`` with exponential-backoff retries.

    Returns ``[]`` when the VLM reports no meal (a normal control-flow branch,
    not an error). Raises :class:`IngredientIdentificationError` if the call
    keeps failing.
    """
    _log.info("identifying ingredients in %s", image_path)
    try:
        ingredients = retry_call(
            lambda: _ai_identify_ingredients(image_path, vlm=vlm),
            retry_on=(ProviderError,),
            policy=policy,
            description="VLM identify_ingredients",
        )
    except ProviderError as exc:
        raise IngredientIdentificationError(str(exc)) from exc

    if not ingredients:
        _log.info("VLM did not recognise a meal in %s", image_path)
    else:
        _log.info("VLM identified %d ingredient(s)", len(ingredients))
    return ingredients


def build_nutrition_provider(
    settings: Settings | None = None,
    *,
    inner: NutritionProvider | None = None,
) -> CachingNutritionProvider:
    """Construct the cache+retry-wrapped nutrition provider from settings."""
    settings = settings or get_settings()
    if inner is None:
        inner = get_nutrition_provider()
    return CachingNutritionProvider(
        inner,
        ttl_seconds=settings.nutrition_cache_ttl_seconds,
        retry_policy=RetryPolicy(
            max_attempts=settings.retry_max_attempts,
            base_delay=settings.retry_base_delay_seconds,
            max_delay=settings.retry_max_delay_seconds,
        ),
    )
