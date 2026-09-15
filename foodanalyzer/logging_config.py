"""Central logging setup — call :func:`configure_logging` once at startup."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Install a single stderr handler with a consistent format.

    Idempotent: calling it again only adjusts the level. ``level`` defaults to
    the ``LOG_LEVEL`` setting.
    """
    global _CONFIGURED

    if level is None:
        from foodanalyzer.config import get_settings

        level = get_settings().log_level

    root = logging.getLogger()
    if not _CONFIGURED:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root.addHandler(handler)
        _CONFIGURED = True

    root.setLevel(level)
    # Keep uvicorn's access log from double-printing through the root handler.
    logging.getLogger("uvicorn.access").propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a module logger, ensuring logging is configured first."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
