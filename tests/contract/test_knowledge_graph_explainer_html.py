"""Contracts for the static VALI Contract Knowledge Graph explainer."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).parents[2]
EXPLAINER = ROOT / "docs" / "knowledge_graph" / "VALI_KNOWLEDGE_GRAPH_EXPLAINER.html"
EXPLORER = ROOT / "docs" / "submission" / "VALI_EXPLORER.html"


class StaticPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.ids: list[str] = []
        self.external_sources: list[str] = []
        self.stylesheet_links = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])
        if tag in {"script", "img", "iframe", "source"} and values.get("src"):
            self.external_sources.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheet_links += 1
            if values.get("href"):
                self.external_sources.append(values["href"])


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_explainer() -> tuple[str, StaticPageParser]:
    text = _read(EXPLAINER)
    parser = StaticPageParser()
    parser.feed(text)
    return text, parser


def test_knowledge_graph_explainer_exists_with_required_content():
    text, parser = _parse_explainer()

    assert EXPLAINER.is_file()
    assert "VALI Contract Knowledge Graph" in text
    assert "From market text to frozen research claims" in text
    for required in (
        "POLITICALSTAT",
        "KXHORMUZNORM",
        "maritime_chokepoint_normalization",
        "TerminalMeasure",
        "Clear Horizon",
        "AttentionConcept",
        "ValidationEvidence",
        "Graph ≠ alpha",
        "Graph ≠ trading authorization",
        "NO P_FLOW",
        "HUMAN REVIEW REQUIRED",
    ):
        assert required in text

    assert {"intro", "ladder", "template", "hormuz", "evidence", "freeze", "future", "references"} <= set(
        parser.ids
    )
    assert len(parser.ids) == len(set(parser.ids))


def test_knowledge_graph_explainer_preserves_claim_boundaries():
    folded = _read(EXPLAINER).casefold()

    assert "not validated" in folded
    assert "the graph does not prove alpha" in folded
    assert "the graph does not authorize trading" in folded
    assert "not a trading signal" in folded
    assert "not runtime input" in folded
    assert "not empirical validation" in folded
    for boundary in (
        "no private data",
        "no proprietary order flow",
        "no credentials",
        "no live trading",
        "no order submission",
        "no p_flow",
    ):
        assert boundary in folded


def test_knowledge_graph_explainer_is_self_contained_and_uses_relative_links():
    text, parser = _parse_explainer()

    assert parser.external_sources == []
    assert parser.stylesheet_links == 0
    for forbidden in ("http://", "https://", "fonts.googleapis", "googletagmanager", "analytics"):
        assert forbidden not in text.casefold()

    ids = set(parser.ids)
    for href in parser.hrefs:
        parsed = urlparse(href)
        assert not parsed.scheme
        assert not parsed.netloc
        if href.startswith("#"):
            assert href[1:] in ids
        else:
            assert not Path(href).is_absolute()
            assert (EXPLAINER.parent / href).resolve().exists()


def test_existing_vali_explorer_links_to_knowledge_graph_explainer():
    explorer = _read(EXPLORER)

    assert "../knowledge_graph/VALI_KNOWLEDGE_GRAPH_EXPLAINER.html" in explorer
    assert "Explore the Contract Knowledge Graph" in explorer
    assert "Contract Knowledge Graph" in explorer or "Knowledge Graph" in explorer
    assert "Design artifact only" in explorer
    assert "not alpha, not trading readiness" in explorer


def test_new_pages_do_not_introduce_forbidden_claims_or_allowed_prohibited_scope():
    combined = "\n".join(
        _read(path)
        for path in (
            EXPLAINER,
            EXPLORER,
            ROOT / "docs" / "submission" / "REVIEWER_GUIDE.md",
            ROOT / "docs" / "submission" / "REVIEWER_GUIDE.html",
        )
    ).casefold()

    for forbidden_claim in (
        "alpha is proven",
        "proves alpha",
        "trading-ready",
        "trading readiness is proven",
        "proves trading readiness",
    ):
        assert forbidden_claim not in combined

    for prohibited_allowed_feature in (
        "p_flow allowed",
        "private data allowed",
        "proprietary order flow allowed",
        "credentials allowed",
        "live trading allowed",
        "order submission allowed",
    ):
        assert prohibited_allowed_feature not in combined
