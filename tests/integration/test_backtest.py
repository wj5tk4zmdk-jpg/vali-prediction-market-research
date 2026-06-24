import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vali.backtest import run_walk_forward, simulate_trades
from vali.config import (
    BacktestConfig,
    DataConfig,
    FeatureConfig,
    MarketConfig,
    RegimeConfig,
    SignalConfig,
    ValiConfig,
)


def config():
    return ValiConfig(
        data=DataConfig(Path("events"), Path("quotes"), Path("features"), Path("manifest")),
        market=MarketConfig(0.1, 50, 30, 120, 10),
        features=FeatureConfig(standardization_window=3, min_periods=2),
        signal=SignalConfig(velocity_window=3, normalization_window=3, min_periods=2, entry_threshold=2, exit_threshold=0.5),
        regime=RegimeConfig(window=5, min_periods=3, max_lag=1),
        backtest=BacktestConfig(min_train_events=2, notional=100, stop_loss_fraction=0.25, max_holding_days=14, days_before_settlement=1),
        parameter_freeze_date="2026-06-23",
    )


def event_frames(count=4):
    events = []
    signals = []
    base = pd.Timestamp("2025-01-01", tz="UTC")
    for index in range(count):
        meeting = base + pd.Timedelta(days=30 * index + 20)
        contract = f"c{index}"
        outcome = index % 2
        events.append({"event_id": f"e{index}", "contract_id": contract, "open_at": meeting - pd.Timedelta(days=10), "meeting_at": meeting, "settlement_at": meeting + pd.Timedelta(hours=4), "yes_label": "lower", "outcome": outcome})
        signals.append({"event_id": f"e{index}", "contract_id": contract, "cutoff_at": meeting - pd.Timedelta(days=2), "meeting_at": meeting, "settlement_at": meeting + pd.Timedelta(hours=4), "outcome": outcome, "price": 0.35 + 0.1 * outcome, "logit_price": np.log((0.35 + 0.1 * outcome) / (0.65 - 0.1 * outcome)), "signed_divergence": -2.5 if not outcome else 2.5, "divergence_magnitude": 2.5, "regime": "attention_leading", "action": "long_yes" if outcome else "long_no", "executable": True, "bid": 0.35, "ask": 0.45, "bid_depth": 80, "ask_depth": 80})
    return pd.DataFrame(events), pd.DataFrame(signals)


class BacktestTests(unittest.TestCase):
    def test_walk_forward_uses_only_prior_events(self):
        events, signals = event_frames()
        forecasts, _ = run_walk_forward(signals, events, config())
        self.assertEqual(len(forecasts), 2)
        self.assertEqual(forecasts.iloc[0]["training_events"], 2)
        changed = events.copy()
        changed.loc[3, "outcome"] = 1 - changed.loc[3, "outcome"]
        changed_signals = signals.copy()
        changed_signals.loc[3, "outcome"] = changed.loc[3, "outcome"]
        rerun, _ = run_walk_forward(changed_signals, changed, config())
        self.assertAlmostEqual(forecasts.iloc[0]["vali_calibrated_probability"], rerun.iloc[0]["vali_calibrated_probability"])

    def test_execution_caps_depth_and_charges_fees(self):
        events, signals = event_frames(3)
        trades, _ = simulate_trades(signals, events, config())
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades.iloc[0]["entry_notional"], 80)
        self.assertGreater(trades.iloc[0]["entry_fee"], 0)
        self.assertEqual(trades.iloc[0]["exit_reason"], "settlement")

    def test_regime_flip_exits_before_settlement(self):
        events, signals = event_frames(3)
        entry = signals.iloc[-1]
        exit_row = entry.copy()
        exit_row["cutoff_at"] = entry["cutoff_at"] + pd.Timedelta(days=1)
        exit_row["regime"] = "market_leading"
        exit_row["action"] = "none"
        exit_row["bid"] = 0.40
        exit_row["ask"] = 0.50
        signals = pd.concat([signals, exit_row.to_frame().T], ignore_index=True)
        trades, _ = simulate_trades(signals, events, config())
        self.assertEqual(trades.iloc[0]["exit_reason"], "regime_change")
        self.assertEqual(trades.iloc[0]["exit_at"], exit_row["cutoff_at"])
        self.assertGreater(trades.iloc[0]["exit_fee"], 0)


if __name__ == "__main__":
    unittest.main()
