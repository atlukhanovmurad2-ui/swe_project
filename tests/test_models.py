"""SE-layer pydantic models."""

from __future__ import annotations

from ai.schemas import Nutrition

from foodanalyzer.models import (
    AnalysisResult,
    AnalysisStatus,
    AnalyzedIngredient,
    IngredientStatus,
    MacroBreakdown,
)


def test_macro_percentages_sum_to_100():
    m = MacroBreakdown(kcal=500, protein_g=25, carbs_g=50, fat_g=20)
    total = m.protein_pct + m.carbs_pct + m.fat_pct
    assert abs(total - 100.0) < 0.2


def test_macro_percentages_zero_when_empty():
    m = MacroBreakdown()
    assert m.protein_pct == 0.0 and m.fat_pct == 0.0


def test_from_ai_nutrition_rounds():
    n = Nutrition(kcal=234.5678, protein_g=4.9012, carbs_g=50.4, fat_g=0.53)
    m = MacroBreakdown.from_ai_nutrition(n)
    assert m.kcal == 234.57
    assert m.protein_g == 4.9


def test_result_to_public_dict_expands_percentages():
    result = AnalysisResult(
        status=AnalysisStatus.OK,
        image_filename="x.png",
        ingredients=[
            AnalyzedIngredient(
                name="rice", estimated_grams=100, confidence=0.9,
                status=IngredientStatus.OK, nutrition=MacroBreakdown(kcal=130),
            )
        ],
        totals=MacroBreakdown(kcal=130, protein_g=2.7, carbs_g=28, fat_g=0.3),
    )
    data = result.to_public_dict()
    assert "protein_pct" in data["totals"]
    assert data["status"] == "ok"
    assert data["ingredients"][0]["name"] == "rice"


def test_record_from_result_roundtrips():
    result = AnalysisResult(status=AnalysisStatus.UNKNOWN_MEAL, image_filename="x.png")
    from foodanalyzer.models import AnalysisRecord

    rec = AnalysisRecord.from_result(result, image_path="/tmp/x.png")
    assert rec.id == result.id
    assert rec.image_path == "/tmp/x.png"
    assert rec.status is AnalysisStatus.UNKNOWN_MEAL
