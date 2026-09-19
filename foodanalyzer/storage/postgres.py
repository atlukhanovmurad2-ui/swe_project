"""PostgreSQL history log by asyncpg.

Schema:

    CREATE TABLE analysis_history (
        id           TEXT PRIMARY KEY,
        created_at   TIMESTAMPTZ NOT NULL,
        image_path   TEXT NOT NULL,
        image_filename TEXT NOT NULL,
        status       TEXT NOT NULL,
        ingredients  JSONB NOT NULL,
        totals       JSONB NOT NULL,
        warnings     JSONB NOT NULL DEFAULT '[]'
    );
"""

from __future__ import annotations

import json

from foodanalyzer.errors import StorageError
from foodanalyzer.logging_config import get_logger
from foodanalyzer.models import AnalysisRecord
from foodanalyzer.storage.base import HistoryRepository

_log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id             TEXT PRIMARY KEY,
    created_at     TIMESTAMPTZ NOT NULL,
    image_path     TEXT NOT NULL,
    image_filename TEXT NOT NULL,
    status         TEXT NOT NULL,
    ingredients    JSONB NOT NULL,
    totals         JSONB NOT NULL,
    warnings       JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS analysis_history_created_at_idx
    ON analysis_history (created_at DESC);
"""


class PostgresHistoryRepository(HistoryRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool = None  # asyncpg.Pool

    async def connect(self) -> None:
        try:
            import asyncpg
        except ImportError as exc:  # pragma: no cover
            raise StorageError("asyncpg is required for PostgreSQL storage") from exc

        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
            async with self._pool.acquire() as conn:
                await conn.execute(_SCHEMA)
        except Exception as exc:  # pragma: no cover - needs a real DB
            raise StorageError(f"could not connect to PostgreSQL: {exc}") from exc
        _log.info("connected to PostgreSQL history log")

    def _require_pool(self):
        if self._pool is None:
            raise StorageError("repository is not connected")
        return self._pool

    async def add(self, record: AnalysisRecord) -> None:
        pool = self._require_pool()
        ingredients = json.dumps([i.model_dump(mode="json") for i in record.ingredients])
        totals = json.dumps(record.totals.model_dump(mode="json"))
        warnings = json.dumps(record.warnings)
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analysis_history
                        (id, created_at, image_path, image_filename, status,
                         ingredients, totals, warnings)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    record.id, record.created_at, record.image_path,
                    record.image_filename, record.status.value,
                    ingredients, totals, warnings,
                )
        except Exception as exc:  # pragma: no cover - needs a real DB
            raise StorageError(f"could not write history record: {exc}") from exc

    async def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        pool = self._require_pool()
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM analysis_history ORDER BY created_at DESC LIMIT $1",
                    max(0, limit),
                )
        except Exception as exc:  # pragma: no cover
            raise StorageError(f"could not read history: {exc}") from exc
        return [_row_to_record(r) for r in rows]

    async def get(self, record_id: str) -> AnalysisRecord | None:
        pool = self._require_pool()
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM analysis_history WHERE id = $1", record_id
                )
        except Exception as exc:  # pragma: no cover
            raise StorageError(f"could not read history record: {exc}") from exc
        return _row_to_record(row) if row is not None else None

    async def count(self) -> int:
        pool = self._require_pool()
        try:
            async with pool.acquire() as conn:
                return int(await conn.fetchval("SELECT COUNT(*) FROM analysis_history"))
        except Exception as exc:  # pragma: no cover
            raise StorageError(f"could not count history: {exc}") from exc

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


def _row_to_record(row) -> AnalysisRecord:
    def _load(value):
        return value if isinstance(value, (list, dict)) else json.loads(value)

    return AnalysisRecord.model_validate(
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "image_path": row["image_path"],
            "image_filename": row["image_filename"],
            "status": row["status"],
            "ingredients": _load(row["ingredients"]),
            "totals": _load(row["totals"]),
            "warnings": _load(row["warnings"]),
        }
    )
