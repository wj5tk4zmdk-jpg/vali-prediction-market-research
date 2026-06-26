"""Contracts for the offline reviewer-facing VALI research library."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).parents[2]
SUBMISSION = ROOT / "docs" / "submission"
EXPLORER = SUBMISSION / "VALI_EXPLORER.html"
ASSETS = (SUBMISSION / "library.css", SUBMISSION / "library.js")
PUBLIC_FRESH_CLONE_DOCS = (
    ROOT / "README.md",
    ROOT / "ENVIRONMENT.md",
    SUBMISSION / "REVIEWER_GUIDE.md",
    SUBMISSION / "REVIEWER_GUIDE.html",
)
PAGES = {
    "KALSHI_QUANT_RESEARCHER_CASE_STUDY.html": "KALSHI_QUANT_RESEARCHER_CASE_STUDY.md",
    "EMPIRICAL_VALIDATION_PLAN.html": "../operational/5A_EMPIRICAL_VALIDATION_PLAN.md",
    "REGIME_CONFIRMATION_PANEL.html": "REGIME_CONFIRMATION_PANEL.md",
    "DATA_AVAILABILITY_AUDIT.html": (
        "../../experiments/fed_easing_kxfed_v1/DATA_AVAILABILITY_AUDIT.md"
    ),
    "ATTENTION_DATA_ACQUISITION_PROTOCOL.html": (
        "../../experiments/fed_easing_kxfed_v1/ATTENTION_DATA_ACQUISITION_PROTOCOL.md"
    ),
    "KALSHI_RECONSTRUCTION_LEDGER.html": (
        "../../experiments/fed_easing_kxfed_v1/KALSHI_RECONSTRUCTION_LEDGER.md"
    ),
    "FINAL_VALIDATION_REPORT.html": "../../FINAL_VALIDATION_REPORT.md",
    "REVIEWER_GUIDE.html": "REVIEWER_GUIDE.md",
}


class LibraryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.section_count = 0
        self.section_toggles: list[dict[str, str | None]] = []
        self.page_options: list[dict[str, str | None]] = []
        self.search_inputs: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href", ""))
        if tag == "section" and "data-doc-section" in values:
            self.section_count += 1
        if tag == "button" and "section-toggle" in values.get("class", "").split():
            self.section_toggles.append(values)
        if tag == "option" and values.get("value"):
            self.page_options.append(values)
        if tag == "input" and values.get("type") == "search":
            self.search_inputs.append(values)


def _parse(path: Path) -> tuple[str, LibraryParser]:
    text = path.read_text(encoding="utf-8")
    parser = LibraryParser()
    parser.feed(text)
    return text, parser


def test_explorer_routes_all_reviewer_documents_to_html_counterparts():
    _, parser = _parse(EXPLORER)
    document_hrefs = {href for href in parser.hrefs if not href.startswith("#")}
    assert set(PAGES).issubset(document_hrefs)
    assert all(not href.casefold().endswith(".md") for href in document_hrefs)
    assert "REGIME_CONFIRMATION_PANEL.html" in document_hrefs


def test_all_library_pages_exist_with_unique_navigation_and_accessible_controls():
    for filename in PAGES:
        path = SUBMISSION / filename
        assert path.is_file()
        text, parser = _parse(path)
        assert text.startswith("<!doctype html>")
        assert parser.section_count > 0
        assert len(parser.ids) == len(set(parser.ids))
        assert parser.scripts == ["library.js"]
        assert parser.stylesheets == ["library.css"]
        assert len(parser.page_options) == len(PAGES)
        assert sum("selected" in option for option in parser.page_options) == 1
        assert parser.search_inputs == [
            {
                "class": "section-search",
                "id": "section-search",
                "type": "search",
                "placeholder": parser.search_inputs[0]["placeholder"],
            }
        ]
        assert len(parser.section_toggles) == parser.section_count
        assert all(toggle.get("type") == "button" for toggle in parser.section_toggles)
        assert all(toggle.get("aria-controls") for toggle in parser.section_toggles)
        assert all(toggle.get("aria-expanded") == "true" for toggle in parser.section_toggles)
        assert all(toggle.get("aria-label", "").startswith("Collapse ") for toggle in parser.section_toggles)


def test_library_links_are_relative_and_resolve_to_files_or_local_targets():
    for filename in PAGES:
        path = SUBMISSION / filename
        _, parser = _parse(path)
        local_ids = set(parser.ids)
        for href in parser.hrefs:
            parsed = urlparse(href)
            assert not parsed.scheme
            assert not parsed.netloc
            if href.startswith("#"):
                assert href[1:] in local_ids
            else:
                assert not Path(href).is_absolute()
                target = (path.parent / parsed.path).resolve()
                assert target.is_file(), f"Missing target for {filename}: {href}"


def test_each_page_preserves_its_markdown_source_link_and_claim_boundary():
    for filename, source_href in PAGES.items():
        text, parser = _parse(SUBMISSION / filename)
        assert source_href in parser.hrefs
        md_hrefs = [href for href in parser.hrefs if href.casefold().split("#", 1)[0].endswith(".md")]
        assert md_hrefs == [source_href]
        folded = text.casefold()
        for boundary in (
            "no empirical alpha claim",
            "no trading-readiness claim",
            "no private data",
            "proprietary order flow",
            "order submission",
            "live trading",
            "p_flow",
        ):
            assert boundary in folded


def test_confirmation_panel_is_linked_and_preserves_execution_sensitivity_boundaries():
    guide_text, guide_parser = _parse(SUBMISSION / "REVIEWER_GUIDE.html")
    panel_text, panel_parser = _parse(SUBMISSION / "REGIME_CONFIRMATION_PANEL.html")
    assert "REGIME_CONFIRMATION_PANEL.html" in guide_parser.hrefs
    folded = (guide_text + "\n" + panel_text).casefold()
    for phrase in (
        "execution sensitivity",
        "not a new signal",
        "not classifier tuning",
        "not alpha evidence",
        "1/1",
        "1/2",
        "2/1",
        "2/2",
        "3/3",
        "delayed-exit summary",
        "per-trade decomposition",
        "delayed_exits_total",
        "delayed_exits_helped",
        "delayed_exits_hurt",
        "net_delay_pnl",
    ):
        assert phrase in folded
    assert "REGIME_CONFIRMATION_PANEL.md" in panel_parser.hrefs


def test_library_has_no_external_resources_analytics_or_absolute_local_paths():
    for path in [*(SUBMISSION / filename for filename in PAGES), *ASSETS]:
        text = path.read_text(encoding="utf-8")
        folded = text.casefold()
        for forbidden in (
            "https://",
            "http://",
            "fonts.googleapis",
            "googletagmanager",
            "google-analytics.com",
            "c:\\users\\",
            "c:/users/",
        ):
            assert forbidden not in folded


def test_shared_assets_exist_and_include_offline_accessibility_contracts():
    css, javascript = (path.read_text(encoding="utf-8") for path in ASSETS)
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert "@media print" in css
    assert "IntersectionObserver" in javascript
    assert "aria-expanded" in javascript
    assert "window.location.href" in javascript


def test_public_landing_documents_use_reproducible_fresh_clone_commands():
    for path in PUBLIC_FRESH_CLONE_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "work\\.venv" not in text
        assert "work/.venv" not in text
        assert ".[dev]" in text
        assert "-m pytest -q" in text
        assert "-m vali --help" in text

    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dev = ["pytest>=8", "pytest-cov>=5"]' in project
