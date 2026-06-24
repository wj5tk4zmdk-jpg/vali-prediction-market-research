# Experiment Manifest: `fed_easing_kxfed_v1`

## A. Experiment identity

- **Experiment ID:** `fed_easing_kxfed_v1`
- **Status:** Data availability audit complete; not yet empirically validated.
- **Canonical config:** `configs/experiments/fed_easing_v1.toml`
- **Feature manifest:** `configs/features/google_trends_candidate_v1.csv`
- **Frozen feature-manifest hash:**
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`
- **Market family:** Kalshi KXFED / Fed easing-style contracts as currently
  implemented.
- **Outcome family:** Fed policy easing / FOMC-style outcome as currently
  implemented.

## B. Hypothesis and null

The primary hypothesis is that predeclared public attention/price divergence
contains incremental out-of-sample resolution information beyond eligible
market probability, historical-frequency, and naive event-prior baselines when
all point-in-time controls are enforced.

The null hypothesis is that VALI provides no incremental predictive or timing
value after accounting for leakage, liquidity, fees, missingness, and public
data availability.

## C. Required inputs

The experiment requires:

- an event roster with stable event identity and scheduled event dates;
- venue event and market identifiers;
- timestamped market prices or probabilities;
- bid/ask or other executable price evidence where available;
- observed depth and order-book evidence where available;
- Google Trends or other frozen public-attention rows;
- observation, public-availability, retrieval, and vintage timestamps as
  required by the data contract;
- the frozen feature manifest;
- outcome labels held outside signal-time frames; and
- settlement or resolution records supporting each outcome.

## D. Required baselines

- market probability baseline;
- prior-only historical-frequency baseline;
- sticky-prior or no-change baseline;
- seeded random or permutation baseline where appropriate; and
- price-only velocity or momentum baseline where appropriate.

## E. Required output families for Step 5C

A later empirical run must produce:

- forecast-quality table;
- timing and Clear-Horizon table;
- regime-performance table;
- robustness and sensitivity table;
- execution-aware table only where executable snapshots are complete; and
- caveat register covering exclusions, missingness, provenance, and claim
  limits.

## F. Data sufficiency decision rule

Step 5B must select exactly one of:

- `sufficient_for_5C`;
- `sufficient_for_fixture_only_validation`;
- `insufficient_pending_data_collection`;
- `insufficient_due_to_missing_point_in_time_data`;
- `insufficient_due_to_missing_outcomes`;
- `insufficient_due_to_missing_market_history`; or
- `insufficient_due_to_missing_attention_history`.

The decision may be “not enough data yet.” The current decision is
`insufficient_due_to_missing_attention_history`: local Kalshi history is
substantial, but the repository contains only three fixture dates of attention
data and no analysis-ready common historical intersection.
