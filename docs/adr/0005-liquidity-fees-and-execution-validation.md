# ADR 0005: Liquidity, Fees, and Execution Validation

## Status

Accepted - 2026-06-23

## Context

Forecast-quality analysis can use public prices without historical depth, but
tradability, capacity, and net returns depend on contemporaneous executable
quotes, depth, costs, market status, and closures.

## Decision

Price-quality and execution-liquidity gates remain separate. Simulated buys use
the ask and exits use the bid with correct YES/NO inversion. Position size is
capped by observed executable depth and is never determined by `M_t`. Volume or
open interest cannot substitute for depth. Fee models must be identified and
versioned. Mandatory exits, closures, failed execution, settlement, and snapshot
completeness must be represented explicitly.

## Consequences

Liquidity, fees, closures, and execution validation are methodology-critical,
not cosmetic reporting adjustments. Capacity and net-return claims remain
disabled whenever execution evidence is incomplete. Current generic basis-point
fees and permissive completeness gating are documented migration issues.

