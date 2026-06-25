"""Contract tests for the KG-2 lightweight knowledge-graph registry."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parents[2]
KG_CONFIG = ROOT / "configs" / "knowledge_graph"
HORMUZ = KG_CONFIG / "examples" / "hormuz_normalization"

NODE_TYPES = KG_CONFIG / "node_types.v1.json"
EDGE_TYPES = KG_CONFIG / "edge_types.v1.json"
STATUS_VALUES = KG_CONFIG / "status_values.v1.json"
POLITICALSTAT = KG_CONFIG / "politicalstat_template.v1.json"
HORMUZ_MANIFEST = HORMUZ / "graph_manifest.v1.json"
HORMUZ_EVENT_FAMILY = HORMUZ / "event_family.v1.json"
HORMUZ_CONCEPTS = HORMUZ / "attention_concepts.v1.csv"
HORMUZ_QUERIES = HORMUZ / "attention_queries.v1.csv"
HORMUZ_EDGES = HORMUZ / "relationship_edges.v1.csv"


REQUIRED_NODE_TYPES = {
    "KalshiCategory",
    "KalshiTag",
    "KalshiSeries",
    "KalshiEvent",
    "KalshiMarket",
    "ContractTemplate",
    "NormalizedContract",
    "TerminalMeasure",
    "SourceAgency",
    "ComparisonOperator",
    "TimePeriod",
    "ClearHorizon",
    "EventFamily",
    "AttentionConcept",
    "AttentionQuery",
    "AttentionSource",
    "ValidationEvidence",
    "FalsificationGate",
    "ClaimBoundary",
}


REQUIRED_EDGE_TYPES = {
    "belongs_to_category",
    "has_tag",
    "belongs_to_series",
    "contains_event",
    "contains_market",
    "uses_template",
    "normalizes_to",
    "settles_by",
    "uses_source_agency",
    "has_operator",
    "has_threshold",
    "has_time_period",
    "has_clear_horizon",
    "belongs_to_event_family",
    "is_measured_by",
    "likely_leads",
    "likely_lags",
    "proxy_for",
    "contaminates",
    "excluded_from",
    "validated_for",
    "failed_for",
    "requires_human_review",
    "frozen_as",
}


EXPECTED_HORMUZ_CONCEPTS = {
    "oil_supply_disruption",
    "maritime_traffic_disruption",
    "military_escalation",
    "deescalation_or_reopening",
    "settlement_source_awareness",
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _registry_files() -> list[Path]:
    return sorted(KG_CONFIG.rglob("*.json")) + sorted(KG_CONFIG.rglob("*.csv"))


def test_registry_core_files_exist_and_parse():
    for path in (NODE_TYPES, EDGE_TYPES, STATUS_VALUES, POLITICALSTAT):
        assert path.is_file()
        assert _json(path)


def test_registry_contains_required_node_and_edge_types():
    node_registry = _json(NODE_TYPES)
    edge_registry = _json(EDGE_TYPES)

    node_types = {entry["type"] for entry in node_registry["node_types"]}
    edge_types = {entry["relationship"] for entry in edge_registry["edge_types"]}

    assert REQUIRED_NODE_TYPES <= node_types
    assert REQUIRED_EDGE_TYPES <= edge_types
    assert node_registry["documentation_only"] is True
    assert edge_registry["runtime_parsing_supported"] is False


def test_status_registry_contains_required_values():
    statuses = _json(STATUS_VALUES)["approved_values"]

    assert {
        "hypothesized",
        "not_validated",
        "validated_out_of_sample",
        "failed",
    } <= set(statuses["evidence_status"])
    assert "review_required" in statuses["human_review_status"]
    assert "research_only" in statuses["claim_status"]
    assert "private_prohibited" in statuses["data_boundary_status"]


def test_politicalstat_template_registry_captures_operator_semantics_and_boundaries():
    template = _json(POLITICALSTAT)
    operators = template["operator_semantics"]

    assert template["template_type"] == "POLITICALSTAT"
    assert template["human_review_required"] is True
    assert operators["above"]["symbol"] == ">"
    assert operators["below"]["symbol"] == "<"
    assert operators["exactly"]["symbol"] == "="
    assert operators["at_least"]["symbol"] == ">="
    assert "Lower bound inclusive" in operators["between"]["description"]
    assert "no automated legal interpretation" in template["claim_boundaries"]
    assert "no alpha claim" in template["claim_boundaries"]
    assert "no trading-readiness claim" in template["claim_boundaries"]
    assert "Do not claim POLITICALSTAT applies to Hormuz" in template["non_applicability_note"]


def test_hormuz_example_manifest_and_event_family_are_non_validated():
    manifest = _json(HORMUZ_MANIFEST)
    event_family = _json(HORMUZ_EVENT_FAMILY)

    assert manifest["graph_id"] == "example_graph:hormuz_normalization:v1"
    assert manifest["status"] == "draft"
    assert manifest["evidence_status"] == "not_validated"
    assert manifest["human_review_status"] == "review_required"
    assert "no alpha claim" in manifest["claim_boundaries"]
    assert "no trading-readiness claim" in manifest["claim_boundaries"]
    assert "no order submission" in manifest["claim_boundaries"]
    assert "no private data" in manifest["claim_boundaries"]
    assert "no proprietary order flow" in manifest["claim_boundaries"]
    assert "no P_flow" in manifest["claim_boundaries"]

    assert event_family["id"] == "maritime_chokepoint_normalization"
    assert event_family["kalshi"]["series_ticker"] == "KXHORMUZNORM"
    assert event_family["evidence_status"] == "not_validated"
    assert event_family["human_review_status"] == "review_required"
    assert "no_alpha_claim" in event_family["claim_status"]
    assert "no_trading_readiness_claim" in event_family["claim_status"]


def test_hormuz_attention_concepts_and_queries_remain_hypothesized():
    concept_rows = _csv_rows(HORMUZ_CONCEPTS)
    query_rows = _csv_rows(HORMUZ_QUERIES)

    assert {row["concept_id"] for row in concept_rows} == EXPECTED_HORMUZ_CONCEPTS
    assert {row["concept_id"] for row in query_rows} <= EXPECTED_HORMUZ_CONCEPTS

    for row in concept_rows + query_rows:
        assert row["evidence_status"] == "hypothesized"
        assert row["human_review_status"] == "review_required"
        assert row["claim_status"] == "research_only"


def test_hormuz_relationship_edges_are_only_non_validated_theory():
    rows = _csv_rows(HORMUZ_EDGES)

    assert rows
    assert {row["relationship"] for row in rows} >= {"likely_leads", "proxy_for"}
    for row in rows:
        assert row["to_id"] == "hormuz_traffic_normalization"
        assert row["evidence_status"] == "hypothesized"
        assert row["human_review_status"] == "review_required"
        assert row["claim_status"] == "research_only"
        assert not row["evidence_status"].startswith("validated")


def test_registry_files_do_not_make_alpha_or_trading_readiness_claims():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in _registry_files())
    folded = combined.casefold()

    for forbidden_claim in (
        "alpha is proven",
        "alpha proven",
        "proves alpha",
        "trading-ready",
        "trading readiness proven",
        "ready for live trading",
        "eligible for live trading",
    ):
        assert forbidden_claim not in folded


def test_registry_files_do_not_allow_prohibited_inputs_or_live_execution():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in _registry_files())
    folded = combined.casefold()

    for prohibited_allowed_feature in (
        "private data allowed",
        "proprietary order flow allowed",
        "credentials allowed",
        "live trading allowed",
        "order submission allowed",
        "p_flow allowed",
    ):
        assert prohibited_allowed_feature not in folded

    assert "no p_flow" in folded
    assert "no private data" in folded
    assert "no proprietary order flow" in folded
    assert "no order submission" in folded
    assert "no live trading" in folded
