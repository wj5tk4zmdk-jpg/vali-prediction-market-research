"""Contracts for the local-only Step 5B data availability audit."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from vali.application.commands import build_parser


ROOT = Path(__file__).parents[2]
EXPERIMENT_DIR = ROOT / "experiments" / "fed_easing_kxfed_v1"
EXPERIMENT_MANIFEST = EXPERIMENT_DIR / "EXPERIMENT_MANIFEST.md"
AUDIT = EXPERIMENT_DIR / "DATA_AVAILABILITY_AUDIT.md"
AVAILABILITY = EXPERIMENT_DIR / "data_availability_manifest.json"
FROZEN_HASH = (
    "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a"
)
ALLOWED_DECISIONS = {
    "sufficient_for_5C",
    "sufficient_for_fixture_only_validation",
    "insufficient_pending_data_collection",
    "insufficient_due_to_missing_point_in_time_data",
    "insufficient_due_to_missing_outcomes",
    "insufficient_due_to_missing_market_history",
    "insufficient_due_to_missing_attention_history",
}


def _parser_surface(parser: argparse.ArgumentParser) -> set[str]:
    surface: set[str] = set()
    for action in parser._actions:
        surface.add(str(action.dest).casefold())
        surface.update(option.casefold() for option in action.option_strings)
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                surface.add(name.casefold())
                surface.update(_parser_surface(child))
    return surface


def test_experiment_audit_artifacts_exist():
    assert EXPERIMENT_MANIFEST.is_file()
    assert AUDIT.is_file()
    assert AVAILABILITY.is_file()


def test_availability_manifest_identity_and_freeze_are_exact():
    manifest = json.loads(AVAILABILITY.read_text(encoding="utf-8"))
    assert manifest["experiment_id"] == "fed_easing_kxfed_v1"
    assert manifest["canonical_config"] == (
        "configs/experiments/fed_easing_v1.toml"
    )
    assert manifest["feature_manifest"] == (
        "configs/features/google_trends_candidate_v1.csv"
    )
    assert manifest["feature_manifest_hash"] == FROZEN_HASH
    assert manifest["audit_scope"] == (
        "local_repository_only_no_live_collection"
    )


def test_availability_decision_and_gap_types_are_valid():
    manifest = json.loads(AVAILABILITY.read_text(encoding="utf-8"))
    assert manifest["decision"] in ALLOWED_DECISIONS
    assert isinstance(manifest["blocking_gaps"], list)
    assert manifest["blocking_gaps"]
    assert isinstance(manifest["claim_limitations"], list)
    assert manifest["claim_limitations"]


def test_documents_make_no_affirmative_alpha_or_trading_claim():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (EXPERIMENT_MANIFEST, AUDIT)
    )
    assert "not yet empirically validated" in combined
    assert "no alpha claim" in combined.casefold()
    assert "no trading-readiness claim" in combined.casefold()
    for disallowed in (
        "VALI alpha is proven",
        "VALI is trading-ready",
        "VALI authorizes live trading",
    ):
        assert disallowed not in combined


def test_audit_records_fixture_and_empirical_limits():
    manifest = json.loads(AVAILABILITY.read_text(encoding="utf-8"))
    assert manifest["google_trends_attention_data"]["fixture_only"] is True
    assert (
        manifest["google_trends_attention_data"][
            "empirical_history_available"
        ]
        is False
    )
    assert (
        manifest["common_intersection"][
            "sufficient_for_empirical_walk_forward"
        ]
        is False
    )
    assert manifest["kalshi_market_data"]["depth_available"] is False


def test_public_api_and_cli_expose_no_prohibited_operations():
    public_modules = (
        "vali",
        "vali.application",
        "vali.providers",
        "vali.providers.kalshi",
        "vali.providers.google_trends",
    )
    exports = {
        str(name).casefold()
        for module_name in public_modules
        for name in getattr(importlib.import_module(module_name), "__all__", ())
    }
    surface = {
        value.replace("-", "_").replace(" ", "_")
        for value in exports | _parser_surface(build_parser())
    }
    prohibited = (
        "p_flow",
        "order_submission",
        "submit_order",
        "credentialed_trading",
        "private_input",
        "private_client_data",
        "proprietary_order_flow",
        "live_trading",
    )
    assert all(not any(term in value for value in surface) for term in prohibited)
