# VALI Reviewer Guide

## Read this first

1. [`VALI_EXPLORER.html`](VALI_EXPLORER.html) - interactive visual tour of the thesis, safeguards, architecture, and current gate.
2. [`../knowledge_graph/VALI_KNOWLEDGE_GRAPH_EXPLAINER.html`](../knowledge_graph/VALI_KNOWLEDGE_GRAPH_EXPLAINER.html) - static visual tour of the contract knowledge graph design artifact.
3. [`../../README.md`](../../README.md) - thesis, status, and quickstart.
4. [`KALSHI_QUANT_RESEARCHER_CASE_STUDY.html`](KALSHI_QUANT_RESEARCHER_CASE_STUDY.html) - interactive project narrative.
5. [`REGIME_CONFIRMATION_PANEL.html`](REGIME_CONFIRMATION_PANEL.html) - execution-sensitivity panel for EM-2, including the `1/1`, `1/2`, `2/1`, `2/2`, `3/3` grid and delayed-exit summary.
6. [`ARCHITECTURE_MAP.md`](ARCHITECTURE_MAP.md) - code and responsibility map.
7. [`EMPIRICAL_VALIDATION_PLAN.html`](EMPIRICAL_VALIDATION_PLAN.html) - interactive predeclared hypotheses and falsification gates.
8. [`DATA_AVAILABILITY_AUDIT.html`](DATA_AVAILABILITY_AUDIT.html) - interactive evidence for the current stop decision.
9. [`APPLICATION_SUBMISSION_NOTE.md`](APPLICATION_SUBMISSION_NOTE.md) - concise, adaptable application note.
10. [`FINAL_REVIEWER_CHECKLIST.md`](FINAL_REVIEWER_CHECKLIST.md) - final access, validation, and claim-boundary checklist.

## Reproduce the checks

From a fresh clone with Python 3.12 or newer, run the following from the
repository root.

PowerShell:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -e ".[dev]"
& '.\.venv\Scripts\python.exe' -m pytest -q
& '.\.venv\Scripts\python.exe' -m vali --help
```

POSIX shells:

```sh
python3.12 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
./.venv/bin/python -m pytest -q
./.venv/bin/python -m vali --help
```

For environment assumptions, see [`../../ENVIRONMENT.md`](../../ENVIRONMENT.md).

## Current validation identity

- Repository: `vali-prediction-market-research`
- Branch: `main`
- Validated baseline: `0493e9a358e59a491116d3bdf4af529a2ee44e79`
- Full deterministic suite: **186 passed, 0 failed**
- Status: **research-engine submission artifact**
- Clean-clone installation test: **verified** at commit `3f1329e`; see
  [`CLEAN_CLONE_INSTALL_TEST.md`](CLEAN_CLONE_INSTALL_TEST.md)
- Latest regime-confirmation branch verification: **240 passed, 0 failed** on
  the EM-2 execution-sensitivity branch. This is a later implementation check,
  not a replacement for the historical validation identity above.

Canonical empirical validation remains blocked pending documented point-in-time
attention history. Capacity and tradability claims remain disabled because
historical observed depth is unavailable. These validation results establish
software and research-contract integrity. They establish no empirical alpha
claim and no trading-readiness claim.

## What to evaluate

- Does the project prevent label, vintage, normalization, and fold leakage?
- Are variables, transformations, polarities, thresholds, and baselines frozen
  before validation?
- Are walk-forward evaluation and falsification gates predeclared?
- Are execution, depth, fee, capacity, and tradability claims constrained by
  observed evidence?
- Is the regime-confirmation panel clearly framed as an execution sensitivity
  overlay rather than a new signal, classifier tuning, or alpha evidence?
- Is the code organized into production-minded, testable boundaries?
- Are provider transport, normalization, archiving, and orchestration separated?
- Does the project preserve exclusions, null results, and data blockers instead
  of optimizing them away?
- Does the project refuse to overclaim?

## What not to infer

- Do not infer proven alpha.
- Do not infer trading readiness or production trading capability.
- Do not infer access to private Kalshi data or proprietary order flow.
- Do not infer order submission, credentialed trading, or a live production API
  integration.
- Do not infer that deterministic fixtures are empirical evidence.
- Do not infer that the regime-confirmation panel proves the buffer improves
  performance; it is a robustness diagnostic until valid empirical data exist.

## Known caveats

- Point-in-time empirical attention history has not been acquired.
- The canonical Step 5C run remains unauthorized.
- Kalshi raw and normalized captures require controlled tier reconstruction.
- Historical order-book depth is unavailable, so capacity claims are disabled.
- The venue fee model remains provisional.
- The latest outcome requires settlement-eligibility verification.
- Package `0.3.0` and migration label `v0.1` remain intentionally distinct.

Historical integrity and migration records retain original local paths as audit
provenance. Those files are not submission landing pages; this README and every
document in `docs/submission/` use repository-relative paths only.

## Next research step

Acquire an approved, documented point-in-time attention history; reconstruct
the Kalshi market lineage into frozen data tiers; then repeat the Step 5B
availability audit. Step 5C may begin only if that repeated audit passes.

This guide makes no alpha or trading-readiness claim and authorizes no live
collection, order submission, or trading.
