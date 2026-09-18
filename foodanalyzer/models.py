"""Pydantic models the SE layer produces and stores.

These are distinct from the ``ai`` package's schemas (``Ingredient``,
``NutritionFacts``, ``Nutrition``): those describe raw AI output, these
describe the analysed, persisted, HTTP-facing result.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisStatus(str, Enum):
    """Outcome of a single analysis."""

    OK = "ok"  # every ingredient priced
    PARTIAL = "partial"  # meal recognised, some lookups missing/failed
    UNKNOWN_MEAL = "unknown_meal"  # the VLM did not recognise a meal


class IngredientStatus(str, Enum):
    OK = "ok"
    NOT_FOUND = "not_found"  # provider has no match for the name
    LOOKUP_FAILED = "lookup_failed"  # provider errored after retries


class MacroBreakdown(BaseModel):
    """Total energy plus macronutrient split for a meal."""

    model_config = ConfigDict(extra="forbid")

    kcal: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0

    @property
    def protein_pct(self) -> float:
        return self._pct(self.protein_g * 4.0)

    @property
    def carbs_pct(self) -> float:
        return self._pct(self.carbs_g * 4.0)

    @property
    def fat_pct(self) -> float:
        return self._pct(self.fat_g * 9.0)

    def _pct(self, energy_from_macro: float) -> float:
        atwater = self.protein_g * 4.0 + self.carbs_g * 4.0 + self.fat_g * 9.0
        if atwater <= 0:
            return 0.0
        return round(100.0 * energy_from_macro / atwater, 1)

    @classmethod
    def from_ai_nutrition(cls, nutrition: Any) -> "MacroBreakdown":
        """Build from an ``ai.schemas.Nutrition`` (or anything with the attrs)."""
        return cls(
            kcal=round(float(nutrition.kcal), 2),
            protein_g=round(float(nutrition.protein_g), 2),
            carbs_g=round(float(nutrition.carbs_g), 2),
            fat_g=round(float(nutrition.fat_g), 2),
        )


class AnalyzedIngredient(BaseModel):
    """One ingredient after identification + nutrition lookup."""

    model_config = ConfigDict(extra="forbid")

    name: str
    estimated_grams: float
    confidence: float
    status: IngredientStatus = IngredientStatus.OK
    matched_food: str | None = None
    source: str | None = None
    nutrition: MacroBreakdown | None = None
    error: str | None = None


class AnalysisResult(BaseModel):
    """The full, serialisable result of analysing one meal photo."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=_utcnow)
    status: AnalysisStatus
    image_filename: str
    ingredients: list[AnalyzedIngredient] = Field(default_factory=list)
    totals: MacroBreakdown = Field(default_factory=MacroBreakdown)
    warnings: list[str] = Field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        """JSON body for the HTTP API (macro percentages expanded)."""
        data = self.model_dump(mode="json")
        data["totals"] = {
            **data["totals"],
            "protein_pct": self.totals.protein_pct,
            "carbs_pct": self.totals.carbs_pct,
            "fat_pct": self.totals.fat_pct,
        }
        return data


class AnalysisRecord(BaseModel):
    """A row in the history log."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    image_path: str
    image_filename: str
    status: AnalysisStatus
    ingredients: list[AnalyzedIngredient]
    totals: MacroBreakdown
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def from_result(cls, result: AnalysisResult, *, image_path: str) -> "AnalysisRecord":
        return cls(
            id=result.id,
            created_at=result.created_at,
            image_path=image_path,
            image_filename=result.image_filename,
            status=result.status,
            ingredients=result.ingredients,
            totals=result.totals,
            warnings=result.warnings,
        )
