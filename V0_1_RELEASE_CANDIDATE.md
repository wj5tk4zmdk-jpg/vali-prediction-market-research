# VALI v0.1 Migration Release Candidate

## A. Release candidate identity

- Release label: **VALI v0.1 migration release candidate**
- Repository: `vali-prediction-market-research`
- Repository branch: `main`
- Submission validation baseline: `0493e9a358e59a491116d3bdf4af529a2ee44e79`
- Full-suite result: **186 passed, 0 failed**
- Submission status: **research-engine submission artifact**
- Package version: `0.3.0`

The labels serve different purposes. `v0.1` identifies the migration and
research-engine release candidate; `0.3.0` is the existing Python package
version declared in `pyproject.toml` and `vali.__version__`. The package has not
been renamed or renumbered. This ambiguity should be resolved in a later
release-management step if distribution packaging becomes necessary.

## B. Scope

This release candidate is a public-data research engine with read-only provider
collection, frozen feature manifests, point-in-time validation, physical label
isolation, event-grouped walk-forward backtesting, execution-aware reporting,
and artifact/report reconstruction. It contains no live trading.

## C. Non-goals

This release candidate provides:

- no empirical alpha claim;
- no managed investment product;
- no live trading or order submission;
- no private inputs, proprietary order flow, or `P_flow`;
- no credentialed Kalshi trading; and
- no official Google Trends alpha integration.

The Google Trends boundary remains offline-ready because the official alpha
protocol and revision guarantees are not implemented or assumed.

## D. Architecture boundaries completed

- `vali.domain.*`
- `vali.data.*`
- `vali.configuration.*`
- `vali.research.*`
- `vali.artifacts.*`
- `vali.execution.*`
- `vali.providers.kalshi_components.*`
- `vali.providers.google_trends_components.*`
- `vali.application.*`

Legacy facades delegate to these boundaries where applicable.

## E. Data and artifact tiers

- `configs/` contains canonical experiment and frozen feature configuration.
- `tests/fixtures/` contains committed deterministic provider fixtures.
- `data/raw/` is reserved for immutable public provider responses.
- `data/interim/` contains normalized provider/source tables.
- `data/processed/` contains frozen analysis-ready datasets.
- `data/quarantine/` contains data requiring provenance or tier review.
- `reports/` separates generated runs, reviewed archives, and quarantine.
- `artifacts/quarantine/` contains stale builds and generated artifacts pending
  review and is never an import source.
- `ARTIFACT_INVENTORY.md` records preservation and quarantine decisions.

## F. Compatibility commitments

For this release candidate, the following remain supported:

- legacy public imports and compatibility facades;
- the compatibility config at `examples/config.toml`;
- the Google Trends fixture compatibility copy at
  `tests/fixtures/google_trends/interest.json`; and
- current CLI command names and arguments.

Retirement requires a separate, reviewed compatibility change.

## G. Known risks and caveats

- Package `0.3.0` and migration `v0.1` have a documented naming ambiguity.
- No dependency lockfile guarantees exact transitive dependency resolution.
- A clean-clone installation test remains pending; the repository-local
  `.venv` was not provisioned during the submission identity refresh.
- Quarantined artifacts still require later review.
- Quarantined Kalshi captures still mix raw archives and normalized tables.
- Kalshi venue configuration remains embedded.
- Historical Kalshi data lacks observed order-book depth, limiting capacity and
  tradability claims; those claims remain disabled.
- The fee model remains provisional.
- The official Google Trends alpha protocol and revision guarantees remain
  unpublished and unimplemented.
- Canonical empirical validation remains blocked pending documented
  point-in-time attention history.
- No empirical alpha claim has been validated.
- No trading-readiness claim has been validated.

## H. Acceptance gates

The 4-series exit requires:

- clean Git state before validation;
- a passing full pytest suite;
- passing deterministic CLI smoke checks;
- an unchanged frozen feature-manifest hash;
- no source imports from quarantined build copies;
- no prohibited concepts or APIs introduced;
- this release-candidate document and `FINAL_VALIDATION_REPORT.md`; and
- a clean working tree after the local release-candidate commit.
