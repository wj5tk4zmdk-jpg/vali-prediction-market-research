# VALI Falsification Gates

This checklist is applied before interpreting empirical results. A checked
failure invalidates the run or falsifies the registered hypothesis; it is not a
prompt to retune the experiment.

## Leakage

- [ ] Outcome labels, future vintages, future normalizers, or test-fold
  observations affect an earlier signal or decision.

## Post-hoc feature selection

- [ ] Features, transformations, polarities, thresholds, horizons, or
  sensitivity windows are changed after outcomes are inspected.
- [ ] An out-of-manifest feature enters Behavioral Attention `A`.

## Private or proprietary inputs

- [ ] The result depends on private client data, proprietary order flow,
  pending orders, confidential venue information, credentials, or `P_flow`.

## Point-in-time failure

- [ ] Observation, availability, vintage, event-identity, or provenance fields
  cannot establish what was public at the decision cutoff.
- [ ] Normalization or calibration is not prior-only.

## Baseline failure

- [ ] VALI does not improve out of sample on the market-probability and
  historical-frequency baselines.
- [ ] A favorable conclusion depends on omitting a stronger predeclared
  baseline.

## Walk-forward failure

- [ ] Apparent improvement disappears in meeting-grouped walk-forward folds.
- [ ] One event or anomalous period determines the result.

## Regime instability

- [ ] Regime direction, coverage, or performance is too unstable across folds
  to support the stated interpretation.
- [ ] Divergence follows price rather than leading it.

## Missingness or composition drift

- [ ] Results require undocumented optional-feature reweighting, suppressed
  observations treated as zero, or missingness-driven composition changes.

## Insufficient depth or capacity evidence

- [ ] Capacity, tradability, or execution conclusions require historical depth
  that was not observed.
- [ ] Volume or open interest is substituted for executable book depth.

## Fee-model dependence

- [ ] The conclusion reverses under plausible fee sensitivity while the fee
  model remains provisional.

## Google Trends revision uncertainty

- [ ] Point-in-time claims rely on undocumented official API revision or
  availability behavior.
- [ ] Future revisions alter earlier signals without being isolated by vintage.

## Kalshi API or specification drift

- [ ] Changed fixed-point, order-book, settlement, or historical-routing
  semantics invalidate the recorded normalization or event mapping.

## Overclaiming

- [ ] An exploratory or forecast-only result is described as proven alpha.
- [ ] A result without observed execution evidence is described as
  trading-ready, capacity-validated, or suitable for live deployment.
- [ ] Live trading or order submission is authorized by a research result.
