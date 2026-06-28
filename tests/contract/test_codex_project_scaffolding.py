"""Contracts for the Codex project working layer."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
CODEX = ROOT / ".codex"
PROJECT = CODEX / "PROJECT.md"
MANIFEST = CODEX / "project.json"
PLAYBOOKS = CODEX / "playbooks"
TASKS = CODEX / "tasks" / "README.md"
AGENTS = ROOT / "AGENTS.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_codex_project_files_exist_and_manifest_parses():
    assert PROJECT.is_file()
    assert MANIFEST.is_file()
    assert TASKS.is_file()
    for playbook in (
        "python-change.md",
        "docs-change.md",
        "kg-handoff.md",
        "data-artifacts.md",
        "release-check.md",
    ):
        assert (PLAYBOOKS / playbook).is_file()

    payload = json.loads(_read(MANIFEST))
    assert payload["schema_version"] == "codex_project.v1"
    assert payload["package"]["python_package"] == "vali"
    assert payload["package"]["cli"] == "vali"
    assert payload["primary_paths"]["governance"] == "AGENTS.md"


def test_codex_project_preserves_vali_boundaries():
    combined = "\n".join(
        _read(path)
        for path in (
            PROJECT,
            TASKS,
            PLAYBOOKS / "python-change.md",
            PLAYBOOKS / "docs-change.md",
            PLAYBOOKS / "kg-handoff.md",
            PLAYBOOKS / "data-artifacts.md",
            PLAYBOOKS / "release-check.md",
        )
    )
    folded = combined.casefold()

    for boundary in (
        "no `p_flow`",
        "no private data",
        "no proprietary order flow",
        "no credentials",
        "no live trading",
        "no order submission",
        "no alpha claim",
        "no trading-readiness claim",
        "expected lead/lag metadata",
        "must not tune",
    ):
        assert boundary in folded

    for forbidden_claim in (
        "alpha is proven",
        "trading-ready",
        "production trading system",
        "submits orders",
        "uses private kalshi data",
    ):
        assert forbidden_claim not in folded


def test_codex_project_references_core_paths_and_commands_without_local_absolute_paths():
    combined = "\n".join(_read(path) for path in (PROJECT, TASKS, MANIFEST))
    for required in (
        "src/vali",
        "tests",
        "configs",
        "docs/knowledge_graph",
        "vali backtest",
        "vali kg preflight",
        "vali kg compile",
        "vali kg review-packet",
    ):
        assert required in combined

    assert "C:\\Users\\" not in combined
    assert "C:/Users/" not in combined


def test_agents_points_to_codex_project_layer_without_replacing_governance():
    text = _read(AGENTS)
    assert ".codex/PROJECT.md" in text
    assert ".codex/playbooks/" in text
    assert "AGENTS.md` file remains the" in text
