"""Contract tests for KG-3 knowledge-graph freeze policy artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parents[2]
KG_DOCS = ROOT / "docs" / "knowledge_graph"
HORMUZ = ROOT / "configs" / "knowledge_graph" / "examples" / "hormuz_normalization"

FREEZE_POLICY = KG_DOCS / "GRAPH_FREEZE_POLICY.md"
FREEZE_CHECKLIST = HORMUZ / "FREEZE_CHECKLIST.v1.md"
HASH_INVENTORY = HORMUZ / "HASH_INVENTORY.v1.md"
GRAPH_MANIFEST = HORMUZ / "graph_manifest.v1.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, Any]:
    return json.loads(_read(path))


def test_freeze_policy_document_exists_and_defines_lifecycle():
    policy = _read(FREEZE_POLICY)

    assert FREEZE_POLICY.is_file()
    for status in (
        "draft",
        "human_review_required",
        "reviewed",
        "frozen",
        "validation_eligible",
        "retired",
        "superseded",
    ):
        assert status in policy
    assert "Draft graph objects are not research inputs" in policy
    assert "Human review is required" in policy


def test_freeze_policy_documents_eligibility_and_hash_policy():
    policy = _read(FREEZE_POLICY).casefold()

    for requirement in (
        "graph manifest exists",
        "all files referenced by the manifest exist",
        "node and edge registries parse",
        "status values parse",
        "template mappings parse",
        "event family object parses",
        "relationship edges identify pre-validation or post-validation phase",
        "clear horizon is identified or marked review-required",
        "terminal measure is identified or marked review-required",
        "settlement source is identified or marked review-required",
    ):
        assert requirement in policy

    for hash_rule in (
        "files are utf-8 text",
        "json files should be serialized with sorted keys",
        "csv files preserve header order and row order",
        "file-level sha256 hashes are acceptable",
        "relative_path:sha256",
        "changing any file in the frozen graph changes the graph hash",
    ):
        assert hash_rule in policy
    assert "not empirical validity" in policy


def test_policy_preserves_hypothesis_and_version_boundaries():
    policy = _read(FREEZE_POLICY).casefold()

    assert "original frozen hypotheses must not be rewritten after outcomes are known" in policy
    assert "validation evidence is appended" in policy
    assert "any material change creates a new version" in policy
    assert "must not quietly alter the frozen graph files" in policy


def test_policy_preserves_claim_and_public_data_boundaries():
    policy = _read(FREEZE_POLICY).casefold()

    for boundary in (
        "no alpha claim",
        "no trading-readiness claim",
        "no private data",
        "no proprietary order flow",
        "no credentials",
        "no live trading",
        "no order submission",
        "no `p_flow`",
    ):
        assert boundary in policy
    assert "without later out-of-sample, execution-aware validation" in policy


def test_hormuz_freeze_checklist_exists_and_keeps_example_unfrozen():
    checklist = _read(FREEZE_CHECKLIST).casefold()

    assert FREEZE_CHECKLIST.is_file()
    assert "draft, human-review-required, not validated, not frozen" in checklist
    assert "not a trading signal" in checklist
    assert "not an alpha claim" in checklist
    assert "not a canonical validation input" in checklist
    assert "verify exact kalshi contract rules" in checklist
    assert "verify settlement source" in checklist
    assert "verify terminal measure" in checklist
    assert "verify clear horizon" in checklist
    assert "confirm no `p_flow`" in checklist
    assert "human-review-required, and not validated" in checklist


def test_hormuz_manifest_references_freeze_policy_and_has_no_hash():
    manifest = _json(GRAPH_MANIFEST)

    assert manifest["freeze_policy"] == "docs/knowledge_graph/GRAPH_FREEZE_POLICY.md"
    assert (
        manifest["freeze_checklist"]
        == "configs/knowledge_graph/examples/hormuz_normalization/FREEZE_CHECKLIST.v1.md"
    )
    assert (
        manifest["hash_inventory"]
        == "configs/knowledge_graph/examples/hormuz_normalization/HASH_INVENTORY.v1.md"
    )
    assert manifest["status"] == "draft"
    assert manifest["freeze_status"] == "draft"
    assert manifest["evidence_status"] == "not_validated"
    assert manifest["human_review_status"] == "review_required"
    assert manifest["graph_hash_status"] == "not_computed"
    assert manifest["graph_hash"] is None
    assert manifest["frozen_at"] is None
    assert manifest["frozen_by"] is None


def test_hormuz_hash_inventory_documents_uncomputed_hashes_only():
    inventory = _read(HASH_INVENTORY).casefold()

    assert HASH_INVENTORY.is_file()
    assert "not_computed" in inventory
    assert "event_family.v1.json" in inventory
    assert "graph_manifest.v1.json" in inventory
    assert "file hashes are for provenance and change" in inventory
    assert "not empirical validity" in inventory
    assert "proof of alpha" in inventory
    assert "trading readiness" in inventory
