"""Human-reviewed evidence recommendation and supersession helpers.

This module sits after append-only evidence. It creates governance artifacts for
human review and superseding draft graph versions. It never rejects concepts
automatically, never mutates frozen source graph files, never prunes features by
itself, and never converts validation evidence into alpha or trading readiness.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
from typing import Any

from .evidence import REQUIRED_CLAIM_BOUNDARIES, summarize_evidence
from .handoff import KnowledgeGraphError, _graph_files, _load_json, _utc_now, _write_json, compute_graph_hash


EVIDENCE_REVIEW_SCHEMA = "kg_evidence_review.v1"
SUPERSEDING_GRAPH_SCHEMA = "kg_superseding_graph.v1"

ALLOWED_REVIEW_ACTIONS = (
    "human_review_required",
    "retain_for_research",
    "needs_more_evidence",
    "quarantine_pending_review",
    "revise_in_superseding_version",
    "retire_in_superseding_version",
)

HUMAN_REVIEWED_STATUSES = {"reviewed", "approved"}

FORBIDDEN_RECOMMENDATION_WORDS = (
    "alpha",
    "production",
    "trading_ready",
    "trading-ready",
    "trade_ready",
    "trade-ready",
    "live_trading",
    "order_submission",
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise KnowledgeGraphError(f"Missing KG review file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise KnowledgeGraphError(f"Invalid KG review JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise KnowledgeGraphError(f"KG review file must contain a JSON object: {path}")
    return payload


def _load_recommendations(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = _read_json(path)
    recommendations = payload.get("recommendations", payload.get("actions", payload))
    if not isinstance(recommendations, list):
        raise KnowledgeGraphError("KG review recommendations must be a list.")
    return [dict(item) for item in recommendations]


def _forbidden_text(value: Any) -> str | None:
    text = json.dumps(value, sort_keys=True).casefold()
    for word in FORBIDDEN_RECOMMENDATION_WORDS:
        if word in text:
            return word
    return None


def _validate_recommendation(record: dict[str, Any], reviewer: str | None) -> dict[str, Any]:
    target_id = str(record.get("target_id", "")).strip()
    action = str(record.get("action", "")).strip()
    rationale = str(record.get("rationale", "")).strip()
    review_status = str(record.get("review_status", "")).strip()
    record_reviewer = str(record.get("reviewer", reviewer or "")).strip()

    if not target_id:
        raise KnowledgeGraphError("KG evidence review recommendation target_id is required.")
    if action not in ALLOWED_REVIEW_ACTIONS:
        raise KnowledgeGraphError(
            "KG evidence review action must be one of: "
            + ", ".join(ALLOWED_REVIEW_ACTIONS)
        )
    forbidden = _forbidden_text(
        {
            "action": action,
            "rationale": rationale,
            "review_status": review_status,
            "reviewer": record_reviewer,
        }
    )
    if forbidden:
        raise KnowledgeGraphError(
            f"KG evidence review recommendations must not claim {forbidden!r}."
        )
    if action != "human_review_required":
        if review_status not in HUMAN_REVIEWED_STATUSES:
            raise KnowledgeGraphError(
                "KG evidence review action requires human review_status reviewed or approved."
            )
        if not record_reviewer:
            raise KnowledgeGraphError(
                "KG evidence review action requires an explicit reviewer."
            )
        if not rationale:
            raise KnowledgeGraphError(
                "KG evidence review action requires an explicit rationale."
            )
    return {
        "target_id": target_id,
        "action": action,
        "review_status": review_status or "human_review_required",
        "reviewer": record_reviewer or None,
        "rationale": rationale or "No human recommendation supplied.",
        "automatic_recommendation": False,
        "claim_status": list(REQUIRED_CLAIM_BOUNDARIES),
    }


def _default_review_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    targets = sorted(summary.get("metrics_by_concept", {}))
    if not targets:
        targets = ["unassigned"]
    return [
        {
            "target_id": target,
            "action": "human_review_required",
            "review_status": "human_review_required",
            "reviewer": None,
            "rationale": "No human recommendation supplied.",
            "automatic_recommendation": False,
            "claim_status": list(REQUIRED_CLAIM_BOUNDARIES),
        }
        for target in targets
    ]


def build_evidence_review_packet(
    graph_path: Path,
    *,
    reviewer: str | None = None,
    recommendations: list[dict[str, Any]] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build a human-review packet from append-only evidence.

    If no recommendations are supplied, every target remains
    ``human_review_required``. Supplied recommendations must explicitly carry
    human-reviewed status, reviewer identity, and rationale.
    """

    created_at = created_at or _utc_now()
    summary = summarize_evidence(graph_path)
    _, _, graph_hash = compute_graph_hash(graph_path)
    if recommendations:
        review_rows = [
            _validate_recommendation(record, reviewer)
            for record in recommendations
        ]
    else:
        review_rows = _default_review_rows(summary)

    return {
        "schema_version": EVIDENCE_REVIEW_SCHEMA,
        "created_at": created_at,
        "graph_manifest": str(graph_path),
        "graph_hash": graph_hash,
        "evidence_summary": summary,
        "recommendations": review_rows,
        "human_review_required": True,
        "automatic_recommendations": False,
        "automatic_rejection": False,
        "automatic_graph_version_bump": False,
        "claim_boundaries": list(REQUIRED_CLAIM_BOUNDARIES),
        "review_note": (
            "Human-reviewed governance artifact only; not alpha evidence, "
            "not trading-readiness evidence, and not an automatic decision."
        ),
    }


def write_evidence_review_packet(
    graph_path: Path,
    out: Path,
    *,
    reviewer: str | None = None,
    recommendations_path: Path | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    recommendations = _load_recommendations(recommendations_path)
    packet = build_evidence_review_packet(
        graph_path,
        reviewer=reviewer,
        recommendations=recommendations,
        created_at=created_at,
    )
    _write_json(out, packet)
    return packet


def read_evidence_review_packet(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema_version") != EVIDENCE_REVIEW_SCHEMA:
        raise KnowledgeGraphError(
            f"KG evidence review schema_version must be {EVIDENCE_REVIEW_SCHEMA}."
        )
    if payload.get("automatic_recommendations") is not False:
        raise KnowledgeGraphError("KG evidence review must not contain automatic recommendations.")
    if payload.get("automatic_rejection") is not False:
        raise KnowledgeGraphError("KG evidence review must not contain automatic rejection.")
    if payload.get("automatic_graph_version_bump") is not False:
        raise KnowledgeGraphError("KG evidence review must not bump graph versions automatically.")
    for record in payload.get("recommendations", []):
        _validate_recommendation(record, record.get("reviewer"))
    return payload


def _review_actions_for_supersession(review: dict[str, Any]) -> list[dict[str, Any]]:
    actions = [
        recommendation
        for recommendation in review.get("recommendations", [])
        if recommendation.get("action") in {
            "quarantine_pending_review",
            "revise_in_superseding_version",
            "retire_in_superseding_version",
        }
    ]
    if not actions:
        raise KnowledgeGraphError(
            "Superseding graph creation requires at least one explicit human-reviewed "
            "quarantine/revise/retire action."
        )
    for action in actions:
        _validate_recommendation(action, action.get("reviewer"))
        if action.get("review_status") not in HUMAN_REVIEWED_STATUSES:
            raise KnowledgeGraphError("Superseding graph actions must be human-reviewed.")
    return actions


def create_superseding_graph_version(
    graph_path: Path,
    review_path: Path,
    out_dir: Path,
    *,
    new_graph_id: str | None = None,
    new_version: str = "v2",
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a draft superseding graph copy from explicit human review.

    The source graph files are copied into ``out_dir`` and the copied manifest is
    marked as a draft superseding version. Source graph files are never modified,
    and concept/query rows are not pruned automatically.
    """

    created_at = created_at or _utc_now()
    source_manifest, source_file_hashes, source_graph_hash = compute_graph_hash(graph_path)
    review = read_evidence_review_packet(review_path)
    if review.get("graph_hash") != source_graph_hash:
        raise KnowledgeGraphError(
            "KG evidence review graph_hash does not match source graph hash."
        )
    actions = _review_actions_for_supersession(review)
    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise KnowledgeGraphError(
            "Superseding graph output directory must be empty or absent."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    source_root = graph_path.resolve().parent
    for relative in _graph_files(source_manifest):
        source = source_root / relative
        target = out_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    updated_manifest = deepcopy(source_manifest)
    old_graph_id = str(source_manifest.get("graph_id", "unknown"))
    updated_manifest["graph_id"] = new_graph_id or f"{old_graph_id}:superseding:{new_version}"
    updated_manifest["version"] = new_version
    updated_manifest["status"] = "draft"
    updated_manifest["review_status"] = "human_review_required"
    updated_manifest["freeze_recommendation"] = "not_ready"
    updated_manifest["freeze_status"] = "draft"
    updated_manifest["graph_hash_status"] = "not_computed"
    updated_manifest["graph_hash"] = None
    updated_manifest["frozen_at"] = None
    updated_manifest["frozen_by"] = None
    updated_manifest["supersedes"] = old_graph_id
    updated_manifest["superseded_by"] = None
    updated_manifest["supersession"] = {
        "schema_version": SUPERSEDING_GRAPH_SCHEMA,
        "created_at": created_at,
        "source_graph_manifest": str(graph_path),
        "source_graph_hash": source_graph_hash,
        "source_file_hashes": [
            {"path": path, "sha256": digest}
            for path, digest in source_file_hashes
        ],
        "review_packet": str(review_path),
        "review_packet_schema": review["schema_version"],
        "actions": actions,
        "original_graph_unchanged": True,
        "automatic_pruning": False,
        "automatic_recommendations": False,
        "automatic_graph_version_bump": False,
        "claim_boundaries": list(REQUIRED_CLAIM_BOUNDARIES),
        "note": (
            "Draft superseding graph copy created from explicit human review. "
            "No source graph mutation and no automatic pruning were performed."
        ),
    }
    notes = list(updated_manifest.get("notes", []))
    notes.append(
        "Draft superseding graph copy created from human-reviewed evidence; "
        "not alpha evidence and not trading-readiness evidence."
    )
    updated_manifest["notes"] = notes
    _write_json(out_dir / graph_path.name, updated_manifest)
    return {
        "schema_version": SUPERSEDING_GRAPH_SCHEMA,
        "output_dir": str(out_dir),
        "source_graph_hash": source_graph_hash,
        "new_graph_manifest": str(out_dir / graph_path.name),
        "new_graph_id": updated_manifest["graph_id"],
        "actions": actions,
        "original_graph_unchanged": True,
        "automatic_pruning": False,
        "automatic_recommendations": False,
        "automatic_graph_version_bump": False,
        "claim_boundaries": list(REQUIRED_CLAIM_BOUNDARIES),
    }


__all__ = [
    "ALLOWED_REVIEW_ACTIONS",
    "EVIDENCE_REVIEW_SCHEMA",
    "SUPERSEDING_GRAPH_SCHEMA",
    "build_evidence_review_packet",
    "create_superseding_graph_version",
    "read_evidence_review_packet",
    "write_evidence_review_packet",
]
