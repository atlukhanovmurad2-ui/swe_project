"""In-memory history log — the default when no PostgreSQL DSN is configured.
used dutinh tests, offline demo and when container db is not set
"""

from __future__ import annotations

import asyncio

from foodanalyzer.models import AnalysisRecord
from foodanalyzer.storage.base import HistoryRepository


class InMemoryHistoryRepository(HistoryRepository):
    def __init__(self) -> None:
        self._records: list[AnalysisRecord] = []
        self._lock = asyncio.Lock()

    async def add(self, record: AnalysisRecord) -> None:
        async with self._lock:
            self._records.append(record.model_copy(deep=True))

    async def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        async with self._lock:
            ordered = sorted(self._records, key=lambda r: r.created_at, reverse=True)
            return [r.model_copy(deep=True) for r in ordered[: max(0, limit)]]

    async def get(self, record_id: str) -> AnalysisRecord | None:
        async with self._lock:
            for r in self._records:
                if r.id == record_id:
                    return r.model_copy(deep=True)
            return None

    async def count(self) -> int:
        async with self._lock:
            return len(self._records)
