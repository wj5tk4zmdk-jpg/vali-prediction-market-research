# ADR 0004: Internal Fed Easing Contract

## Status

Accepted - 2026-06-23

## Context

The initial research target is binary: whether the Federal Reserve target range
will be lower after the next scheduled FOMC meeting. Venue contracts may use
threshold ladders rather than this direct question.

## Decision

For the Fed pilot, the internal contract is `EASING`: YES means the target-range
upper bound is lower after the scheduled meeting. A venue adapter must preserve
its source event, ticker, side, strike, settlement rule, and mapping rationale.
The current KXFED normalization selects the threshold immediately below the
pre-meeting upper bound and maps internal easing YES to the appropriate
complementary venue side. Ambiguous ladders, missing strikes, non-quarter-point
targets, and unclear settlements are exclusions.

This assumption is specific to the Fed pilot. It is not a universal VALI event
or market design.

## Consequences

Venue details remain in adapters. The core receives a normalized binary public
probability and audit metadata. Extending VALI to other event families requires
a separate target-definition decision.

