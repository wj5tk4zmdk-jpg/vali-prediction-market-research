"""Contract tests for the KG-4 standalone graph hash utility."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
UTILITY = ROOT / "tools" / "knowledge_graph" / "compute_graph_hash.py"
MANIFEST = ROOT / "configs" / "knowledge_graph" / "examples" / "hormuz_normalization" / "graph_manifest.v1.json"
HASH_DOC = ROOT / "docs" / "knowledge_graph" / "GRAPH_HASH_UTILITY.md"


EXPECTED_GRAPH_FILES = {
    "event_family.v1.json",
    "attention_concepts.v1.csv",
    "attention_queries.v1.csv",
    "relationship_edges.v1.csv",
    "graph_manifest.v1.json",
    "REVIEW_RECORD.v1.json",
}


def _run_hash_utility() -> str:
    completed = subprocess.run(
        [sys.executable, str(UTILITY), str(MANIFEST)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_hash_utility_exists_and_manifest_lists_graph_files():
    assert UTILITY.is_file()
    assert HASH_DOC.is_file()

    manifest = _manifest()
    assert set(manifest["graph_files"]) == EXPECTED_GRAPH_FILES
    assert manifest["freeze_status"] == "draft"
    assert manifest["graph_hash_status"] == "not_computed"


def test_hash_utility_runs_and_outputs_expected_files_and_hash():
    output = _run_hash_utility()

    assert "Graph manifest:" in output
    assert "Graph status: draft" in output
    assert "Graph hash status: not_computed" in output
    assert "Graph hash:" in output
    for graph_file in EXPECTED_GRAPH_FILES:
        assert graph_file in output

    hash_lines = [line.strip() for line in output.splitlines() if len(line.strip()) == 64]
    assert hash_lines
    assert all(set(line) <= set("0123456789abcdef") for line in hash_lines)


def test_hash_utility_output_is_deterministic_across_runs():
    assert _run_hash_utility() == _run_hash_utility()


def test_hash_utility_warns_hash_is_not_evidence_or_trading_authority():
    output = _run_hash_utility().casefold()

    assert "does not prove empirical validity" in output
    assert "does not prove alpha" in output
    assert "does not authorize trading" in output


def test_hash_utility_read_only_mode_does_not_modify_manifest():
    before = MANIFEST.read_bytes()
    _run_hash_utility()
    after = MANIFEST.read_bytes()

    assert after == before


def test_hormuz_manifest_remains_draft_not_frozen_and_non_validated():
    manifest = _manifest()

    assert manifest["status"] == "draft"
    assert manifest["freeze_status"] == "draft"
    assert manifest["evidence_status"] == "not_validated"
    assert manifest["human_review_status"] == "review_required"
    assert manifest["graph_hash_status"] == "not_computed"
    assert manifest["graph_hash"] is None
    assert manifest["frozen_at"] is None
    assert manifest["frozen_by"] is None
    assert "This is not a trading signal." in manifest["notes"]


def test_hash_utility_docs_do_not_allow_prohibited_scope():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            UTILITY,
            HASH_DOC,
            ROOT / "docs" / "knowledge_graph" / "GRAPH_FREEZE_POLICY.md",
            MANIFEST,
        )
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

    assert "does not implement `p_flow`" in combined
    assert "does not inspect private data" in combined
    assert "does not use proprietary order flow" in combined
    assert "does not perform live trading or order submission" in combined
