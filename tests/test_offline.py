"""Bundled offline fake providers."""

from __future__ import annotations

import json

import pytest

from ai.providers.base import ProviderError

from foodanalyzer.offline import OfflineNutrition, OfflineVLM


def test_offline_vlm_reads_filename():
    payload = json.loads(OfflineVLM().describe("data/rice_chicken.png", "prompt"))
    assert payload["meal_recognized"] is True
    names = {i["name"] for i in payload["ingredients"]}
    assert names == {"white rice (cooked)", "grilled chicken breast"}


def test_offline_vlm_unknown_meal():
    payload = json.loads(OfflineVLM().describe("data/no_meal_blue.png", "prompt"))
    assert payload["meal_recognized"] is False
    assert payload["ingredients"] == []


def test_offline_nutrition_known():
    facts = OfflineNutrition().lookup("broccoli")
    assert facts.kcal_per_100g == 34


def test_offline_nutrition_unknown_raises():
    with pytest.raises(ProviderError):
        OfflineNutrition().lookup("dragonfruit")
