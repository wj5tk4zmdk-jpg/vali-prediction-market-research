"""Daily point-in-time price selection and liquidity filtering."""

from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .config import ValiConfig


def _cutoff_time(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":"))
    return time(hour=hour, minute=minute)


def build_daily_cutoffs(events: pd.DataFrame, config: ValiConfig) -> pd.DataFrame:
    tz = ZoneInfo(config.features.timezone)
    cutoff_clock = _cutoff_time(config.features.daily_cutoff)
    rows: list[dict] = []
    for event in events.itertuples(index=False):
        open_local = event.open_at.tz_convert(tz)
        settle_local = event.settlement_at.tz_convert(tz)
        for day in pd.date_range(open_local.normalize(), settle_local.normalize(), freq="D", tz=tz):
            cutoff_local = day.replace(hour=cutoff_clock.hour, minute=cutoff_clock.minute)
            cutoff = cutoff_local.tz_convert("UTC")
            if event.open_at <= cutoff <= event.settlement_at:
                rows.append(
                    {
                        "event_id": event.event_id,
                        "contract_id": event.contract_id,
                        "cutoff_at": cutoff,
                        "meeting_at": event.meeting_at,
                        "settlement_at": event.settlement_at,
                    }
                )
    return pd.DataFrame(rows).sort_values(["contract_id", "cutoff_at"]).reset_index(drop=True)


def select_daily_market(
    events: pd.DataFrame,
    quotes: pd.DataFrame,
    trades: pd.DataFrame | None,
    config: ValiConfig,
) -> pd.DataFrame:
    cutoffs = build_daily_cutoffs(events, config)
    rows: list[dict] = []
    max_age = pd.Timedelta(minutes=config.market.max_quote_age_minutes)
    trade_window = pd.Timedelta(minutes=config.market.fallback_trade_window_minutes)

    for contract_id, contract_cutoffs in cutoffs.groupby("contract_id", sort=False):
        contract_quotes = quotes.loc[quotes["contract_id"] == contract_id].sort_values("observed_at")
        contract_trades = None
        if trades is not None:
            contract_trades = trades.loc[trades["contract_id"] == contract_id].sort_values("observed_at")
        for cutoff in contract_cutoffs.itertuples(index=False):
            prior = contract_quotes.loc[contract_quotes["observed_at"] <= cutoff.cutoff_at]
            quote = prior.iloc[-1] if not prior.empty else None
            record = cutoff._asdict()
            record.update(
                {
                    "bid": np.nan,
                    "ask": np.nan,
                    "bid_depth": np.nan,
                    "ask_depth": np.nan,
                    "spread": np.nan,
                    "price": np.nan,
                    "price_source": "none",
                    "price_quality_pass": False,
                    "execution_liquidity_pass": False,
                    "depth_observed": False,
                    "liquidity_pass": False,
                    "executable": False,
                    "rejection_reason": "no_quote",
                }
            )
            price_valid = False
            if quote is not None:
                age = cutoff.cutoff_at - quote["observed_at"]
                spread = float(quote["ask"] - quote["bid"])
                depth_observed = bool(quote.get("depth_observed", True))
                depth_ok = (
                    depth_observed
                    and min(float(quote["bid_depth"]), float(quote["ask_depth"]))
                    >= config.market.min_depth
                )
                spread_ok = spread <= config.market.max_spread
                fresh = age <= max_age
                record.update(
                    {
                        "bid": float(quote["bid"]),
                        "ask": float(quote["ask"]),
                        "bid_depth": float(quote["bid_depth"]),
                        "ask_depth": float(quote["ask_depth"]),
                        "spread": spread,
                        "depth_observed": depth_observed,
                    }
                )
                if fresh and spread_ok:
                    price_valid = True
                    record.update(
                        {
                            "price": (float(quote["bid"]) + float(quote["ask"])) / 2,
                            "price_source": "midquote",
                            "price_quality_pass": True,
                            "execution_liquidity_pass": depth_ok,
                            "liquidity_pass": True,
                            "executable": depth_ok,
                            "rejection_reason": ""
                            if depth_ok
                            else ("depth_unobserved" if not depth_observed else "thin_depth"),
                        }
                    )
                elif not fresh:
                    record["rejection_reason"] = "stale_quote"
                elif not spread_ok:
                    record["rejection_reason"] = "wide_spread"
                else:
                    record["rejection_reason"] = "wide_spread"

            if not price_valid and contract_trades is not None and not contract_trades.empty:
                eligible = contract_trades.loc[
                    (contract_trades["observed_at"] <= cutoff.cutoff_at)
                    & (contract_trades["observed_at"] > cutoff.cutoff_at - trade_window)
                ]
                dollar_volume = float((eligible["price"] * eligible["size"]).sum())
                if not eligible.empty and dollar_volume >= config.market.min_depth:
                    vwap = float(np.average(eligible["price"], weights=eligible["size"]))
                    record.update(
                        {
                            "price": vwap,
                            "price_source": "trade_vwap",
                            "price_quality_pass": True,
                            "execution_liquidity_pass": False,
                            "liquidity_pass": True,
                            "executable": False,
                            "rejection_reason": "non_executable_vwap",
                        }
                    )
            rows.append(record)
    return pd.DataFrame(rows).sort_values(["contract_id", "cutoff_at"]).reset_index(drop=True)
