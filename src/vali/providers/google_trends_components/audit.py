"""Google Trends readiness, coverage, and missing-query audit output."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from .contracts import PROVIDER, TrendsQuerySpec, parse_bool
from .manifest import query_manifest_sha256
from .normalization import read_existing_csv


def trends_status(
    output_root: str | Path,
    specs: Sequence[TrendsQuerySpec],
) -> dict[str, Any]:
    root = Path(output_root).resolve()
    observations = read_existing_csv(
        root / "trends_observations.csv",
        [
            "query_id",
            "observation_date",
            "status",
            "usable",
            "retrieved_at",
        ],
    )
    active = {spec.query_id for spec in specs if spec.active}
    if observations.empty:
        return {
            "provider": PROVIDER,
            "query_manifest_sha256": query_manifest_sha256(specs),
            "query_set_frozen": all(
                spec.freeze_date for spec in specs if spec.active
            ),
            "observation_rows": 0,
            "latest_usable_date": None,
            "missing_active_queries": sorted(active),
            "suppressed_observations": 0,
            "low_volume_observations": 0,
            "coverage": {},
        }
    observations["usable"] = observations["usable"].map(
        lambda value: parse_bool(value, "observations.usable")
    )
    usable = observations.loc[observations["usable"]]
    latest = pd.to_datetime(
        usable["observation_date"], errors="coerce"
    ).max()
    present = set(usable["query_id"].astype(str))
    all_dates = sorted(observations["observation_date"].astype(str).unique())
    denominator = len(all_dates)
    coverage = {
        query_id: (
            float(
                (usable["query_id"].astype(str) == query_id).sum()
                / denominator
            )
            if denominator
            else 0.0
        )
        for query_id in sorted(active)
    }
    return {
        "provider": PROVIDER,
        "query_manifest_sha256": query_manifest_sha256(specs),
        "query_set_frozen": all(
            spec.freeze_date for spec in specs if spec.active
        ),
        "observation_rows": len(observations),
        "latest_usable_date": (
            latest.date().isoformat() if not pd.isna(latest) else None
        ),
        "missing_active_queries": sorted(active.difference(present)),
        "suppressed_observations": int(
            (observations["status"] == "suppressed").sum()
        ),
        "low_volume_observations": int(
            (observations["status"] == "low_volume").sum()
        ),
        "coverage": coverage,
    }


__all__ = ["trends_status"]
