"""Final deterministic contracts for the VALI v0.1 migration candidate."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys

from vali.application.commands import build_parser
from vali.config import ValiConfig
from vali.providers.google_trends import (
    load_query_manifest,
    query_manifest_sha256,
)


ROOT = Path(__file__).parents[2]
SOURCE_ROOT = (ROOT / "src" / "vali").resolve()
CANONICAL_CONFIG = ROOT / "configs" / "experiments" / "fed_easing_v1.toml"
COMPATIBILITY_CONFIG = ROOT / "examples" / "config.toml"
TRENDS_MANIFEST = (
    ROOT / "configs" / "features" / "google_trends_candidate_v1.csv"
)
FROZEN_TRENDS_HASH = (
    "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a"
)

BOUNDARIES = (
    "vali.domain",
    "vali.data",
    "vali.configuration",
    "vali.research",
    "vali.artifacts",
    "vali.execution",
    "vali.providers.kalshi_components",
    "vali.providers.google_trends_components",
    "vali.application",
)
FACADES = (
    "vali.backtest",
    "vali.calibration",
    "vali.cli",
    "vali.config",
    "vali.features",
    "vali.io",
    "vali.pipeline",
    "vali.regimes",
    "vali.reporting",
    "vali.signals",
    "vali.providers.kalshi",
    "vali.providers.google_trends",
)
PUBLIC_PACKAGES = (
    "vali",
    "vali.application",
    "vali.artifacts",
    "vali.configuration",
    "vali.data",
    "vali.domain",
    "vali.execution",
    "vali.providers",
    "vali.providers.kalshi",
    "vali.providers.google_trends",
)
PROHIBITED = (
    "p_flow",
    "proprietary_order_flow",
    "private_client_data",
    "order_submission",
    "submit_order",
    "place_order",
    "credentialed_trading",
    "live_trading",
)


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


def test_release_candidate_documents_exist():
    assert (ROOT / "V0_1_RELEASE_CANDIDATE.md").is_file()
    assert (ROOT / "FINAL_VALIDATION_REPORT.md").is_file()


def test_canonical_and_compatibility_config_paths_load():
    canonical = ValiConfig.from_toml(CANONICAL_CONFIG)
    compatibility = ValiConfig.from_toml(COMPATIBILITY_CONFIG)
    assert canonical.methodology_version == "1.0.1"
    assert compatibility.methodology_version == "1.0.1"
    assert canonical.market == compatibility.market
    assert canonical.features == compatibility.features
    assert canonical.signal == compatibility.signal
    assert canonical.regime == compatibility.regime
    assert canonical.backtest == compatibility.backtest


def test_frozen_google_trends_manifest_hash_remains_unchanged():
    specs = load_query_manifest(TRENDS_MANIFEST)
    assert query_manifest_sha256(specs) == FROZEN_TRENDS_HASH


def test_boundaries_and_legacy_facades_resolve_from_source_tree():
    quarantined_build = (
        ROOT / "artifacts" / "quarantine" / "build" / "lib"
    ).resolve()
    assert quarantined_build.exists()
    for module_name in BOUNDARIES + FACADES:
        module = importlib.import_module(module_name)
        module_path = Path(module.__file__).resolve()
        assert module_path.is_relative_to(SOURCE_ROOT)
        assert not module_path.is_relative_to(quarantined_build)
    assert all(
        not Path(entry or ".").resolve().is_relative_to(quarantined_build)
        for entry in sys.path
    )


def test_public_api_cli_and_configs_expose_no_prohibited_surface():
    export_surface = {
        str(name).casefold()
        for module_name in PUBLIC_PACKAGES
        for name in getattr(importlib.import_module(module_name), "__all__", ())
    }
    cli_surface = _parser_surface(build_parser())
    config_surface = {
        CANONICAL_CONFIG.as_posix().casefold(),
        COMPATIBILITY_CONFIG.as_posix().casefold(),
        CANONICAL_CONFIG.read_text(encoding="utf-8").casefold(),
        COMPATIBILITY_CONFIG.read_text(encoding="utf-8").casefold(),
    }
    normalized = {
        value.replace("-", "_").replace(" ", "_")
        for value in export_surface | cli_surface | config_surface
    }
    assert all(
        not any(term in value for value in normalized) for term in PROHIBITED
    )


def test_provider_facades_remain_read_only_by_public_export():
    for module_name in (
        "vali.providers.kalshi",
        "vali.providers.google_trends",
    ):
        exported = {
            str(name).casefold()
            for name in getattr(importlib.import_module(module_name), "__all__")
        }
        assert all(term not in exported for term in PROHIBITED)
