# ADR 0003: Point-in-Time Data and Label Isolation

## Status

Accepted - 2026-06-23

## Context

Behavioral series may be revised, market data arrives asynchronously, and event
outcomes are known only after the research decision. Keeping labels beside
signal-time rows makes accidental leakage possible even when current formulas
do not reference them.

## Decision

All observations must carry observation time, public availability time,
vintage, and source. At a cutoff, only then-available values may be selected.
Normalization is prior-only and shifted. Outcomes are stored separately and
may be joined only for calibration training, walk-forward scoring, settlement,
and post-run reporting. Signal, regime, and decision tables must not contain
outcomes.

## Consequences

Leakage tests are mandatory. The current inclusion of outcomes in daily market
tables is a documented migration issue; this ADR does not change code during
the governance step.

