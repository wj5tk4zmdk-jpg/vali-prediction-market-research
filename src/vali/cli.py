"""Command line interface for repeatable VALI research runs."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

from .config import ValiConfig
from .pipeline import rebuild_report, run_backtest_pipeline, run_signal_pipeline, validate_inputs
from .sample import make_synthetic_dataset
from .providers.kalshi import (
    ArchiveStore,
    KalshiAdapter,
    KalshiClient,
    PRODUCTION_BASE_URL,
    load_upper_bounds,
)
from .providers.google_trends import (
    FixtureTrendsGateway,
    RetryingTrendsGateway,
    TrendsAdapter,
    TrendsError,
    UnavailableOfficialTrendsGateway,
    load_query_manifest,
    trends_status,
    write_request_plan,
)


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vali", description="Offline VALI research pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "signal", "backtest"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--config", required=True, type=Path)
        if command != "validate":
            subparser.add_argument("--out", required=True, type=Path)
    report = subparsers.add_parser("report")
    report.add_argument("--run-dir", required=True, type=Path)
    sample = subparsers.add_parser("sample-data")
    sample.add_argument("--out", required=True, type=Path)
    sample.add_argument("--seed", type=int, default=20260623)
    sample.add_argument("--events", type=int, default=24)
    kalshi = subparsers.add_parser("kalshi", help="Read-only Kalshi market-data ingestion")
    kalshi_commands = kalshi.add_subparsers(dest="kalshi_command", required=True)
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
    backfill.add_argument("--candle-interval", type=int, choices=(1, 60, 1440), default=60)
    snapshot = kalshi_commands.choices["snapshot"]
    snapshot.add_argument("--depth-band", type=Decimal, default=Decimal("0.05"))
    trends = subparsers.add_parser("trends", help="Official Google Trends API alpha readiness")
    trends_commands = trends.add_subparsers(dest="trends_command", required=True)
    for command in ("plan", "backfill", "collect", "status"):
        subparser = trends_commands.add_parser(command)
        subparser.add_argument("--out", required=True, type=Path)
        subparser.add_argument("--manifest", type=Path)
    plan = trends_commands.choices["plan"]
    plan.add_argument("--as-of", type=_iso_date, default=date.today())
    plan.add_argument("--days", type=int, default=1800)
    backfill = trends_commands.choices["backfill"]
    backfill.add_argument("--as-of", type=_iso_date, default=date.today())
    backfill.add_argument("--days", type=int, default=1800)
    backfill.add_argument("--fixture", type=Path)
    backfill.add_argument("--max-retries", type=int, default=5)
    collect = trends_commands.choices["collect"]
    collect.add_argument("--as-of", type=_iso_date, default=date.today())
    collect.add_argument("--lookback-days", type=int, default=7)
    collect.add_argument("--fixture", type=Path)
    collect.add_argument("--max-retries", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "sample-data":
        config = make_synthetic_dataset(args.out, seed=args.seed, event_count=args.events)
        print(json.dumps({"config": str(config), "synthetic": True}, indent=2))
        return
    if args.command == "report":
        report = rebuild_report(args.run_dir)
        print(json.dumps({"report": str(report)}, indent=2))
        return
    if args.command == "kalshi":
        archive = ArchiveStore(args.out)
        client = KalshiClient(
            args.base_url,
            max_retries=args.max_retries,
            archive=archive,
        )
        adapter = KalshiAdapter(client, args.out, series_ticker=args.series)
        if args.kalshi_command == "discover":
            result = adapter.discover()
        elif args.kalshi_command == "backfill":
            result = adapter.backfill(
                min_events=args.min_events,
                upper_bounds=load_upper_bounds(args.upper_bounds),
                include_trades=not args.no_trades,
                candle_interval_minutes=args.candle_interval,
            )
        else:
            result = adapter.snapshot(depth_band=args.depth_band)
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "counts": result.counts,
                    "mapped_events": result.mapped_events,
                    "walk_forward_ready": result.walk_forward_ready,
                    "read_only": True,
                },
                indent=2,
            )
        )
        return
    if args.command == "trends":
        try:
            specs = load_query_manifest(args.manifest)
            if args.trends_command == "plan":
                path = write_request_plan(
                    args.out, specs, as_of=args.as_of, days=args.days
                )
                print(json.dumps({"request_plan": str(path), "live_access_used": False}, indent=2))
                return
            if args.trends_command == "status":
                print(json.dumps(trends_status(args.out, specs), indent=2, sort_keys=True))
                return
            gateway = (
                FixtureTrendsGateway(args.fixture)
                if args.fixture
                else UnavailableOfficialTrendsGateway()
            )
            adapter = TrendsAdapter(
                RetryingTrendsGateway(gateway, max_retries=args.max_retries),
                args.out,
                live_access_used=False,
            )
            if args.trends_command == "backfill":
                result = adapter.backfill(specs, as_of=args.as_of, days=args.days)
            else:
                result = adapter.collect(
                    specs, as_of=args.as_of, lookback_days=args.lookback_days
                )
            print(
                json.dumps(
                    {
                        "output_dir": str(result.output_dir),
                        "counts": result.counts,
                        "latest_usable_date": result.latest_usable_date,
                        "query_manifest_sha256": result.query_manifest_sha256,
                        "live_access_used": result.live_access_used,
                    },
                    indent=2,
                )
            )
        except TrendsError as exc:
            raise SystemExit(f"Google Trends: {exc}") from exc
        return

    config = ValiConfig.from_toml(args.config)
    if args.command == "validate":
        bundle = validate_inputs(config)
        print(json.dumps(bundle.validation.as_dict(), indent=2))
    elif args.command == "signal":
        result = run_signal_pipeline(config, args.out)
        print(json.dumps({"output_dir": str(result.output_dir), "signal_rows": len(result.signals)}, indent=2))
    elif args.command == "backtest":
        result = run_backtest_pipeline(config, args.out)
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "signal_rows": len(result.signals),
                    "forecast_rows": len(result.forecasts),
                    "trade_rows": len(result.trades),
                },
                indent=2,
            )
        )
