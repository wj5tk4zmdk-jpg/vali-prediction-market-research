# KG Preflight Report Schema v1

Status: schema contract only. This document defines the shape of a future
availability preflight report. It does not implement `vali kg preflight`, graph
parsing, provider calls, empirical validation, live APIs, credentials, order
submission, live trading, or `P_flow`.

## Purpose

A KG preflight report answers one question:

> Is this reviewed graph likely runnable from documented, point-in-time public
> data sources?

It is an availability attestation, not a performance check. It is not alpha
evidence, not trading-readiness evidence, and not permission to run a canonical
empirical validation.

## Required top-level fields

| Field | Required | Meaning |
|---|---:|---|
| `schema_version` | yes | Must be `kg_preflight.v1`. |
| `graph_id` | yes | Stable graph identifier under review. |
| `graph_hash` | yes | Hash of the graph files checked by preflight. |
| `checked_at` | yes | Timestamp when availability checks were performed. |
| `overall_status` | yes | One of `pass`, `fail`, or `unknown`. |
| `checks` | yes | List of individual availability checks. |
| `blockers` | yes | List of blocking check IDs or plain-language blockers. |
| `warnings` | yes | List of non-blocking warnings. |
| `claim_boundary` | yes | Explicit non-performance and non-alpha boundaries. |

## Required check fields

Every item in `checks` must include:

| Field | Required | Meaning |
|---|---:|---|
| `check_id` | yes | Namespaced check identifier such as `preflight.check.attention_source_available`. |
| `status` | yes | One of `pass`, `fail`, or `unknown`. |
| `severity` | yes | One of `critical`, `warning`, or `info`. |
| `scope` | yes | Node, edge, query, market, or graph scope being checked. |
| `evidence` | yes | Short public-data availability note or missing-evidence note. |
| `blocking` | yes | Boolean indicating whether failure blocks compile eligibility. |

`check_id` values must be namespaced under `preflight.check.*` so the check
suite is greppable and versionable.

## Required check suite

The v1 preflight schema requires checks covering:

- `preflight.check.graph_manifest_exists`;
- `preflight.check.graph_hash_available`;
- `preflight.check.attention_source_available`;
- `preflight.check.point_in_time_availability_documented`;
- `preflight.check.revision_behavior_documented`;
- `preflight.check.query_source_geo_frequency_present`;
- `preflight.check.p_side_market_mapping_present`;
- `preflight.check.terminal_measure_present`;
- `preflight.check.clear_horizon_present`;
- `preflight.check.settlement_source_present`;
- `preflight.check.required_timestamps_available`;
- `preflight.check.historical_market_fields_available`;
- `preflight.check.depth_availability_classified`.

Depth must be classified as observed, unavailable, or unknown. Historical
volume, open interest, or trades must not be used to infer historical order-book
depth.

## Example

```json
{
  "schema_version": "kg_preflight.v1",
  "graph_id": "example_graph:hormuz_normalization:v1",
  "graph_hash": "sha256:example",
  "checked_at": "2026-06-26T16:00:00Z",
  "overall_status": "fail",
  "checks": [
    {
      "check_id": "preflight.check.attention_source_available",
      "status": "unknown",
      "severity": "critical",
      "scope": "AttentionQuery:q_oil_supply_disruption_001",
      "evidence": "Official point-in-time provider access has not been documented.",
      "blocking": true
    }
  ],
  "blockers": ["preflight.check.attention_source_available"],
  "warnings": [],
  "claim_boundary": [
    "availability_only",
    "not_performance_validation",
    "not_alpha_evidence",
    "not_trading_readiness_evidence",
    "public_data_only"
  ]
}
```

## Compile eligibility

A future compiler may consume a preflight report only when:

- `schema_version` is `kg_preflight.v1`;
- `graph_hash` matches the current graph hash;
- all critical blocking checks pass; and
- unresolved warnings are preserved in the compiled manifest.

If the graph hash and preflight hash diverge, compilation must fail. A stale
preflight report cannot silently authorize compilation.

## Claim and data boundaries

Preflight is not performance validation. It must not inspect outcomes, optimize
features, select queries based on results, tune lag windows, or weaken
falsification gates.

The preflight schema prohibits private data, proprietary order flow,
credentials, live trading, order submission, live APIs as an execution surface,
and `P_flow`. It authorizes no alpha claim and no trading-readiness claim.
