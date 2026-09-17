"""The end-to-end meal-analysis pipeline.

    validate → identify ingredients (VLM, retried)
             → look up nutrition per ingredient (parallel, cached, retried)
             → compute totals (pure)
             → persist to the history log

Every branch returns a structured :class:`AnalysisResult`; the only things
that raise are unrecoverable (VLM down after retries, bad upload).
"""

from __future__ import annotations

from pathlib import Path

from ai import compute_totals
from ai.nutrition import NutritionProvider
from ai.providers.base import VLMProvider
from ai.schemas import Ingredient

from foodanalyzer.config import Settings, get_settings
from foodanalyzer.concurrency.pipeline import lookup_nutrition
from foodanalyzer.logging_config import get_logger
from foodanalyzer.models import (
    AnalysisRecord,
    AnalysisResult,
    AnalysisStatus,
    AnalyzedIngredient,
    IngredientStatus,
    MacroBreakdown,
)
from foodanalyzer.services.ai_service import build_nutrition_provider, identify_ingredients
from foodanalyzer.services.nutrition_cache import CachingNutritionProvider
from foodanalyzer.services.retry import RetryPolicy
from foodanalyzer.storage.base import HistoryRepository
from foodanalyzer.validation import validate_image_file

_log = get_logger(__name__)


async def analyze_image(
    image_path: str | Path,
    *,
    settings: Settings | None = None,
    vlm: VLMProvider | None = None,
    nutrition_provider: NutritionProvider | None = None,
    repository: HistoryRepository | None = None,
    original_filename: str | None = None,
    validate: bool = True,
) -> AnalysisResult:
    """Analyse a single meal photo and (best-effort) persist the result."""
    settings = settings or get_settings()
    path = Path(image_path)
    filename = original_filename or path.name

    if validate:
        validate_image_file(path, max_size_bytes=settings.max_image_size_bytes)

    policy = RetryPolicy(
        max_attempts=settings.retry_max_attempts,
        base_delay=settings.retry_base_delay_seconds,
        max_delay=settings.retry_max_delay_seconds,
    )

    ingredients: list[Ingredient] = identify_ingredients(str(path), vlm=vlm, policy=policy)

    if not ingredients:
        result = AnalysisResult(
            status=AnalysisStatus.UNKNOWN_MEAL,
            image_filename=filename,
            warnings=["The model could not identify a meal in this image."],
        )
        await _persist(repository, result, image_path=str(path))
        return result

    if nutrition_provider is None:
        provider = build_nutrition_provider(settings)
    elif isinstance(nutrition_provider, CachingNutritionProvider):
        provider = nutrition_provider
    else:
        # Wrap injected providers too, so caching/retries/error-translation apply.
        provider = build_nutrition_provider(settings, inner=nutrition_provider)
    pipeline = await lookup_nutrition(
        ingredients, provider, max_concurrency=settings.max_concurrency
    )

    facts_by_name = pipeline.facts_by_name
    totals = compute_totals(ingredients, facts_by_name)

    analysed: list[AnalyzedIngredient] = []
    outcome_by_name = {o.name: o for o in pipeline.outcomes}
    for ing in ingredients:
        outcome = outcome_by_name.get(ing.name)
        facts = facts_by_name.get(ing.name)
        if facts is not None:
            analysed.append(
                AnalyzedIngredient(
                    name=ing.name,
                    estimated_grams=ing.estimated_grams,
                    confidence=ing.confidence,
                    status=IngredientStatus.OK,
                    matched_food=facts.name,
                    source=facts.source,
                    nutrition=MacroBreakdown.from_ai_nutrition(
                        facts.for_grams(ing.estimated_grams)
                    ),
                )
            )
        else:
            err = outcome.error if outcome else "no result"
            not_found = err is not None and "no match" in err.lower()
            analysed.append(
                AnalyzedIngredient(
                    name=ing.name,
                    estimated_grams=ing.estimated_grams,
                    confidence=ing.confidence,
                    status=IngredientStatus.NOT_FOUND if not_found else IngredientStatus.LOOKUP_FAILED,
                    error=err,
                )
            )

    missing = [a.name for a in analysed if a.status != IngredientStatus.OK]
    warnings: list[str] = []
    if missing:
        warnings.append(
            f"No nutrition data for {len(missing)} ingredient(s): {', '.join(missing)}. "
            "Totals cover the remaining ingredients only."
        )
    status = AnalysisStatus.OK if not missing else AnalysisStatus.PARTIAL

    result = AnalysisResult(
        status=status,
        image_filename=filename,
        ingredients=analysed,
        totals=MacroBreakdown.from_ai_nutrition(totals),
        warnings=warnings,
    )
    _log.info(
        "analysis %s: status=%s kcal=%.0f (%d/%d ingredients priced)",
        result.id, status.value, result.totals.kcal,
        len(ingredients) - len(missing), len(ingredients),
    )
    await _persist(repository, result, image_path=str(path))
    return result


async def _persist(
    repository: HistoryRepository | None,
    result: AnalysisResult,
    *,
    image_path: str,
) -> None:
    if repository is None:
        return
    try:
        await repository.add(AnalysisRecord.from_result(result, image_path=image_path))
    except Exception:  # storage must never break a successful analysis
        _log.exception("failed to persist analysis %s to the history log", result.id)
