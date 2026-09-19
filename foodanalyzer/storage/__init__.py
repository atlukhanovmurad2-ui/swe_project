"""History-log storage backends."""

from foodanalyzer.storage.base import HistoryRepository
from foodanalyzer.storage.memory import InMemoryHistoryRepository

__all__ = ["HistoryRepository", "InMemoryHistoryRepository", "get_repository"]


async def get_repository() -> HistoryRepository:
    """Return the configured repository """
    from foodanalyzer.config import get_settings
    from foodanalyzer.logging_config import get_logger

    log = get_logger(__name__)
    settings = get_settings()
    dsn = settings.normalised_database_url()

    if dsn is None:
        log.warning(
            "DATABASE_URL is not a usable PostgreSQL DSN — using an in-memory "
            "history log (records will not survive a restart)."
        )
        return InMemoryHistoryRepository()

    from foodanalyzer.storage.postgres import PostgresHistoryRepository

    repo = PostgresHistoryRepository(dsn)
    await repo.connect()
    return repo
