"""Application orchestration for read-only public data collection."""

from __future__ import annotations

import json
from typing import Any

from ..providers.google_trends import (
    FixtureTrendsGateway,
    RetryingTrendsGateway,
    TrendsAdapter,
    TrendsError,
    UnavailableOfficialTrendsGateway,
    load_query_manifest,
    trends_status,
    write_request_plan,
)
from ..providers.kalshi import (
    ArchiveStore,
    KalshiAdapter,
    KalshiClient,
    load_upper_bounds,
)


def run_kalshi_command(args: Any) -> None:
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


def run_trends_command(args: Any) -> None:
    try:
        specs = load_query_manifest(args.manifest)
        if args.trends_command == "plan":
            path = write_request_plan(
                args.out, specs, as_of=args.as_of, days=args.days
            )
            print(
                json.dumps(
                    {
                        "request_plan": str(path),
                        "live_access_used": False,
                    },
                    indent=2,
                )
            )
            return
        if args.trends_command == "status":
            print(
                json.dumps(
                    trends_status(args.out, specs),
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        gateway = (
            FixtureTrendsGateway(args.fixture)
            if args.fixture
            else UnavailableOfficialTrendsGateway()
        )
        adapter = TrendsAdapter(
            RetryingTrendsGateway(
                gateway, max_retries=args.max_retries
            ),
            args.out,
            live_access_used=False,
        )
        if args.trends_command == "backfill":
            result = adapter.backfill(
                specs, as_of=args.as_of, days=args.days
            )
        else:
            result = adapter.collect(
                specs,
                as_of=args.as_of,
                lookback_days=args.lookback_days,
            )
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "counts": result.counts,
                    "latest_usable_date": result.latest_usable_date,
                    "query_manifest_sha256": (
                        result.query_manifest_sha256
                    ),
                    "live_access_used": result.live_access_used,
                },
                indent=2,
            )
        )
    except TrendsError as exc:
        raise SystemExit(f"Google Trends: {exc}") from exc


__all__ = ["run_kalshi_command", "run_trends_command"]
