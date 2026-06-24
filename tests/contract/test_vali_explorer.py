"""Contracts for the self-contained reviewer-facing VALI explorer."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).parents[2]
EXPLORER = ROOT / "docs" / "submission" / "VALI_EXPLORER.html"
FROZEN_HASH = (
    "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a"
)
VALIDATION_BASELINE = "0493e9a"
VALIDATION_RESULT = "186 passed, 0 failed"
REPOSITORY_NAME = "vali-prediction-market-research"
REQUIRED_SECTIONS = {
    "intro",
    "signal-lab",
    "pipeline",
    "guardrails",
    "architecture",
    "evidence",
    "blocker",
    "tour",
}


class ExplorerParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.external_sources: list[str] = []
        self.buttons: list[dict[str, str | None]] = []
        self.stylesheet_links = 0
        self._current_button: dict[str, str | None] | None = None

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
        if tag == "button":
            self._current_button = {
                "type": values.get("type"),
                "pressed": values.get("aria-pressed"),
                "controls": values.get("aria-controls"),
                "scenario": values.get("data-scenario"),
                "module": values.get("data-module"),
                "text": "",
            }
            self.buttons.append(self._current_button)

    def handle_data(self, data: str) -> None:
        if self._current_button is not None:
            self._current_button["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "button":
            self._current_button = None


def _parse() -> tuple[str, ExplorerParser]:
    text = EXPLORER.read_text(encoding="utf-8")
    parser = ExplorerParser()
    parser.feed(text)
    return text, parser


def test_explorer_exists_with_required_sections_and_unique_ids():
    assert EXPLORER.is_file()
    _, parser = _parse()
    assert REQUIRED_SECTIONS.issubset(set(parser.ids))
    assert len(parser.ids) == len(set(parser.ids))


def test_internal_navigation_targets_exist_and_repository_links_are_relative():
    _, parser = _parse()
    ids = set(parser.ids)
    for href in parser.hrefs:
        parsed = urlparse(href)
        assert not parsed.scheme
        assert not parsed.netloc
        if href.startswith("#"):
            assert href[1:] in ids
        else:
            assert not Path(href).is_absolute()
            assert (EXPLORER.parent / href).resolve().is_file()


def test_explorer_is_self_contained_and_has_no_network_resources():
    text, parser = _parse()
    assert parser.external_sources == []
    assert parser.stylesheet_links == 0
    folded = text.casefold()
    for forbidden in (
        "https://",
        "http://",
        "fonts.googleapis",
        "googletagmanager",
        "analytics",
    ):
        assert forbidden not in folded


def test_interactive_controls_have_accessible_state_contracts():
    _, parser = _parse()
    scenarios = [button for button in parser.buttons if button["scenario"]]
    modules = [button for button in parser.buttons if button["module"]]
    assert len(scenarios) == 4
    assert len(modules) == 8
    assert all(button["type"] == "button" for button in scenarios + modules)
    assert all(button["pressed"] in {"true", "false"} for button in scenarios + modules)
    assert all(str(button["text"]).strip() for button in scenarios + modules)
    assert all(button["controls"] == "architecture-detail" for button in modules)


def test_explorer_preserves_claim_boundaries_and_current_blocker():
    text = EXPLORER.read_text(encoding="utf-8")
    folded = text.casefold()
    assert FROZEN_HASH in text
    assert "point-in-time attention history is missing" in folded
    assert "may_proceed_to_5c" in folded
    assert VALIDATION_BASELINE in text
    assert VALIDATION_RESULT in text
    assert REPOSITORY_NAME in text
    assert "clean-clone installation remains pending" in folded
    for boundary in (
        "no empirical alpha claim",
        "no trading-readiness claim",
        "no private kalshi data",
        "order submission",
        "proprietary order flow",
        "`p_flow`",
    ):
        assert boundary in folded
    for disallowed in (
        "vali alpha is proven",
        "vali is trading-ready",
        "vali submits orders",
    ):
        assert disallowed not in folded


def test_explorer_contains_no_local_absolute_path():
    text = EXPLORER.read_text(encoding="utf-8")
    assert "C:\\Users\\" not in text
    assert "C:/Users/" not in text
