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
- Created local commit `230f9c88cab898876ff2aaa09f9a2456c5e7846d`
  with subject `migration: extract execution boundary`.

## Step 4G-1 - Kalshi provider decomposition

Completed 2026-06-23.

- Created the non-conflicting internal `kalshi_components` package while
  retaining `vali.providers.kalshi` as the public compatibility facade.
- Moved Kalshi constants, typed mappings, run results, the shared exception,
  and the read-only transport contract into `contracts.py`.
- Moved canonical payload serialization and immutable content-addressed gzip
  response archiving into `archive.py`, preserving directory layout, archive
  names, content SHA-256 calculation, and envelope fields.
- Moved public REST URL construction, retry/backoff, cursor pagination,
  historical/live endpoint routing, candlestick chunking, and read-only client
  methods into `transport.py` without adding network requirements to tests.
- Moved KXFED strike parsing, threshold-ladder settlement validation, target
  upper-bound derivation, internal EASING mapping, timestamps, and upper-bound
  CSV loading into `mapping.py`.
- Moved candlestick, trade, event, and bid-only fixed-point order-book
  normalization into `normalization.py`, preserving YES/NO inversion, observed
  and unavailable depth behavior, columns, ordering, values, and dtypes.
- Kept `KalshiAdapter` orchestration in `vali.providers.kalshi` and preserved
  all existing public imports and private aliases used by the adapter.
- Added deterministic fixture-based compatibility tests for imports, mappings,
  normalized frames and dtypes, depth, archive path/name/hash/envelope,
  pagination/retry behavior, and the absence of credentials or order methods.
- Files created:
  - `src/vali/providers/kalshi_components/__init__.py`
  - `src/vali/providers/kalshi_components/contracts.py`
  - `src/vali/providers/kalshi_components/transport.py`
  - `src/vali/providers/kalshi_components/archive.py`
  - `src/vali/providers/kalshi_components/normalization.py`
  - `src/vali/providers/kalshi_components/mapping.py`
  - `tests/test_kalshi_provider_decomposition.py`
- Existing source file modified as the compatibility facade:
  - `src/vali/providers/kalshi.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- Google Trends was not changed. No normalized outputs, archive paths or hashes,
  mapping rules, pagination/retry behavior, timestamp behavior, schemas,
  formulas, execution policies, fee assumptions, reports, artifacts,
  configuration behavior, TOML handling, or test layout changed. No data
  artifact was moved or deleted.
- No credentialed endpoint, order-submission logic, private input, proprietary
  order flow, or `P_flow` was introduced.
- Full result after Step 4G-1: **110 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Created local commit `9358b5954b3b6985530297b9bc9e47d11ecb58e3`
  with subject `migration: decompose Kalshi provider boundary`.

## Step 4G-2 - Google Trends provider decomposition

Completed 2026-06-23.

- Created the non-conflicting internal `google_trends_components` package while
  retaining `vali.providers.google_trends` as the public compatibility facade.
- Moved typed query/request/observation/response/run contracts, constants,
  shared exceptions, UTC parsing, deterministic hashing, and secret redaction
  into `contracts.py`.
- Moved frozen query-manifest loading and validation, balanced active-basket
  enforcement, manifest frames and hashes, T-2 request planning, and plan-file
  generation into `manifest.py`.
- Moved the deterministic recorded-fixture gateway and fixture validation into
  `fixtures.py` without changing filtering, status, missingness, request IDs,
  or fixture response content.
- Moved feature-manifest construction, response normalization, T-2 and partial
  exclusions, UTC `retrieved_at` handling, vintage hashes, and append/deduplication
  helpers into `normalization.py`.
- Moved coverage, missing-active-query, suppression, low-volume, and latest-date
  status reporting into `audit.py`.
- Moved the explicit unavailable-official-access gate and protocol-independent
  retry wrapper into `client.py`. The module intentionally contains no HTTP
  transport, credentials, or assumptions about the unpublished alpha protocol.
- Kept `TrendsArchiveStore` and `TrendsAdapter` orchestration in the public
  facade to preserve archive and persistence behavior exactly. Existing private
  helper aliases used by the adapter remain available.
- Added deterministic compatibility tests for old/new imports, query manifests,
  active/inactive selection, request-plan bytes, fixture responses, normalized
  frames and dtypes, audit/exclusion output, UTC/Parquet serialization,
  archive names and hashes, redaction, and the absence of live networking or
  credentials.
- Files created:
  - `src/vali/providers/google_trends_components/__init__.py`
  - `src/vali/providers/google_trends_components/contracts.py`
  - `src/vali/providers/google_trends_components/manifest.py`
  - `src/vali/providers/google_trends_components/fixtures.py`
  - `src/vali/providers/google_trends_components/normalization.py`
  - `src/vali/providers/google_trends_components/audit.py`
  - `src/vali/providers/google_trends_components/client.py`
  - `tests/test_google_trends_provider_decomposition.py`
- Existing source file modified as the compatibility facade:
  - `src/vali/providers/google_trends.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- Kalshi was not changed. No query-manifest behavior, fixture output,
  normalized output, audit/exclusion output, archive path or hash, timestamp,
  dtype, schema, formula, report, artifact, configuration, TOML behavior, or
  test layout changed. No data artifact was moved or deleted.
- No live API call, network dependency, credential use, official-alpha protocol
  assumption, private input, proprietary order flow, order submission, or
  `P_flow` was introduced.
- Full result after Step 4G-2: **118 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Created local commit `8c2ab104cd48409994c514f11006ec64447f2f2c`
  with subject `migration: decompose Google Trends provider boundary`.

## Step 4H - Application and CLI boundary

Completed 2026-06-23.

- Created `src/vali/application/` for command registration and dispatch,
  research-run orchestration, read-only public-data collection, report
  reconstruction, and configuration/input validation commands.
- Moved the existing argparse command tree into `application/commands.py`
  without changing command names, subcommands, flags, types, defaults, choices,
  required arguments, descriptions, or help text.
- Moved sample-data, signal, and backtest command handlers into
  `application/research.py`, delegating to the existing sample and research
  pipeline APIs.
- Moved Kalshi and Google Trends command handlers into
  `application/collection.py`, retaining the existing public read-only provider
  facades, printed JSON, failure behavior, and explicit no-live-access Trends
  gate.
- Moved report reconstruction into `application/reporting.py` and validation
  command orchestration into `application/validation.py` without changing
  output paths, artifacts, report content, configuration loading, or validation
  output.
- Preserved `vali.cli._iso_date`, `vali.cli._parser`, and `vali.cli.main` as
  compatibility wrappers. `vali.__main__` and the `vali` console-script entry
  point remain unchanged.
- Added deterministic compatibility tests for application imports, parser/help
  parity, exact command and argument surfaces, parsed namespaces, validation and
  signal outputs, artifact sets, report delegation, `python -m vali`, and the
  absence of trading, credential, private-input, and `P_flow` commands.
- Files created:
  - `src/vali/application/__init__.py`
  - `src/vali/application/commands.py`
  - `src/vali/application/research.py`
  - `src/vali/application/collection.py`
  - `src/vali/application/reporting.py`
  - `src/vali/application/validation.py`
  - `tests/test_application_cli_compatibility.py`
- Existing source file modified only as the compatibility facade:
  - `src/vali/cli.py`
- Governance file modified:
  - `MIGRATION_LOG.md`
- No command, argument, output, config/TOML behavior, provider behavior,
  formula, execution policy, report text, artifact name, manifest field,
  schema, or test layout changed. No data artifact was moved or deleted.
- No credentialed trading endpoint, order-submission logic, private input,
  proprietary order flow, live trading, live API assumption, or `P_flow` was
  introduced.
- Full result after Step 4H: **125 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Created local commit `a6b6c427d2df8b77ad3b10cde5df88b765175dbb`
  with subject `migration: extract application CLI boundary`.

## Step 4I - Config, test, and fixture relocation

Completed 2026-06-23.

- Created the target configuration layout under `configs/experiments/`,
  `configs/features/`, and `configs/venues/`.
- Added `configs/experiments/fed_easing_v1.toml` as a byte-identical copy of
  `examples/config.toml`. The old example path remains in place as a
  compatibility copy; both TOML files load with identical run, market, feature,
  signal, regime, and backtest settings.
- Added `configs/features/google_trends_candidate_v1.csv` as a byte-identical
  copy of the packaged manifest at
  `src/vali/data/google_trends_query_manifest.v1.csv`. The packaged path remains
  the default compatibility source for installed distributions.
- Verified the Google Trends logical manifest hash remains
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
  Query order, active IDs, inactive IDs, baskets, polarity, required flags, and
  all candidate metadata remain identical.
- No external Kalshi/KXFED configuration existed. Venue mapping remains
  embedded by design; no speculative venue config was invented.
- Relocated tests by purpose into `tests/unit/`, `tests/contract/`,
  `tests/leakage/`, and `tests/integration/`, retaining `tests/__init__.py` and
  unchanged expected values.
- Relocated recorded provider fixtures into
  `tests/fixtures/providers/kalshi/` and
  `tests/fixtures/providers/google_trends/` without changing fixture bytes.
- Retained a byte-identical compatibility copy at
  `tests/fixtures/google_trends/interest.json` because the existing README
  documents that path. No old Kalshi fixture path was documented outside the
  historical baseline inventory.
- Updated only relocated test-local fixture and repository-root path references.
  Provider code, application code, configuration loading, and package data were
  not changed.
- Added `tests/contract/test_project_layout_compatibility.py` covering old/new
  config paths, byte identity, manifest order/status/hash, deterministic `A_t`
  and audit equivalence, forbidden post-freeze features, required and optional
  missingness, dynamic reweighting, provider fixture content hashes and
  normalization, pytest discovery, and CLI config/fixture paths.
- Frozen attention composition remains unchanged: feature IDs and order,
  active/inactive status, missing-required and missing-optional exclusions,
  fixed composition, explicit dynamic reweighting, audit rows, and `A_t` are
  identical. Relocated paths cannot broaden the candidate feature universe.
- Pytest collection increased only by the six new layout compatibility tests:
  131 tests are discovered across the four target test groups.
- Files copied for compatibility or target layout:
  - `configs/experiments/fed_easing_v1.toml`
  - `configs/features/google_trends_candidate_v1.csv`
  - `tests/fixtures/google_trends/interest.json`
- New layout marker:
  - `configs/venues/.gitkeep`
- New test:
  - `tests/contract/test_project_layout_compatibility.py`
- Existing tests and fixtures were moved into their target directories; four
  provider tests had fixture paths updated, and the application CLI test had
  its repository-root calculation updated for its new depth.
- Governance file modified:
  - `MIGRATION_LOG.md`
- No source logic, methodology, formula, TOML format, CLI behavior, provider
  behavior, normalized output, fixture content, report, artifact, manifest
  field, schema, execution policy, fee model, or generated artifact changed.
  No data artifact was deleted or cleaned.
- No live API, network dependency, credential use, private input, proprietary
  flow, order submission, live trading, or `P_flow` was introduced.
- Full result after Step 4I: **131 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Created local commit `28cda08073eecf206313878670e6b736ebdac0f1`
  with subject `migration: relocate configs tests and fixtures`.

## Step 4J - Artifact quarantine and data tiers

Completed 2026-06-23.

- Created the data tiers `data/raw/`, `data/interim/`, `data/processed/`, and
  `data/quarantine/`; report tiers `reports/archive/`, `reports/runs/`, and
  `reports/quarantine/`; and `artifacts/quarantine/` for generated package and
  source snapshots.
- Added `ARTIFACT_INVENTORY.md` with original/current paths, classifications,
  move/deletion status, file and byte summaries, reproducibility and empirical
  flags, reasons, and SHA-256 values for package bundles and the archived
  verification report.
- Moved stale generated `build/lib` source copies, package metadata, historical
  wheels, source archives, duplicated wheel builds, and the legacy output
  README into `artifacts/quarantine/`. No quarantined package file was deleted.
- Moved the known normalized Kalshi live snapshot into
  `data/interim/kalshi/`. Moved mixed raw/normalized Kalshi captures into
  `data/quarantine/kalshi/` rather than guessing their final tier.
- Moved the fixture-derived Trends acceptance run into
  `data/quarantine/google_trends/`. Committed provider fixtures and the old
  Google Trends compatibility fixture remained unchanged in place.
- Moved the deterministic synthetic output run into `reports/runs/`; moved
  older unreviewed work runs into `reports/quarantine/legacy-work/`; and moved
  the reviewed `KALSHI_ADAPTER_VERIFICATION.md` into `reports/archive/` without
  changing its filename or text.
- Left `.pytest_cache`, `.coverage`, `.venv`, `work/.venv`, `work/tools`, and
  previously quarantined invalid Git metadata in place. They are inventoried as
  local caches, environments, or needs-review metadata. No file was deleted.
- Updated `.gitignore` narrowly:
  - added `dist/` for standard generated package distributions;
  - ignored `artifacts/quarantine/*` while retaining its layout marker;
  - ignored only the specifically relocated local Kalshi/Trends data payloads,
    leaving future `data/raw/` and `data/processed/` visible by default;
  - ignored generated `reports/runs/*` and unreviewed
    `reports/quarantine/*` while retaining layout markers.
- Added `tests/contract/test_artifact_layout_compatibility.py` covering provider
  fixtures and compatibility copies, new config/CLI paths, report
  reconstruction, authoritative `src/vali` import resolution, absence of stale
  build dependencies, and absence of prohibited live/trading/private surfaces.
- Verified no project import resolves from `artifacts/quarantine/build` and no
  test references the former `build/lib` source snapshot.
- Files created or modified for repository state:
  - `ARTIFACT_INVENTORY.md`
  - `.gitignore`
  - data/report/artifact tier `.gitkeep` markers
  - `reports/archive/KALSHI_ADAPTER_VERIFICATION.md`
  - `tests/contract/test_artifact_layout_compatibility.py`
  - `MIGRATION_LOG.md`
- No source logic, methodology, formula, provider behavior, normalized output,
  fixture content, config/TOML behavior, CLI behavior, execution policy, fee
  model, report content, artifact content, manifest field, schema, or existing
  test expectation changed.
- The frozen Google Trends manifest hash remains
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
- All raw public/empirical data was preserved in interim or quarantine tiers;
  none was deleted. No compatibility copy was deleted.
- No live API, network dependency, credential use, private input, proprietary
  flow, order submission, live trading, or `P_flow` was introduced.
- Full result after Step 4J: **137 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Created local commit `195a2e33202b834f5f4b560f2c1abc4078d2ad27`
  with subject `migration: quarantine artifacts and establish data tiers`.

## Step 4K - Package and repository hygiene

Completed 2026-06-23.

- Confirmed Step 4J created `data/{raw,interim,processed,quarantine}/`,
  `reports/{archive,runs,quarantine}/`, and `artifacts/quarantine/`, together
  with `ARTIFACT_INVENTORY.md`.
- Confirmed stale builds, wheels, archives, egg metadata, mixed Kalshi
  captures, Trends acceptance outputs, synthetic and legacy runs, and the
  reviewed Kalshi verification report were quarantined or tiered without
  deleting public data.
- Confirmed imports resolve from `src/vali`, never from the quarantined
  `build/lib` source copy.
- Step 4J baseline before hygiene changes: **137 passed, 0 failed** at commit
  `195a2e33202b834f5f4b560f2c1abc4078d2ad27`.
- Added `REPOSITORY_POLICY.md` covering authoritative source imports, data and
  report tiers, artifact quarantine, deterministic fixtures, compatibility
  copies, and the public-data-only research boundary.
- Added `ENVIRONMENT.md` covering Python and dependency guidance, the tested
  local command, local environment state, import policy, and the deliberately
  absent live Google Trends and credentialed Kalshi trading integrations.
- Updated `README.md` with a concise v0.1 migration orientation, canonical
  config path, governance/documentation map, test command, and explicit
  no-alpha/no-live-trading caveats.
- Reviewed `pyproject.toml`: package version `0.3.0` remains consistent with
  `vali.__version__` and generated run manifests; package discovery is already
  limited to `src/`, and pytest already discovers the relocated `tests/` tree.
  No metadata or dependency change was needed.
- Reviewed `.gitignore` and retained it unchanged because it narrowly ignores
  local/generated state while leaving source, docs, configs, tests, fixtures,
  reviewed reports, and future intentional raw/processed data visible.
- Reviewed root, provider, and boundary package exports. Existing compatibility
  facades remain importable and no unstable export was added or removed.
- Added `tests/contract/test_repository_hygiene.py` covering authoritative
  import resolution, boundary and legacy facade imports, documentation,
  canonical and compatibility configs, package/version consistency, the frozen
  Trends manifest hash, and prohibited operational API surfaces.
- No source logic, formula, methodology, provider behavior, normalized output,
  config/TOML behavior, CLI behavior, fixture content, report, artifact,
  manifest field, schema, execution policy, fee model, or legacy public import
  changed.
- The frozen Google Trends manifest hash remains
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
- No live API, network dependency, credential use, private input, proprietary
  flow, order submission, live trading, or `P_flow` was introduced.
- Full result after Step 4K: **143 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Files created:
  - `REPOSITORY_POLICY.md`
  - `ENVIRONMENT.md`
  - `tests/contract/test_repository_hygiene.py`
- Files modified:
  - `README.md`
  - `MIGRATION_LOG.md`
- Created local commit `3639580d81d4b6b2e7039f36771b7e6f785c74b5`
  with subject `migration: harden package and repository hygiene`.
- At that checkpoint, imports resolved exclusively from `src/vali`; package
  version `0.3.0` remained internally consistent; and configs, fixtures,
  manifests, CLI, providers, outputs, reports, artifacts, schemas, execution,
  and methodology were unchanged.

## Step 4L - Final validation and v0.1 migration release candidate

Completed 2026-06-23.

- Validated a clean `main` branch at Step 4K commit
  `3639580d81d4b6b2e7039f36771b7e6f785c74b5` before editing.
- Added `V0_1_RELEASE_CANDIDATE.md`, documenting the migration release label,
  package-version distinction, completed boundaries, data/artifact tiers,
  compatibility commitments, known risks, and 4-series acceptance gates.
- Added `FINAL_VALIDATION_REPORT.md` with the validation identity, exact test
  and CLI smoke commands, manifest/import/prohibited-surface/config/fixture
  results, caveats, and a bounded readiness conclusion.
- Added `tests/contract/test_final_release_candidate.py` with six deterministic
  release-candidate checks. No live API, credentials, or mutable empirical data
  were used.
- Ran help-only smoke checks for the root CLI; `validate`, `signal`,
  `backtest`, `report`, and `sample-data`; all Kalshi subcommands; and all
  Google Trends subcommands. All returned exit code 0 without network access or
  output creation.
- Searched for `P_flow`, order-submission terms, credentialed/live trading,
  private-client data, proprietary order flow, and pending orders. Matches were
  confined to prohibition documentation, input-rejection contracts, and tests;
  no executable or public operational API was found.
- Confirmed `pyproject.toml`, `vali.__version__`, and run-manifest metadata
  remain consistent at package version `0.3.0`. `v0.1` is only the migration
  release-candidate label; no package version was changed.
- Confirmed imports resolve from `src/vali`, never quarantined build artifacts;
  canonical and compatibility configs and fixtures remain available; and the
  frozen Google Trends manifest hash remains
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
- No source logic, formula, methodology, provider behavior, normalized output,
  config/TOML behavior, CLI behavior, fixture content, existing test behavior,
  report output, artifact, manifest field, schema, execution policy, fee model,
  or legacy compatibility surface changed.
- No live API behavior, dependency, credential use, private input, proprietary
  flow, order submission, live trading, or `P_flow` was introduced.
- Full result after Step 4L: **149 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Files created:
  - `V0_1_RELEASE_CANDIDATE.md`
  - `FINAL_VALIDATION_REPORT.md`
  - `tests/contract/test_final_release_candidate.py`
- File modified:
  - `MIGRATION_LOG.md`
- Created local commit `96b57645517bf93469184e0ce8a51c1f61a9adb5`
  with subject `migration: prepare v0.1 release candidate`.
- The repository was cleared to exit the 4-series and enter 5-series
  operational research readiness. This is research-engine readiness, not
  evidence of alpha or trading readiness.
- Before Step 5A, local editor state at `.vscode/` was reviewed and ignored in
  follow-up hygiene commit `630f142066635e1d1291d3780e953ec181e1652e`.
  The local file was preserved and no source or test behavior changed.

## Step 5A - Empirical validation plan and falsification gates

Completed 2026-06-24.

- Created `docs/operational/` and registered the canonical experiment
  `fed_easing_kxfed_v1` before empirical evaluation.
- Added `docs/operational/5A_EMPIRICAL_VALIDATION_PLAN.md` defining the primary
  and null hypotheses; market, historical-frequency, sticky-prior,
  permutation, and price-only baselines; forecast, timing, regime,
  execution-aware, and robustness metrics; validity and falsification gates;
  conservative acceptance categories; and explicit claim boundaries.
- Added `docs/operational/FALSIFICATION_GATES.md` covering leakage, post-hoc
  selection, prohibited inputs, point-in-time and baseline failure,
  walk-forward and regime instability, composition drift, depth/capacity,
  provisional fees, provider uncertainty, specification drift, and
  overclaiming.
- Added `docs/operational/EXPERIMENT_REGISTRY.md` with the canonical config,
  frozen Google Trends feature manifest, Kalshi KXFED market family, and the
  status `registered, not yet empirically validated`.
- Added `tests/contract/test_operational_research_plan.py` with six
  deterministic documentation and prohibited-surface checks. It uses no live
  API, credentials, or mutable empirical data.
- The frozen Google Trends manifest hash remains
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
- No empirical alpha claim or trading-readiness claim was made. Passing Step
  5A authorizes only disciplined data-availability and empirical validation
  work.
- No source logic, methodology, formula, provider behavior, normalized output,
  config/TOML behavior, CLI behavior, fixture content, existing test behavior,
  report output, artifact, manifest field, schema, execution policy, or fee
  model changed.
- No live API behavior, network dependency, credential use, private input,
  proprietary flow, order submission, live trading, or `P_flow` was introduced.
- Full result after Step 5A: **155 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
- Files created:
  - `docs/operational/5A_EMPIRICAL_VALIDATION_PLAN.md`
  - `docs/operational/FALSIFICATION_GATES.md`
  - `docs/operational/EXPERIMENT_REGISTRY.md`
  - `tests/contract/test_operational_research_plan.py`
- File modified:
  - `MIGRATION_LOG.md`
- Created local commit `dd8e67c286c8b0321addcf1c7da290d184add86c`
  with subject `research: define empirical validation plan`.
- Step 5A predeclared the hypotheses, baselines, metrics, falsification gates,
  and acceptance categories without making an alpha or trading-readiness claim.

## Step 5B - Data availability audit and experiment manifest

Completed 2026-06-24.

- Created `experiments/fed_easing_kxfed_v1/EXPERIMENT_MANIFEST.md` with the
  registered identity, hypothesis/null, required inputs and baselines, later
  output families, and allowed sufficiency decisions.
- Created `experiments/fed_easing_kxfed_v1/DATA_AVAILABILITY_AUDIT.md` from
  local repository files only. No live provider call, credential, or new
  provider output was used.
- Created machine-readable
  `experiments/fed_easing_kxfed_v1/data_availability_manifest.json` and selected
  `insufficient_due_to_missing_attention_history`.
- The local public Kalshi capture contains 34 mapped EASING events, 66,465
  hourly bid/ask rows from December 2021 through June 2026, 42,168 trades in a
  separate capture, and one observed-depth snapshot. Historical quotes contain
  no book depth, and mixed raw/normalized runs remain quarantined.
- All 34 mapped event rows contain outcomes (28 outcome 0 and 6 outcome 1), but
  the latest outcome requires settlement-availability verification before
  training. Outcomes are absent from the quote table and remain governed by
  label-isolation contracts.
- The only local Google Trends attention rows are a three-date `fixture-v1`
  response from June 19–21, 2026. It has stable UTC retrieval serialization but
  is not empirical history and cannot supply the 30-prior-observation warm-up
  or a pre-decision intersection with the resolved meetings.
- `data/raw/` and `data/processed/` are empty, and the canonical TOML resolves
  to four absent analysis-ready inputs under `configs/experiments/data/`.
- Updated `docs/operational/EXPERIMENT_REGISTRY.md` with the experiment/audit
  paths, machine manifest, 5B decision, and explicit not-yet-validated status.
- Added `tests/contract/test_data_availability_manifest.py` with six
  deterministic identity, parsing, decision, claim-boundary, availability, and
  prohibited-surface checks.
- The common intersection is sufficient for fixture validation only, not
  exploratory or proper empirical walk-forward validation. Data collection or
  reconstruction and a repeated availability audit are required before 5C.
- The frozen Google Trends manifest hash remains
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
- No source logic, methodology, formula, provider behavior, normalized output,
  config/TOML behavior, CLI behavior, fixture content, existing test behavior,
  report output, artifact, manifest field, schema, execution policy, or fee
  model changed.
- No alpha or trading-readiness claim, live API behavior, network dependency,
  credential use, private input, proprietary flow, order submission, live
  trading, or `P_flow` was introduced.
- Full result after Step 5B: **161 passed, 0 failed** using
  `& '.\work\.venv\Scripts\python.exe' -m pytest -q`.
