"""CLI parser construction and application command dispatch."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path

from ..providers.kalshi import PRODUCTION_BASE_URL
from .collection import run_kalshi_command, run_trends_command
from .knowledge_graph import run_kg_command
from .reporting import run_report_command
from .research import run_research_command, run_sample_data_command
from .validation import run_validation_command


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vali", description="Offline VALI research pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "signal"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--config", required=True, type=Path)
        if command == "signal":
            subparser.add_argument("--out", required=True, type=Path)
    backtest = subparsers.add_parser("backtest")
    backtest.add_argument("--config", type=Path)
    backtest.add_argument("--manifest", type=Path)
    backtest.add_argument("--out", required=True, type=Path)
    confirmation = subparsers.add_parser(
        "confirmation-panel",
        help="Paired regime-confirmation execution sensitivity report",
    )
    confirmation.add_argument("--config", required=True, type=Path)
    confirmation.add_argument("--out", required=True, type=Path)
    confirmation.add_argument("--grid", default=None)
    report = subparsers.add_parser("report")
    report.add_argument("--run-dir", required=True, type=Path)
    sample = subparsers.add_parser("sample-data")
    sample.add_argument("--out", required=True, type=Path)
    sample.add_argument("--seed", type=int, default=20260623)
    sample.add_argument("--events", type=int, default=24)
    kg = subparsers.add_parser(
        "kg", help="Knowledge-graph handoff scaffolding"
    )
    kg_commands = kg.add_subparsers(dest="kg_command", required=True)
    kg_preflight = kg_commands.add_parser(
        "preflight", help="Write an availability-only KG preflight report"
    )
    kg_preflight.add_argument("--graph", required=True, type=Path)
    kg_preflight.add_argument("--out", required=True, type=Path)
    kg_compile = kg_commands.add_parser(
        "compile", help="Write a flat compiled VALI manifest from a KG fixture"
    )
    kg_compile.add_argument("--graph", required=True, type=Path)
    kg_compile.add_argument("--preflight", required=True, type=Path)
    kg_compile.add_argument("--out", required=True, type=Path)
    kg_evidence_summary = kg_commands.add_parser(
        "evidence-summary",
        help="Write a human-readable append-only KG validation evidence summary",
    )
    kg_evidence_summary.add_argument("--graph", required=True, type=Path)
    kg_evidence_summary.add_argument("--out", required=True, type=Path)
    kg_review = kg_commands.add_parser(
        "review-packet",
        help="Write a human-reviewed KG evidence recommendation packet",
    )
    kg_review.add_argument("--graph", required=True, type=Path)
    kg_review.add_argument("--out", required=True, type=Path)
    kg_review.add_argument("--recommendations", type=Path)
    kg_review.add_argument("--reviewer")
    kg_supersede = kg_commands.add_parser(
        "supersede",
        help="Create a draft superseding graph copy from explicit human review",
    )
    kg_supersede.add_argument("--graph", required=True, type=Path)
    kg_supersede.add_argument("--review", required=True, type=Path)
    kg_supersede.add_argument("--out-dir", required=True, type=Path)
    kg_supersede.add_argument("--graph-id")
    kg_supersede.add_argument("--version", default="v2")
    kalshi = subparsers.add_parser(
        "kalshi", help="Read-only Kalshi market-data ingestion"
    )
    kalshi_commands = kalshi.add_subparsers(
        dest="kalshi_command", required=True
    )
    for command in ("discover", "backfill", "snapshot"):
        subparser = kalshi_commands.add_parser(command)
        subparser.add_argument("--out", required=True, type=Path)
        subparser.add_argument("--series", default="KXFED")
        subparser.add_argument("--base-url", default=PRODUCTION_BASE_URL)
        subparser.add_argument("--max-retries", type=int, default=5)
    backfill = kalshi_commands.choices["backfill"]
    backfill.add_argument("--min-events", type=int, default=16)
    backfill.add_argument("--upper-bounds", type=Path)
    backfill.add_argument("--no-trades", action="store_true")
    backfill.add_argument(
        "--candle-interval", type=int, choices=(1, 60, 1440), default=60
    )
    snapshot = kalshi_commands.choices["snapshot"]
    snapshot.add_argument(
        "--depth-band", type=Decimal, default=Decimal("0.05")
    )
    trends = subparsers.add_parser(
        "trends", help="Official Google Trends API alpha readiness"
    )
    trends_commands = trends.add_subparsers(
        dest="trends_command", required=True
    )
    for command in ("plan", "backfill", "collect", "status"):
        subparser = trends_commands.add_parser(command)
        subparser.add_argument("--out", required=True, type=Path)
        subparser.add_argument("--manifest", type=Path)
    plan = trends_commands.choices["plan"]
    plan.add_argument("--as-of", type=iso_date, default=date.today())
    plan.add_argument("--days", type=int, default=1800)
    trends_backfill = trends_commands.choices["backfill"]
    trends_backfill.add_argument(
        "--as-of", type=iso_date, default=date.today()
    )
    trends_backfill.add_argument("--days", type=int, default=1800)
    trends_backfill.add_argument("--fixture", type=Path)
    trends_backfill.add_argument("--max-retries", type=int, default=5)
    collect = trends_commands.choices["collect"]
    collect.add_argument("--as-of", type=iso_date, default=date.today())
    collect.add_argument("--lookback-days", type=int, default=7)
    collect.add_argument("--fixture", type=Path)
    collect.add_argument("--max-retries", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "sample-data":
        run_sample_data_command(args)
        return
    if args.command == "report":
        run_report_command(args)
        return
    if args.command == "kalshi":
        run_kalshi_command(args)
        return
    if args.command == "kg":
        run_kg_command(args)
        return
    if args.command == "trends":
        run_trends_command(args)
        return
    if args.command == "validate":
        run_validation_command(args)
        return
    run_research_command(args)


__all__ = ["build_parser", "iso_date", "main"]
