"""Contract tests for KG-Handoff Step 2 preflight/compile scaffolding."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vali.application.commands import main as application_main
from vali.knowledge_graph import (
    KG_PRECHECKS,
    KnowledgeGraphError,
    compile_graph_manifest,
    preflight_graph,
)


ROOT = Path(__file__).parents[2]
HORMUZ_GRAPH = (
    ROOT
    / "configs"
    / "knowledge_graph"
    / "examples"
    / "hormuz_normalization"
    / "graph_manifest.v1.json"
)


def _capture(arguments: list[str]) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        application_main(arguments)
    return json.loads(output.getvalue())


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class KnowledgeGraphHandoffCommandTests(unittest.TestCase):
    def test_preflight_command_writes_schema_report_for_hormuz_fixture(self):
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / "preflight.json"
            summary = _capture(
                ["kg", "preflight", "--graph", str(HORMUZ_GRAPH), "--out", str(out)]
            )
            report = _load(out)

        self.assertEqual(summary["output"], str(out))
        self.assertEqual(report["schema_version"], "kg_preflight.v1")
        self.assertEqual(report["graph_id"], "example_graph:hormuz_normalization:v1")
        self.assertTrue(report["graph_hash"].startswith("sha256:"))
        self.assertEqual({check["check_id"] for check in report["checks"]}, set(KG_PRECHECKS))
        self.assertEqual(report["claim_boundary"], [
            "availability_only",
            "not_performance_validation",
            "not_alpha_evidence",
            "not_trading_readiness_evidence",
            "public_data_only",
        ])
        self.assertIn(report["overall_status"], {"pass", "unknown", "fail"})
        self.assertNotIn("performance", json.dumps(report["checks"]).casefold())

    def test_compile_command_writes_schema_manifest_for_hormuz_fixture(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            preflight = root / "preflight.json"
            manifest = root / "compiled.json"
            preflight_graph(HORMUZ_GRAPH, preflight)
            summary = _capture(
                [
                    "kg",
                    "compile",
                    "--graph",
                    str(HORMUZ_GRAPH),
                    "--preflight",
                    str(preflight),
                    "--out",
                    str(manifest),
                ]
            )
            payload = _load(manifest)
            preflight_hash = _load(preflight)["graph_hash"]

        self.assertEqual(summary["output"], str(manifest))
        self.assertEqual(payload["schema_version"], "compiled_vali_manifest.v1")
        self.assertEqual(payload["source_graph"]["graph_hash"], preflight_hash)
        self.assertEqual(payload["source_graph"]["preflight_schema_version"], "kg_preflight.v1")
        self.assertEqual(payload["event_family"]["event_family_id"], "maritime_chokepoint_normalization")
        self.assertEqual(payload["runtime_constraints"]["no_learned_weights"], True)
        self.assertEqual(payload["runtime_constraints"]["no_dynamic_query_selection"], True)
        self.assertEqual(payload["runtime_constraints"]["no_graph_traversal_required"], True)
        self.assertEqual(
            payload["runtime_constraints"]["lag_metadata_usage"],
            "documentation_and_falsification_only",
        )
        self.assertIn("no_alpha_claim", payload["claim_boundaries"])
        self.assertIn("no_trading_readiness_claim", payload["claim_boundaries"])
        self.assertIn("public_data_only", payload["claim_boundaries"])
        self.assertTrue(payload["a_side"]["features"])
        self.assertTrue(
            all(
                feature["feature_id"].startswith("feature.maritime_chokepoint_normalization.")
                for feature in payload["a_side"]["features"]
            )
        )
        self.assertEqual(
            {feature["polarity"] for feature in payload["a_side"]["features"]},
            {-1, 1},
        )
        self.assertEqual(payload["p_side"]["markets"][0]["depth_availability"], "unknown")
        self.assertIn("Add explicit runtime_inputs", payload["compile_note"])
        self.assertIn("runtime_parameters", payload["compile_note"])

    def test_compile_rejects_mismatched_preflight_graph_hash(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            preflight = root / "preflight.json"
            manifest = root / "compiled.json"
            report = preflight_graph(HORMUZ_GRAPH, preflight)
            report["graph_hash"] = "sha256:bad"
            preflight.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(KnowledgeGraphError, "graph_hash does not match"):
                compile_graph_manifest(HORMUZ_GRAPH, preflight, manifest)

    def test_compile_rejects_frozen_graph_with_missing_required_fields(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "event_family.v1.json").write_text(
                json.dumps(
                    {
                        "id": "frozen_family",
                        "type": "EventFamily",
                        "version": "v1",
                        "mapping_status": "frozen",
                        "clear_horizon_status": "frozen",
                        "kalshi": {"series_ticker": "KXFROZEN"},
                        "terminal_measure": {
                            "id": "frozen_terminal",
                            "source": "public_settlement_source",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "attention_concepts.v1.csv").write_text(
                "concept_id,event_family_id,concept_name,rationale,expected_direction,expected_lag_min_days,expected_lag_max_days,contamination_risk,evidence_status,human_review_status,claim_status\n"
                "attention_1,frozen_family,Attention 1,Rationale,positive_toward_event,1,3,,hypothesized,approved,research_only\n",
                encoding="utf-8",
            )
            (root / "attention_queries.v1.csv").write_text(
                "query_id,concept_id,query,source,geo,time_window,search_type,evidence_status,human_review_status,claim_status,notes\n"
                "query_1,attention_1,public query,,US,past_5_years,web_search,hypothesized,approved,research_only,source intentionally missing\n",
                encoding="utf-8",
            )
            (root / "relationship_edges.v1.csv").write_text(
                "edge_id,from_type,from_id,relationship,to_type,to_id,expected_sign,expected_lag_min_days,expected_lag_max_days,rationale,evidence_status,human_review_status,claim_status\n",
                encoding="utf-8",
            )
            graph = root / "graph_manifest.v1.json"
            graph.write_text(
                json.dumps(
                    {
                        "graph_id": "example_graph:frozen_missing_source:v1",
                        "version": "v1",
                        "status": "frozen",
                        "freeze_status": "frozen",
                        "review_record": "REVIEW_RECORD.v1.json",
                        "graph_files": [
                            "event_family.v1.json",
                            "attention_concepts.v1.csv",
                            "attention_queries.v1.csv",
                            "relationship_edges.v1.csv",
                            "graph_manifest.v1.json",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            preflight = root / "preflight.json"
            manifest = root / "compiled.json"
            preflight_graph(graph, preflight)

            with self.assertRaisesRegex(
                KnowledgeGraphError,
                "Frozen graph is missing required field",
            ):
                compile_graph_manifest(graph, preflight, manifest)

    def test_compile_handles_empty_optional_graph_fields_without_runtime_wiring(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "event_family.v1.json").write_text(
                json.dumps({"id": "minimal_family", "kalshi": {}}),
                encoding="utf-8",
            )
            (root / "attention_concepts.v1.csv").write_text(
                "concept_id,event_family_id,concept_name,rationale,expected_direction,expected_lag_min_days,expected_lag_max_days,contamination_risk,evidence_status,human_review_status,claim_status\n",
                encoding="utf-8",
            )
            (root / "attention_queries.v1.csv").write_text(
                "query_id,concept_id,query,source,geo,time_window,search_type,evidence_status,human_review_status,claim_status,notes\n",
                encoding="utf-8",
            )
            (root / "relationship_edges.v1.csv").write_text(
                "edge_id,from_type,from_id,relationship,to_type,to_id,expected_sign,expected_lag_min_days,expected_lag_max_days,rationale,evidence_status,human_review_status,claim_status\n",
                encoding="utf-8",
            )
            graph = root / "graph_manifest.v1.json"
            graph.write_text(
                json.dumps(
                    {
                        "graph_id": "example_graph:minimal:v1",
                        "version": "v1",
                        "status": "draft",
                        "freeze_status": "draft",
                        "review_record": "REVIEW_RECORD.v1.json",
                        "graph_files": [
                            "event_family.v1.json",
                            "attention_concepts.v1.csv",
                            "attention_queries.v1.csv",
                            "relationship_edges.v1.csv",
                            "graph_manifest.v1.json",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            preflight = root / "preflight.json"
            manifest = root / "compiled.json"

            preflight_graph(graph, preflight)
            payload = compile_graph_manifest(graph, preflight, manifest)

        self.assertEqual(payload["event_family"]["event_family_id"], "minimal_family")
        self.assertEqual(payload["event_family"]["terminal_measure_id"], "TBD")
        self.assertEqual(payload["a_side"]["features"], [])
        self.assertEqual(payload["p_side"]["markets"][0]["series_ticker"], "TBD")
        self.assertIn("no_P_flow", payload["claim_boundaries"])


if __name__ == "__main__":
    unittest.main()
