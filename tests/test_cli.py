"""CLI: python -m foodanalyzer ..."""

from __future__ import annotations

import json

from foodanalyzer.cli import main


def test_analyze_offline_table(meal_png, capsys):
    rc = main(["analyze", str(meal_png), "--offline", "--no-store"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "TOTAL" in out
    assert "grilled chicken breast" in out
    assert "macro split" in out


def test_analyze_offline_json(meal_png, capsys):
    rc = main(["analyze", str(meal_png), "--offline", "--no-store", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["totals"]["kcal"] > 0


def test_analyze_missing_file(capsys):
    rc = main(["analyze", "does_not_exist.png", "--offline"])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_analyze_unknown_meal(tmp_path, png_bytes, capsys):
    p = tmp_path / "no_meal_blue.png"
    p.write_bytes(png_bytes)
    rc = main(["analyze", str(p), "--offline", "--no-store"])
    assert rc == 0
    assert "unknown_meal" in capsys.readouterr().out


def test_history_empty(capsys):
    rc = main(["history"])
    assert rc == 0
    assert "no analyses" in capsys.readouterr().out
