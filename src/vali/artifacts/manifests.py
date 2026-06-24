"""Reproducibility hashes and run-manifest construction."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..configuration.contracts import ValiConfig
from .reports import WARNING


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_run_manifest(config: ValiConfig) -> dict[str, Any]:
    paths = {
        "events": config.data.events,
        "quotes": config.data.quotes,
        "features": config.data.features,
        "feature_manifest": config.data.feature_manifest,
    }
    if config.data.trades:
        paths["trades"] = config.data.trades
    return {
        "package_version": "0.3.0",
        "methodology_version": config.methodology_version,
        "parameter_freeze_date": config.parameter_freeze_date,
        "config_path": str(config.source_path) if config.source_path else None,
        "config_sha256": sha256_file(config.source_path) if config.source_path else None,
        "input_sha256": {name: sha256_file(path) for name, path in paths.items()},
        "research_warning": WARNING,
    }


__all__ = ["build_run_manifest", "sha256_file"]
