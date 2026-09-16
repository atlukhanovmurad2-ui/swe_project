"""Parallel nutrition lookups.

When the VLM returns N ingredients we have N independent, blocking HTTP calls.
Running them with ``asyncio.gather`` over a thread pool cuts wall-clock time
roughly N-fold, bounded by a semaphore so we never burst past the provider's
rate limit.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from ai.nutrition import NutritionProvider
from ai.schemas import Ingredient, NutritionFacts

from foodanalyzer.errors import NutritionLookupError
from foodanalyzer.logging_config import get_logger

_log = get_logger(__name__)


@dataclass
class LookupOutcome:
    """Result of one ingredient's nutrition lookup."""

    name: str
    facts: NutritionFacts | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.facts is not None


@dataclass
class PipelineResult:
    facts_by_name: dict[str, NutritionFacts] = field(default_factory=dict)
    outcomes: list[LookupOutcome] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def failures(self) -> list[LookupOutcome]:
        return [o for o in self.outcomes if not o.ok]


async def lookup_nutrition(
    ingredients: list[Ingredient],
    provider: NutritionProvider,
    *,
    max_concurrency: int = 10,
) -> PipelineResult:
    """Look up nutrition facts for every ingredient, in parallel.

    Never raises for an individual failure — each ingredient's fate is
    recorded in :class:`LookupOutcome`. De-duplicates repeated names so the
    same string is only looked up once per call.
    """
    unique_names = list(dict.fromkeys(i.name for i in ingredients))
    if not unique_names:
        return PipelineResult()

    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    _log.info(
        "looking up %d unique ingredient(s) with concurrency=%d",
        len(unique_names), max_concurrency,
    )

    async def _one(name: str) -> LookupOutcome:
        async with semaphore:
            try:
                facts = await asyncio.to_thread(provider.lookup, name)
                return LookupOutcome(name=name, facts=facts)
            except NutritionLookupError as exc:
                _log.warning("nutrition lookup failed for %r: %s", name, exc)
                return LookupOutcome(name=name, error=str(exc))
            except Exception as exc:  # defensive: a provider bug must not kill the batch
                _log.exception("unexpected error looking up %r", name)
                return LookupOutcome(name=name, error=f"{type(exc).__name__}: {exc}")

    start = time.perf_counter()
    outcomes = await asyncio.gather(*(_one(n) for n in unique_names))
    elapsed = time.perf_counter() - start

    facts_by_name = {o.name: o.facts for o in outcomes if o.facts is not None}
    _log.info(
        "nutrition lookups done in %.3fs (%d ok, %d failed)",
        elapsed, len(facts_by_name), len(outcomes) - len(facts_by_name),
    )
    return PipelineResult(
        facts_by_name=facts_by_name,
        outcomes=list(outcomes),
        elapsed_seconds=elapsed,
    )
