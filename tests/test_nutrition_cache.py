"""TTL cache + retry wrapper around a NutritionProvider."""

from __future__ import annotations

import pytest

from ai.nutrition import NutritionProvider
from ai.providers.base import ProviderError
from ai.schemas import NutritionFacts

from foodanalyzer.errors import NutritionLookupError
from foodanalyzer.services.nutrition_cache import CachingNutritionProvider
from foodanalyzer.services.retry import RetryPolicy

FACTS = NutritionFacts(
    name="Rice", kcal_per_100g=130, protein_g_per_100g=2.7,
    carbs_g_per_100g=28, fat_g_per_100g=0.3, source="fake",
)


class CountingProvider(NutritionProvider):
    def __init__(self, *, fail_times: int = 0):
        self.calls = 0
        self.fail_times = fail_times

    def lookup(self, ingredient_name: str) -> NutritionFacts:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ProviderError("transient")
        if ingredient_name.strip().lower() == "unobtainium":
            raise ProviderError("USDA: no match for 'unobtainium'")
        return FACTS


@pytest.fixture
def clock():
    return {"t": 0.0}


def _cache(inner, clock, ttl=100.0):
    return CachingNutritionProvider(
        inner,
        ttl_seconds=ttl,
        retry_policy=RetryPolicy(max_attempts=3, base_delay=0, jitter=0),
        clock=lambda: clock["t"],
    )


def test_second_lookup_is_cached(clock):
    inner = CountingProvider()
    cache = _cache(inner, clock)
    cache.lookup("white rice")
    cache.lookup("White Rice")  # normalised to the same key
    assert inner.calls == 1
    assert cache.stats.hits == 1 and cache.stats.misses == 1


def test_cache_expires_after_ttl(clock):
    inner = CountingProvider()
    cache = _cache(inner, clock, ttl=10.0)
    cache.lookup("rice")
    clock["t"] = 11.0
    cache.lookup("rice")
    assert inner.calls == 2


def test_retries_transient_failures(clock):
    inner = CountingProvider(fail_times=2)
    cache = _cache(inner, clock)
    assert cache.lookup("rice") is FACTS
    assert inner.calls == 3


def test_persistent_failure_raises_nutrition_error(clock):
    inner = CountingProvider(fail_times=99)
    cache = _cache(inner, clock)
    with pytest.raises(NutritionLookupError):
        cache.lookup("rice")


def test_no_match_raises_and_is_not_cached(clock):
    inner = CountingProvider()
    cache = _cache(inner, clock)
    with pytest.raises(NutritionLookupError):
        cache.lookup("unobtainium")
    assert len(cache) == 0


def test_empty_name_rejected(clock):
    cache = _cache(CountingProvider(), clock)
    with pytest.raises(NutritionLookupError):
        cache.lookup("   ")
