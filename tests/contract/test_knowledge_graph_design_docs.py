"""Documentation contracts for the KG-1 knowledge-graph design pass."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[2]
KG_DOCS = ROOT / "docs" / "knowledge_graph"
MAIN = KG_DOCS / "VALI_CONTRACT_KNOWLEDGE_GRAPH.md"
SCHEMA = KG_DOCS / "GRAPH_SCHEMA_SKETCH.md"
HORMUZ = KG_DOCS / "HORMUZ_EVENT_FAMILY_EXAMPLE.md"
POLITICALSTAT = KG_DOCS / "POLITICALSTAT_TEMPLATE_MAPPING.md"
DOCUMENTS = (MAIN, SCHEMA, HORMUZ, POLITICALSTAT)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_knowledge_graph_design_documents_exist():
    assert all(path.is_file() for path in DOCUMENTS)


def test_design_covers_required_nodes_operators_and_examples():
    main = _read(MAIN)
    combined = "\n".join(_read(path) for path in DOCUMENTS)
    folded = combined.casefold()

    assert "POLITICALSTAT" in combined
    assert "KXHORMUZNORM" in combined
    for node in (
        "ContractTemplate",
        "NormalizedContract",
        "TerminalMeasure",
        "ClearHorizon",
        "EventFamily",
        "AttentionConcept",
        "AttentionQuery",
        "ValidationEvidence",
    ):
        assert node in main
    for semantic in (
        "`above` means `>`",
        "`below` means `<`",
        "`exactly` means `=`",
        "`at least` means `>=`",
        "lower-bound inclusive and upper-bound exclusive",
    ):
        assert semantic in main
    assert "human review" in folded


def test_design_freezes_theory_before_appending_evidence():
    combined = "\n".join(_read(path) for path in (MAIN, SCHEMA, HORMUZ))
    folded = combined.casefold()
    assert "pre-validation theory" in folded
    assert "post-validation evidence" in folded
    assert "freeze the graph version" in folded
    assert "graph hash" in folded
    assert "without rewriting the original hypothesis" in folded
    for status in (
        "hypothesized",
        "not_validated",
        "validated_exploratory",
        "validated_out_of_sample",
        "failed",
        "quarantined",
        "retired",
    ):
        assert status in combined


def test_design_preserves_claim_and_public_input_boundaries():
    combined = "\n".join(_read(path) for path in DOCUMENTS)
    folded = combined.casefold()
    for boundary in (
        "does not prove alpha",
        "does not authorize trading",
        "no empirical alpha claim",
        "no trading-readiness claim",
        "no private data",
        "no proprietary order flow",
        "no credentials",
        "no live trading",
        "no order submission",
        "no `p_flow`",
    ):
        assert boundary in folded
    assert "this hormuz example is not empirically validated" in folded
    assert "status: validated_out_of_sample" not in folded
    assert "alpha is proven" not in folded
    assert "trading-ready" not in folded


def test_kg1_is_documentation_only_and_does_not_claim_runtime_support():
    main = _read(MAIN).casefold()
    assert "design-only" in main
    assert "does not mean every kalshi template is operationally" in main
    assert "creates no runtime config" in main
    assert "not automated legal interpretation" in main
