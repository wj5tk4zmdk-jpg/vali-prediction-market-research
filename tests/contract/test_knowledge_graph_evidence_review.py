"""Contract tests for KG-Handoff Step 5 human-reviewed evidence governance."""

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
from vali.knowledge_graph.evidence import REQUIRED_CLAIM_BOUNDARIES, append_evidence
from vali.knowledge_graph.handoff import KnowledgeGraphError
from vali.knowledge_graph.review import (
    create_superseding_graph_version,
    read_evidence_review_packet,
    write_evidence_review_packet,
)


ROOT = Path(__file__).parents[2]
HORMUZ_ROOT = (
    ROOT / "configs" / "knowledge_graph" / "examples" / "hormuz_normalization"
)
REVIEW_DOC = ROOT / "docs" / "knowledge_graph" / "EVIDENCE_REVIEW_AND_SUPERSESSION.v1.md"


def _copy_hormuz_graph(root: Path) -> Path:
    target = root / "hormuz_normalization"
    shutil.copytree(HORMUZ_ROOT, target)
    return target / "graph_manifest.v1.json"


def _capture(arguments: list[str]) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        application_main(arguments)
    return json.loads(output.getvalue())


def _evidence(target: str, status: str = "failed") -> dict:
    return {
        "id": f"validation_evidence:test:{target}:{status}",
        "type": "ValidationEvidence",
        "version": "v1",
        "source": {
            "experiment_id": "experiment:test",
            "artifact_hashes": ["sha256:test"],
        },
        "target_node_ids": [target],
        "target_edge_ids": [],
        "metrics": {"brier_score": 0.42},
        "falsification_gate_results": [],
        "status": status,
        "claim_status": list(REQUIRED_CLAIM_BOUNDARIES),
        "evidence_status": status,
    }


class KnowledgeGraphEvidenceReviewTests(unittest.TestCase):
    def test_review_schema_doc_preserves_human_review_boundaries(self):
        text = REVIEW_DOC.read_text(encoding="utf-8").casefold()
        for phrase in (
            "kg_evidence_review.v1",
            "human_review_required",
            "automatic_pruning = false",
            "automatic_recommendations = false",
            "automatic_graph_version_bump = false",
            "no automatic rejection",
            "no automatic recommendations",
            "no automatic graph version bumping",
            "no mutation of frozen graph files",
            "no alpha claim",
            "no trading-readiness claim",
            "no `p_flow`",
        ):
            self.assertIn(phrase, text)

    def test_review_packet_defaults_to_human_review_required_without_auto_recommendations(self):
        with TemporaryDirectory() as temporary:
            graph = _copy_hormuz_graph(Path(temporary))
            append_evidence(
                graph,
                _evidence("attention_concept:oil_supply_disruption", "failed"),
                created_at="2026-06-26T16:00:00Z",
            )
            review_path = Path(temporary) / "review.json"
            packet = write_evidence_review_packet(graph, review_path)
            read_back = read_evidence_review_packet(review_path)

        self.assertEqual(packet["schema_version"], "kg_evidence_review.v1")
        self.assertEqual(read_back["schema_version"], "kg_evidence_review.v1")
        self.assertFalse(packet["automatic_recommendations"])
        self.assertFalse(packet["automatic_rejection"])
        self.assertFalse(packet["automatic_graph_version_bump"])
        self.assertEqual(packet["recommendations"][0]["action"], "human_review_required")
        self.assertIsNone(packet["recommendations"][0]["reviewer"])
        self.assertEqual(packet["claim_boundaries"], list(REQUIRED_CLAIM_BOUNDARIES))
        self.assertIn("not alpha evidence", packet["review_note"])

    def test_explicit_review_recommendation_requires_reviewer_status_and_rationale(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            graph = _copy_hormuz_graph(root)
            recommendations = root / "recommendations.json"
            recommendations.write_text(
                json.dumps(
                    {
                        "recommendations": [
                            {
                                "target_id": "attention_concept:oil_supply_disruption",
                                "action": "retire_in_superseding_version",
                                "review_status": "approved",
                                "rationale": "Repeated failed validation evidence in fixture.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            review_path = root / "review.json"
            packet = write_evidence_review_packet(
                graph,
                review_path,
                reviewer="human.reviewer",
                recommendations_path=recommendations,
            )

        self.assertEqual(packet["recommendations"][0]["reviewer"], "human.reviewer")
        self.assertEqual(packet["recommendations"][0]["review_status"], "approved")
        self.assertFalse(packet["recommendations"][0]["automatic_recommendation"])

    def test_invalid_recommendation_cannot_claim_production_or_skip_review(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            graph = _copy_hormuz_graph(root)
            recommendations = root / "recommendations.json"
            recommendations.write_text(
                json.dumps(
                    {
                        "recommendations": [
                            {
                                "target_id": "attention_concept:oil_supply_disruption",
                                "action": "recommended_for_production",
                                "review_status": "approved",
                                "reviewer": "human.reviewer",
                                "rationale": "Forbidden wording.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(KnowledgeGraphError, "action must be one of"):
                write_evidence_review_packet(
                    graph,
                    root / "review.json",
                    recommendations_path=recommendations,
                )

            recommendations.write_text(
                json.dumps(
                    {
                        "recommendations": [
                            {
                                "target_id": "attention_concept:oil_supply_disruption",
                                "action": "retire_in_superseding_version",
                                "review_status": "human_review_required",
                                "rationale": "No reviewer approval yet.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(KnowledgeGraphError, "requires human review_status"):
                write_evidence_review_packet(
                    graph,
                    root / "review.json",
                    recommendations_path=recommendations,
                )

    def test_superseding_graph_copy_preserves_original_and_records_review_actions(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            graph = _copy_hormuz_graph(root)
            before_manifest, before_hashes, before_graph_hash = compute_graph_hash(graph)
            recommendations = root / "recommendations.json"
            recommendations.write_text(
                json.dumps(
                    {
                        "recommendations": [
                            {
                                "target_id": "attention_concept:oil_supply_disruption",
                                "action": "retire_in_superseding_version",
                                "review_status": "approved",
                                "reviewer": "human.reviewer",
                                "rationale": "Fixture failed repeatedly; propose retirement in a draft successor.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            review_path = root / "review.json"
            write_evidence_review_packet(
                graph,
                review_path,
                recommendations_path=recommendations,
            )
            out_dir = root / "superseding"
            result = create_superseding_graph_version(
                graph,
                review_path,
                out_dir,
                new_graph_id="example_graph:hormuz_normalization:v2",
                new_version="v2",
            )
            after_manifest, after_hashes, after_graph_hash = compute_graph_hash(graph)
            new_manifest = json.loads(
                (out_dir / "graph_manifest.v1.json").read_text(encoding="utf-8")
            )
            copied_attention_concepts_exists = (out_dir / "attention_concepts.v1.csv").exists()

        self.assertEqual(before_manifest, after_manifest)
        self.assertEqual(before_hashes, after_hashes)
        self.assertEqual(before_graph_hash, after_graph_hash)
        self.assertTrue(result["original_graph_unchanged"])
        self.assertFalse(result["automatic_pruning"])
        self.assertFalse(result["automatic_recommendations"])
        self.assertFalse(result["automatic_graph_version_bump"])
        self.assertEqual(new_manifest["graph_id"], "example_graph:hormuz_normalization:v2")
        self.assertEqual(new_manifest["version"], "v2")
        self.assertEqual(new_manifest["status"], "draft")
        self.assertEqual(new_manifest["freeze_status"], "draft")
        self.assertEqual(new_manifest["supersedes"], before_manifest["graph_id"])
        self.assertEqual(
            new_manifest["supersession"]["actions"][0]["action"],
            "retire_in_superseding_version",
        )
        self.assertFalse(new_manifest["supersession"]["automatic_pruning"])
        self.assertTrue(copied_attention_concepts_exists)

    def test_review_and_supersede_cli_commands_write_expected_artifacts(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            graph = _copy_hormuz_graph(root)
            recommendations = root / "recommendations.json"
            recommendations.write_text(
                json.dumps(
                    {
                        "recommendations": [
                            {
                                "target_id": "attention_concept:oil_supply_disruption",
                                "action": "revise_in_superseding_version",
                                "review_status": "reviewed",
                                "rationale": "Fixture review requests a draft revision.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            review = root / "review.json"
            review_stdout = _capture(
                [
                    "kg",
                    "review-packet",
                    "--graph",
                    str(graph),
                    "--out",
                    str(review),
                    "--recommendations",
                    str(recommendations),
                    "--reviewer",
                    "human.reviewer",
                ]
            )
            supersede_stdout = _capture(
                [
                    "kg",
                    "supersede",
                    "--graph",
                    str(graph),
                    "--review",
                    str(review),
                    "--out-dir",
                    str(root / "superseding"),
                    "--graph-id",
                    "example_graph:hormuz_normalization:v2",
                ]
            )
            superseding_manifest_exists = Path(
                supersede_stdout["new_graph_manifest"]
            ).exists()

        self.assertEqual(review_stdout["output"], str(review))
        self.assertFalse(review_stdout["automatic_recommendations"])
        self.assertEqual(supersede_stdout["actions"], 1)
        self.assertTrue(supersede_stdout["original_graph_unchanged"])
        self.assertTrue(superseding_manifest_exists)


if __name__ == "__main__":
    unittest.main()
