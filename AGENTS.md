# VALI Repository Governance

This file applies to the entire repository.

## Methodology authority

- VALI 1.0 is authoritative for the core research methodology.
- The core system uses public Behavioral Attention `A` and public, executable
  Priced Conviction `P`.
- Attention velocity is `gA`; price velocity is `gP`; signed divergence is
  `S_t`; divergence magnitude is `M_t = abs(S_t)`.
- Regime classification, Clear Horizon, liquidity filters, walk-forward
  validation, and execution-aware simulation are methodology-critical.

## Prohibited scope

- Do not implement `P_flow` in the core system.
- Do not use proprietary order flow, client data, pending orders, confidential
  venue information, product-launch information, or other non-public desk data.
- Do not add live trading, order submission, production credentials, or order
  management logic.
- Public venue quotes, trades, settlement data, and public order-book snapshots
  may be used only for research, liquidity validation, and execution simulation.

## Research discipline

- All validation must be point-in-time and walk-forward.
- Outcome labels must be physically separated from signal-time tables.
- Data must carry observation time, public availability time, vintage, and
  source provenance where applicable.
- Candidate variables, transformations, polarities, thresholds, and horizons
  must be frozen before evaluation.
- Refactors must preserve existing behavior unless a test-backed methodology
  correction is explicitly approved.
- No alpha claim may be made without out-of-sample, execution-aware results
  that include realistic costs, liquidity, closures, and rejected trades.
- Honest null and negative results are valid research outcomes.

## Artifacts and changes

- `data/raw` is immutable. Normalization belongs in `data/interim`; frozen
  analysis inputs belong in `data/processed`.
- Generated artifacts must not be deleted until they have been inventoried,
  reviewed, and logged as superseded or reproducible.
- Keep changes small and reviewable. Separate governance, tests, data movement,
  methodology corrections, and structural refactors into distinct changes.
- Do not silently alter formulas, sign conventions, fee assumptions, mapping
  rules, or test expectations.

## Codex project layer

- `.codex/PROJECT.md` is the Codex-facing project card for future sessions.
- `.codex/playbooks/` contains task-specific operating guides.
- `.codex/tasks/README.md` contains a reusable task brief template.
- These files are navigational aids only; this `AGENTS.md` file remains the
  repository-wide governance authority.
