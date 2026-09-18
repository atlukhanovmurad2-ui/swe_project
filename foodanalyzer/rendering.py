"""Plain-text table rendering for the CLI."""

from __future__ import annotations

from foodanalyzer.models import AnalysisResult, IngredientStatus


def render_totals_table(result: AnalysisResult) -> str:
    headers = ("ingredient", "g", "kcal", "protein", "carbs", "fat")
    rows: list[tuple[str, ...]] = []

    for ing in result.ingredients:
        if ing.nutrition is not None:
            n = ing.nutrition
            rows.append((
                ing.name,
                f"{ing.estimated_grams:.0f}",
                f"{n.kcal:.0f}",
                f"{n.protein_g:.1f}",
                f"{n.carbs_g:.1f}",
                f"{n.fat_g:.1f}",
            ))
        else:
            label = "not found" if ing.status == IngredientStatus.NOT_FOUND else "lookup failed"
            rows.append((ing.name, f"{ing.estimated_grams:.0f}", f"({label})", "-", "-", "-"))

    t = result.totals
    total_row = (
        "TOTAL",
        f"{sum(i.estimated_grams for i in result.ingredients):.0f}",
        f"{t.kcal:.0f}",
        f"{t.protein_g:.1f}",
        f"{t.carbs_g:.1f}",
        f"{t.fat_g:.1f}",
    )

    all_rows = [headers, *rows, total_row]
    widths = [max(len(r[i]) for r in all_rows) for i in range(len(headers))]

    def fmt(row: tuple[str, ...]) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(row))

    sep = "-" * (sum(widths) + 2 * (len(widths) - 1))
    lines = [fmt(headers), sep, *(fmt(r) for r in rows), sep, fmt(total_row)]

    if result.status.value != "ok":
        lines.append("")
        lines.append(f"status: {result.status.value}")
    for w in result.warnings:
        lines.append(f"! {w}")
    if t.kcal > 0:
        lines.append("")
        lines.append(
            f"macro split (energy): protein {t.protein_pct:.0f}%  "
            f"carbs {t.carbs_pct:.0f}%  fat {t.fat_pct:.0f}%"
        )
    return "\n".join(lines)
