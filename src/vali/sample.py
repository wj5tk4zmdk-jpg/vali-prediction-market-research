"""Deterministic synthetic data for tests and the explanatory notebook."""

from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


def _sigmoid(value):
    return 1.0 / (1.0 + np.exp(-value))


def make_synthetic_dataset(
    output_dir: str | Path, seed: int = 20260623, event_count: int = 24
) -> Path:
    """Create a schema-valid, non-empirical VALI demonstration dataset."""
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    tz = ZoneInfo("America/New_York")
    first_meeting = pd.Timestamp("2021-01-27 14:00", tz=tz)
    meetings = [first_meeting + pd.Timedelta(days=45 * index) for index in range(event_count)]
    start = (meetings[0] - pd.Timedelta(days=170)).normalize()
    end = (meetings[-1] + pd.Timedelta(days=2)).normalize()
    days = pd.date_range(start, end, freq="D", tz=tz)

    latent = np.zeros(len(days))
    innovations = rng.normal(0, 0.35, len(days))
    for index in range(1, len(days)):
        latent[index] = 0.94 * latent[index - 1] + innovations[index]
    for pulse in range(90, len(days), 137):
        latent[pulse : pulse + 8] += np.linspace(0, 2.8, min(8, len(days) - pulse))

    feature_specs = [
        ("labor_cooling", latent + rng.normal(0, 0.12, len(days)), 1),
        ("inflation_cooling", 0.8 * latent + rng.normal(0, 0.16, len(days)), 1),
        ("financial_tightness", -0.7 * latent + rng.normal(0, 0.18, len(days)), -1),
    ]
    feature_rows: list[dict] = []
    manifest_rows: list[dict] = []
    for feature_id, values, polarity in feature_specs:
        for day, value in zip(days, values, strict=True):
            observation = day.replace(hour=8).tz_convert("UTC")
            available = day.replace(hour=9).tz_convert("UTC")
            feature_rows.append(
                {
                    "feature_id": feature_id,
                    "observation_at": observation.isoformat(),
                    "available_at": available.isoformat(),
                    "vintage": "initial",
                    "source": "synthetic_fixture",
                    "value": float(value),
                }
            )
        manifest_rows.append(
            {
                "feature_id": feature_id,
                "rationale": "Synthetic point-in-time proxy used only to exercise the research pipeline",
                "transformation": "level",
                "polarity": polarity,
                "availability_lag_days": 0,
                "missing_policy": "asof",
                "max_age_days": 2,
                "required": True,
                "source": "synthetic_fixture",
            }
        )

    latent_by_day = pd.Series(latent, index=days.normalize())
    event_rows: list[dict] = []
    quote_rows: list[dict] = []
    for index, meeting in enumerate(meetings):
        event_id = f"fomc-{index + 1:03d}"
        contract_id = f"ease-{index + 1:03d}"
        open_at = (meeting - pd.Timedelta(days=135)).replace(hour=9)
        settlement = meeting.replace(hour=18)
        meeting_latent = float(latent_by_day.loc[meeting.normalize()])
        event_probability = float(_sigmoid(-0.15 + 0.8 * meeting_latent))
        outcome = int(rng.random() < event_probability)
        event_rows.append(
            {
                "event_id": event_id,
                "contract_id": contract_id,
                "open_at": open_at.tz_convert("UTC").isoformat(),
                "meeting_at": meeting.tz_convert("UTC").isoformat(),
                "settlement_at": settlement.tz_convert("UTC").isoformat(),
                "yes_label": "Fed target range lower after scheduled meeting",
                "outcome": outcome,
            }
        )
        contract_days = pd.date_range(open_at.normalize(), meeting.normalize(), freq="D", tz=tz)
        for contract_day in contract_days:
            day_position = days.get_indexer([contract_day.normalize()])[0]
            leading_position = max(0, day_position - 3)
            price_center = float(
                np.clip(
                    _sigmoid(-0.15 + 0.70 * latent[leading_position] + rng.normal(0, 0.08)),
                    0.03,
                    0.97,
                )
            )
            spread = 0.04
            bid = max(0.001, price_center - spread / 2)
            ask = min(0.999, price_center + spread / 2)
            quote_rows.append(
                {
                    "contract_id": contract_id,
                    "observed_at": contract_day.replace(hour=15, minute=55).tz_convert("UTC").isoformat(),
                    "bid": bid,
                    "ask": ask,
                    "last": price_center,
                    "volume": 2500 + index * 10,
                    "bid_depth": 500,
                    "ask_depth": 500,
                }
            )

    pd.DataFrame(event_rows).to_csv(root / "events.csv", index=False)
    pd.DataFrame(quote_rows).to_csv(root / "quotes.csv", index=False)
    pd.DataFrame(feature_rows).to_csv(root / "features.csv", index=False)
    pd.DataFrame(manifest_rows).to_csv(root / "feature_manifest.csv", index=False)
    config = f'''[run]
parameter_freeze_date = "2026-06-23"
methodology_version = "1.0.1"

[data]
events = "events.csv"
quotes = "quotes.csv"
features = "features.csv"
feature_manifest = "feature_manifest.csv"

[market]
max_spread = 0.10
min_depth = 100.0
max_quote_age_minutes = 30
fallback_trade_window_minutes = 120
fee_bps = 5.0
probability_epsilon = 0.0001

[features]
timezone = "America/New_York"
daily_cutoff = "16:00"
standardization_window = 90
min_periods = 30

[signal]
velocity_window = 7
normalization_window = 90
min_periods = 30
entry_threshold = 2.0
exit_threshold = 0.5
sensitivity_windows = [3, 14, 30]

[regime]
window = 90
min_periods = 30
max_lag = 7
min_abs_correlation = 0.20
tie_margin = 0.05

[backtest]
min_train_events = 16
notional = 100.0
stop_loss_fraction = 0.25
max_holding_days = 14
days_before_settlement = 1
calibration_l2 = 1.0
'''
    (root / "config.toml").write_text(config, encoding="utf-8")
    return root / "config.toml"

