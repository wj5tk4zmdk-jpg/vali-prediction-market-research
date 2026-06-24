"""Contracts for the Step 5A empirical pre-analysis plan."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from vali.application.commands import build_parser


ROOT = Path(__file__).parents[2]
OPERATIONAL = ROOT / "docs" / "operational"
PLAN = OPERATIONAL / "5A_EMPIRICAL_VALIDATION_PLAN.md"
GATES = OPERATIONAL / "FALSIFICATION_GATES.md"
REGISTRY = OPERATIONAL / "EXPERIMENT_REGISTRY.md"
FROZEN_HASH = (
    "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def test_operational_plan_documents_exist():
    assert PLAN.is_file()
    assert GATES.is_file()
    assert REGISTRY.is_file()


def test_registered_experiment_identity_and_freeze_are_explicit():
    registry = _text(REGISTRY)
    assert "fed_easing_kxfed_v1" in registry
    assert "configs/experiments/fed_easing_v1.toml" in registry
    assert "configs/features/google_trends_candidate_v1.csv" in registry
    assert registry.count(FROZEN_HASH) == 1
    assert "Registered, not yet empirically validated" in registry


def test_plan_predeclares_null_baselines_metrics_and_falsification():
    plan = _text(PLAN).casefold()
    gates = _text(GATES).casefold()
    assert "null hypothesis" in plan
    assert "required baselines" in plan
    assert "market probability" in plan
    assert "brier score" in plan
    assert "log loss" in plan
    assert "falsification gates" in plan
    assert "walk-forward failure" in gates
    assert "baseline failure" in gates


def test_claim_boundaries_do_not_assert_alpha_or_trading_readiness():
    plan = _text(PLAN)
    registry = _text(REGISTRY)
    assert "Passing Step 5A does not prove alpha." in plan
    assert "Passing Step 5A does not authorize trading." in plan
    assert "No empirical alpha claim has been established." in plan
    assert "Allowed claims:** Methodology readiness only" in registry
    assert "Prohibited claims:** Alpha proven; trading-ready" in registry
    combined = "\n".join(_text(path) for path in (PLAN, GATES, REGISTRY))
    for disallowed_assertion in (
        "VALI alpha is proven",
        "VALI is trading-ready",
        "VALI authorizes live trading",
    ):
        assert disallowed_assertion not in combined


def test_frozen_hash_and_canonical_files_remain_present():
    assert (ROOT / "configs" / "experiments" / "fed_easing_v1.toml").is_file()
    manifest = (
        ROOT / "configs" / "features" / "google_trends_candidate_v1.csv"
    )
    assert manifest.is_file()
    assert FROZEN_HASH in _text(REGISTRY)


def test_public_api_and_cli_do_not_expose_prohibited_operations():
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
    cli_surface = _parser_surface(build_parser())
    normalized = {
        value.replace("-", "_").replace(" ", "_")
        for value in exports | cli_surface
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
    assert all(
        not any(term in value for value in normalized) for term in prohibited
    )
