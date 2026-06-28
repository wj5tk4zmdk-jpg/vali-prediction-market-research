# VALI Codex Project

Status: Codex working context for the VALI Python research repository.

This directory is a navigation and operating layer for Codex sessions. It does
not replace `AGENTS.md`, `README.md`, or the methodology documents. When in
doubt, `AGENTS.md` and VALI 1.0 are authoritative.

## Project identity

- Repository: `vali-prediction-market-research`
- Python package: `vali-research`
- Source root: `src/vali/`
- CLI entry point: `vali`
- Python version: 3.12+
- Current role: offline, public-data-only VALI research engine.

## Core thesis

VALI tests whether public Behavioral Attention `A` and public/executable
Priced Conviction `P` can expose resolution latency in prediction markets.

Core quantities:

```text
gA_t = attention velocity
gP_t = priced-conviction velocity
S_t  = z(gA_t) - z(gP_t)
M_t  = abs(S_t)
```

The engine must remain point-in-time, walk-forward, public-data-only, and
execution-aware.

## Non-negotiable boundaries

Do not introduce:

- `P_flow`;
- private inputs;
- proprietary order flow;
- client data;
- pending orders;
- product-launch information;
- credentials;
- live trading;
- order submission;
- production order-management logic;
- no alpha claim;
- no trading-readiness claim.

Expected lead/lag metadata in the knowledge graph is documentation and
falsification metadata only. It must not tune VALI runtime windows, thresholds,
entries, exits, sizing, or execution timing.

## Install and test

PowerShell:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e ".[dev]"
& '.\.venv\Scripts\python.exe' -m pytest -q
& '.\.venv\Scripts\python.exe' -m vali --help
```

POSIX:

```sh
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
./.venv/bin/python -m pytest -q
./.venv/bin/python -m vali --help
```

In this workspace, the known local test command is:

```powershell
.\work\.venv\Scripts\python.exe -m pytest -q
```

## Where to work

| Purpose | Path |
|---|---|
| CLI/application orchestration | `src/vali/application/` |
| Methodology math | `src/vali/domain/` |
| Signals/decisions/regimes compatibility facades | `src/vali/signals.py`, `src/vali/decisions.py`, `src/vali/regimes.py` |
| Backtest and execution simulation | `src/vali/backtest.py`, `src/vali/execution/` |
| Configuration contracts | `src/vali/configuration/` |
| Data contracts and validation | `src/vali/data/`, `src/vali/io.py` |
| Provider adapters | `src/vali/providers/` |
| Knowledge graph handoff | `src/vali/knowledge_graph/` |
| Tests | `tests/` |
| Submission/reviewer docs | `docs/submission/` |
| KG docs | `docs/knowledge_graph/` |
| Reports | `reports/` |

## Important commands

```powershell
.\work\.venv\Scripts\python.exe -m vali --help
.\work\.venv\Scripts\python.exe -m vali sample-data --out outputs\sample
.\work\.venv\Scripts\python.exe -m vali validate --config configs\experiments\fed_easing_v1.toml
.\work\.venv\Scripts\python.exe -m vali backtest --config configs\experiments\fed_easing_v1.toml --out reports\runs\local
.\work\.venv\Scripts\python.exe -m vali confirmation-panel --config configs\experiments\fed_easing_v1.toml --out reports\runs\confirmation_panel
```

Knowledge graph workflow:

```powershell
.\work\.venv\Scripts\python.exe -m vali kg preflight --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json --out outputs\kg_preflight.json
.\work\.venv\Scripts\python.exe -m vali kg compile --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json --preflight outputs\kg_preflight.json --out outputs\compiled_manifest.json
.\work\.venv\Scripts\python.exe -m vali backtest --manifest outputs\compiled_manifest.json --out outputs\kg_backtest
.\work\.venv\Scripts\python.exe -m vali kg evidence-summary --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json --out outputs\evidence_summary.md
.\work\.venv\Scripts\python.exe -m vali kg review-packet --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json --out outputs\review_packet.json
```

The current Hormuz draft graph is compileable but not runnable until explicit
`runtime_inputs` and `runtime_parameters` are supplied.

## Current operational blockers

- Canonical empirical validation is blocked pending point-in-time attention
  history.
- Historical order-book depth is not reconstructed from volume or open
  interest.
- Hormuz KG draft is a workflow pilot fixture, not an empirical dataset.

## Codex playbooks

Use the playbooks in `.codex/playbooks/`:

- `python-change.md` for source changes;
- `docs-change.md` for documentation/reviewer artifacts;
- `kg-handoff.md` for knowledge-graph work;
- `data-artifacts.md` for data/report artifact handling;
- `release-check.md` before commit/push handoff.

## Stop rules

Stop and report rather than guessing when a task would require:

- missing data to be invented;
- external credentials;
- live trading or order submission;
- a methodology formula change;
- a new alpha/trading-readiness claim;
- deleting or rewriting generated artifacts without inventory.
