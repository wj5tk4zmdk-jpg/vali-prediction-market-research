"""Reviewer-facing documentation contracts for Submission Polish Pass S1."""

from __future__ import annotations

from pathlib import Path

from vali.providers.google_trends import (
    load_query_manifest,
    query_manifest_sha256,
)


ROOT = Path(__file__).parents[2]
README = ROOT / "README.md"
SUBMISSION = ROOT / "docs" / "submission"
CASE_STUDY = SUBMISSION / "KALSHI_QUANT_RESEARCHER_CASE_STUDY.md"
GUIDE = SUBMISSION / "REVIEWER_GUIDE.md"
BLURBS = SUBMISSION / "RESUME_BLURBS.md"
ARCHITECTURE = SUBMISSION / "ARCHITECTURE_MAP.md"
VALIDATION_REPORT = ROOT / "FINAL_VALIDATION_REPORT.md"
RELEASE_CANDIDATE = ROOT / "V0_1_RELEASE_CANDIDATE.md"
EXPLORER = SUBMISSION / "VALI_EXPLORER.html"
VALIDATION_BASELINE = "0493e9a358e59a491116d3bdf4af529a2ee44e79"
VALIDATION_RESULT = "186 passed, 0 failed"
FROZEN_HASH = (
    "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_submission_documents_exist():
    assert CASE_STUDY.is_file()
    assert GUIDE.is_file()
    assert BLURBS.is_file()
    assert ARCHITECTURE.is_file()


def test_readme_exposes_status_quickstart_and_canonical_experiment():
    readme = _read(README)
    folded = readme.casefold()
    assert "no empirical alpha claim" in folded
    assert "no trading-readiness claim" in folded
    assert "configs/experiments/fed_easing_v1.toml" in readme
    assert "python -m venv .venv" in readme
    assert ".\\.venv\\Scripts\\python.exe' -m pip install -e \".[dev]\"" in readme
    assert ".\\.venv\\Scripts\\python.exe' -m pytest -q" in readme
    assert "./.venv/bin/python -m pytest -q" in readme
    assert FROZEN_HASH in readme
    assert "docs/submission/REVIEWER_GUIDE.md" in readme


def test_submission_pack_covers_research_discipline_and_blocker():
    combined = "\n".join(
        _read(path) for path in (README, CASE_STUDY, GUIDE, BLURBS)
    ).casefold()
    for concept in (
        "public-data-only",
        "leakage controls",
        "walk-forward",
        "falsification gates",
        "point-in-time attention history",
    ):
        assert concept in combined


def test_submission_pack_makes_no_affirmative_operational_claims():
    combined = "\n".join(
        _read(path)
        for path in (README, CASE_STUDY, GUIDE, BLURBS, ARCHITECTURE)
    )
    folded = combined.casefold()
    for required_boundary in (
        "no alpha claim",
        "no trading-readiness claim",
        "no private kalshi data",
        "no order submission",
    ):
        assert required_boundary in folded
    assert "does not implement `p_flow`" in folded
    for disallowed_assertion in (
        "VALI alpha is proven",
        "VALI is trading-ready",
        "VALI is a production trading system",
        "VALI submits orders",
        "VALI uses private Kalshi data",
        "VALI uses proprietary order flow",
        "VALI implements P_flow",
    ):
        assert disallowed_assertion not in combined

    current_docs = (
        README,
        GUIDE,
        VALIDATION_REPORT,
        RELEASE_CANDIDATE,
        EXPLORER,
    )
    for path in current_docs:
        text = _read(path)
        normalized = " ".join(text.casefold().split())
        assert VALIDATION_RESULT in text
        assert "main" in normalized
        assert "research-engine submission artifact" in normalized
        assert "no empirical alpha claim" in normalized or "no alpha claim" in normalized
        assert "no trading-readiness claim" in normalized
        for affirmative_claim in (
            "we conclude vali alpha is proven",
            "submission status: proven alpha",
            "vali is trading-ready.",
            "submission status: trading-ready",
        ):
            assert affirmative_claim not in normalized
        assert "C:\\Users\\" not in text
        assert "C:/Users/" not in text
        assert "work\\.venv" not in text
        assert "work/.venv" not in text

    assert VALIDATION_BASELINE in _read(VALIDATION_REPORT)
    assert VALIDATION_BASELINE in _read(RELEASE_CANDIDATE)
    for stale in (
        "149 passed",
        "155 passed",
        "161 passed",
        "167 passed",
        "185 passed",
    ):
        assert all(stale not in _read(path) for path in current_docs)


def test_submission_facing_docs_contain_no_local_absolute_path():
    for path in (README, CASE_STUDY, GUIDE, BLURBS, ARCHITECTURE):
        text = _read(path)
        assert "C:\\Users\\" not in text
        assert "C:/Users/" not in text


def test_frozen_manifest_hash_is_unchanged():
    manifest = ROOT / "configs" / "features" / "google_trends_candidate_v1.csv"
    assert query_manifest_sha256(load_query_manifest(manifest)) == FROZEN_HASH
