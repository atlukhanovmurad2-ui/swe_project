"""HTTP API (FastAPI TestClient, offline nutrition provider injected)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from foodanalyzer import api as api_module

from foodanalyzer.offline import OfflineNutrition, OfflineVLM


@pytest.fixture
def client(monkeypatch):
    # Force the offline VLM so no API keys / network are needed.
    import foodanalyzer.core.analyzer as analyzer

    real_analyze = analyzer.analyze_image

    async def offline_analyze(image_path, **kw):
        kw.setdefault("vlm", OfflineVLM())
        return await real_analyze(image_path, **kw)

    monkeypatch.setattr(api_module, "analyze_image", offline_analyze)
    with TestClient(api_module.app) as c:
        c.app.state.nutrition_provider = OfflineNutrition()
        yield c


def _png(name="rice_chicken_broccoli.png"):
    data = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000"
        "00907753de0000000c4944415408d76360000000000004000146a13a"
        "020000000049454e44ae426082"
    )
    return (name, data, "image/png")


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_happy_path(client):
    name, data, ct = _png()
    r = client.post("/analyze", files={"image": (name, data, ct)})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["totals"]["kcal"] > 0
    assert "protein_pct" in body["totals"]
    assert len(body["ingredients"]) == 3


def test_analyze_rejects_non_image(client):
    r = client.post("/analyze", files={"image": ("bad.png", b"not a real image", "image/png")})
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_media_type"


def test_analyze_rejects_oversize(client, monkeypatch):
    client.app.state.settings.max_image_size_mb = 0.00001
    name, data, ct = _png()
    r = client.post("/analyze", files={"image": (name, data, ct)})
    assert r.status_code == 413


def test_analyze_missing_field(client):
    r = client.post("/analyze")
    assert r.status_code == 422


def test_history_roundtrip(client):
    name, data, ct = _png()
    client.post("/analyze", files={"image": (name, data, ct)})
    r = client.get("/history")
    assert r.status_code == 200
    assert r.json()["count"] >= 1
    rec_id = r.json()["items"][0]["id"]
    assert client.get(f"/history/{rec_id}").status_code == 200
    assert client.get("/history/nonexistent").status_code == 404


def test_unknown_meal_returns_200(client):
    name, data, ct = _png("no_meal_blue.png")
    r = client.post("/analyze", files={"image": (name, data, ct)})
    assert r.status_code == 200
    assert r.json()["status"] == "unknown_meal"
