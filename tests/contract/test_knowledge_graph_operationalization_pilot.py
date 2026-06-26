"""Contracts for the KG-Handoff operationalization pilot documentation."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[2]
GUIDE = ROOT / "docs" / "knowledge_graph" / "RESEARCHER_GUIDE.md"
FRICTION = ROOT / "docs" / "knowledge_graph" / "OPERATIONALIZATION_PILOT_FRICTION_LOG.md"
PILOT_RECORD = ROOT / "reports" / "kg_handoff_pilot" / "HORMUZ_DRAFT_PILOT_RUN.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_operationalization_pilot_documents_exist():
    assert GUIDE.is_file()
    assert FRICTION.is_file()
    assert PILOT_RECORD.is_file()


def test_hormuz_pilot_records_runtime_input_blocker_without_empirical_claims():
    combined = "\n".join(_read(path) for path in (FRICTION, PILOT_RECORD))
    folded = combined.casefold()

    for phrase in (
        "missing `runtime_inputs`",
        "compiled manifest is missing object field: runtime_inputs",
        "compileable but not runnable",
        "no hormuz events, quotes, trades, or point-in-time attention observations were invented",
        "no empirical result was produced",
    ):
        assert phrase in folded

    for boundary in (
        "does not validate the hormuz hypothesis",
        "does not prove alpha",
        "does not prove trading readiness",
        "does not authorize trading",
        "no private data",
        "proprietary order flow",
        "order submission",
        "`p_flow`",
    ):
        assert boundary in folded


def test_researcher_guide_preserves_handoff_workflow_and_boundaries():
    text = _read(GUIDE)
    folded = text.casefold()

    for command in (
        "vali kg preflight",
        "vali kg compile",
        "vali backtest",
        "--manifest",
        "vali kg evidence-summary",
        "vali kg review-packet",
        "vali kg supersede",
    ):
        assert command in text

    for phrase in (
        "no runtime graph traversal",
        "no learned weights",
        "no dynamic query selection",
        "expected lead/lag metadata is documentation and falsification metadata only",
        "runtime_inputs.events",
        "runtime_parameters.market",
        "do not patch around this by inventing data",
        "supersession is a governance action",
    ):
        assert phrase in folded

    for forbidden_claim in (
        "alpha is proven",
        "trading-ready",
        "production trading system",
        "submits orders",
    ):
        assert forbidden_claim not in folded


def test_compile_note_now_points_to_runtime_inputs_not_unimplemented_backtest():
    from vali.knowledge_graph.handoff import build_compiled_manifest, preflight_graph

    graph = ROOT / "configs" / "knowledge_graph" / "examples" / "hormuz_normalization" / "graph_manifest.v1.json"
    preflight = ROOT / ".pytest_cache" / "kg_pilot_preflight.json"
    preflight.parent.mkdir(exist_ok=True)
    preflight_graph(graph, preflight)
    manifest = build_compiled_manifest(graph, preflight)
    note = manifest["compile_note"]

    assert "runtime_inputs" in note
    assert "runtime_parameters" in note
    assert "not wired to vali backtest --manifest" not in note
