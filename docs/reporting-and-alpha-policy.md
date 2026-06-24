# Reporting and Alpha Policy

VALI reports are research artifacts, not trading recommendations.

Every empirical report must show:

- sample dates, event count, fold definitions, freeze date, and input/config
  hashes;
- raw-market, historical-frequency, and VALI forecast metrics;
- gross performance and net performance separately;
- spreads, fees, slippage assumptions, closures, depth caps, and settlement;
- no-trade days and no-trade rate;
- rejected signals and their reasons;
- liquidity exclusions and snapshot completeness;
- calibration, sensitivity results, and unresolved divergences;
- limitations caused by missing depth, small samples, revisions, or inferred
  availability.

Capacity and net-return metrics must be disabled when execution validation is
incomplete. Missing execution information must appear as unavailable, not as
zero cost or zero return.

Do not describe results as alpha unless they survive a predeclared,
out-of-sample, execution-aware walk-forward test after realistic costs and
liquidity constraints. In-sample fit, descriptive correlation, a single
successful event, or gross historical returns are not alpha. Null and negative
results must be reported without suppression.

