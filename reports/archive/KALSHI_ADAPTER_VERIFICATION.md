# VALI Kalshi Adapter Verification

Date: 2026-06-23  
Package: `vali-research 0.2.0`

The adapter was verified against Kalshi's public production REST API without
credentials. It contains no order-entry methods.

## Live checks

- Discovery: 39 settled KXFED events, 7 open events, and 98 open markets.
- Settlement mapping: 34 meetings mapped unambiguously to internal EASING
  contracts; 9 exclusions were retained with reasons.
- Hourly historical backfill: 66,465 normalized quote observations across all
  34 mapped events.
- Public trade path: 42,168 normalized trades.
- Current order-book snapshot: 11-market ladder, 96 price levels, and one
  mapped easing quote with observed depth.
- VALI 16:00 ET selection: 3,208 of 10,111 candidate daily cutoffs passed the
  existing 30-minute freshness and spread rules. Historical execution remained
  disabled because candlesticks do not contain observed book depth.

## Regression checks

- 31 automated tests passed.
- Package metadata and import version both report `0.2.0`.
- The original synthetic backtest still produced 3,264 signal rows, 8
  walk-forward forecasts, and 7 simulated trades when actual depth was present.

## Operational gate

Run the supplied cutoff snapshot script for 30 consecutive days and require at
least 99% completeness before enabling execution-aware paper simulation. A real
VALI report also remains blocked until the behavioral feature universe and
point-in-time data are frozen and supplied.
