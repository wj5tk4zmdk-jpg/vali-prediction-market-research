# KG-Handoff Operationalization Pilot Friction Log

Status: non-empirical pilot log. This document records operational friction
from the Hormuz draft KG workflow. It is not validation evidence, not an alpha
claim, and not a trading-readiness claim.

Pilot date: 2026-06-26

Pilot case:

```text
configs/knowledge_graph/examples/hormuz_normalization/
```

## Summary

The Hormuz draft graph successfully runs through:

```text
vali kg preflight
vali kg compile
```

It stops correctly at:

```text
vali backtest --manifest
```

because the compiled manifest is missing `runtime_inputs`. This is a useful
pilot finding: the graph is compileable but not runnable.

## Observed workflow

| Step | Result | Notes |
|---|---|---|
| `vali kg preflight` | Completed | Overall status `unknown`; no blockers. |
| `vali kg compile` | Completed | Produced 8 A-side features. |
| `vali backtest --manifest` | Blocked | Missing `runtime_inputs`. |
| Evidence append | Not run | Backtest did not execute. |
| Review packet | Not run | No new evidence was produced. |
| Supersede | Not run | No human-reviewed evidence action exists. |

## Friction items

### F1 — Compileable does not mean runnable

Severity: critical blocker for pilot execution.

The Hormuz draft graph can produce a compiled manifest, but that manifest lacks:

- `runtime_inputs.events`;
- `runtime_inputs.quotes`;
- `runtime_inputs.features`;
- optional `runtime_inputs.trades`;
- `runtime_parameters`.

Without these fields, `vali backtest --manifest` correctly refuses to run.

Recommendation: keep this as a hard boundary. Do not invent data. Add a future
helper or example showing how a human-reviewed graph receives a separate
runnable runtime-input packet.

### F2 — P-side mapping remains review-required

Severity: critical for real pilot readiness.

The Hormuz graph has a Kalshi series ticker, but compiled market fields still
contain review-required placeholders:

- event ticker;
- market ticker;
- operator;
- threshold;
- cutoff rules;
- depth availability.

Recommendation: require human review of the market ladder and normalized
contract mapping before treating the graph as runnable.

### F3 — A-side attention acquisition remains unresolved

Severity: critical for empirical readiness.

The graph contains candidate Google Trends queries, but several fields remain
draft or provider-dependent:

- point-in-time availability;
- revision behavior;
- geography;
- time window;
- query frequency semantics.

Recommendation: do not run empirical validation until point-in-time attention
history is acquired and the query manifest is frozen.

### F4 — Historical depth remains unavailable

Severity: important for execution-aware claims.

The preflight report classifies depth availability as unknown. This is expected
for the current draft. It blocks capacity and tradability claims.

Recommendation: keep execution metrics disabled or explicitly unavailable until
real public snapshots are accumulated.

### F5 — Stale compile-note wording

Severity: UX issue; fixed during pilot.

The pilot exposed that scaffolded compiled manifests still said they were “not
wired to `vali backtest --manifest`.” That became stale after KG-Handoff Step 4.

Resolution: update the compile note to say scaffolded manifests are not
validation eligible and require explicit `runtime_inputs` and
`runtime_parameters` before `vali backtest --manifest`.

## Prioritized next fixes

1. Add a documented runtime-input manifest pattern for fixture pilots.
2. Add a command or guide section that distinguishes “compiled” from “runnable.”
3. Add a small non-empirical runnable fixture manifest that uses synthetic data
   and is clearly labeled fixture-only.
4. Create a human-review checklist for P-side normalized market mapping.
5. Keep Hormuz empirical validation blocked until point-in-time attention data
   and public market mappings exist.

## Claim boundary

This pilot log makes no empirical claim. It does not prove that any Hormuz
attention concept leads any market. It does not prove alpha or trading
readiness. It does not authorize trading and does not use private data,
proprietary order flow, credentials, live trading, order submission, or
`P_flow`.
