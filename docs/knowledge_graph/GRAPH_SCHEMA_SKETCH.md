# VALI Knowledge Graph Schema Sketch

Status: documentation-only sketches. These examples are not runtime schemas and
do not imply empirical validation.

## Common node schema

```json
{
  "id": "node_namespace:stable_id",
  "type": "TerminalMeasure",
  "version": "v1",
  "source": {"kind": "public_contract_rule", "reference": null},
  "attributes": {},
  "human_review_status": "human_review_required",
  "frozen_at": null,
  "hash": null,
  "claim_status": "no_empirical_claim",
  "evidence_status": "not_validated"
}
```

## Common edge schema

```json
{
  "id": "edge_namespace:stable_id",
  "type": "likely_leads",
  "version": "v1",
  "source": "attention_concept:oil_supply_disruption",
  "target": "terminal_measure:hormuz_traffic_normalization",
  "relationship_basis": "pre_validation_theory",
  "expected_direction": "negative_toward_normalization",
  "expected_lag_window_days": [1, 14],
  "contamination_risks": [],
  "human_review_status": "human_review_required",
  "frozen_at": null,
  "hash": null,
  "claim_status": "hypothesis_only",
  "evidence_status": "hypothesized"
}
```

## Normalized contract schema

```json
{
  "id": "normalized_contract:market_ticker:v1",
  "type": "NormalizedContract",
  "version": "v1",
  "source": {"market_ticker": null, "rules_reference": null},
  "template_type": null,
  "template_version": null,
  "series_ticker": null,
  "event_ticker": null,
  "market_ticker": null,
  "underlying": null,
  "terminal_measure_id": null,
  "source_agency_ids": [],
  "operator_id": null,
  "threshold_value": null,
  "time_period_id": null,
  "clear_horizon_id": null,
  "first_release_only": null,
  "revision_rule": null,
  "last_trading_rule": null,
  "expiration_rule": null,
  "settlement_contingency": null,
  "human_review_status": "human_review_required",
  "frozen_at": null,
  "hash": null,
  "claim_status": "mapping_only",
  "evidence_status": "not_validated"
}
```

## Event family schema

```json
{
  "id": "event_family:maritime_chokepoint_normalization",
  "type": "EventFamily",
  "version": "v1",
  "source": {"series_tickers": ["KXHORMUZNORM"]},
  "name": "Maritime chokepoint normalization",
  "terminal_measure_ids": ["terminal_measure:hormuz_traffic_normalization"],
  "clear_horizon_id": null,
  "contract_template_ids": [],
  "attention_concept_ids": [],
  "falsification_gate_ids": [],
  "claim_boundary_ids": [],
  "human_review_status": "human_review_required",
  "frozen_at": null,
  "hash": null,
  "claim_status": "no_empirical_claim",
  "evidence_status": "not_validated"
}
```

## Attention concept schema

```json
{
  "id": "attention_concept:oil_supply_disruption",
  "type": "AttentionConcept",
  "version": "v1",
  "source": "pre_validation_research_rationale",
  "event_family_id": "event_family:maritime_chokepoint_normalization",
  "rationale": null,
  "expected_direction": null,
  "expected_lag_window_days": null,
  "contamination_risks": [],
  "query_ids": [],
  "human_review_status": "human_review_required",
  "frozen_at": null,
  "hash": null,
  "claim_status": "hypothesis_only",
  "evidence_status": "hypothesized"
}
```

## Attention query schema

```json
{
  "id": "attention_query:example:v1",
  "type": "AttentionQuery",
  "version": "v1",
  "source": "attention_source:official_public_provider",
  "concept_id": "attention_concept:oil_supply_disruption",
  "query_text": null,
  "geo": null,
  "frequency": "daily",
  "availability_rule": null,
  "revision_rule": null,
  "active": false,
  "human_review_status": "human_review_required",
  "frozen_at": null,
  "hash": null,
  "claim_status": "candidate_only",
  "evidence_status": "hypothesized"
}
```

## Validation evidence schema

```json
{
  "id": "validation_evidence:experiment:fold_set:v1",
  "type": "ValidationEvidence",
  "version": "v1",
  "source": {"experiment_id": null, "artifact_hashes": []},
  "target_node_ids": [],
  "target_edge_ids": [],
  "walk_forward_folds": [],
  "baselines": [],
  "metrics": {},
  "execution_evidence": {},
  "falsification_gate_results": [],
  "human_review_status": "human_review_required",
  "frozen_at": null,
  "hash": null,
  "claim_status": "bounded_by_evidence",
  "evidence_status": "not_validated"
}
```

Evidence is appended after testing. It must not mutate the hash of the frozen
pre-validation theory. No schema object proves alpha or authorizes trading.
Ambiguous fields require human review. No private data, proprietary order flow,
credentials, live trading, order submission, or `P_flow` is permitted.

