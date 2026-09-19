"""A TTL local cache and retry wrapper around ai.NutritionProvider"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from ai.nutrition import NutritionProvider
from ai.providers.base import ProviderError
from ai.schemas import NutritionFacts

from foodanalyzer.errors import NutritionLookupError
from foodanalyzer.logging_config import get_logger
from foodanalyzer.services.retry import RetryPolicy, retry_call

_log = get_logger(__name__)


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


@dataclass
class _Entry:
    facts: NutritionFacts
    stored_at: float


class CacheStats:
    __slots__ = ("hits", "misses")

    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0

    @property
    def lookups(self) -> int:
        return self.hits + self.misses

    def as_dict(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses, "lookups": self.lookups}


class CachingNutritionProvider(NutritionProvider):

    def __init__(
        self,
        inner: NutritionProvider,
        *,
        ttl_seconds: float,
        retry_policy: RetryPolicy | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._inner = inner
        self._ttl = float(ttl_seconds)
        self._retry_policy = retry_policy
        self._clock = clock or time.monotonic
        self._store: dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self.stats = CacheStats()

    
    def lookup(self, ingredient_name: str) -> NutritionFacts:
        if not ingredient_name or not ingredient_name.strip():
            raise NutritionLookupError("ingredient name must be non-empty")

        key = _norm(ingredient_name)
        now = self._clock()

        with self._lock:
            entry = self._store.get(key)
            if entry is not None and (self._ttl == 0 or now - entry.stored_at < self._ttl):
                self.stats.hits += 1
                _log.debug("nutrition cache hit for %r", key)
                return entry.facts

        self.stats.misses += 1
        _log.debug("nutrition cache miss for %r — querying provider", key)

        try:
            facts = retry_call(
                lambda: self._inner.lookup(ingredient_name),
                retry_on=(ProviderError,),
                policy=self._retry_policy,
                description=f"nutrition lookup {ingredient_name!r}",
            )
        except ProviderError as exc:
            raise NutritionLookupError(str(exc)) from exc

        with self._lock:
            self._store[key] = _Entry(facts=facts, stored_at=self._clock())
        return facts

    
    def invalidate(self, ingredient_name: str | None = None) -> None:
        with self._lock:
            if ingredient_name is None:
                self._store.clear()
            else:
                self._store.pop(_norm(ingredient_name), None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
