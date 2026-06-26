"""Contract tests for KG-handoff schema-governance documentation."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
KG_DOCS = ROOT / "docs" / "knowledge_graph"

GOVERNANCE = KG_DOCS / "KG_SCHEMA_GOVERNANCE.md"
PREFLIGHT = KG_DOCS / "KG_PREFLIGHT_REPORT_SCHEMA.v1.md"
COMPILED = KG_DOCS / "COMPILED_VALI_MANIFEST_SCHEMA.v1.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json_code_blocks(markdown: str) -> list[dict]:
    blocks = re.findall(r"```json\n(.*?)\n```", markdown, flags=re.DOTALL)
    return [json.loads(block) for block in blocks]


def _example_with_schema(path: Path, schema_version: str) -> dict:
    for block in _json_code_blocks(_read(path)):
        if block.get("schema_version") == schema_version:
            return block
    raise AssertionError(f"Missing JSON example for {schema_version}")


def test_kg_handoff_schema_docs_exist_and_json_examples_parse():
    for path in (GOVERNANCE, PREFLIGHT, COMPILED):
        assert path.is_file()
        assert _read(path).startswith("# ")

    assert _json_code_blocks(_read(PREFLIGHT))
    assert _json_code_blocks(_read(COMPILED))


def test_schema_governance_defines_versioning_lifecycle_and_vali_boundary():
    text = _read(GOVERNANCE).casefold()

    for phrase in (
        "kg_preflight.v1",
        "compiled_vali_manifest.v1",
        "v1 required fields are immutable",
        "breaking changes require a new major version",
        "non-breaking clarifications",
        "draft -> review -> frozen -> retired / superseded",
        "schemas are contracts",
        "not empirical evidence",
        "relationship to vali",
        "vali engine remains responsible",
        "expected lag metadata is not a runtime tuning input",
    ):
        assert phrase in text


def test_preflight_schema_names_required_fields_and_check_suite():
    text = _read(PREFLIGHT)
    folded = text.casefold()

    for required_field in (
        "schema_version",
        "graph_id",
        "graph_hash",
        "checked_at",
        "overall_status",
        "checks",
        "blockers",
        "warnings",
        "claim_boundary",
        "check_id",
        "status",
        "severity",
        "scope",
        "evidence",
        "blocking",
    ):
        assert f"`{required_field}`" in text

    for check_id in (
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
    ):
        assert check_id in text

    for boundary in (
        "availability attestation",
        "not performance validation",
        "not_alpha_evidence",
        "graph hash and preflight hash diverge",
    ):
        assert boundary in folded

    example = _example_with_schema(PREFLIGHT, "kg_preflight.v1")
    assert {
        "availability_only",
        "not_performance_validation",
        "not_alpha_evidence",
    } <= set(example["claim_boundary"])


def test_compiled_manifest_schema_names_required_fields_and_runtime_constraints():
    text = _read(COMPILED)
    folded = text.casefold()

    for required_field in (
        "schema_version",
        "manifest_id",
        "created_at",
        "source_graph",
        "event_family",
        "p_side",
        "a_side",
        "relationships",
        "falsification_gates",
        "claim_boundaries",
        "runtime_constraints",
        "runtime_inputs",
        "runtime_parameters",
        "graph_manifest_path",
        "feature_id",
        "concept_id",
        "query_id",
        "source",
        "query_text",
        "geo",
        "frequency",
        "polarity",
        "transform",
        "availability_lag",
        "missing_policy",
        "required",
        "contamination_risks",
        "expected_lead_days",
    ):
        assert f"`{required_field}`" in text

    for constraint in (
        "no_graph_traversal_required",
        "no_learned_weights",
        "no_dynamic_query_selection",
        "lag_metadata_usage",
        "documentation_and_falsification_only",
        "lag_metadata_constraint",
        "must not use expected_lead_days to tune rolling windows or entry/exit timing",
    ):
        assert constraint in folded

    assert "feature.{event_family}.{concept_id}.{query_id}" in text
    assert "must be exactly `1` or `-1`" in text
    assert "`+1` or `-1`" in text

    example = _example_with_schema(COMPILED, "compiled_vali_manifest.v1")
    runtime = example["runtime_constraints"]
    assert runtime["no_learned_weights"] is True
    assert runtime["no_dynamic_query_selection"] is True
    assert runtime["no_graph_traversal_required"] is True
    assert runtime["lag_metadata_usage"] == "documentation_and_falsification_only"
    assert (
        runtime["lag_metadata_constraint"]
        == "VALI engine MUST NOT use expected_lead_days to tune rolling windows or entry/exit timing"
    )
    assert {
        "no_alpha_claim",
        "no_trading_readiness_claim",
        "public_data_only",
    } <= set(example["claim_boundaries"])


def test_handoff_schemas_preserve_forbidden_behavior_and_claim_boundaries():
    combined = "\n".join(_read(path) for path in (GOVERNANCE, PREFLIGHT, COMPILED))
    folded = combined.casefold()

    for boundary in (
        "no empirical alpha claim",
        "no trading-readiness claim",
        "no private data",
        "no proprietary order flow",
        "no credentials",
        "no live trading",
        "no order submission",
        "no `p_flow`",
        "not alpha evidence",
        "not trading-readiness evidence",
    ):
        assert boundary in folded

    for forbidden_permission in (
        "private data allowed",
        "proprietary order flow allowed",
        "credentials allowed",
        "live trading allowed",
        "order submission allowed",
        "p_flow allowed",
        "alpha is proven",
        "trading-ready",
    ):
        assert forbidden_permission not in folded


def test_handoff_step_documents_runtime_handoff_without_graph_traversal():
    combined = "\n".join(_read(path) for path in (GOVERNANCE, PREFLIGHT, COMPILED))
    folded = combined.casefold()

    for implemented_boundary in (
        "`vali kg preflight`",
        "`vali kg compile`",
        "`vali backtest --manifest`",
        "is implemented",
    ):
        assert implemented_boundary in folded

    for non_implementation_boundary in (
        "does not implement graph parsing",
        "does not implement runtime graph traversal",
        "does not implement provider ingestion",
    ):
        assert non_implementation_boundary in folded
