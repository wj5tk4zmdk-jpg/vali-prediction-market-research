# VALI: Kalshi Quant Researcher Case Study

## Project summary

VALI is a minimum viable public-data prediction-market research engine. It
tests whether divergence between public Behavioral Attention and executable
market-implied Priced Conviction contains incremental out-of-sample information
about event resolution.

I built the project from methodology through validation infrastructure: data
contracts, deterministic signal math, read-only provider adapters, leakage
controls, walk-forward tests, execution caveats, reproducible reports, and
predeclared falsification gates. The project deliberately reports that its
canonical empirical run is blocked rather than dressing fixture results up as
alpha.

## Problem

Prediction markets can incorporate information quickly, but public behavioral
attention may sometimes reveal resolution latency or a change in regime before
price conviction fully adjusts. The research question is whether that public
attention/price divergence adds information beyond the market probability,
historical-frequency, sticky-prior, permutation, and price-only baselines.

## Approach

- `A`: frozen, public behavioral-attention features with documented polarity,
  lag, missingness, and provenance.
- `P`: public or executable market-implied probability, subject to spread,
  freshness, and liquidity checks.
- `S_t = z(gA_t) - z(gP_t)`: signed prior-only velocity divergence.
- `M_t = |S_t|`: divergence magnitude, never a substitute for direction.
- Regimes: attention-leading, market-leading, coupled, or unstable.
- Clear Horizon: whether divergence resolves before price movement rather than
  following it.
- Validation: meeting-grouped expanding walk-forward folds, prior-only
  normalization, label isolation, and predeclared baselines.
- Execution: bid/ask, fees, closures, and observed depth where evidence exists;
  capacity is disabled where it does not.
- Falsification: leakage, post-hoc feature selection, baseline failure,
  single-event dependence, composition drift, and overclaiming are explicit
  failure modes.

## Engineering work

The repository separates domain math, data contracts, typed configuration,
research orchestration, report artifacts, execution simulation, provider
components, and the application/CLI boundary. Kalshi and Google Trends adapters
are decomposed behind compatibility facades, with public-data-only boundaries
and no order-entry surface.

EM-1 added configurable regime-confirmation periods as an execution/backtest
sensitivity overlay with default `1/1` behavior preserved. EM-2 added
`vali confirmation-panel`, a paired robustness report comparing `1/1`, `1/2`,
`2/1`, `2/2`, and `3/3` confirmation arms, including delayed-exit summary and
per-trade decomposition. The raw regime classifier remains methodology-locked.

The repository also contains a final validation report, architecture decisions,
a frozen experiment registry, data-tier policy, and an artifact
quarantine/inventory process that preserves provenance instead of deleting
inconvenient evidence.

## Result

The minimum viable research engine is complete and fixture validation is
reproducible. Canonical alpha validation is not authorized: point-in-time
empirical attention history is missing, mixed Kalshi captures still require
controlled tier reconstruction, historical depth is absent, and the latest
outcome needs settlement-eligibility review.

That is the result of the current phase - not a footnote. The project treats
"insufficient data" as a valid gate rather than a reason to weaken the design.

## Why this matters for Kalshi

The work is directly relevant to new index and model research around event
markets: translating an ambiguous hypothesis into frozen variables, executable
market mappings, falsifiable benchmarks, and operational data requirements. It
also demonstrates the collaboration surface a quant researcher needs across
engineering, product, market design, and trading: clear interfaces, reviewable
assumptions, reproducible outputs, and practical ownership when the data are
messy.

The regime-confirmation panel adds one more desk-relevant discipline: if an
execution buffer looks helpful, the report immediately separates whipsaw
reduction from delayed losses instead of letting a headline PnL delta obscure
the risk.

## Claim boundaries

This case study makes no alpha claim and no trading-readiness claim. It uses no
private Kalshi data, proprietary order flow, client information, or `P_flow`.
It performs no order submission, live trading, or production deployment. The
confirmation panel is execution sensitivity, not a new signal, not classifier
tuning, and not alpha evidence.
