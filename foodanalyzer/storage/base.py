"""The storage contract every history backend implements."""

from __future__ import annotations

import abc

from foodanalyzer.models import AnalysisRecord


class HistoryRepository(abc.ABC):
    """Append-only log of past analyses: timestamp, image, ingredients, totals."""

    @abc.abstractmethod
    async def add(self, record: AnalysisRecord) -> None:
        """Persist one analysis record."""

    @abc.abstractmethod
    async def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        """Return the most recent records, newest first."""

    @abc.abstractmethod
    async def get(self, record_id: str) -> AnalysisRecord | None:
        """Return a single record by id, or ``None``."""

    @abc.abstractmethod
    async def count(self) -> int:
        """Total number of stored records."""

    async def close(self) -> None:  # pragma: no cover - default no-op
        """Release any held resources (connection pools etc.)."""
