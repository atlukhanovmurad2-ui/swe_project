"""In-memory history repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from foodanalyzer.models import (
    AnalysisRecord,
    AnalysisStatus,
    MacroBreakdown,
)
from foodanalyzer.storage import get_repository
from foodanalyzer.storage.memory import InMemoryHistoryRepository

pytestmark = pytest.mark.asyncio


def _record(rid: str, when: datetime) -> AnalysisRecord:
    return AnalysisRecord(
        id=rid,
        created_at=when,
        image_path=f"/tmp/{rid}.png",
        image_filename=f"{rid}.png",
        status=AnalysisStatus.OK,
        ingredients=[],
        totals=MacroBreakdown(kcal=500),
        warnings=[],
    )


async def test_add_and_get():
    repo = InMemoryHistoryRepository()
    now = datetime.now(timezone.utc)
    await repo.add(_record("a", now))
    assert (await repo.get("a")).image_filename == "a.png"
    assert await repo.get("missing") is None
    assert await repo.count() == 1


async def test_list_recent_is_newest_first():
    repo = InMemoryHistoryRepository()
    now = datetime.now(timezone.utc)
    await repo.add(_record("old", now - timedelta(hours=2)))
    await repo.add(_record("new", now))
    await repo.add(_record("mid", now - timedelta(hours=1)))
    ids = [r.id for r in await repo.list_recent(limit=2)]
    assert ids == ["new", "mid"]


async def test_stored_record_is_a_copy():
    repo = InMemoryHistoryRepository()
    rec = _record("a", datetime.now(timezone.utc))
    await repo.add(rec)
    rec.warnings.append("mutated after store")
    assert (await repo.get("a")).warnings == []


async def test_get_repository_falls_back_to_memory_without_dsn():
    repo = await get_repository()
    assert isinstance(repo, InMemoryHistoryRepository)
