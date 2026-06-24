# Attention Data Acquisition Protocol

## A. Purpose

This protocol defines how point-in-time empirical attention history must be
acquired before Step 5C for `fed_easing_kxfed_v1`. The current three-day fixture
is sufficient for deterministic contracts only and is insufficient for
empirical validation. This protocol authorizes neither an alpha claim nor a
trading-readiness claim, and it does not authorize collection by itself.

## B. Frozen manifest

- Feature manifest: `configs/features/google_trends_candidate_v1.csv`
- Frozen manifest hash:
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`

Before Step 5C there may be no feature addition, removal, reordering,
relabeling, polarity change, or post-hoc query expansion. Any proposed change
requires a new registered experiment rather than mutation of this one.

## C. Required attention-history fields

The acquisition record must preserve every field below. This is an acquisition
and provenance contract, not a change to the existing normalized feature
schema.

| Canonical acquisition field | Current implementation field/location | Requirement |
|---|---|---|
| `feature_id` | `feature_id` | Must exactly match the frozen manifest. |
| `query` | Query manifest and `trends_observations.query` | Preserve the exact submitted text. |
| `value` | `features.value` and `trends_observations.value` | Preserve source precision; suppressed values remain missing. |
| `date` | `observation_at` / `observation_date` | Record the represented search-interest date. |
| `retrieved_at` | `trends_observations.retrieved_at`; normalized `vintage` | Timezone-aware UTC retrieval time. |
| `source` | `features.source` | Public source identifier. |
| `source_method` | Raw envelope or acquisition sidecar | Official API/export/manual export method and version. |
| `geo` | Request metadata/raw envelope | Exact geography or empty/global designation. |
| `time_window` | Request metadata/raw envelope | Exact request start/end and aggregation. |
| `is_partial` | `trends_observations.partial` | Must not be inferred from value. |
| `revision_policy` | Run/acquisition sidecar | Document revision guarantees or explicitly mark unknown. |
| `manifest_hash` | `trends_run_manifest.query_manifest_sha256` | Must equal the frozen hash. |
| `collection_batch_id` | `request_id` or explicit batch sidecar | Stable ID linking simultaneous query retrievals. |
| `raw_file_hash` | Raw archive `content_sha256` | Content hash of the immutable raw response/export. |
| `notes` | Acquisition sidecar/audit table | Record anomalies without changing the value. |

The current normalized feature contract also requires `available_at` and
`vintage`. `available_at` must be derived only from documented availability and
the frozen lag; `vintage` must identify the retrieval used. Acquisition-only
metadata stays in immutable raw records or a reviewed sidecar until a separate
schema change is approved.

## D. Acceptable sources

Potentially acceptable sources are:

- the official Google Trends alpha/API export when its authentication,
  retrieval, scaling, quota, revision, and availability semantics are
  documented;
- Google Trends export files when retrieval time, exact query window,
  geography, aggregation, scaling, and revision behavior are documented; and
- another public attention source only if it is predeclared and mapped to the
  frozen manifest before any outcome is inspected.

Acceptance requires immutable raw preservation, hashes, provenance, and the
fields in Section C. “Public” alone is not sufficient.

## E. Quarantine-only sources

These may be archived for review but cannot enter canonical Step 5C without a
separate approval:

- undocumented scraped data;
- manually copied charts without retrieval metadata;
- historical files missing `retrieved_at`;
- files with an unknown query window, geography, or scaling context;
- files using a changed feature universe;
- files whose revision behavior cannot be described; and
- values recomputed after outcome dates without point-in-time provenance.

Reconstructed historical attention without contemporaneous retrieval evidence
must be labeled non-canonical or exploratory. It cannot support canonical
walk-forward claims.

## F. Prohibited sources

The experiment must never use private search logs, search-RAG provider internal
logs, user or client query logs, proprietary attention feeds, private platform
analytics, `P_flow`, proprietary order flow, pending orders, client behavior,
or credentialed-account data. Order submission and live trading are outside the
research system.

## G. Revision and retrieval semantics

Google Trends values may be normalized or revised depending on retrieval
method, query set, geography, aggregation, and time window. Every retrieval
must record `retrieved_at`, the exact query window, geography, batch ID, source
method/version, and raw hash. Cross-batch values cannot be assumed comparable
without official documentation or a predeclared linking design.

If revision semantics cannot be established, the data can support fixture or
clearly labeled exploratory checks only. It cannot support canonical
point-in-time walk-forward claims. Later revisions must be stored as new
vintages and may not overwrite an earlier retrieval.

## H. Minimum coverage before repeating Step 5B

The next availability audit requires:

- daily coverage spanning the meetings selected for
  `fed_easing_kxfed_v1`, beginning early enough to provide at least the frozen
  90-day window and 30 prior eligible observations before each evaluated
  decision;
- point-in-time retrieval or defensible vintage evidence for each observation;
- all six frozen active features, or explicit missingness handled exactly by
  the current required-feature exclusion rule;
- documented T-2 or source-specific availability and partial-period handling;
- immutable raw files and acquisition metadata linked by hashes and batch IDs;
- no broadening of the candidate feature universe; and
- no outcome label in any attention or pre-decision frame.

Coverage should overlap enough of the 34-event market roster to permit the
predeclared minimum of 16 prior resolved meetings and meaningful test folds.

## I. Acquisition status

- **Status:** `not_acquired`
- **Reason:** Only three days of Google Trends `fixture-v1` data currently
  exist. Canonical empirical attention history is missing.
- **Next gate:** Repeat Step 5B after a separately authorized, documented
  acquisition and provenance review. Step 5C remains unauthorized.
