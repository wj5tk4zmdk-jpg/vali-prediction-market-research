"""Contract tests for KG-5 knowledge-graph review records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parents[2]
KG_DOCS = ROOT / "docs" / "knowledge_graph"
KG_CONFIG = ROOT / "configs" / "knowledge_graph"
HORMUZ = KG_CONFIG / "examples" / "hormuz_normalization"

REVIEW_DOCS = KG_DOCS / "GRAPH_REVIEW_RECORDS.md"
REVIEW_SCHEMA = KG_CONFIG / "review_record_schema.v1.json"
STATUS_VALUES = KG_CONFIG / "status_values.v1.json"
MANIFEST = HORMUZ / "graph_manifest.v1.json"
REVIEW_RECORD = HORMUZ / "REVIEW_RECORD.v1.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, Any]:
    return json.loads(_read(path))


def test_review_record_docs_schema_and_example_exist_and_parse():
    assert REVIEW_DOCS.is_file()
    assert REVIEW_SCHEMA.is_file()
    assert REVIEW_RECORD.is_file()

    assert _json(REVIEW_SCHEMA)["schema_id"] == "knowledge_graph_review_record"
    assert _json(REVIEW_RECORD)["review_id"] == "review:hormuz_normalization:v1:draft"


def test_review_schema_defines_required_statuses_and_fields():
    schema = _json(REVIEW_SCHEMA)
    statuses = _json(STATUS_VALUES)["approved_values"]

    for field in (
        "review_id",
        "graph_id",
        "graph_version",
        "review_status",
        "reviewed_files",
        "review_checks",
        "claim_boundaries",
        "human_review_required",
        "freeze_recommendation",
    ):
        assert field in schema["required_fields"]

    for status in (
        "draft",
        "review_in_progress",
        "reviewed_with_open_items",
        "approved_for_freeze",
        "blocked",
        "rejected",
    ):
        assert status in schema["allowed_review_statuses"]
        assert status in statuses["review_status"]

    assert "not_ready" in schema["allowed_freeze_recommendations"]
    assert "not_ready" in statuses["freeze_recommendation"]


def test_hormuz_manifest_references_review_record_and_remains_not_ready():
    manifest = _json(MANIFEST)

    assert manifest["review_record"] == "REVIEW_RECORD.v1.json"
    assert "REVIEW_RECORD.v1.json" in manifest["graph_files"]
    assert manifest["review_status"] == "draft"
    assert manifest["freeze_recommendation"] == "not_ready"
    assert manifest["freeze_status"] == "draft"
    assert manifest["graph_hash_status"] == "not_computed"
    assert manifest["graph_hash"] is None
    assert manifest["frozen_at"] is None
    assert manifest["frozen_by"] is None


def test_hormuz_review_record_is_not_approved_for_freeze():
    record = _json(REVIEW_RECORD)

    assert record["review_status"] != "approved_for_freeze"
    assert record["review_status"] == "reviewed_with_open_items"
    assert record["freeze_recommendation"] == "not_ready"
    assert record["freeze_approved"] is False
    assert record["evidence_status"] == "not_validated"
    assert record["human_review_required"] is True
    assert "no_alpha_claim" in record["claim_status"]
    assert "no_trading_readiness_claim" in record["claim_status"]
    assert "research_only" in record["claim_status"]


def test_review_record_has_required_open_items():
    record = _json(REVIEW_RECORD)
    open_items = "\n".join(record["open_items"]).casefold()
    checks = json.dumps(record["review_checks"]).casefold()
    combined = f"{open_items}\n{checks}"

    for required in (
        "contract rules",
        "settlement source",
        "terminal measure",
        "clear horizon",
        "candidate queries",
        "contamination risks",
        "claim boundaries",
    ):
        assert required in combined

    assert "verify whether politicalstat applies" in open_items
    assert "market/date-bucket mapping" in open_items


def test_review_docs_preserve_boundaries_and_do_not_claim_validation():
    docs = _read(REVIEW_DOCS).casefold()

    assert "not empirical validation" in docs
    assert "does not prove alpha" in docs
    assert "does not authorize trading" in docs
    assert "does not prove trading readiness" in docs
    assert "does not replace contract, legal" in docs
    assert "ambiguous fields must remain `review_required` or `blocked`" in docs


def test_review_artifacts_do_not_allow_prohibited_scope():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REVIEW_DOCS, REVIEW_SCHEMA, REVIEW_RECORD, MANIFEST)
    ).casefold()

    for prohibited_allowed_feature in (
        "p_flow allowed",
        "private data allowed",
        "proprietary order flow allowed",
        "credentials allowed",
        "live trading allowed",
        "order submission allowed",
        "authorizes trading",
        "proves alpha",
    ):
        assert prohibited_allowed_feature not in combined

    assert "no `p_flow`" in combined
    assert "no private data" in combined
    assert "no proprietary order flow" in combined
    assert "no credentials" in combined
    assert "no live trading" in combined
    assert "no order submission" in combined
