"""Flat compiled-manifest adapter for VALI research backtests.

This module is the KG handoff boundary. It reads a compiled manifest, validates
the runtime constraints, converts the flat A-side feature declarations into the
existing frozen feature-manifest table, and loads public local data files. It
does not traverse the graph, learn weights, use expected lead/lag metadata for
signal construction, fetch providers, submit orders, or make alpha claims.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ..configuration.contracts import (
    BacktestConfig,
    ConfigError,
    DataConfig,
    FeatureConfig,
    MarketConfig,
    RegimeConfig,
    SignalConfig,
    ValiConfig,
)
from ..data.contracts import InputBundle
from ..data.validation import validate_frames
from ..io import read_table
from .handoff import COMPILED_MANIFEST_SCHEMA, KnowledgeGraphError


REQUIRED_RUNTIME_CONSTRAINTS = {
    "no_graph_traversal_required": True,
    "no_learned_weights": True,
    "no_dynamic_query_selection": True,
    "lag_metadata_usage": "documentation_and_falsification_only",
}

REQUIRED_CLAIM_BOUNDARIES = {
    "no_alpha_claim",
    "no_trading_readiness_claim",
    "public_data_only",
    "no_private_data",
    "no_proprietary_order_flow",
    "no_credentials",
    "no_live_trading",
    "no_order_submission",
    "no_P_flow",
}

ALLOWED_TRANSFORMS = {"level", "diff", "pct_change", "log_diff", "log1p"}


@dataclass(frozen=True)
class CompiledManifestRuntime:
    manifest_path: Path
    manifest: dict[str, Any]
    config: ValiConfig
    feature_manifest: pd.DataFrame
    graph_path: Path


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KnowledgeGraphError(f"Missing compiled manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise KnowledgeGraphError(f"Invalid compiled manifest JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise KnowledgeGraphError("Compiled manifest must contain a JSON object.")
    return payload


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise KnowledgeGraphError(f"Compiled manifest is missing object field: {key}")
    return value


def _required_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise KnowledgeGraphError(f"Compiled manifest is missing non-empty list: {key}")
    return value


def _resolve_path(value: Any, base: Path, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeGraphError(f"Compiled manifest runtime input is missing: {field}")
    candidate = Path(value)
    return candidate if candidate.is_absolute() else (base / candidate).resolve()


def _required_setting(section: dict[str, Any], key: str, section_name: str) -> Any:
    if key not in section:
        raise KnowledgeGraphError(
            f"Compiled manifest runtime_parameters.{section_name} is missing {key}"
        )
    return section[key]


def _parse_availability_lag_days(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value or "T-0").strip().upper()
    if text.startswith("T-"):
        return int(text.removeprefix("T-"))
    if text in {"T", "T-0"}:
        return 0
    return int(text)


def _normalize_missing_policy(value: Any) -> str:
    text = str(value or "reject").strip()
    if text == "reject_required":
        return "reject"
    if text in {"reject", "asof"}:
        return text
    raise KnowledgeGraphError(
        "Compiled manifest feature missing_policy must be reject, asof, or reject_required."
    )


def _validate_runtime_constraints(manifest: dict[str, Any]) -> None:
    constraints = _required_mapping(manifest, "runtime_constraints")
    for key, expected in REQUIRED_RUNTIME_CONSTRAINTS.items():
        if constraints.get(key) != expected:
            raise KnowledgeGraphError(
                f"Compiled manifest runtime_constraints.{key} must be {expected!r}."
            )
    lag_constraint = str(constraints.get("lag_metadata_constraint", "")).casefold()
    if "must not use expected_lead_days" not in lag_constraint:
        raise KnowledgeGraphError(
            "Compiled manifest must explicitly prohibit using expected_lead_days "
            "for runtime tuning."
        )


def _validate_claim_boundaries(manifest: dict[str, Any]) -> None:
    boundaries = set(_required_list(manifest, "claim_boundaries"))
    missing = sorted(REQUIRED_CLAIM_BOUNDARIES.difference(boundaries))
    if missing:
        raise KnowledgeGraphError(
            "Compiled manifest is missing claim boundaries: " + ", ".join(missing)
        )


def _validate_p_side(manifest: dict[str, Any]) -> None:
    p_side = _required_mapping(manifest, "p_side")
    markets = _required_list(p_side, "markets")
    for index, market in enumerate(markets, start=1):
        if not isinstance(market, dict):
            raise KnowledgeGraphError(f"Compiled manifest p_side.markets[{index}] must be an object.")
        for field in (
            "venue",
            "normalized_contract_id",
            "price_source_policy",
            "liquidity_policy",
            "depth_availability",
        ):
            if not str(market.get(field, "")).strip():
                raise KnowledgeGraphError(
                    f"Compiled manifest p_side.markets[{index}].{field} is required."
                )
        if market.get("price_source_policy") != "public_executable_prices":
            raise KnowledgeGraphError(
                "Compiled manifest P-side must use public_executable_prices."
            )


def _feature_rows_from_manifest(
    manifest: dict[str, Any],
    *,
    default_max_age_days: int,
) -> list[dict[str, Any]]:
    a_side = _required_mapping(manifest, "a_side")
    if a_side.get("composition_policy") != "equal_weight":
        raise KnowledgeGraphError(
            "Compiled manifest a_side.composition_policy must be equal_weight."
        )
    if a_side.get("weight_policy") != "frozen_equal_weight":
        raise KnowledgeGraphError(
            "Compiled manifest a_side.weight_policy must be frozen_equal_weight."
        )
    features = _required_list(a_side, "features")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, feature in enumerate(features, start=1):
        if not isinstance(feature, dict):
            raise KnowledgeGraphError(f"Compiled manifest a_side.features[{index}] must be an object.")
        feature_id = str(feature.get("feature_id", "")).strip()
        if not feature_id:
            raise KnowledgeGraphError(
                f"Compiled manifest a_side.features[{index}].feature_id is required."
            )
        if feature_id in seen:
            raise KnowledgeGraphError(
                f"Compiled manifest contains duplicate feature_id: {feature_id}"
            )
        seen.add(feature_id)
        polarity = int(feature.get("polarity", 0))
        if polarity not in {-1, 1}:
            raise KnowledgeGraphError(
                f"Compiled manifest feature {feature_id} polarity must be -1 or 1."
            )
        transform = str(feature.get("transform", "level"))
        if transform not in ALLOWED_TRANSFORMS:
            raise KnowledgeGraphError(
                f"Compiled manifest feature {feature_id} transform is unsupported: {transform}"
            )
        source = str(feature.get("source", "")).strip()
        if not source:
            raise KnowledgeGraphError(
                f"Compiled manifest feature {feature_id} source is required."
            )
        rows.append(
            {
                "feature_id": feature_id,
                "rationale": feature.get(
                    "rationale",
                    f"Compiled KG feature for {feature.get('concept_id', feature_id)}",
                ),
                "transformation": transform,
                "polarity": polarity,
                "availability_lag_days": _parse_availability_lag_days(
                    feature.get("availability_lag_days", feature.get("availability_lag", "T-0"))
                ),
                "missing_policy": _normalize_missing_policy(
                    feature.get("missing_policy", "reject")
                ),
                "max_age_days": int(feature.get("max_age_days", default_max_age_days)),
                "required": bool(feature.get("required", True)),
                "source": source,
            }
        )
    return rows


def feature_manifest_from_compiled_manifest(
    manifest: dict[str, Any],
    *,
    default_max_age_days: int = 2,
) -> pd.DataFrame:
    """Return the frozen feature manifest table implied by a flat manifest.

    Expected lead/lag metadata is intentionally ignored here. Runtime windows,
    thresholds, and entry/exit timing come only from runtime parameters and the
    methodology-locked engine configuration.
    """

    return pd.DataFrame(
        _feature_rows_from_manifest(
            manifest,
            default_max_age_days=default_max_age_days,
        )
    )


def _config_from_manifest(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> tuple[ValiConfig, pd.DataFrame, Path]:
    base = manifest_path.parent
    runtime_inputs = _required_mapping(manifest, "runtime_inputs")
    runtime_parameters = _required_mapping(manifest, "runtime_parameters")
    run = _required_mapping(runtime_parameters, "run")
    market_raw = _required_mapping(runtime_parameters, "market")
    feature_raw = dict(runtime_parameters.get("features", {}))
    signal_raw = dict(runtime_parameters.get("signal", {}))
    regime_raw = dict(runtime_parameters.get("regime", {}))
    backtest_raw = dict(runtime_parameters.get("backtest", {}))
    defaults = dict(runtime_parameters.get("feature_manifest_defaults", {}))
    if "sensitivity_windows" in signal_raw:
        signal_raw["sensitivity_windows"] = tuple(signal_raw["sensitivity_windows"])

    data = DataConfig(
        events=_resolve_path(runtime_inputs.get("events"), base, "events"),
        quotes=_resolve_path(runtime_inputs.get("quotes"), base, "quotes"),
        features=_resolve_path(runtime_inputs.get("features"), base, "features"),
        feature_manifest=manifest_path.resolve(),
        trades=(
            _resolve_path(runtime_inputs.get("trades"), base, "trades")
            if runtime_inputs.get("trades")
            else None
        ),
    )
    market = MarketConfig(
        max_spread=float(_required_setting(market_raw, "max_spread", "market")),
        min_depth=float(_required_setting(market_raw, "min_depth", "market")),
        max_quote_age_minutes=int(
            _required_setting(market_raw, "max_quote_age_minutes", "market")
        ),
        fallback_trade_window_minutes=int(
            _required_setting(market_raw, "fallback_trade_window_minutes", "market")
        ),
        fee_bps=float(_required_setting(market_raw, "fee_bps", "market")),
        probability_epsilon=float(market_raw.get("probability_epsilon", 1e-4)),
    )
    feature_manifest = feature_manifest_from_compiled_manifest(
        manifest,
        default_max_age_days=int(defaults.get("max_age_days", 2)),
    )
    source_graph = _required_mapping(manifest, "source_graph")
    graph_path = _resolve_path(
        source_graph.get("graph_manifest_path"),
        manifest_path.parent,
        "source_graph.graph_manifest_path",
    )
    config = ValiConfig(
        data=data,
        market=market,
        features=FeatureConfig(**feature_raw),
        signal=SignalConfig(**signal_raw),
        regime=RegimeConfig(**regime_raw),
        backtest=BacktestConfig(**backtest_raw),
        parameter_freeze_date=str(
            _required_setting(run, "parameter_freeze_date", "run")
        ),
        methodology_version=str(run.get("methodology_version", "1.0.1")),
        source_path=manifest_path.resolve(),
    )
    try:
        config.validate()
    except ConfigError as exc:
        raise KnowledgeGraphError(f"Compiled manifest runtime config is invalid: {exc}") from exc
    return config, feature_manifest, graph_path


def load_compiled_manifest_runtime(manifest_path: str | Path) -> CompiledManifestRuntime:
    """Load and validate a compiled manifest for backtest execution."""

    path = Path(manifest_path).resolve()
    manifest = _load_json(path)
    if manifest.get("schema_version") != COMPILED_MANIFEST_SCHEMA:
        raise KnowledgeGraphError(
            f"Compiled manifest schema_version must be {COMPILED_MANIFEST_SCHEMA}."
        )
    _validate_runtime_constraints(manifest)
    _validate_claim_boundaries(manifest)
    _validate_p_side(manifest)
    config, feature_manifest, graph_path = _config_from_manifest(path, manifest)
    source_hash = _required_mapping(manifest, "source_graph").get("graph_hash")
    if not str(source_hash or "").startswith("sha256:"):
        raise KnowledgeGraphError("Compiled manifest source_graph.graph_hash is required.")
    return CompiledManifestRuntime(
        manifest_path=path,
        manifest=manifest,
        config=config,
        feature_manifest=feature_manifest,
        graph_path=graph_path,
    )


def load_inputs_from_compiled_manifest(runtime: CompiledManifestRuntime) -> InputBundle:
    """Load local public input files and the manifest-derived feature table."""

    return validate_frames(
        read_table(runtime.config.data.events),
        read_table(runtime.config.data.quotes),
        read_table(runtime.config.data.features),
        runtime.feature_manifest,
        read_table(runtime.config.data.trades) if runtime.config.data.trades else None,
    )


__all__ = [
    "CompiledManifestRuntime",
    "feature_manifest_from_compiled_manifest",
    "load_compiled_manifest_runtime",
    "load_inputs_from_compiled_manifest",
]
