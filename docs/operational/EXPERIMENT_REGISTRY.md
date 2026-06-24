# VALI Experiment Registry

The registry freezes experiment identity before empirical evaluation. New
experiments require a new identifier and reviewed entry; existing outcomes do
not authorize silent changes to a registered experiment.

## `fed_easing_kxfed_v1`

- **Purpose:** Test whether predeclared public attention/price divergence adds
  out-of-sample resolution or timing information for the next scheduled Fed
  easing outcome.
- **Canonical config:** `configs/experiments/fed_easing_v1.toml`
- **Feature manifest:** `configs/features/google_trends_candidate_v1.csv`
- **Frozen manifest hash:**
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`
- **Venue/market family:** Kalshi KXFED / Fed easing-style contracts, as
  currently implemented.
- **Status:** Registered, not yet empirically validated.
- **Allowed claims:** Methodology readiness only.
- **Prohibited claims:** Alpha proven; trading-ready; capacity-validated; live
  deployment ready.

Evaluation is governed by `5A_EMPIRICAL_VALIDATION_PLAN.md` and
`FALSIFICATION_GATES.md`. Registration does not authorize live collection,
credentials, order submission, or trading.
