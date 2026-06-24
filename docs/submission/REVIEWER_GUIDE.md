# VALI Reviewer Guide

## Read this first

1. [`VALI_EXPLORER.html`](VALI_EXPLORER.html) — interactive visual tour of the thesis, safeguards, architecture, and current gate.
2. [`../../README.md`](../../README.md) — thesis, status, and quickstart.
3. [`KALSHI_QUANT_RESEARCHER_CASE_STUDY.html`](KALSHI_QUANT_RESEARCHER_CASE_STUDY.html) — interactive project narrative.
4. [`ARCHITECTURE_MAP.md`](ARCHITECTURE_MAP.md) — code and responsibility map.
5. [`EMPIRICAL_VALIDATION_PLAN.html`](EMPIRICAL_VALIDATION_PLAN.html) — interactive predeclared hypotheses and falsification gates.
6. [`DATA_AVAILABILITY_AUDIT.html`](DATA_AVAILABILITY_AUDIT.html) — interactive evidence for the current stop decision.

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
- Clean-clone installation test: **pending**

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
