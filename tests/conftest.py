"""Shared fixtures for Topic 2 smoke tests."""

from __future__ import annotations

import json
from typing import Any

import pytest

from ai.providers.base import VLMProvider
from ai.nutrition import NutritionProvider
from ai.schemas import NutritionFacts


class FakeVLM(VLMProvider):
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or {
            "meal_recognized": True,
            "ingredients": [
                {"name": "white rice (cooked)", "estimated_grams": 200.0, "confidence": 0.9},
                {"name": "grilled chicken breast", "estimated_grams": 150.0, "confidence": 0.85},
                {"name": "broccoli", "estimated_grams": 80.0, "confidence": 0.8},
            ],
        }
        self.calls: list[tuple[str, str]] = []

    def describe(
        self,
        image_path: str,
        prompt: str,
        *,
        json_schema: dict | None = None,
    ) -> str:
        self.calls.append((image_path, prompt))
        return json.dumps(self.payload)


class FakeNutrition(NutritionProvider):
    """In-memory nutrition database for tests. No network."""

    DB = {
        "white rice (cooked)": NutritionFacts(
            name="Rice, white, cooked",
            kcal_per_100g=130, protein_g_per_100g=2.7,
            carbs_g_per_100g=28, fat_g_per_100g=0.3,
            source="fake",
        ),
        "grilled chicken breast": NutritionFacts(
            name="Chicken breast, grilled",
            kcal_per_100g=165, protein_g_per_100g=31,
            carbs_g_per_100g=0, fat_g_per_100g=3.6,
            source="fake",
        ),
        "broccoli": NutritionFacts(
            name="Broccoli, raw",
            kcal_per_100g=34, protein_g_per_100g=2.8,
            carbs_g_per_100g=7, fat_g_per_100g=0.4,
            source="fake",
        ),
    }

    def lookup(self, ingredient_name: str) -> NutritionFacts:
        from ai.providers.base import ProviderError
        if ingredient_name not in self.DB:
            raise ProviderError(f"unknown ingredient: {ingredient_name!r}")
        return self.DB[ingredient_name]


@pytest.fixture
def fake_vlm() -> FakeVLM:
    return FakeVLM()


@pytest.fixture
def fake_nutrition() -> FakeNutrition:
    return FakeNutrition()


@pytest.fixture
def sample_image(tmp_path):
    """Tiny valid PNG for VLM input checks."""
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000"
        "00907753de0000000c4944415408d76360000000000004000146a13a"
        "020000000049454e44ae426082"
    )
    p = tmp_path / "meal.png"
    p.write_bytes(png_bytes)
    return str(p)


# --- SE-layer shared fixtures (added by the project; the smoke tests above
#     do not depend on anything below) -----------------------------------

_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c4944415408d76360000000000004000146a13a"
    "020000000049454e44ae426082"
)
_TINY_JPEG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")


@pytest.fixture
def png_bytes() -> bytes:
    return _TINY_PNG


@pytest.fixture
def jpeg_bytes() -> bytes:
    return _TINY_JPEG


@pytest.fixture
def meal_png(tmp_path):
    """A PNG on disk whose name drives the offline VLM (rice + chicken + broccoli)."""
    p = tmp_path / "rice_chicken_broccoli.png"
    p.write_bytes(_TINY_PNG)
    return p


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Give every SE-layer test a clean, offline configuration."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("RETRY_BASE_DELAY_SECONDS", "0")
    monkeypatch.setenv("RETRY_MAX_DELAY_SECONDS", "0")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    try:
        from foodanalyzer.config import reset_settings_cache

        reset_settings_cache()
    except Exception:
        pass
    yield
    try:
        from foodanalyzer.config import reset_settings_cache

        reset_settings_cache()
    except Exception:
        pass
