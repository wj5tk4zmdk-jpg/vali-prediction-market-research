# VALI 1.0 Methodology Contract

VALI is a public-data research framework for measuring divergence between
behavioral attention and market-implied conviction. This document governs the
core implementation; venue adapters and research pilots must conform to it.

## Core quantities

### Behavioral Attention `A`

`A_t` is a frozen, equal-weighted composite of public behavioral features.
Every feature must have a rationale, transformation, polarity, publication lag,
missing-data rule, required/optional status, and point-in-time provenance.
Required missing features produce no signal. Private desk data is prohibited.

### Priced Conviction `P`

`P_t` is a public market probability selected from a qualifying executable
midpoint. A public trade-derived price may be used for research when the quote
is stale, but it must remain non-executable unless contemporaneous depth is
observed. Probabilities are clipped before applying the logit transformation.

### Velocities and divergence

- `gA_t` is the predeclared-window OLS slope of `A_t`.
- `gP_t` is the same-window OLS slope of `logit(P_t)`.
- Both velocities are standardized using shifted, prior-only history.
- `S_t = z(gA_t) - z(gP_t)` is signed divergence.
- `M_t = abs(S_t)` is divergence magnitude and is not a sizing rule.

The baseline velocity window is seven days. Sensitivity windows must be
predeclared and reported together; the best result must not be selected after
testing.

## Regimes

Regimes are classified from rolling lead/lag correlations of standardized
attention and price velocities:

- positive lag: attention-leading;
- negative lag: market-leading;
- zero lag: coupled;
- weak, conflicting, insufficient, or illiquid evidence: unstable.

Full-sample or realized regime labels are evaluation-only and must not enter
signal generation or decisions.

## Clear Horizon

Clear Horizon is the predeclared period over which a divergence is permitted to
resolve. It must be fixed before testing and bounded by the event lifecycle.
Entries must exit on convergence, regime change, stop loss, maximum holding
period, mandatory pre-settlement cutoff, closure, or settlement as applicable.
The horizon must not be optimized after observing outcomes.

Regime confirmation is an optional execution-sensitivity overlay, not a new
signal and not a change to the raw regime classifier. The default confirmation
period of `1` preserves baseline behavior. Values above `1` must be
predeclared sensitivity tests and are not alpha evidence. Stop loss,
convergence, maximum holding period, mandatory pre-settlement exits, failed
mandatory exits, and settlement boundaries remain immediate; trade-count,
spread, and fee deltas require a separately run unbuffered comparison.

## Liquidity and execution

Signal-price quality and execution liquidity are separate gates. Forecasting
may use qualifying public prices without historical depth; simulated trading
and capacity claims require observed contemporaneous executable depth. Volume
or open interest must never be substituted for missing depth.

Execution simulation must use buy-at-ask and sell-at-bid mechanics, side-correct
YES/NO inversion, depth caps, closures, fees, and settlement. `M_t` must not
determine position size.

## Validation and claims

Validation is expanding walk-forward by complete event. No event may be split
between training and test, and no future outcome, vintage, normalization value,
or test observation may affect an earlier result. VALI must be compared with
raw market probability and a prior historical-frequency baseline.

Reports must include exclusions, rejected signals, no-trade rates, calibration,
costs, and liquidity limitations. In-sample results, small samples, descriptive
relationships, or gross returns are not alpha. A null result is acceptable.
