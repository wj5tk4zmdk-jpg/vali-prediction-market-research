# Step 5A Empirical Validation Plan

## A. Purpose

This pre-analysis plan defines how VALI v0.1 will be judged before empirical
work begins. It freezes the experiment, hypotheses, baselines, metrics,
validity gates, falsification conditions, acceptance categories, and claim
boundaries. No empirical alpha claim has been established.

## B. Canonical experiment

The registered experiment is the Fed easing / Kalshi KXFED-oriented research
setup. It uses public Behavioral Attention `A` and public or executable
market-implied Priced Conviction `P`. VALI measures attention velocity `gA`,
price velocity `gP`, signed divergence `S_t`, divergence magnitude
`M_t = abs(S_t)`, and the predeclared regime classification.

Evaluation must preserve the Clear Horizon, use prior-only normalization, keep
labels outside signal-time frames, and group walk-forward folds by meeting.
Execution-aware simulation is permitted only where contemporaneous executable
price and observed-depth evidence support it. Forecast evaluation may proceed
without historical depth, but capacity and tradability claims may not.

## C. Primary hypothesis

VALI's predeclared public attention/price divergence measures contain
incremental resolution information beyond market-implied probability,
historical-frequency, and naive event-prior baselines when evaluated strictly
out of sample using prior-only normalization and point-in-time data.

## D. Null hypothesis

The null hypothesis is that VALI provides no incremental predictive or timing
value beyond market-implied probability, historical-frequency baselines, or
naive event-prior baselines after accounting for leakage, liquidity, fees,
missingness, and data availability.

## E. Required baselines

Every canonical evaluation must include:

- the executable or otherwise eligible market probability at the decision
  cutoff;
- the prior-only historical easing frequency available before each test event;
- a no-change or sticky-prior forecast that carries the last eligible market
  probability forward;
- a seeded random or within-event permutation baseline that preserves the
  declared event and time structure; and
- a price-only momentum or `gP` baseline, where the available history supports
  the same prior-only construction.

VALI must not be compared only with a weak or retrospectively chosen baseline.

## F. Required metrics

### Forecast quality

- Brier score is the primary proper scoring rule.
- Log loss is reported with the declared probability clipping where numerically
  safe.
- Calibration is reported by predeclared probability buckets with counts.
- Directional hit rate is secondary evidence and cannot override proper scores.

Score differences must be computed out of sample by event. Event-level
uncertainty intervals must be reported when sample size permits; folds and
excluded events remain visible even when an interval is not reliable.

### Timing

- Clear-Horizon distribution and event coverage;
- lead/lag between `A` movement and `P` movement; and
- whether divergence resolves before price movement or merely follows it.

### Regimes

- performance and coverage by regime;
- performance by predeclared divergence-magnitude bucket; and
- stability of direction and coverage across walk-forward folds.

### Execution awareness

- simulated P&L only for complete executable snapshots;
- all fee results labeled provisional while the fee model is provisional; and
- capacity and tradability metrics disabled when historical depth is
  unavailable rather than inferred from volume or open interest.

### Robustness

- leave-one-event-out sensitivity;
- feature-family sensitivity without post-hoc replacement features;
- missingness and fixed-composition sensitivity; and
- date-cutoff sensitivity using only predeclared alternative cutoffs.

## G. Data validity gates

A run is invalid unless all applicable hard gates pass:

- the frozen feature-manifest hash is unchanged;
- every research input is public and its provenance is documented;
- no private, proprietary, client, pending-order, or order-flow input is used;
- observation, public-availability, and vintage timestamps exist where the
  contract requires them;
- outcome labels are physically isolated from signal-time and pre-decision
  frames;
- normalization and calibration use prior observations only;
- internal event identity is stable and uniquely maps to the EASING contract;
- no out-of-manifest feature enters `A`;
- optional-feature missingness follows exactly the frozen exclusion or
  reweighting rule, with composition audited; and
- provider fixture provenance and raw-data provenance are documented.

## H. Falsification gates

The canonical hypothesis is falsified or the run is invalid if any of these
conditions applies:

- apparent value requires changing features or thresholds after outcomes are
  inspected;
- outcome labels enter signal-time or pre-decision frames;
- the signal disappears in grouped walk-forward evaluation;
- one event or anomalous period drives the result;
- VALI fails to improve on market-probability and historical-frequency
  baselines out of sample;
- divergence follows market movement rather than providing lead information;
- performance requires missingness-driven composition drift;
- a capacity or tradability claim relies on unavailable historical depth;
- the conclusion changes materially with the provisional fee assumption; or
- the result requires private inputs, proprietary flow, `P_flow`, credentials,
  order submission, or live trading.

Failure is a valid research result and must be reported without retuning the
registered experiment into success.

## I. Acceptance thresholds

### Fail

Classify the experiment as **Fail** if leakage is detected, the frozen manifest
changes, valid point-in-time data are unavailable, VALI shows no out-of-sample
improvement over the required baselines, any improvement exists only in sample,
an execution claim requires unavailable depth, or a prohibited input appears.

### Promising but exploratory

Classify the result as **Exploratory** when direction is promising but the event
sample is small, VALI improves on only some baselines, the event-level
uncertainty interval includes zero, leave-one-event-out analysis reverses the
conclusion, or capacity cannot be evaluated. Exploratory results authorize no
alpha or trading claim.

### Proceed to Step 5B or 5C

Proceed when data availability is sufficient to run the canonical validation
honestly, every hard validity gate passes, baselines and metrics remain
predeclared, all caveats are documented, and no alpha or trading claim is made.
This is a readiness threshold, not a performance threshold.

### Potential alpha evidence, not trading readiness

Potential alpha evidence would require out-of-sample improvement over the
predeclared baselines, robustness across folds and sensitivity checks, evidence
of lead time rather than post-price reaction, and transparent failure modes.
Execution-aware evidence counts only where executable price, depth, fees, and
closures are observed or defensibly specified. Even this category is not
trading readiness.

## J. Claim boundaries

- Passing Step 5A does not prove alpha.
- Passing Step 5A does not authorize trading.
- Passing Step 5A authorizes only disciplined empirical validation.
- Any alpha claim requires later out-of-sample empirical evidence.
- Any trading claim requires later execution, depth, fee, capacity, operational,
  and compliance validation.

## K. Next step

The next step is **Step 5B — data availability audit and experiment manifest**.
Step 5A authorizes that audit but does not authorize live collection or an
empirical performance claim.
