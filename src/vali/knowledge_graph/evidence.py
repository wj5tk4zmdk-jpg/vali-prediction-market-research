"""Append-only validation evidence helpers for KG handoff artifacts.

Evidence files created here are descriptive governance artifacts. They do not
mutate frozen graph files, reject hypotheses automatically, run VALI backtests,
or authorize trading.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .handoff import KnowledgeGraphError, _utc_now, _write_json, compute_graph_hash


VALIDATION_EVIDENCE_SCHEMA = "validation_evidence.v1"
VALIDATION_EVIDENCE_SUMMARY_SCHEMA = "validation_evidence_summary.v1"

EVIDENCE_STATUSES = (
    "hypothesized",
    "candidate",
    "not_validated",
    "validated_exploratory",
    "validated_out_of_sample",
    "failed",
    "quarantined",
    "retired",
)

PASSING_EVIDENCE_STATUSES = {
    "validated_exploratory",
    "validated_out_of_sample",
}
FAILING_EVIDENCE_STATUSES = {"failed"}

REQUIRED_CLAIM_BOUNDARIES = (
    "bounded_by_evidence",
    "not_alpha_claim",
    "not_trading_readiness_claim",
)

REQUIRED_EVIDENCE_FIELDS = (
    "id",
    "type",
    "version",
    "source",
    "target_node_ids",
    "metrics",
    "falsification_gate_results",
    "status",
    "claim_status",
    "evidence_status",
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KnowledgeGraphError(f"Missing evidence file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise KnowledgeGraphError(f"Invalid evidence file: {path}") from exc
    if not isinstance(payload, dict):
        raise KnowledgeGraphError(f"Evidence file must contain an object: {path}")
    return payload


def _normalize_claim_status(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [str(item) for item in value]
    else:
        raise KnowledgeGraphError("Validation evidence claim_status must be a string or list.")
    missing = [claim for claim in REQUIRED_CLAIM_BOUNDARIES if claim not in values]
    if missing:
        raise KnowledgeGraphError(
            "Validation evidence claim_status must preserve claim boundaries: "
            + ", ".join(missing)
        )
    return values


def _validate_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise KnowledgeGraphError(f"Validation evidence {field} must be a list.")
    return value


def _validate_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise KnowledgeGraphError(f"Validation evidence {field} must be an object.")
    return value


def _validate_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    missing = [
        field
        for field in REQUIRED_EVIDENCE_FIELDS
        if field not in payload or payload[field] in (None, "")
    ]
    if missing:
        raise KnowledgeGraphError(
            "Validation evidence is missing required field(s): " + ", ".join(missing)
        )
    if payload["type"] != "ValidationEvidence":
        raise KnowledgeGraphError("Validation evidence type must be ValidationEvidence.")
    if payload["version"] != "v1":
        raise KnowledgeGraphError("Validation evidence version must be v1.")

    status = str(payload["status"])
    evidence_status = str(payload["evidence_status"])
    for field, value in (("status", status), ("evidence_status", evidence_status)):
        if value not in EVIDENCE_STATUSES:
            raise KnowledgeGraphError(
                f"Validation evidence {field} must be one of: "
                + ", ".join(EVIDENCE_STATUSES)
            )

    payload = deepcopy(payload)
    payload["source"] = _validate_mapping(payload["source"], "source")
    payload["target_node_ids"] = [
        str(value) for value in _validate_list(payload["target_node_ids"], "target_node_ids")
    ]
    if "target_edge_ids" in payload:
        payload["target_edge_ids"] = [
            str(value)
            for value in _validate_list(payload["target_edge_ids"], "target_edge_ids")
        ]
    payload["metrics"] = _validate_mapping(payload["metrics"], "metrics")
    payload["falsification_gate_results"] = _validate_list(
        payload["falsification_gate_results"],
        "falsification_gate_results",
    )
    payload["claim_status"] = _normalize_claim_status(payload["claim_status"])
    payload.setdefault("schema_version", VALIDATION_EVIDENCE_SCHEMA)
    if payload["schema_version"] != VALIDATION_EVIDENCE_SCHEMA:
        raise KnowledgeGraphError(
            f"Validation evidence schema_version must be {VALIDATION_EVIDENCE_SCHEMA}."
        )
    return payload


def _timestamp_for_filename(timestamp: str) -> str:
    return (
        timestamp.replace("-", "")
        .replace(":", "")
        .replace("+00:00", "Z")
        .replace(".", "")
    )


def _evidence_path(graph_path: Path, timestamp: str) -> Path:
    stem = _timestamp_for_filename(timestamp)
    root = graph_path.resolve().parent
    candidate = root / f"validation_evidence_{stem}.v1.json"
    suffix = 2
    while candidate.exists():
        candidate = root / f"validation_evidence_{stem}_{suffix}.v1.json"
        suffix += 1
    return candidate


def write_evidence(
    evidence_data: dict[str, Any],
    graph_path: Path,
    *,
    created_at: str | None = None,
) -> Path:
    """Write one append-only evidence file beside ``graph_path``.

    The graph manifest and declared graph files are read for provenance only;
    they are never modified by this function.
    """

    created_at = created_at or _utc_now()
    _, _, graph_hash = compute_graph_hash(graph_path)
    payload = _validate_evidence(evidence_data)
    payload["created_at"] = created_at
    payload["graph_manifest"] = graph_path.name
    payload["graph_hash"] = graph_hash
    payload["append_only"] = True
    payload["claim_boundary_note"] = (
        "Validation evidence is descriptive only; it is not alpha evidence, "
        "not trading readiness evidence, and not an automatic rejection."
    )

    path = _evidence_path(graph_path, created_at)
    _write_json(path, payload)
    return path


def append_evidence(
    graph_path: Path,
    evidence_data: dict[str, Any],
    *,
    created_at: str | None = None,
) -> Path:
    """Append evidence for a graph by writing a new immutable evidence file."""

    return write_evidence(evidence_data, graph_path, created_at=created_at)


def read_evidence(evidence_path: Path) -> dict[str, Any]:
    """Read and validate one validation evidence file."""

    return _validate_evidence(_load_json(evidence_path))


def evidence_files(graph_path: Path) -> list[Path]:
    """Return append-only evidence files stored beside a graph manifest."""

    return sorted(graph_path.resolve().parent.glob("validation_evidence_*.v1.json"))


def _numeric_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    numeric: dict[str, float] = {}
    for key, value in metrics.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            numeric[key] = float(value)
    return numeric


def summarize_evidence(graph_path: Path) -> dict[str, Any]:
    """Aggregate append-only evidence files for human review.

    This function deliberately returns descriptive counts and metric summaries
    only. It does not recommend rejection, upgrade claim status, or alter the
    graph.
    """

    _, _, graph_hash = compute_graph_hash(graph_path)
    included: list[dict[str, Any]] = []
    excluded_files: list[str] = []
    for path in evidence_files(graph_path):
        evidence = read_evidence(path)
        if evidence.get("graph_hash") not in {None, graph_hash}:
            excluded_files.append(path.name)
            continue
        evidence["_path"] = path.name
        included.append(evidence)

    status_counts = {status: 0 for status in EVIDENCE_STATUSES}
    metric_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    experiments: list[dict[str, Any]] = []

    for evidence in included:
        status = str(evidence["evidence_status"])
        status_counts[status] += 1
        targets = evidence["target_node_ids"] or ["unassigned"]
        metrics = _numeric_metrics(evidence["metrics"])
        for target in targets:
            for metric, value in metrics.items():
                metric_values[str(target)][metric].append(value)
        experiments.append(
            {
                "id": evidence["id"],
                "status": status,
                "target_node_ids": evidence["target_node_ids"],
                "evidence_file": evidence["_path"],
            }
        )

    metrics_by_concept: dict[str, dict[str, dict[str, float | int]]] = {}
    for target, metrics in sorted(metric_values.items()):
        metrics_by_concept[target] = {}
        for metric, values in sorted(metrics.items()):
            metrics_by_concept[target][metric] = {
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            }

    return {
        "schema_version": VALIDATION_EVIDENCE_SUMMARY_SCHEMA,
        "graph_manifest": str(graph_path),
        "graph_hash": graph_hash,
        "evidence_files": [evidence["_path"] for evidence in included],
        "excluded_evidence_files": excluded_files,
        "total_experiments": len(included),
        "passing_count": sum(
            count for status, count in status_counts.items() if status in PASSING_EVIDENCE_STATUSES
        ),
        "failing_count": sum(
            count for status, count in status_counts.items() if status in FAILING_EVIDENCE_STATUSES
        ),
        "status_counts": status_counts,
        "metrics_by_concept": metrics_by_concept,
        "experiments": experiments,
        "claim_boundaries": list(REQUIRED_CLAIM_BOUNDARIES),
        "summary_note": (
            "Human-review summary only; no automatic rejection, no recommendation, "
            "no alpha claim, and no trading-readiness claim."
        ),
    }


def format_evidence_summary(summary: dict[str, Any]) -> str:
    """Render a compact human-readable evidence summary table."""

    lines = [
        "VALI KG Evidence Summary",
        "========================",
        "",
        f"Graph manifest: {summary['graph_manifest']}",
        f"Graph hash: {summary['graph_hash']}",
        f"Total experiments: {summary['total_experiments']}",
        f"Passing evidence count: {summary['passing_count']}",
        f"Failing evidence count: {summary['failing_count']}",
        "",
        "Status counts",
        "-------------",
        "| status | count |",
        "| --- | ---: |",
    ]
    for status, count in summary["status_counts"].items():
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "Metrics by concept",
            "------------------",
            "| target | metric | count | mean | min | max |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    metrics_by_concept = summary["metrics_by_concept"]
    if metrics_by_concept:
        for target, metrics in metrics_by_concept.items():
            for metric, values in metrics.items():
                lines.append(
                    "| {target} | {metric} | {count} | {mean:.6g} | {min:.6g} | {max:.6g} |".format(
                        target=target,
                        metric=metric,
                        count=values["count"],
                        mean=values["mean"],
                        min=values["min"],
                        max=values["max"],
                    )
                )
    else:
        lines.append("| none | none | 0 | 0 | 0 | 0 |")

    lines.extend(
        [
            "",
            "Claim boundary",
            "--------------",
            "- Append-only evidence summary for human review.",
            "- No automatic rejection or recommendation is made.",
            "- Not alpha evidence and not trading-readiness evidence.",
            "- No private data, proprietary order flow, credentials, live trading, order submission, or P_flow.",
            "",
        ]
    )
    return "\n".join(lines)


def write_evidence_summary(graph_path: Path, out: Path) -> dict[str, Any]:
    """Write a human-readable evidence summary file and return its payload."""

    summary = summarize_evidence(graph_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_evidence_summary(summary), encoding="utf-8", newline="\n")
    return summary


__all__ = [
    "EVIDENCE_STATUSES",
    "REQUIRED_CLAIM_BOUNDARIES",
    "VALIDATION_EVIDENCE_SCHEMA",
    "append_evidence",
    "evidence_files",
    "format_evidence_summary",
    "read_evidence",
    "summarize_evidence",
    "write_evidence",
    "write_evidence_summary",
]
