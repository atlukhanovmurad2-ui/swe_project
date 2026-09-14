"""Command-line interface: ``python -m foodanalyzer analyze <path>``."""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import argparse
import asyncio
import json
import sys
from pathlib import Path

from foodanalyzer import __version__
from foodanalyzer.config import get_settings
from foodanalyzer.core.analyzer import analyze_image
from foodanalyzer.errors import FoodAnalyzerError
from foodanalyzer.logging_config import configure_logging, get_logger
from foodanalyzer.offline import OfflineNutrition, OfflineVLM
from foodanalyzer.rendering import render_totals_table
from foodanalyzer.storage import get_repository

_log = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m foodanalyzer",
        description="Analyse a meal photo: ingredients, portions, calories and macros.",
    )
    parser.add_argument("--version", action="version", version=f"foodanalyzer {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyse one meal image.")
    analyze.add_argument("image", type=str, help="Path to a JPEG or PNG meal photo.")
    analyze.add_argument(
        "--offline", action="store_true",
        help="Use bundled fake providers (no API keys, no network).",
    )
    analyze.add_argument(
        "--json", action="store_true", help="Emit the raw JSON result instead of a table.",
    )
    analyze.add_argument(
        "--no-store", action="store_true", help="Do not write to the history log.",
    )

    history = sub.add_parser("history", help="Show recent analyses from the history log.")
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--json", action="store_true")

    return parser


async def _cmd_analyze(args: argparse.Namespace) -> int:
    image = Path(args.image)
    if not image.is_file():
        print(f"error: image not found: {image}", file=sys.stderr)
        return 2

    vlm = OfflineVLM() if args.offline else None
    nutrition = OfflineNutrition() if args.offline else None
    repo = None if args.no_store else await get_repository()

    try:
        result = await analyze_image(
            image,
            vlm=vlm,
            nutrition_provider=nutrition,
            repository=repo,
        )
    except FoodAnalyzerError as exc:
        print(f"error: {exc.code}: {exc}", file=sys.stderr)
        return 1
    finally:
        if repo is not None:
            await repo.close()

    if args.json:
        print(json.dumps(result.to_public_dict(), indent=2))
    else:
        print(f"Analyzing: {result.image_filename}\n")
        print(render_totals_table(result))
    return 0


async def _cmd_history(args: argparse.Namespace) -> int:
    repo = await get_repository()
    try:
        records = await repo.list_recent(limit=args.limit)
    finally:
        await repo.close()

    if args.json:
        print(json.dumps([r.model_dump(mode="json") for r in records], indent=2))
        return 0

    if not records:
        print("(no analyses recorded yet)")
        return 0
    for r in records:
        ts = r.created_at.strftime("%Y-%m-%d %H:%M")
        print(f"{ts}  {r.status.value:<12}  {r.totals.kcal:6.0f} kcal  {r.image_filename}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(get_settings().log_level)

    if args.command == "analyze":
        return asyncio.run(_cmd_analyze(args))
    if args.command == "history":
        return asyncio.run(_cmd_history(args))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
