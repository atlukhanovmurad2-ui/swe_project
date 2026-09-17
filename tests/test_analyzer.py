"""End-to-end analyzer pipeline (offline)."""

from __future__ import annotations

import json

import pytest

from ai.providers.base import ProviderError, VLMProvider

from foodanalyzer.core.analyzer import analyze_image
from foodanalyzer.errors import IngredientIdentificationError, UnsupportedMediaTypeError
from foodanalyzer.models import AnalysisStatus, IngredientStatus
from foodanalyzer.offline import OfflineNutrition, OfflineVLM
from foodanalyzer.storage.memory import InMemoryHistoryRepository


pytestmark = pytest.mark.asyncio

async def test_happy_path(meal_png):
    repo = InMemoryHistoryRepository()
    result = await analyze_image(
        meal_png, vlm=OfflineVLM(), nutrition_provider=OfflineNutrition(), repository=repo,
    )
    assert result.status is AnalysisStatus.OK
    names = {i.name for i in result.ingredients}
    assert names == {"white rice (cooked)", "grilled chicken breast", "broccoli"}
    assert result.totals.kcal > 0
    assert all(i.status is IngredientStatus.OK for i in result.ingredients)
    assert await repo.count() == 1


async def test_unknown_meal(tmp_path, png_bytes):
    p = tmp_path / "no_meal_blue.png"
    p.write_bytes(png_bytes)
    repo = InMemoryHistoryRepository()
    result = await analyze_image(
        p, vlm=OfflineVLM(), nutrition_provider=OfflineNutrition(), repository=repo,
    )
    assert result.status is AnalysisStatus.UNKNOWN_MEAL
    assert result.ingredients == []
    assert result.warnings
    assert await repo.count() == 1


async def test_partial_when_a_lookup_is_missing(meal_png):
    class HalfNutrition(OfflineNutrition):
        def lookup(self, name):
            if name == "broccoli":
                raise ProviderError("USDA: no match for 'broccoli'")
            return super().lookup(name)

    result = await analyze_image(
        meal_png, vlm=OfflineVLM(), nutrition_provider=HalfNutrition(),
    )
    assert result.status is AnalysisStatus.PARTIAL
    broc = next(i for i in result.ingredients if i.name == "broccoli")
    assert broc.status is IngredientStatus.NOT_FOUND
    assert broc.nutrition is None


async def test_vlm_failure_raises_after_retries(meal_png):
    class BrokenVLM(VLMProvider):
        def describe(self, *a, **k):
            raise ProviderError("503 from provider")

    with pytest.raises(IngredientIdentificationError):
        await analyze_image(meal_png, vlm=BrokenVLM(), nutrition_provider=OfflineNutrition())


async def test_rejects_non_image(tmp_path):
    p = tmp_path / "meal.png"
    p.write_bytes(b"this is not a png")
    with pytest.raises(UnsupportedMediaTypeError):
        await analyze_image(p, vlm=OfflineVLM(), nutrition_provider=OfflineNutrition())


async def test_transient_vlm_error_recovers(meal_png):
    class FlakyVLM(VLMProvider):
        def __init__(self):
            self.n = 0

        def describe(self, image_path, prompt, *, json_schema=None):
            self.n += 1
            if self.n < 2:
                raise ProviderError("temporary blip")
            return json.dumps(
                {"meal_recognized": True,
                 "ingredients": [{"name": "broccoli", "estimated_grams": 80, "confidence": 0.9}]}
            )

    result = await analyze_image(
        meal_png, vlm=FlakyVLM(), nutrition_provider=OfflineNutrition(),
    )
    assert result.status is AnalysisStatus.OK
    assert result.ingredients[0].name == "broccoli"
