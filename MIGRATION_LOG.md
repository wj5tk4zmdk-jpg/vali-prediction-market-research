# VALI Migration Log

## Steps 1 and 2 - Baseline and governance

Completed 2026-06-23.

- Recorded the pre-refactor repository and environment in
  `BASELINE_INVENTORY.md` after confirming Git was not valid.
- Added repository governance in `AGENTS.md`.
- Added the VALI 1.0 methodology contract, data contracts, research protocol,
  reporting policy, and ADRs 0001 through 0006.
- No source logic was changed, no files were moved, and no artifacts were
  deleted.

## Step 2.5 - Stable Google Trends `retrieved_at`

Completed 2026-06-23.

- Normalized Google Trends exclusion `retrieved_at` values to a timezone-aware
  UTC pandas datetime before PyArrow serialization.
- Added a narrow Parquet serialization assertion.
- Files changed:
  - `src/vali/providers/google_trends.py`
  - `tests/test_google_trends.py`
- Result after Step 2.5: **42 passed, 0 failed**.

## Step 3A - Methodology characterization and label isolation

Completed 2026-06-23.

- Added deterministic characterization coverage for `A`, `P`, `gA`, `gP`,
  `S_t`, `M_t`, liquidity gating, and regime classification.
- Added outcome-label isolation coverage for market, signal, pre-decision,
  decision, and walk-forward evaluation tables.
- Removed the outcome field from daily signal-time market rows; evaluation
  continues to receive outcomes from the separate events table.
- Files created:
  - `tests/test_methodology_characterization.py`
  - `tests/test_label_isolation.py`
- Source file changed:
  - `src/vali/market.py`
- Full result after Step 3A: **49 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.

## Step 3B - Walk-forward population and execution contracts

Completed 2026-06-23.

- Added deterministic walk-forward tests proving that historical frequency uses
  every prior resolved event, including events without market snapshots, while
  calibration continues to use only complete prior market/signal snapshots.
- Enforced strict event-time boundaries: the current and future events cannot
  enter an earlier training population, and multiple daily rows cannot split an
  event across folds.
- Replaced the permissive any-observed-depth execution-reporting gate with a
  complete-snapshot check covering quotes, spread, observed depth, price
  quality, execution liquidity, executable status, and explicit closures.
- Prevented closed or otherwise non-executable entries from reaching trade
  simulation. A failed mandatory pre-settlement exit is now labeled
  `forced_settlement_after_failed_pre_settlement_exit` with an explicit
  execution-failure flag.
- Kept the existing generic basis-point fee calculation and labeled it
  `provisional_bps` in trade results and the run manifest.
- Added report warnings when execution snapshot history is incomplete.
- Files created:
  - `tests/test_walk_forward_population.py`
  - `tests/test_execution_contract.py`
- Source files modified:
  - `src/vali/backtest.py`
  - `src/vali/decisions.py`
  - `src/vali/pipeline.py`
  - `src/vali/reporting.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No VALI signal, attention, price-velocity, divergence, or regime formula was
  changed. No file was moved or deleted.
- Full result after Step 3B: **57 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.

## Step 3C - Public inputs, frozen composition, and event identity

Completed 2026-06-23.

- Added core validation that rejects forbidden private/proprietary provenance,
  `P_flow`, order-flow fields, client data, pending orders, product-launch
  information, credentialed trading, execution APIs, and order-submission
  configuration. Public behavioral/search/filing sources, public market prices,
  and unauthenticated public venue snapshots remain permitted.
- Made optional-feature behavior explicit. The default `reject` policy preserves
  fixed equal-weight composition and emits `missing_optional_feature` rather
  than reweighting silently. `dynamic_reweight` remains available only as an
  explicit, reported configuration choice.
- Rejected observations outside the frozen feature manifest and added fixed
  composition weights and missingness fields to the feature audit. The existing
  run manifest continues to hash the feature manifest and record the parameter
  freeze date.
- Added internal event validation requiring exactly one internal `EASING` event
  per represented meeting date. Missing or duplicate EASING identities and
  mismatched event/contract identifiers are validation errors. Walk-forward and
  execution simulation invoke this validation before evaluation.
- Files created:
  - `tests/test_public_input_boundary.py`
  - `tests/test_feature_composition_freeze.py`
  - `tests/test_event_identity_contract.py`
- Source files modified:
  - `src/vali/config.py`
  - `src/vali/io.py`
  - `src/vali/features.py`
  - `src/vali/backtest.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No VALI velocity, divergence, regime, threshold, or outcome-label formula was
  changed. No provider module was changed. No file was moved or deleted.
- Full result after Step 3C: **70 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.

## Step 4A - Pure domain mathematics boundary

Completed 2026-06-23.

- Created `src/vali/domain/` as a dependency-light boundary for deterministic
  VALI mathematics only.
- Extracted feature transformation, equal-weight composition, and fixed-weight
  helpers into `domain/attention.py`.
- Extracted probability clipping and logit transformation into
  `domain/conviction.py`.
- Extracted shifted rolling normalization, rolling OLS velocity, signed
  divergence `S_t`, and magnitude `M_t` into `domain/divergence.py`.
- Extracted lagged correlations and correlation-vector regime classification
  into `domain/regimes.py`, preserving the positive-lag attention-leading
  convention and conflicting near-tie behavior.
- Preserved `vali.features`, `vali.signals`, and `vali.regimes` as compatibility
  wrappers. Their existing imports, orchestration, and output schemas remain
  unchanged.
- Added deterministic equivalence tests for old wrapper imports and new domain
  imports. Existing methodology characterization expected values were not
  changed.
- Files created:
  - `src/vali/domain/__init__.py`
  - `src/vali/domain/attention.py`
  - `src/vali/domain/conviction.py`
  - `src/vali/domain/divergence.py`
  - `src/vali/domain/regimes.py`
  - `tests/test_domain_compatibility.py`
- Existing source files modified only as compatibility wrappers:
  - `src/vali/features.py`
  - `src/vali/signals.py`
  - `src/vali/regimes.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No formulas, provider behavior, backtest logic, execution logic,
  configuration, or output schemas were changed. No file or data artifact was
  moved or deleted.
- Full result after Step 4A: **74 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.

## Step 4B - Data contracts and validation boundary

Completed 2026-06-23.

- Created `src/vali/data/` for versioned input contracts, public provenance,
  point-in-time selection, feature-manifest validation, forbidden-input
  validation, and internal EASING event identity.
- Moved input column contracts, `DataValidationError`, `ValidationSummary`, and
  `InputBundle` into `data/contracts.py` while preserving their existing
  `vali.io` imports.
- Moved public-input marker detection and configuration/frame provenance checks
  into `data/provenance.py`. `vali.config` and `vali.io` retain compatibility
  wrappers with the same exception types and messages.
- Moved timezone-aware parsing, as-of vintage selection, strictly-prior fold
  selection, and the label-isolation helper into `data/point_in_time.py`.
- Moved frame, feature-manifest, frozen-universe, and internal EASING identity
  validation into `data/validation.py`. `vali.io.validate_frames` and
  `vali.io.validate_event_identity` remain supported delegators.
- Updated `vali.features` to delegate frozen-manifest and as-of selection rules
  to the data boundary. Updated walk-forward filtering to delegate the existing
  strict-prior comparison to the point-in-time helper.
- Added deterministic compatibility tests covering old and new imports,
  returned frames, exception types/messages, provenance rejection, manifest
  rejection, event identity, vintage selection, fold isolation, and label
  isolation.
- Files created:
  - `src/vali/data/__init__.py`
  - `src/vali/data/contracts.py`
  - `src/vali/data/provenance.py`
  - `src/vali/data/point_in_time.py`
  - `src/vali/data/validation.py`
  - `tests/test_data_boundary_compatibility.py`
- Existing source files modified only for delegation:
  - `src/vali/config.py`
  - `src/vali/io.py`
  - `src/vali/features.py`
  - `src/vali/backtest.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No formulas, output schemas, provider behavior, execution logic, backtest
  decisions, config-file format, or test layout changed. No file or data
  artifact was moved or deleted.
- Full result after Step 4B: **80 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.

## Step 4C - Configuration contracts and loading boundary

Completed 2026-06-23.

- Created `src/vali/configuration/` for typed configuration contracts, unchanged
  TOML loading/path resolution, and configuration validation.
- Moved `ConfigError`, `DataConfig`, `MarketConfig`, `FeatureConfig`,
  `SignalConfig`, `RegimeConfig`, `BacktestConfig`, and `ValiConfig` into
  `configuration/contracts.py`. Their validation methods and
  `ValiConfig.from_toml` delegate to the new boundary.
- Moved required-setting checks, TOML loading, relative-path resolution,
  defaults, tuple conversion, and typed object construction into
  `configuration/loading.py` without changing the TOML schema.
- Moved market, feature, signal, regime, backtest, run-level, and forbidden
  public-input configuration checks into `configuration/validation.py` with the
  same exception classes and messages.
- Preserved `vali.config` as a compatibility facade. Existing imports are
  aliases of the new contract classes, and existing provenance helper names
  continue to delegate to the extracted implementation.
- Added deterministic compatibility tests for old/new class identity, TOML
  object equality, resolved paths, defaults, validation messages, unknown keys
  in typed sections, and forbidden configuration.
- Files created:
  - `src/vali/configuration/__init__.py`
  - `src/vali/configuration/contracts.py`
  - `src/vali/configuration/loading.py`
  - `src/vali/configuration/validation.py`
  - `tests/test_configuration_compatibility.py`
- Existing source file modified only as a compatibility facade:
  - `src/vali/config.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No formulas, output schemas, provider behavior, execution logic, backtest
  decisions, TOML keys/defaults, config-file locations, or test layout changed.
  No file or data artifact was moved or deleted.
- Full result after Step 4C: **85 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.

## Step 4D - Research and application orchestration boundary

Completed 2026-06-23.

- Created `src/vali/research/` for deterministic calibration, event-grouped
  walk-forward evaluation, frozen sensitivity orchestration, and high-level
  research pipeline coordination.
- Moved logistic calibration helpers into `research/calibration.py` and retained
  `vali.calibration` as a signature-compatible delegating facade.
- Moved event snapshot selection and walk-forward fold evaluation into
  `research/walk_forward.py`, preserving all-prior-resolved historical
  frequency, complete-prior-signal calibration, strict current/future event
  exclusion, event grouping, outcomes only in evaluation, and exclusion rows.
- Left trade simulation, entry/exit rules, fees, depth caps, closures, and
  settlement mechanics unchanged in `vali.backtest`. Its walk-forward entry
  points now delegate to the research boundary.
- Moved signal/backtest pipeline orchestration and report reconstruction into
  `research/pipeline.py` with unchanged inputs, output tables, manifests,
  execution-validation summaries, hashes, exclusions, metrics, and HTML calls.
  `vali.pipeline` remains a public compatibility facade.
- Moved the fixed sensitivity-window panel into `research/sensitivity.py`
  without changing window order, metrics, execution gates, or selection rules.
- Added deterministic compatibility tests for old/new imports, calibration
  coefficients, predictions, folds, exclusions, execution summaries, signal
  tables, artifact names, and run manifests.
- Files created:
  - `src/vali/research/__init__.py`
  - `src/vali/research/calibration.py`
  - `src/vali/research/walk_forward.py`
  - `src/vali/research/pipeline.py`
  - `src/vali/research/sensitivity.py`
  - `tests/test_research_boundary_compatibility.py`
- Existing source files modified only for delegation:
  - `src/vali/calibration.py`
  - `src/vali/backtest.py`
  - `src/vali/pipeline.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No formulas, output schemas, providers, execution mechanics, backtest
  decisions, configuration behavior, TOML handling, test layout, or artifact
  locations changed. No file or data artifact was moved or deleted.
- Full result after Step 4D: **90 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.

## Step 4E-0 - Repository integrity checkpoint

Completed 2026-06-23.

- Git commands initially could not run because no `git` executable was
  installed or discoverable on `PATH`.
- The project root and `C:\Users\matte\Documents\Codex` parent each contained
  an ordinary, non-linked, empty `.git` directory. Both were invalid repository
  metadata.
- Preserved the invalid metadata by moving it to:
  - `C:\Users\matte\Documents\Codex\2026-06-23\sdfas\.git.invalid-20260623-202713`
  - `C:\Users\matte\Documents\Codex\.git.invalid-20260623-202713`
- Installed the official Git for Windows portable distribution
  (`2.54.0.windows.1`) under ignored `work/tools/` and verified archive SHA-256
  `BEA006A6CC69673F27B1647E84AB3A68E912FBC175AB6320C5987E012897F311`.
- Quarantined a later plugin-created empty `.git` directory at
  `.git.invalid-plugin-20260623-204606`, an interrupted initialization at
  `.git.partial-init-20260623-204907`, and an interrupted portable extraction at
  `work/tools/PortableGit.partial-20260623-204606`.
- Initialized a valid project-root repository on branch `main`.
- Inspected the 87-file checkpoint candidate set. Updated `.gitignore` to omit
  generated `build/`, portable tools, downloads, outputs, virtual environments,
  and quarantined Git metadata.
- Configured the user-approved repository-local identity
  `wj5tk4zmdk-jpg <matteaton084@gmail.com>`.
- Created the 87-file migration checkpoint commit
  `895f0e2118c04f1301c6fd74ce4aa19ffda27518` with subject
  `checkpoint: VALI migration baseline through Step 4D`.
- Created `REPO_INTEGRITY_STATUS.md` with the inspection result, quarantine
  paths, verification status, and required follow-up.
- No source, formula, provider, reporting, execution, configuration, test, or
  data-artifact behavior was changed.
- Full result after Step 4E-0 inspection: **90 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Step 4E reporting extraction is cleared to proceed from the valid `main`
  branch checkpoint. A GitHub remote is optional and has not been configured.

## Step 4E - Artifact and reporting boundary

Completed 2026-06-23.

- Created `src/vali/artifacts/` for deterministic metrics and diagnostics,
  reproducibility hashes and run-manifest construction, stable DataFrame
  serialization, dependency-light HTML assembly, and report reconstruction.
- Preserved `vali.reporting` as a compatibility facade with unchanged public
  names, signatures, return values, warning text, and rendered report text.
- Updated research orchestration and the fixed sensitivity panel to consume the
  artifact boundary. Preserved the private pipeline hash and manifest wrappers
  used by existing compatibility surfaces.
- Preserved the exact run-manifest keys, package/methodology metadata, artifact
  base names, CSV/Parquet behavior, report section names, execution-validation
  warning, and research-only warning.
- Added deterministic compatibility tests covering old/new imports, forecast
  and trade metrics, divergence and regime diagnostics, serialization names and
  CSV content, hashes and manifest keys, HTML rendering, and report rebuilding.
- Files created:
  - `src/vali/artifacts/__init__.py`
  - `src/vali/artifacts/metrics.py`
  - `src/vali/artifacts/manifests.py`
  - `src/vali/artifacts/serialization.py`
  - `src/vali/artifacts/reports.py`
  - `tests/test_artifact_reporting_compatibility.py`
- Existing source files modified only for delegation:
  - `src/vali/reporting.py`
  - `src/vali/research/pipeline.py`
  - `src/vali/research/sensitivity.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No formulas, output schemas, provider behavior, execution mechanics,
  backtest decisions, metric definitions, warning text, report text,
  configuration behavior, TOML handling, test layout, or artifact locations
  changed. No source file or data artifact was moved or deleted.
- Full result after Step 4E: **96 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Created local commit `ed9e74968e0e03b2c82b2519d813631e094a2692`
  with subject `migration: extract artifact reporting boundary`.

## Step 4F - Execution boundary

Completed 2026-06-23.

- Created `src/vali/execution/` for decision-time execution gates, liquidity
  and capacity helpers, explicitly provisional basis-point fees, executable
  snapshot completeness, YES/NO quote transformations, Clear Horizon and
  settlement handling, failed mandatory exits, and trade simulation.
- Preserved `vali.decisions.generate_decisions`,
  `vali.backtest.simulate_trades`, `vali.pipeline.execution_validation_summary`,
  and all existing research/reporting imports as compatibility wrappers or
  unchanged call sites.
- Left `BacktestResult`, walk-forward evaluation, and backtest orchestration in
  `vali.backtest`; only the execution simulator and liquidation helper now
  delegate to the execution boundary.
- Preserved closed/non-executable rejection, price-quality and depth gates,
  fixed-notional depth caps, YES/NO quote inversion, all exit rules, settlement
  payoff, failed pre-settlement exit labeling, and `execution_failure=True`.
- Preserved the generic fee model and its explicit `provisional_bps`, `fee_bps`,
  and `fee_assumption_provisional` output and manifest fields.
- Added deterministic compatibility tests for old/new imports, decision gates,
  snapshot completeness, no-depth capacity gating, quote inversion, depth
  caps, provisional fees, settlement failure, simulator outputs, and the exact
  trade output schema.
- Files created:
  - `src/vali/execution/__init__.py`
  - `src/vali/execution/liquidity.py`
  - `src/vali/execution/fees.py`
  - `src/vali/execution/snapshots.py`
  - `src/vali/execution/settlement.py`
  - `src/vali/execution/simulator.py`
  - `tests/test_execution_boundary_compatibility.py`
- Existing source files modified only for delegation:
  - `src/vali/decisions.py`
  - `src/vali/backtest.py`
  - `src/vali/research/pipeline.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No formulas, execution policies, eligibility rules, fee assumptions, capacity
  claims, output schemas, report text, artifact names, manifest fields,
  providers, configuration behavior, TOML handling, or test layout changed.
  No source file or data artifact was moved or deleted.
- Full result after Step 4F: **102 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
