"""Versioned constants and record containers for VALI research inputs."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


class DataValidationError(ValueError):
    """Raised when an input violates the published data contract."""


EVENT_COLUMNS = {
    "event_id",
    "contract_id",
    "open_at",
    "meeting_at",
    "settlement_at",
    "yes_label",
    "outcome",
}
QUOTE_COLUMNS = {
    "contract_id",
    "observed_at",
    "bid",
    "ask",
    "last",
    "volume",
    "bid_depth",
    "ask_depth",
}
FEATURE_COLUMNS = {
    "feature_id",
    "observation_at",
    "available_at",
    "vintage",
    "source",
    "value",
}
TRADE_COLUMNS = {"trade_id", "contract_id", "observed_at", "price", "size"}
MANIFEST_COLUMNS = {
    "feature_id",
    "rationale",
    "transformation",
    "polarity",
    "availability_lag_days",
    "missing_policy",
    "max_age_days",
    "required",
    "source",
}
EXECUTION_SNAPSHOT_FIELDS = {
    "contract_id",
    "observed_at",
    "bid",
    "ask",
    "bid_depth",
    "ask_depth",
    "depth_observed",
}
EVENT_IDENTITY_FIELDS = {"event_id", "contract_id", "meeting_at"}
PUBLIC_SOURCE_CLASSIFICATIONS = {
    "public_behavioral_data",
    "public_search_data",
    "public_filings",
    "public_market_quotes",
    "public_executable_prices",
    "public_venue_snapshot",
}
PROHIBITED_SOURCE_CLASSIFICATIONS = {
    "private",
    "proprietary",
    "client_data",
    "order_flow",
    "pending_order",
    "product_launch",
    "credentialed_trading",
    "execution_api",
    "P_flow",
}


@dataclass
class ValidationSummary:
    rows: dict[str, int] = field(default_factory=dict)
    unresolved_events: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "rows": self.rows,
            "unresolved_events": self.unresolved_events,
            "warnings": self.warnings,
        }


@dataclass
class InputBundle:
    events: pd.DataFrame
    quotes: pd.DataFrame
    features: pd.DataFrame
    manifest: pd.DataFrame
    trades: pd.DataFrame | None = None
    validation: ValidationSummary = field(default_factory=ValidationSummary)
