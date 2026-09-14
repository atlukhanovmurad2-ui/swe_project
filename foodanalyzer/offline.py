"""Offline fake providers for keyless demos, the CLI ``--offline`` flag and tests.

These mirror the fakes in ``demo_ai.py``: the VLM derives a plausible
ingredient list from the filename, and the nutrition provider serves
hard-coded per-100g facts. No network, no API keys.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai.nutrition import NutritionProvider
from ai.providers.base import ProviderError, VLMProvider
from ai.schemas import NutritionFacts

_KNOWN_INGREDIENTS: dict[str, tuple[str, float]] = {
    "rice": ("white rice (cooked)", 180.0),
    "chicken": ("grilled chicken breast", 150.0),
    "broccoli": ("broccoli", 80.0),
    "salmon": ("salmon, baked", 140.0),
    "potato": ("baked potato", 200.0),
    "egg": ("boiled egg", 50.0),
    "salad": ("mixed green salad", 100.0),
    "pasta": ("pasta, cooked", 220.0),
    "tomato": ("tomato, raw", 70.0),
    "cheese": ("cheddar cheese", 30.0),
    "avocado": ("avocado", 100.0),
    "bread": ("white bread", 60.0),
}


def _nf(name: str, kcal: float, protein: float, carbs: float, fat: float) -> NutritionFacts:
    return NutritionFacts(
        name=name,
        kcal_per_100g=kcal,
        protein_g_per_100g=protein,
        carbs_g_per_100g=carbs,
        fat_g_per_100g=fat,
        source="offline",
    )


_OFFLINE_DB: dict[str, NutritionFacts] = {
    "white rice (cooked)": _nf("Rice, white, cooked", 130, 2.7, 28, 0.3),
    "grilled chicken breast": _nf("Chicken breast, grilled", 165, 31, 0, 3.6),
    "broccoli": _nf("Broccoli, raw", 34, 2.8, 7, 0.4),
    "salmon, baked": _nf("Salmon, baked", 206, 22, 0, 13),
    "baked potato": _nf("Potato, baked", 93, 2.5, 21, 0.1),
    "boiled egg": _nf("Egg, boiled", 155, 13, 1.1, 11),
    "mixed green salad": _nf("Lettuce, mixed greens", 15, 1.4, 2.9, 0.2),
    "pasta, cooked": _nf("Pasta, cooked", 158, 5.8, 31, 0.9),
    "tomato, raw": _nf("Tomato, raw", 18, 0.9, 3.9, 0.2),
    "cheddar cheese": _nf("Cheese, cheddar", 403, 25, 1.3, 33),
    "avocado": _nf("Avocado, raw", 160, 2, 9, 15),
    "white bread": _nf("Bread, white", 265, 9, 49, 3.2),
}


class OfflineVLM(VLMProvider):
    """Derives ingredients from filename keywords (see ``data/`` samples)."""

    def describe(self, image_path: str, prompt: str, *, json_schema=None) -> str:
        stem = Path(image_path).stem.lower()
        ingredients = [
            {"name": name, "estimated_grams": grams, "confidence": 0.85}
            for keyword, (name, grams) in _KNOWN_INGREDIENTS.items()
            if keyword in stem
        ]
        if not ingredients:
            return json.dumps({"meal_recognized": False, "ingredients": []})
        return json.dumps({"meal_recognized": True, "ingredients": ingredients})


class OfflineNutrition(NutritionProvider):
    def lookup(self, ingredient_name: str) -> NutritionFacts:
        key = ingredient_name.strip().lower()
        if key not in _OFFLINE_DB:
            raise ProviderError(f"offline DB: no match for {ingredient_name!r}")
        return _OFFLINE_DB[key]
