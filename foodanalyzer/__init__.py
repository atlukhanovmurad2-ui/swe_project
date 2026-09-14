"""AI Food Analyzer — the software-engineering layer around the provided ``ai`` module.

Public entry points:

* :func:`foodanalyzer.core.analyzer.analyze_image` — the end-to-end pipeline.
* :mod:`foodanalyzer.api` — the FastAPI application (``POST /analyze``).
* :mod:`foodanalyzer.cli` — the ``python -m foodanalyzer`` command line.
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = ["__version__"]
