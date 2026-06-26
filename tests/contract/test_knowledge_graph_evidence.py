"""Contract tests for KG-Handoff Step 3 append-only validation evidence."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from vali.application.commands import main as application_main
from vali.knowledge_graph import compute_graph_hash
from vali.knowledge_graph.evidence import (
    EVIDENCE_STATUSES,
    REQUIRED_CLAIM_BOUNDARIES,
    append_evidence,
    read_evidence,
    summarize_evidence,
)


ROOT = Path(__file__).parents[2]
HORMUZ_ROOT = (
    ROOT / "configs" / "knowledge_graph" / "examples" / "hormuz_normalization"
)
STATUS_VALUES = ROOT / "configs" / "knowledge_graph" / "status_values.v1.json"
SCHEMA_DOC = ROOT / "docs" / "knowledge_graph" / "VALIDATION_EVIDENCE_SCHEMA.v1.md"


def _copy_hormuz_graph(root: Path) -> Path:
    target = root / "hormuz_normalization"
    shutil.copytree(HORMUZ_ROOT, target)
    return target / "graph_manifest.v1.json"


def _evidence(
    evidence_id: str,
    status: str,
    metric_value: float,
    *,
    target: str = "attention_concept:oil_supply_disruption",
) -> dict:
    return {
        "id": evidence_id,
        "type": "ValidationEvidence",
        "version": "v1",
        "source": {
            "experiment_id": f"experiment:{evidence_id}",
            "artifact_hashes": ["sha256:fixture"],
        },
        "target_node_ids": [target],
        "target_edge_ids": [],
        "metrics": {
            "brier_score": metric_value,
            "hit_rate": 1.0 if status != "failed" else 0.0,
            "nonnumeric_note": "ignored by aggregate metrics",
        },
        "falsification_gate_results": [],
        "status": status,
        "claim_status": list(REQUIRED_CLAIM_BOUNDARIES),
        "evidence_status": status,
    }


def _capture(arguments: list[str]) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        application_main(arguments)
    return json.loads(output.getvalue())


class KnowledgeGraphEvidenceTests(unittest.TestCase):
    def test_validation_evidence_schema_doc_names_required_boundaries(self):
        text = SCHEMA_DOC.read_text(encoding="utf-8")
        folded = text.casefold()

        for field in (
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
        ):
            self.assertIn(f"`{field}`", text)
        for status in EVIDENCE_STATUSES:
            self.assertIn(f"`{status}`", text)
        for boundary in REQUIRED_CLAIM_BOUNDARIES:
            self.assertIn(f"`{boundary}`", text)
        for phrase in (
            "append-only",
            "must not modify",
            "no automatic rejection",
            "no recommendation",
            "not alpha",
            "not trading-readiness",
            "no private data",
            "no proprietary order flow",
            "no credentials",
            "no live trading",
            "no order submission",
            "no `p_flow`",
        ):
            self.assertIn(phrase, folded)

    def test_evidence_statuses_match_registry(self):
        registry = json.loads(STATUS_VALUES.read_text(encoding="utf-8"))
        self.assertEqual(
            tuple(registry["approved_values"]["evidence_status"]),
            EVIDENCE_STATUSES,
        )

    def test_append_evidence_does_not_modify_frozen_graph_files(self):
        with TemporaryDirectory() as temporary:
            graph = _copy_hormuz_graph(Path(temporary))
            before_manifest, before_hashes, before_graph_hash = compute_graph_hash(graph)

            evidence_path = append_evidence(
                graph,
                _evidence("validation_evidence:experiment:001", "not_validated", 0.44),
                created_at="2026-06-26T16:00:00Z",
            )
            after_manifest, after_hashes, after_graph_hash = compute_graph_hash(graph)
            payload = read_evidence(evidence_path)

        self.assertEqual(before_manifest, after_manifest)
        self.assertEqual(before_hashes, after_hashes)
        self.assertEqual(before_graph_hash, after_graph_hash)
        self.assertEqual(payload["graph_hash"], before_graph_hash)
        self.assertEqual(payload["graph_manifest"], "graph_manifest.v1.json")
        self.assertTrue(payload["append_only"])
        self.assertEqual(payload["claim_status"], list(REQUIRED_CLAIM_BOUNDARIES))
        self.assertIn("not alpha evidence", payload["claim_boundary_note"])
        self.assertEqual(
            evidence_path.name,
            "validation_evidence_20260626T160000Z.v1.json",
        )

    def test_evidence_summary_aggregates_statuses_and_metrics_by_target(self):
        with TemporaryDirectory() as temporary:
            graph = _copy_hormuz_graph(Path(temporary))
            append_evidence(
                graph,
                _evidence("validation_evidence:experiment:pass", "validated_out_of_sample", 0.20),
                created_at="2026-06-26T16:00:00Z",
            )
            append_evidence(
                graph,
                _evidence("validation_evidence:experiment:fail", "failed", 0.40),
                created_at="2026-06-27T16:00:00Z",
            )

            summary = summarize_evidence(graph)

        self.assertEqual(summary["schema_version"], "validation_evidence_summary.v1")
        self.assertEqual(summary["total_experiments"], 2)
        self.assertEqual(summary["passing_count"], 1)
        self.assertEqual(summary["failing_count"], 1)
        self.assertEqual(summary["status_counts"]["validated_out_of_sample"], 1)
        self.assertEqual(summary["status_counts"]["failed"], 1)
        metrics = summary["metrics_by_concept"]["attention_concept:oil_supply_disruption"]
        self.assertEqual(metrics["brier_score"]["count"], 2)
        self.assertAlmostEqual(metrics["brier_score"]["mean"], 0.30)
        self.assertEqual(metrics["brier_score"]["min"], 0.20)
        self.assertEqual(metrics["brier_score"]["max"], 0.40)
        self.assertEqual(metrics["hit_rate"]["count"], 2)
        self.assertNotIn("nonnumeric_note", metrics)
        self.assertEqual(summary["claim_boundaries"], list(REQUIRED_CLAIM_BOUNDARIES))
        self.assertIn("no automatic rejection", summary["summary_note"])
        self.assertNotIn("recommendations", summary)

    def test_evidence_summary_command_writes_human_readable_table(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            graph = _copy_hormuz_graph(root)
            summary_path = root / "evidence_summary.md"
            append_evidence(
                graph,
                _evidence("validation_evidence:experiment:cli", "validated_exploratory", 0.25),
                created_at="2026-06-26T16:00:00Z",
            )

            stdout = _capture(
                [
                    "kg",
                    "evidence-summary",
                    "--graph",
                    str(graph),
                    "--out",
                    str(summary_path),
                ]
            )
            summary_text = summary_path.read_text(encoding="utf-8")

        self.assertEqual(stdout["output"], str(summary_path))
        self.assertEqual(stdout["total_experiments"], 1)
        self.assertEqual(stdout["passing_count"], 1)
        self.assertEqual(stdout["failing_count"], 0)
        self.assertIn("VALI KG Evidence Summary", summary_text)
        self.assertIn("| validated_exploratory | 1 |", summary_text)
        self.assertIn("| attention_concept:oil_supply_disruption | brier_score | 1 |", summary_text)
        self.assertIn("No automatic rejection or recommendation is made.", summary_text)
        self.assertIn("Not alpha evidence and not trading-readiness evidence.", summary_text)
        self.assertIn("No private data", summary_text)

    def test_invalid_status_and_missing_claim_boundaries_are_rejected(self):
        with TemporaryDirectory() as temporary:
            graph = _copy_hormuz_graph(Path(temporary))
            invalid_status = _evidence("validation_evidence:experiment:bad-status", "failed", 0.4)
            invalid_status["evidence_status"] = "trading_ready"
            with self.assertRaisesRegex(ValueError, "evidence_status must be one of"):
                append_evidence(graph, invalid_status, created_at="2026-06-26T16:00:00Z")

            missing_boundary = _evidence(
                "validation_evidence:experiment:bad-claim",
                "not_validated",
                0.4,
            )
            missing_boundary["claim_status"] = ["bounded_by_evidence"]
            with self.assertRaisesRegex(ValueError, "preserve claim boundaries"):
                append_evidence(graph, missing_boundary, created_at="2026-06-27T16:00:00Z")


if __name__ == "__main__":
    unittest.main()
