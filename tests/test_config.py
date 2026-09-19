"""Settings parsing and derived properties"""

from __future__ import annotations

import pytest

from foodanalyzer.config import Settings


def test_defaults_are_sane():
    s = Settings(_env_file=None)
    assert s.llm_provider == "anthropic"
    assert s.nutrition_cache_ttl_seconds == 86_400
    assert s.max_concurrency == 10
    assert s.max_image_size_bytes == 5 * 1024 * 1024


def test_log_level_is_normalised():
    assert Settings(_env_file=None, log_level="debug").log_level == "DEBUG"


def test_invalid_log_level_rejected():
    with pytest.raises(ValueError):
        Settings(_env_file=None, log_level="chatty")


@pytest.mark.parametrize(
    "dsn,expected",
    [
        ("", False),
        ("myDatabaseUrl", False),
        ("sqlite:///x.db", False),
        ("postgresql://u:p@h:5432/db", True),
        ("postgres://u:p@h/db", True),
    ],
)
def test_has_real_database(dsn, expected):
    assert Settings(_env_file=None, database_url=dsn).has_real_database is expected


def test_normalised_database_url_strips_driver_suffix():
    s = Settings(_env_file=None, database_url="postgresql+asyncpg://u:p@h/db")
    assert s.normalised_database_url() == "postgresql://u:p@h/db"


def test_normalised_database_url_none_when_placeholder():
    assert Settings(_env_file=None, database_url="nope").normalised_database_url() is None
