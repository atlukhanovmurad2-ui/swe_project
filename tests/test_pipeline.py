"""Parallel nutrition-lookup pipeline."""

from __future__ import annotations

import asyncio
import time

import pytest

from ai.nutrition import NutritionProvider
from ai.schemas import Ingredient, NutritionFacts

from foodanalyzer.concurrency.pipeline import lookup_nutrition
from foodanalyzer.errors import NutritionLookupError

pytestmark = pytest.mark.asyncio


def _facts(name: str) -> NutritionFacts:
    return NutritionFacts(
        name=name, kcal_per_100g=100, protein_g_per_100g=5,
        carbs_g_per_100g=10, fat_g_per_100g=2, source="fake",
    )


class SlowProvider(NutritionProvider):
    def __init__(self, delay=0.1, *, unknown=frozenset(), boom=frozenset()):
        self.delay = delay
        self.unknown = unknown
        self.boom = boom
        self.max_in_flight = 0
        self._in_flight = 0
        self._lock = __import__("threading").Lock()

    def lookup(self, ingredient_name: str) -> NutritionFacts:
        with self._lock:
            self._in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self._in_flight)
        try:
            time.sleep(self.delay)
            if ingredient_name in self.boom:
                raise NutritionLookupError("kaboom")
            if ingredient_name in self.unknown:
                raise NutritionLookupError("USDA: no match")
            return _facts(ingredient_name)
        finally:
            with self._lock:
                self._in_flight -= 1


def _ings(*names) -> list[Ingredient]:
    return [Ingredient(name=n, estimated_grams=100, confidence=0.9) for n in names]


async def test_runs_in_parallel():
    provider = SlowProvider(delay=0.1)
    ings = _ings("a", "b", "c", "d", "e")
    start = time.perf_counter()
    result = await lookup_nutrition(ings, provider, max_concurrency=5)
    elapsed = time.perf_counter() - start
    assert len(result.facts_by_name) == 5
    assert elapsed < 0.35  # ~0.1s in parallel, not 0.5s serial


async def test_semaphore_bounds_concurrency():
    provider = SlowProvider(delay=0.05)
    ings = _ings(*(f"i{n}" for n in range(12)))
    await lookup_nutrition(ings, provider, max_concurrency=3)
    assert provider.max_in_flight <= 3


async def test_deduplicates_names():
    provider = SlowProvider(delay=0.01)
    calls: list[str] = []
    orig = provider.lookup

    def spy(name):
        calls.append(name)
        return orig(name)

    provider.lookup = spy  # type: ignore
    await lookup_nutrition(_ings("rice", "rice", "rice"), provider)
    assert calls == ["rice"]


async def test_failures_are_captured_not_raised():
    provider = SlowProvider(delay=0.01, unknown={"mystery"}, boom={"cursed"})
    result = await lookup_nutrition(_ings("ok", "mystery", "cursed"), provider)
    assert set(result.facts_by_name) == {"ok"}
    assert {o.name for o in result.failures} == {"mystery", "cursed"}


async def test_empty_ingredient_list():
    result = await lookup_nutrition([], SlowProvider())
    assert result.facts_by_name == {}
