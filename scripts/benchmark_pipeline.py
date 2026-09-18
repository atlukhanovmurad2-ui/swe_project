"""Measure the wall-clock speed-up from parallelising nutrition lookups.

Uses a fake provider with a fixed per-call latency so the result is
deterministic and offline.

    python scripts/benchmark_pipeline.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.nutrition import NutritionProvider
from ai.schemas import Ingredient, NutritionFacts

from foodanalyzer.concurrency.pipeline import lookup_nutrition

LATENCY = 0.20  # seconds per simulated USDA call
N = 6


class LatentProvider(NutritionProvider):
    def lookup(self, ingredient_name: str) -> NutritionFacts:
        time.sleep(LATENCY)
        return NutritionFacts(
            name=ingredient_name, kcal_per_100g=100, protein_g_per_100g=5,
            carbs_g_per_100g=10, fat_g_per_100g=2, source="bench",
        )


async def main() -> None:
    ingredients = [
        Ingredient(name=f"ingredient {i}", estimated_grams=100, confidence=0.9)
        for i in range(N)
    ]
    provider = LatentProvider()

    serial_start = time.perf_counter()
    for ing in ingredients:
        provider.lookup(ing.name)
    serial = time.perf_counter() - serial_start

    result = await lookup_nutrition(ingredients, provider, max_concurrency=N)

    print(f"ingredients          : {N}")
    print(f"per-call latency     : {LATENCY * 1000:.0f} ms")
    print(f"serial               : {serial:.3f} s")
    print(f"parallel (gather)    : {result.elapsed_seconds:.3f} s")
    print(f"speed-up             : {serial / result.elapsed_seconds:.1f}x")


if __name__ == "__main__":
    asyncio.run(main())
