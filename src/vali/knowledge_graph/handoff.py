"""Minimal KG-to-VALI handoff scaffolding.

The functions in this module read local, declared knowledge-graph files and
emit schema-shaped handoff artifacts. They do not contact providers, inspect
outcomes, run signal math, submit orders, or perform empirical validation.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


KG_PREFLIGHT_SCHEMA = "kg_preflight.v1"
COMPILED_MANIFEST_SCHEMA = "compiled_vali_manifest.v1"

KG_PRECHECKS = (
    "preflight.check.graph_manifest_exists",
    "preflight.check.graph_hash_available",
    "preflight.check.attention_source_available",
    "preflight.check.point_in_time_availability_documented",
    "preflight.check.revision_behavior_documented",
    "preflight.check.query_source_geo_frequency_present",
    "preflight.check.p_side_market_mapping_present",
    "preflight.check.terminal_measure_present",
    "preflight.check.clear_horizon_present",
    "preflight.check.settlement_source_present",
    "preflight.check.required_timestamps_available",
    "preflight.check.historical_market_fields_available",
    "preflight.check.depth_availability_classified",
)

CLAIM_BOUNDARY = [
    "availability_only",
    "not_performance_validation",
    "not_alpha_evidence",
    "not_trading_readiness_evidence",
    "public_data_only",
]

COMPILED_CLAIM_BOUNDARIES = [
    "no_alpha_claim",
    "no_trading_readiness_claim",
    "public_data_only",
    "no_private_data",
    "no_proprietary_order_flow",
    "no_credentials",
    "no_live_trading",
    "no_order_submission",
    "no_P_flow",
]

RUNTIME_CONSTRAINTS = {
    "no_graph_traversal_required": True,
    "no_learned_weights": True,
    "no_dynamic_query_selection": True,
    "lag_metadata_usage": "documentation_and_falsification_only",
    "lag_metadata_constraint": (
        "VALI engine MUST NOT use expected_lead_days to tune rolling windows "
        "or entry/exit timing"
    ),
}


class KnowledgeGraphError(ValueError):
    """Raised when local KG handoff artifacts cannot be produced safely."""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KnowledgeGraphError(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise KnowledgeGraphError(f"Invalid JSON file: {path}") from exc
    if not isinstance(data, dict):
        raise KnowledgeGraphError(f"JSON file must contain an object: {path}")
    return data


def _csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except FileNotFoundError as exc:
        raise KnowledgeGraphError(f"Missing CSV file: {path}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text_file(path: Path) -> str:
    return "sha256:" + _sha256_file(path)


def _graph_files(manifest: dict[str, Any]) -> list[str]:
    raw_files = manifest.get("graph_files", manifest.get("files_included"))
    if not isinstance(raw_files, list) or not raw_files:
        raise KnowledgeGraphError("Graph manifest must define a non-empty graph_files list.")
    files: list[str] = []
    for value in raw_files:
        if not isinstance(value, str) or not value.strip():
            raise KnowledgeGraphError("Graph file entries must be non-empty strings.")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise KnowledgeGraphError(f"Graph file path must be relative and local: {value}")
        files.append(value.replace("\\", "/"))
    return files


def compute_graph_hash(graph: Path) -> tuple[dict[str, Any], list[tuple[str, str]], str]:
    """Compute a deterministic provenance hash for a graph manifest."""

    graph = graph.resolve()
    manifest = _load_json(graph)
    file_hashes: list[tuple[str, str]] = []
    for relative in _graph_files(manifest):
        path = graph.parent / relative
        if not path.is_file():
            raise KnowledgeGraphError(f"Graph file listed by manifest does not exist: {relative}")
        file_hashes.append((relative, _sha256_file(path)))
    graph_hash_input = "".join(
        f"{relative}:{digest}\n" for relative, digest in sorted(file_hashes)
    )
    return manifest, file_hashes, "sha256:" + hashlib.sha256(
        graph_hash_input.encode("utf-8")
    ).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _value_present(value: Any) -> bool:
    return value is not None and str(value).strip() not in {"", "TBD", "null", "None"}


def _check(
    check_id: str,
    status: str,
    severity: str,
    scope: str,
    evidence: str,
    blocking: bool = False,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": status,
        "severity": severity,
        "scope": scope,
        "evidence": evidence,
        "blocking": bool(blocking),
    }


def _overall_status(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "fail" and check["blocking"] for check in checks):
        return "fail"
    if any(check["status"] == "unknown" for check in checks):
        return "unknown"
    return "pass"


def _load_graph_parts(graph: Path) -> dict[str, Any]:
    manifest, _, graph_hash = compute_graph_hash(graph)
    root = graph.resolve().parent
    return {
        "manifest": manifest,
        "graph_hash": graph_hash,
        "event_family": _load_json(root / "event_family.v1.json")
        if (root / "event_family.v1.json").is_file()
        else {},
        "review_record": _load_json(root / "REVIEW_RECORD.v1.json")
        if (root / "REVIEW_RECORD.v1.json").is_file()
        else {},
        "concepts": _csv_rows(root / "attention_concepts.v1.csv")
        if (root / "attention_concepts.v1.csv").is_file()
        else [],
        "queries": _csv_rows(root / "attention_queries.v1.csv")
        if (root / "attention_queries.v1.csv").is_file()
        else [],
        "edges": _csv_rows(root / "relationship_edges.v1.csv")
        if (root / "relationship_edges.v1.csv").is_file()
        else [],
    }


def build_preflight_report(graph: Path, checked_at: str | None = None) -> dict[str, Any]:
    """Return a schema-shaped availability-only KG preflight report."""

    parts = _load_graph_parts(graph)
    manifest = parts["manifest"]
    event_family = parts["event_family"]
    queries = parts["queries"]
    checks: list[dict[str, Any]] = [
        _check(
            "preflight.check.graph_manifest_exists",
            "pass",
            "critical",
            str(graph),
            "Graph manifest exists and parses as JSON.",
        ),
        _check(
            "preflight.check.graph_hash_available",
            "pass",
            "critical",
            str(graph),
            "Graph hash computed from declared local graph_files.",
        ),
    ]

    source_present = bool(queries) and all(_value_present(row.get("source")) for row in queries)
    checks.append(
        _check(
            "preflight.check.attention_source_available",
            "pass" if source_present else "unknown",
            "critical" if not source_present else "info",
            "AttentionQuery",
            "Attention query sources are named." if source_present else "Attention query source is missing or unknown.",
            blocking=not source_present,
        )
    )
    documented_time = bool(queries) and all(
        _value_present(row.get("time_window")) and _value_present(row.get("frequency", row.get("search_type")))
        for row in queries
    )
    checks.append(
        _check(
            "preflight.check.point_in_time_availability_documented",
            "pass" if documented_time else "unknown",
            "warning",
            "AttentionQuery",
            "Point-in-time availability fields are populated."
            if documented_time
            else "Point-in-time availability remains TBD or provider-dependent.",
        )
    )
    checks.append(
        _check(
            "preflight.check.revision_behavior_documented",
            "unknown",
            "warning",
            "AttentionSource",
            "Revision semantics are not yet documented for this draft graph.",
        )
    )
    query_fields_present = bool(queries) and all(
        _value_present(row.get("source"))
        and _value_present(row.get("geo"))
        and _value_present(row.get("search_type"))
        for row in queries
    )
    checks.append(
        _check(
            "preflight.check.query_source_geo_frequency_present",
            "pass" if query_fields_present else "unknown",
            "warning",
            "AttentionQuery",
            "Query source, geo, and frequency/search type are populated."
            if query_fields_present
            else "One or more query source/geo/frequency fields are TBD.",
        )
    )
    kalshi = event_family.get("kalshi", {}) if isinstance(event_family, dict) else {}
    has_series = _value_present(kalshi.get("series_ticker"))
    checks.append(
        _check(
            "preflight.check.p_side_market_mapping_present",
            "unknown" if has_series else "fail",
            "warning" if has_series else "critical",
            "EventFamily",
            "Series ticker is present, but event/market mapping remains review-required."
            if has_series
            else "No P-side series or market mapping is present.",
            blocking=not has_series,
        )
    )
    terminal = event_family.get("terminal_measure", {}) if isinstance(event_family, dict) else {}
    checks.append(
        _check(
            "preflight.check.terminal_measure_present",
            "pass" if _value_present(terminal.get("id")) else "fail",
            "critical",
            "TerminalMeasure",
            "Terminal measure is identified."
            if _value_present(terminal.get("id"))
            else "Terminal measure is missing.",
            blocking=not _value_present(terminal.get("id")),
        )
    )
    clear_status = str(event_family.get("clear_horizon_status", ""))
    checks.append(
        _check(
            "preflight.check.clear_horizon_present",
            "unknown" if clear_status else "fail",
            "warning" if clear_status else "critical",
            "ClearHorizon",
            f"Clear Horizon status is {clear_status or 'missing'}.",
            blocking=not bool(clear_status),
        )
    )
    checks.append(
        _check(
            "preflight.check.settlement_source_present",
            "pass" if _value_present(terminal.get("source")) else "unknown",
            "warning",
            "SourceAgency",
            "Settlement source is named."
            if _value_present(terminal.get("source"))
            else "Settlement source remains unknown.",
        )
    )
    for check_id, evidence in (
        (
            "preflight.check.required_timestamps_available",
            "Required observation, availability, cutoff, and settlement timestamps remain review-required.",
        ),
        (
            "preflight.check.historical_market_fields_available",
            "Historical market fields are not inspected by this local schema scaffold.",
        ),
        (
            "preflight.check.depth_availability_classified",
            "Depth availability is classified as unknown; no depth is inferred from volume or trades.",
        ),
    ):
        checks.append(_check(check_id, "unknown", "warning", "Graph", evidence))

    blockers = [
        check["check_id"]
        for check in checks
        if check["blocking"] and check["status"] in {"fail", "unknown"}
    ]
    warnings = [
        check["check_id"]
        for check in checks
        if check["severity"] == "warning" and check["status"] != "pass"
    ]
    return {
        "schema_version": KG_PREFLIGHT_SCHEMA,
        "graph_id": manifest.get("graph_id", "unknown"),
        "graph_hash": parts["graph_hash"],
        "checked_at": checked_at or _utc_now(),
        "overall_status": _overall_status(checks),
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def preflight_graph(graph: Path, out: Path) -> dict[str, Any]:
    payload = build_preflight_report(graph)
    _write_json(out, payload)
    return payload


def _polarity(expected_direction: str) -> int | None:
    lowered = expected_direction.casefold()
    if lowered.startswith("positive"):
        return 1
    if lowered.startswith("negative"):
        return -1
    return None


def _lead_days(row: dict[str, str]) -> list[int]:
    values: list[int] = []
    for key in ("expected_lag_min_days", "expected_lag_max_days"):
        try:
            values.append(int(row.get(key, "")))
        except ValueError:
            values.append(0)
    return values


def _status_value(value: Any) -> str:
    return str(value or "").strip().casefold()


def _is_frozen_graph(parts: dict[str, Any]) -> bool:
    manifest = parts["manifest"]
    event_family = parts["event_family"]
    frozen_statuses = {"frozen"}
    return (
        _status_value(manifest.get("freeze_status")) in frozen_statuses
        or _status_value(manifest.get("status")) in frozen_statuses
        or _status_value(event_family.get("mapping_status")) in frozen_statuses
    )


def _require_frozen_field(value: Any, field: str, failures: list[str]) -> None:
    if not _value_present(value):
        failures.append(field)


def _assert_frozen_graph_required_fields(parts: dict[str, Any]) -> None:
    """Reject frozen graphs that are not complete enough to compile safely."""

    if not _is_frozen_graph(parts):
        return

    failures: list[str] = []
    event_family = parts["event_family"]
    terminal = event_family.get("terminal_measure", {}) if isinstance(event_family, dict) else {}
    kalshi = event_family.get("kalshi", {}) if isinstance(event_family, dict) else {}
    concepts = {str(row.get("concept_id", "")): row for row in parts["concepts"]}

    _require_frozen_field(event_family.get("id"), "event_family.id", failures)
    _require_frozen_field(
        terminal.get("id"),
        "event_family.terminal_measure.id",
        failures,
    )
    _require_frozen_field(
        terminal.get("source"),
        "event_family.terminal_measure.source",
        failures,
    )
    _require_frozen_field(
        event_family.get("clear_horizon_status"),
        "event_family.clear_horizon_status",
        failures,
    )
    _require_frozen_field(
        kalshi.get("series_ticker"),
        "event_family.kalshi.series_ticker",
        failures,
    )

    if not parts["queries"]:
        failures.append("attention_queries")

    for index, query in enumerate(parts["queries"], start=1):
        prefix = f"attention_queries[{index}]"
        for field in ("query_id", "concept_id", "query", "source", "geo", "search_type"):
            _require_frozen_field(query.get(field), f"{prefix}.{field}", failures)
        concept_id = str(query.get("concept_id", ""))
        concept = concepts.get(concept_id)
        if concept is None:
            failures.append(f"{prefix}.concept_id.references_known_concept")
            continue
        polarity = _polarity(str(concept.get("expected_direction", "")))
        if polarity not in {-1, 1}:
            failures.append(f"attention_concepts[{concept_id}].expected_direction")

    if failures:
        joined = ", ".join(failures)
        raise KnowledgeGraphError(
            "Frozen graph is missing required field(s) for compilation: "
            f"{joined}"
        )


def build_compiled_manifest(
    graph: Path,
    preflight: Path,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Return a flat compiled manifest from local graph files and preflight."""

    parts = _load_graph_parts(graph)
    report = _load_json(preflight)
    if report.get("schema_version") != KG_PREFLIGHT_SCHEMA:
        raise KnowledgeGraphError("Preflight report schema_version must be kg_preflight.v1.")
    if report.get("graph_hash") != parts["graph_hash"]:
        raise KnowledgeGraphError(
            "Preflight report graph_hash does not match current graph hash."
        )
    _assert_frozen_graph_required_fields(parts)

    manifest = parts["manifest"]
    event_family = parts["event_family"]
    terminal = event_family.get("terminal_measure", {}) if isinstance(event_family, dict) else {}
    kalshi = event_family.get("kalshi", {}) if isinstance(event_family, dict) else {}
    event_family_id = str(event_family.get("id", manifest.get("graph_id", "unknown")))
    terminal_id = str(terminal.get("id", "TBD"))
    clear_horizon_id = f"clear_horizon:{event_family_id}:v1"
    concepts = {row.get("concept_id", ""): row for row in parts["concepts"]}

    features: list[dict[str, Any]] = []
    for query in parts["queries"]:
        concept_id = str(query.get("concept_id", ""))
        concept = concepts.get(concept_id, {})
        polarity = _polarity(str(concept.get("expected_direction", "")))
        if polarity is None:
            continue
        query_id = str(query.get("query_id", ""))
        risks = [
            risk.strip()
            for risk in str(concept.get("contamination_risk", "")).split(",")
            if risk.strip()
        ]
        features.append(
            {
                "feature_id": f"feature.{event_family_id}.{concept_id}.{query_id}",
                "concept_id": f"attention_concept:{concept_id}",
                "query_id": f"attention_query:{query_id}",
                "source": query.get("source", "TBD") or "TBD",
                "query_text": query.get("query", "TBD") or "TBD",
                "geo": query.get("geo", "TBD") or "TBD",
                "frequency": "daily",
                "polarity": polarity,
                "transform": "log1p",
                "availability_lag": "T-2",
                "missing_policy": "reject_required",
                "required": True,
                "contamination_risks": risks,
                "expected_lead_days": _lead_days(concept),
                "evidence_status": concept.get("evidence_status", "hypothesized") or "hypothesized",
            }
        )

    relationships = [
        {
            "edge_id": edge.get("edge_id", "TBD") or "TBD",
            "from": f"{edge.get('from_type', 'Node')}:{edge.get('from_id', 'TBD')}",
            "to": f"{edge.get('to_type', 'Node')}:{edge.get('to_id', 'TBD')}",
            "relationship": edge.get("relationship", "TBD") or "TBD",
            "expected_direction": edge.get("expected_sign", "TBD") or "TBD",
            "expected_lead_days": _lead_days(edge),
        }
        for edge in parts["edges"]
    ]

    return {
        "schema_version": COMPILED_MANIFEST_SCHEMA,
        "manifest_id": f"compiled:{manifest.get('graph_id', event_family_id)}",
        "created_at": created_at or _utc_now(),
        "source_graph": {
            "graph_id": manifest.get("graph_id", "unknown"),
            "graph_version": manifest.get("version", "v1"),
            "graph_hash": parts["graph_hash"],
            "graph_manifest_path": str(graph.resolve()),
            "freeze_status": manifest.get("freeze_status", manifest.get("status", "unknown")),
            "review_record": manifest.get("review_record", "TBD"),
            "preflight_report_hash": _sha256_text_file(preflight),
            "preflight_schema_version": report.get("schema_version", "unknown"),
        },
        "event_family": {
            "event_family_id": event_family_id,
            "terminal_measure_id": terminal_id,
            "clear_horizon_id": clear_horizon_id,
        },
        "p_side": {
            "markets": [
                {
                    "venue": "kalshi",
                    "series_ticker": kalshi.get("series_ticker", "TBD") or "TBD",
                    "event_ticker": "TBD",
                    "market_ticker": "TBD",
                    "normalized_contract_id": f"normalized_contract:{event_family_id}:v1",
                    "operator": "TBD",
                    "threshold": "TBD",
                    "terminal_measure_id": terminal_id,
                    "settlement_source": terminal.get("source", "TBD") or "TBD",
                    "cutoff_rules": "TBD",
                    "clear_horizon_id": clear_horizon_id,
                    "price_source_policy": "public_executable_prices",
                    "liquidity_policy": "configured_spread_depth_staleness_fee_gates",
                    "depth_availability": "unknown",
                    "exclusion_status": "review_required",
                }
            ]
        },
        "a_side": {
            "composition_policy": "equal_weight",
            "weight_policy": "frozen_equal_weight",
            "features": features,
        },
        "relationships": relationships,
        "falsification_gates": [],
        "claim_boundaries": COMPILED_CLAIM_BOUNDARIES,
        "runtime_constraints": RUNTIME_CONSTRAINTS,
        "preflight_status": report.get("overall_status", "unknown"),
        "preflight_warnings": report.get("warnings", []),
        "compile_note": (
            "Scaffolded manifest only; not validation eligible and not wired to "
            "vali backtest --manifest."
        ),
    }


def compile_graph_manifest(graph: Path, preflight: Path, out: Path) -> dict[str, Any]:
    payload = build_compiled_manifest(graph, preflight)
    _write_json(out, payload)
    return payload
