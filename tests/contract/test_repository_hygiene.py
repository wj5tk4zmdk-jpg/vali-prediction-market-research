"""Repository and package hygiene contracts for the VALI v0.1 migration."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import tomllib

import vali
from vali.application.commands import build_parser
from vali.config import ValiConfig
from vali.providers.google_trends import (
    load_query_manifest,
    query_manifest_sha256,
)


ROOT = Path(__file__).parents[2]
AUTHORITATIVE_SOURCE = (ROOT / "src" / "vali").resolve()
CANONICAL_CONFIG = ROOT / "configs" / "experiments" / "fed_easing_v1.toml"
COMPATIBILITY_CONFIG = ROOT / "examples" / "config.toml"
CANONICAL_TRENDS_MANIFEST = (
    ROOT / "configs" / "features" / "google_trends_candidate_v1.csv"
)
FROZEN_TRENDS_HASH = (
    "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a"
)


def test_package_metadata_and_authoritative_source_are_consistent():
    metadata = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert metadata["project"]["version"] == vali.__version__
    assert metadata["tool"]["setuptools"]["packages"]["find"]["where"] == [
        "src"
    ]
    assert Path(vali.__file__).resolve().is_relative_to(AUTHORITATIVE_SOURCE)

    quarantined_build = (
        ROOT / "artifacts" / "quarantine" / "build" / "lib"
    ).resolve()
    assert quarantined_build.exists()
    assert all(
        not Path(entry or ".").resolve().is_relative_to(quarantined_build)
        for entry in sys.path
    )


def test_new_boundaries_and_legacy_facades_remain_importable():
    boundaries = (
        "vali.application",
        "vali.artifacts",
        "vali.configuration",
        "vali.data",
        "vali.domain",
        "vali.execution",
        "vali.providers",
        "vali.research",
    )
    facades = (
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
    )
    for module_name in boundaries + facades:
        module = importlib.import_module(module_name)
        assert Path(module.__file__).resolve().is_relative_to(
            AUTHORITATIVE_SOURCE
        )


def test_repository_orientation_documents_exist():
    for relative_path in (
        "README.md",
        "AGENTS.md",
        "ARTIFACT_INVENTORY.md",
        "REPOSITORY_POLICY.md",
        "ENVIRONMENT.md",
        "docs/methodology/vali-1.0-contract.md",
        "docs/research-protocol.md",
        "docs/reporting-and-alpha-policy.md",
    ):
        assert (ROOT / relative_path).is_file()


def test_canonical_and_compatibility_configs_load_with_same_settings():
    canonical = ValiConfig.from_toml(CANONICAL_CONFIG)
    compatibility = ValiConfig.from_toml(COMPATIBILITY_CONFIG)
    assert canonical.methodology_version == compatibility.methodology_version
    assert canonical.methodology_version == "1.0.1"
    assert canonical.market == compatibility.market
    assert canonical.features == compatibility.features
    assert canonical.signal == compatibility.signal
    assert canonical.regime == compatibility.regime
    assert canonical.backtest == compatibility.backtest
    assert canonical.source_path == CANONICAL_CONFIG.resolve()
    assert compatibility.source_path == COMPATIBILITY_CONFIG.resolve()


def test_frozen_google_trends_manifest_hash_is_unchanged():
    specs = load_query_manifest(CANONICAL_TRENDS_MANIFEST)
    assert query_manifest_sha256(specs) == FROZEN_TRENDS_HASH


def test_public_exports_and_cli_have_no_prohibited_operational_surface():
    exported = {
        name.casefold()
        for module_name in (
            "vali",
            "vali.application",
            "vali.providers",
            "vali.providers.google_trends_components",
            "vali.providers.kalshi_components",
        )
        for name in getattr(importlib.import_module(module_name), "__all__", ())
    }
    cli_help = build_parser().format_help().casefold()
    forbidden = (
        "p_flow",
        "submit_order",
        "order_submission",
        "credentialed_trading",
        "private_input",
        "proprietary_order_flow",
    )
    assert all(token not in exported for token in forbidden)
    assert all(token.replace("_", "-") not in cli_help for token in forbidden)
