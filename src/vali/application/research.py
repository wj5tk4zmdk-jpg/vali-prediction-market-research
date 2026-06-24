"""Application orchestration for sample data and research runs."""

from __future__ import annotations

import json
from typing import Any

from ..config import ValiConfig
from ..pipeline import run_backtest_pipeline, run_signal_pipeline
from ..sample import make_synthetic_dataset


def run_sample_data_command(args: Any) -> None:
    config = make_synthetic_dataset(
        args.out, seed=args.seed, event_count=args.events
    )
    print(json.dumps({"config": str(config), "synthetic": True}, indent=2))


def run_research_command(args: Any) -> None:
    config = ValiConfig.from_toml(args.config)
    if args.command == "signal":
        result = run_signal_pipeline(config, args.out)
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "signal_rows": len(result.signals),
                },
                indent=2,
            )
        )
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


__all__ = ["run_research_command", "run_sample_data_command"]
