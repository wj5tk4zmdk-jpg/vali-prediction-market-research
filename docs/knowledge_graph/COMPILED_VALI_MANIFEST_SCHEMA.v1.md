# Compiled VALI Manifest Schema v1

Status: schema contract only. This document defines a future flat handoff
manifest from a reviewed knowledge graph into the VALI research engine. It does
not implement `vali kg compile`. It does not implement `vali backtest --manifest`.
It does not implement runtime graph traversal, provider ingestion, empirical
validation, live APIs, credentials, order submission, live trading, or `P_flow`.
Boundary phrase: this schema does not implement `vali kg compile`.
Boundary phrase: this schema does not implement `vali backtest --manifest`.
Boundary phrase: this schema does not implement runtime graph traversal.

## Purpose

The compiled VALI manifest is the boring runtime seam between a rich reviewed
knowledge graph and the methodology-locked VALI engine.

```text
Frozen graph -> preflight report -> compiled manifest -> VALI engine
```

The manifest carries a frozen claim into flat, auditable runtime inputs. It does
not compute `A`, `P`, `gA`, `gP`, `S_t`, `M_t`, regimes, forecasts, returns, or
validation evidence.

## Required top-level fields

| Field | Required | Meaning |
|---|---:|---|
| `schema_version` | yes | Must be `compiled_vali_manifest.v1`. |
| `manifest_id` | yes | Stable identifier for this compiled handoff. |
| `created_at` | yes | Timestamp of manifest compilation. |
| `source_graph` | yes | Graph identity, version, freeze, hash, and preflight linkage. |
| `event_family` | yes | Event-family, terminal-measure, and Clear Horizon identity. |
| `p_side` | yes | Flat public/executable Priced Conviction mapping inputs. |
| `a_side` | yes | Flat public Behavioral Attention feature inputs. |
| `relationships` | yes | Frozen relationship metadata for audit and falsification. |
| `falsification_gates` | yes | Predeclared gates carried from the graph. |
| `claim_boundaries` | yes | Claim and data-use boundaries. |
| `runtime_constraints` | yes | Hard constraints preventing graph overreach at runtime. |

## `source_graph`

`source_graph` must include:

- `graph_id`;
- `graph_version`;
- `graph_hash`;
- `freeze_status`;
- `review_record`;
- `preflight_report_hash`; and
- `preflight_schema_version`.

A future compiler must verify that the preflight report's `graph_hash` matches
the graph hash used for compilation. Mismatches are blocking errors.

## `p_side`

The `p_side` block describes public/executable Priced Conviction inputs in flat
form. It must include a `markets` list. Each market entry must include:

- `venue`;
- `series_ticker`;
- `event_ticker`;
- `market_ticker`;
- `normalized_contract_id`;
- `operator`;
- `threshold`;
- `terminal_measure_id`;
- `settlement_source`;
- `cutoff_rules`;
- `clear_horizon_id`;
- `price_source_policy`;
- `liquidity_policy`;
- `depth_availability`; and
- `exclusion_status`.

The manifest may identify missing or unavailable historical depth. It must not
infer historical depth from volume, open interest, or trade history.

## `a_side`

The `a_side` block describes public Behavioral Attention inputs in flat form.
It must include:

- `composition_policy`;
- `weight_policy`;
- `features`.

The default composition policy should be `equal_weight` unless a future,
separately approved methodology predeclares another policy before validation.

Every feature entry must include:

- `feature_id`;
- `concept_id`;
- `query_id`;
- `source`;
- `query_text`;
- `geo`;
- `frequency`;
- `polarity`;
- `transform`;
- `availability_lag`;
- `missing_policy`;
- `required`;
- `contamination_risks`;
- `expected_lead_days`; and
- `evidence_status`.

`feature_id` should use the namespace:

```text
feature.{event_family}.{concept_id}.{query_id}
```

`polarity` must be exactly `1` or `-1`. In documentation, these correspond to
`+1` or `-1` multipliers on the feature contribution. Positive polarity means
the feature is aligned toward the target outcome; negative polarity means the
feature is inverted before composition.

## Runtime constraints

The manifest must include this boundary block:

```json
{
  "runtime_constraints": {
    "no_graph_traversal_required": true,
    "no_learned_weights": true,
    "no_dynamic_query_selection": true,
    "lag_metadata_usage": "documentation_and_falsification_only",
    "lag_metadata_constraint": "VALI engine MUST NOT use expected_lead_days to tune rolling windows or entry/exit timing"
  }
}
```

Expected lead/lag metadata may be used for review, documentation, reporting, and
falsification analysis. It must not tune rolling windows, standardization
windows, regime settings, entry thresholds, exit thresholds, confirmation
periods, position sizing, or execution timing.

## Example

```json
{
  "schema_version": "compiled_vali_manifest.v1",
  "manifest_id": "compiled:example_graph:hormuz_normalization:v1",
  "created_at": "2026-06-26T16:00:00Z",
  "source_graph": {
    "graph_id": "example_graph:hormuz_normalization:v1",
    "graph_version": "v1",
    "graph_hash": "sha256:example",
    "freeze_status": "frozen",
    "review_record": "REVIEW_RECORD.v1.json",
    "preflight_report_hash": "sha256:preflight-example",
    "preflight_schema_version": "kg_preflight.v1"
  },
  "event_family": {
    "event_family_id": "maritime_chokepoint_normalization",
    "terminal_measure_id": "hormuz_traffic_normalization",
    "clear_horizon_id": "clear_horizon:hormuz:v1"
  },
  "p_side": {
    "markets": [
      {
        "venue": "kalshi",
        "series_ticker": "KXHORMUZNORM",
        "event_ticker": "TBD",
        "market_ticker": "TBD",
        "normalized_contract_id": "normalized_contract:hormuz:v1",
        "operator": "TBD",
        "threshold": "TBD",
        "terminal_measure_id": "hormuz_traffic_normalization",
        "settlement_source": "contract_defined_settlement_source",
        "cutoff_rules": "TBD",
        "clear_horizon_id": "clear_horizon:hormuz:v1",
        "price_source_policy": "public_executable_prices",
        "liquidity_policy": "configured_spread_depth_staleness_fee_gates",
        "depth_availability": "unknown",
        "exclusion_status": "review_required"
      }
    ]
  },
  "a_side": {
    "composition_policy": "equal_weight",
    "weight_policy": "frozen_equal_weight",
    "features": [
      {
        "feature_id": "feature.maritime_chokepoint_normalization.oil_supply_disruption.q_oil_supply_disruption_001",
        "concept_id": "attention_concept:oil_supply_disruption",
        "query_id": "attention_query:q_oil_supply_disruption_001",
        "source": "Google Trends official API",
        "query_text": "oil supply disruption",
        "geo": "TBD",
        "frequency": "daily",
        "polarity": -1,
        "transform": "log1p",
        "availability_lag": "T-2",
        "missing_policy": "reject_required",
        "required": true,
        "contamination_risks": ["oil-price news", "unrelated producers"],
        "expected_lead_days": [1, 14],
        "evidence_status": "hypothesized"
      }
    ]
  },
  "relationships": [
    {
      "edge_id": "edge_oil_supply_leads_measure",
      "from": "AttentionConcept:oil_supply_disruption",
      "to": "TerminalMeasure:hormuz_traffic_normalization",
      "relationship": "likely_leads",
      "expected_direction": "negative_toward_normalization",
      "expected_lead_days": [1, 14]
    }
  ],
  "falsification_gates": [],
  "claim_boundaries": [
    "no_alpha_claim",
    "no_trading_readiness_claim",
    "public_data_only",
    "no_private_data",
    "no_proprietary_order_flow",
    "no_credentials",
    "no_live_trading",
    "no_order_submission",
    "no_P_flow"
  ],
  "runtime_constraints": {
    "no_graph_traversal_required": true,
    "no_learned_weights": true,
    "no_dynamic_query_selection": true,
    "lag_metadata_usage": "documentation_and_falsification_only",
    "lag_metadata_constraint": "VALI engine MUST NOT use expected_lead_days to tune rolling windows or entry/exit timing"
  }
}
```

## Relationship to VALI runtime

The VALI engine consumes flat inputs only after a future implementation is
approved. It remains responsible for deterministic computation of public
Behavioral Attention `A`, public/executable Priced Conviction `P`, attention
velocity `gA`, price velocity `gP`, signed divergence `S_t`, divergence
magnitude `M_t`, regimes, walk-forward validation, and execution-aware
simulation.

The compiled manifest must not contain learned weights, private data,
proprietary order flow, credentials, live trading authorization, order
submission instructions, or `P_flow`.

## Claim boundaries

The compiled manifest is not alpha evidence and not trading-readiness evidence.
It is a frozen handoff contract. Validation evidence, if later produced, must
be appended separately without rewriting the frozen graph or compiled manifest.
