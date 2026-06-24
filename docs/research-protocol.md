# VALI Research Protocol

## Freeze before evaluation

Before inspecting test outcomes, freeze the candidate variable universe,
rationales, transformations, polarities, missing-data policies, availability
lags, signal thresholds, regime parameters, Clear Horizon, liquidity rules,
fee assumptions, and sensitivity windows. Record a freeze date and hashes of
the configuration and manifests. Changes create a new experiment version.

## Point-in-time construction

At each research cutoff, use only observations publicly available by that
cutoff. Standardization uses trailing history shifted by one observation so the
current and future values cannot determine the reference mean or variance.
Later revisions are new vintages and must not overwrite the historical view.

## Train/test rules

- Group all rows by complete FOMC meeting/event.
- Use an expanding window of earlier resolved events.
- Never split one event across train and test.
- Keep outcomes physically separate until training or scoring.
- Fit calibration and any learned parameters only on prior events.
- Evaluate the next event without selecting thresholds or features from it.

## Required reporting records

Every candidate cutoff must produce either a signal record or an exclusion.
Every potential decision must record trade/no-trade status and its reason.
Reports must include:

- missing or unavailable behavioral features;
- stale, wide, or absent market prices;
- unavailable or insufficient depth;
- unstable or ineligible regimes;
- below-threshold signals;
- rejected entries and failed exits;
- unresolved events and insufficient-history folds;
- no-trade rate and liquidity-exclusion rate.

Sensitivity analyses are reported as a fixed panel. Results must not be ranked
and selected after observing performance. Negative and null outcomes remain in
the research record.

