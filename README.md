# VALI — Public-Signal Research Engine for Prediction-Market Resolution Latency

> A public-data prediction-market research engine for testing whether
> behavioral-attention / market-price divergence contains out-of-sample
> resolution information, with leakage controls, walk-forward validation,
> execution-aware caveats, and explicit falsification gates.

Repository identity: **`vali-prediction-market-research`**

Prediction markets aggregate beliefs about future events into prices. VALI
tests a narrower, falsifiable thesis: public attention may sometimes move before
market conviction, creating measurable resolution latency. It represents
Behavioral Attention as `A`, executable market-implied Priced Conviction as `P`,
and tests their signed velocity divergence using only predeclared public inputs.

This repository demonstrates ownership of the full research lifecycle: a typed
Python engine, point-in-time data contracts, label isolation, prior-only
normalization, meeting-grouped walk-forward evaluation, read-only provider
adapters, execution constraints, reproducible artifacts, and an explicit
decision to stop when the empirical data are not yet sufficient.

**[Open the interactive VALI Research Explorer →](docs/submission/VALI_EXPLORER.html)**

## What is complete

- Public-data-only Python research engine and CLI.
- Frozen feature universe and manifest hash:
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
- `A` / `P` divergence, prior-only velocities, regime classification, and
  Clear-Horizon research workflow.
- Leakage controls, physical outcome-label isolation, and deterministic
  characterization tests.
- Event-grouped walk-forward validation with predeclared baselines and
  falsification gates.
- Execution-aware simulation boundaries that disable capacity claims when
  historical depth is absent.
- Decomposed domain, data, configuration, research, artifact, execution,
  provider, and application/CLI layers.
- Read-only public Kalshi KXFED adapter and offline-ready official Google Trends
  boundary.
- Local data-availability audit, Kalshi reconstruction ledger, and attention
  acquisition protocol.

> **Claim boundary**
>
> VALI makes **no empirical alpha claim** and **no trading-readiness claim**.
> It submits no orders, uses no private Kalshi data or proprietary order flow,
> and does not implement `P_flow`. Canonical empirical validation remains
> blocked pending documented point-in-time attention history.

## Current status

- Research-engine MVP: complete.
- 4-series behavior-preserving migration: complete.
- Step 5A pre-analysis plan: complete.
- Step 5B data-availability audit: complete.
- Step 5B-1 remediation protocol: complete.
- Step 5C empirical validation: **not authorized**.
- Submission validation baseline: `0493e9a` on `main`.
- Full deterministic suite: **186 passed, 0 failed**.
- Submission status: **research-engine submission artifact**.
- Clean-clone installation test: **pending**.

The repository contains substantial public Kalshi price history, but historical
order-book depth is unavailable and the only local Google Trends observations
are a three-day fixture. The current remediation manifest therefore records
`may_proceed_to_5C=false`. Honest null, negative, and “not enough data” outcomes
are valid research results here.

## Quickstart

From a fresh clone with Python 3.12 or newer, create an isolated environment,
install the declared development dependencies, run the complete test suite,
and inspect the CLI.

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

The help command does not contact a provider.

Canonical experiment config:
[`configs/experiments/fed_easing_v1.toml`](configs/experiments/fed_easing_v1.toml)

Environment and dependency guidance:
[`ENVIRONMENT.md`](ENVIRONMENT.md)

## Where to look first

For a 2–5 minute review, start with:

1. [`docs/submission/VALI_EXPLORER.html`](docs/submission/VALI_EXPLORER.html)
2. [`docs/submission/REVIEWER_GUIDE.md`](docs/submission/REVIEWER_GUIDE.md)
3. [`docs/submission/KALSHI_QUANT_RESEARCHER_CASE_STUDY.md`](docs/submission/KALSHI_QUANT_RESEARCHER_CASE_STUDY.md)
4. [`docs/submission/ARCHITECTURE_MAP.md`](docs/submission/ARCHITECTURE_MAP.md)
5. [`V0_1_RELEASE_CANDIDATE.md`](V0_1_RELEASE_CANDIDATE.md)
6. [`FINAL_VALIDATION_REPORT.md`](FINAL_VALIDATION_REPORT.md)

## Repository tour

| Area | Review path | Why it matters |
|---|---|---|
| Pre-analysis discipline | [`docs/operational/5A_EMPIRICAL_VALIDATION_PLAN.md`](docs/operational/5A_EMPIRICAL_VALIDATION_PLAN.md) | Hypotheses, baselines, metrics, acceptance thresholds, and claim boundaries are frozen before evaluation. |
| Data honesty | [`experiments/fed_easing_kxfed_v1/DATA_AVAILABILITY_AUDIT.md`](experiments/fed_easing_kxfed_v1/DATA_AVAILABILITY_AUDIT.md) | Shows why fixture readiness is not empirical readiness. |
| Attention blocker | [`experiments/fed_easing_kxfed_v1/ATTENTION_DATA_ACQUISITION_PROTOCOL.md`](experiments/fed_easing_kxfed_v1/ATTENTION_DATA_ACQUISITION_PROTOCOL.md) | Defines acceptable provenance, retrieval, revision, and coverage requirements. |
| Kalshi data | [`experiments/fed_easing_kxfed_v1/KALSHI_RECONSTRUCTION_LEDGER.md`](experiments/fed_easing_kxfed_v1/KALSHI_RECONSTRUCTION_LEDGER.md) | Separates quotes, trades, depth evidence, fixtures, and mixed quarantined captures. |
| Falsifiability | [`docs/operational/FALSIFICATION_GATES.md`](docs/operational/FALSIFICATION_GATES.md) | Specifies conditions that invalidate or falsify the research result. |
| Governance | [`REPOSITORY_POLICY.md`](REPOSITORY_POLICY.md) | Defines public-data, compatibility, data-tier, and artifact rules. |
| Artifact provenance | [`ARTIFACT_INVENTORY.md`](ARTIFACT_INVENTORY.md) | Preserves generated and quarantined material rather than silently deleting it. |

## Research formulation

For prior-only standardized attention and price velocities:

```text
S_t = z(gA_t) - z(gP_t)
M_t = |S_t|
```

`S_t` preserves direction; `M_t` measures divergence magnitude. Regime
classification tests whether attention leads, price leads, the series are
coupled, or the relationship is unstable. The Clear Horizon measures whether a
divergence resolves before the market moves—not merely whether two series are
correlated after the fact.

All empirical claims must remain point-in-time, out of sample, benchmarked
against market probability and prior baselines, and constrained by executable
evidence. See [`AGENTS.md`](AGENTS.md) and
[`docs/methodology/vali-1.0-contract.md`](docs/methodology/vali-1.0-contract.md)
for the governing methodology boundary.
