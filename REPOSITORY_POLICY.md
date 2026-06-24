# VALI Repository Policy

This policy describes the repository layout used during the VALI v0.1
migration. `AGENTS.md` and the VALI 1.0 methodology contract remain
authoritative when a policy conflicts.

## Source and imports

- Authoritative Python source lives under `src/vali/`.
- Development and test imports must resolve from `src/vali`, never from a
  generated or quarantined `build/lib` copy.
- Existing compatibility facades remain supported until a separate reviewed
  change explicitly retires them. New boundary packages do not make every
  internal helper a stable public API.

## Data tiers

- `data/raw/` holds immutable public provider responses. Raw records are not
  normalized or rewritten in place.
- `data/interim/` holds normalized provider and source tables.
- `data/processed/` holds frozen, analysis-ready datasets.
- `data/quarantine/` holds data whose provenance, tier, or reproducibility
  requires review. Quarantine is not deletion.

## Reports and artifacts

- `reports/runs/` holds generated research runs.
- `reports/archive/` holds reviewed historical reports intended for retention.
- `reports/quarantine/` holds reports requiring review.
- `artifacts/quarantine/` holds stale builds and generated artifacts pending
  review. Nothing there is an import source.
- Generated artifacts are inventoried before deletion or retirement. See
  `ARTIFACT_INVENTORY.md`.

## Fixtures and compatibility copies

- Committed deterministic fixtures live under `tests/fixtures/` and must not
  depend on live APIs or credentials.
- Older compatibility fixture and config paths may remain while callers still
  rely on them. Retirement requires an explicit, reviewed compatibility change.

## Research boundary

VALI contains no live trading, order submission, credentials, private inputs,
proprietary order flow, or `P_flow`. Public venue data may be used only for
research, liquidity validation, and execution simulation under the repository
governance rules.
