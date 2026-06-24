"""Contracts for the Step 5B-1 data remediation protocol."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
EXPERIMENT = ROOT / "experiments" / "fed_easing_kxfed_v1"
ATTENTION = EXPERIMENT / "ATTENTION_DATA_ACQUISITION_PROTOCOL.md"
KALSHI = EXPERIMENT / "KALSHI_RECONSTRUCTION_LEDGER.md"
REMEDIATION = EXPERIMENT / "data_remediation_manifest.json"
FROZEN_HASH = (
    "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a"
)


def _manifest() -> dict:
    return json.loads(REMEDIATION.read_text(encoding="utf-8"))


def test_remediation_artifacts_exist():
    assert ATTENTION.is_file()
    assert KALSHI.is_file()
    assert REMEDIATION.is_file()


def test_remediation_manifest_identity_and_freeze_are_exact():
    manifest = _manifest()
    assert manifest["experiment_id"] == "fed_easing_kxfed_v1"
    assert manifest["step"] == "5B-1"
    assert manifest["feature_manifest_hash"] == FROZEN_HASH


def test_attention_history_is_not_falsely_marked_acquired():
    attention = _manifest()["attention_history"]
    assert attention["status"] == "not_acquired"
    assert attention["fixture_days_available"] == 3
    assert attention["canonical_empirical_history_available"] is False
    assert attention["blocking_gap"] == (
        "point_in_time_empirical_attention_history_missing"
    )


def test_5c_and_capacity_claims_remain_disabled():
    manifest = _manifest()
    reconstruction = manifest["kalshi_reconstruction"]
    assert manifest["may_proceed_to_5C"] is False
    assert reconstruction["historical_depth_available"] is False
    assert reconstruction["capacity_claims_enabled"] is False
    assert reconstruction["complete_cutoff_snapshot_series_available"] is False


def test_claim_boundaries_are_explicit():
    boundaries = set(_manifest()["claim_boundaries"])
    assert "no_alpha_claim" in boundaries
    assert "no_trading_readiness_claim" in boundaries
    assert "no_capacity_claim_without_depth" in boundaries


def test_documents_prohibit_private_and_operational_sources():
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in (ATTENTION, KALSHI)
    )
    folded = combined.casefold()
    for required_prohibition in (
        "private search logs",
        "proprietary order flow",
        "order submission",
        "live trading",
        "p_flow",
    ):
        assert required_prohibition.casefold() in folded
    for disallowed_claim in (
        "VALI alpha is proven",
        "VALI is trading-ready",
        "Step 5C is authorized",
    ):
        assert disallowed_claim not in combined
    assert "Step 5C remains unauthorized" in combined
