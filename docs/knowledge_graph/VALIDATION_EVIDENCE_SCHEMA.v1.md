# Validation Evidence Schema v1

Status: schema and implementation contract. This document formalizes the
append-only validation evidence concept sketched in
`GRAPH_SCHEMA_SKETCH.md`.

Validation evidence is post-freeze evidence about a graph hypothesis. It is
not part of the frozen pre-validation graph itself. Evidence files are written
beside a graph manifest and are summarized for human review without mutating
the graph files, rewriting the hypothesis, or producing automatic rejection
decisions.

## Purpose

`ValidationEvidence` records the result of an experiment, audit, or
falsification gate against one or more knowledge-graph nodes or edges. It is a
governance artifact for VALI research reviewers. It does not run VALI signal
math, integrate with the backtest engine, authorize trading, or prove alpha.

## Required fields

Every `ValidationEvidence` object must include:

- `id`
- `type`
- `version`
- `source`
- `target_node_ids`
- `metrics`
- `falsification_gate_results`
- `status`
- `claim_status`
- `evidence_status`

Required field semantics:

- `id`: stable evidence identifier, preferably namespaced by experiment.
- `type`: must be `ValidationEvidence`.
- `version`: must be `v1`.
- `source`: object describing the experiment, artifact hashes, or review
  source.
- `target_node_ids`: list of graph node identifiers evaluated by this
  evidence record.
- `metrics`: object of descriptive metric names and values.
- `falsification_gate_results`: list of declared gate results.
- `status`: evidence lifecycle status using the approved evidence-status set.
- `claim_status`: claim boundary labels. v1 evidence must preserve
  `bounded_by_evidence`, `not_alpha_claim`, and
  `not_trading_readiness_claim`.
- `evidence_status`: evidence lifecycle status using the approved
  evidence-status set.

## Optional fields

Optional fields include:

- `target_edge_ids`
- `walk_forward_folds`
- `baselines`
- `execution_evidence`
- `notes`
- `created_at`
- `graph_manifest`
- `graph_hash`
- `append_only`

`execution_evidence`, when present, is descriptive only. It is not trading
authorization and is not evidence of production readiness.

## Approved evidence statuses

The v1 evidence-status set is:

- `hypothesized`
- `candidate`
- `not_validated`
- `validated_exploratory`
- `validated_out_of_sample`
- `failed`
- `quarantined`
- `retired`

Passing summary counts are limited to `validated_exploratory` and
`validated_out_of_sample`. Failing summary counts are limited to `failed`.
Other statuses remain visible for human review and do not trigger automatic
acceptance, rejection, or deletion.

## Claim boundaries

Validation evidence must preserve these claim boundaries:

- `bounded_by_evidence`
- `not_alpha_claim`
- `not_trading_readiness_claim`

Additional standing VALI boundaries still apply:

- no private data;
- no proprietary order flow;
- no credentials;
- no live trading;
- no order submission;
- no `P_flow`;
- no production-readiness claim.

## Append-only storage

Evidence must be stored outside the frozen graph files. The v1 implementation
writes one JSON file per evidence append beside the graph manifest:

```text
validation_evidence_{timestamp}.v1.json
```

Appending evidence must not modify:

- `graph_manifest.v1.json`;
- `event_family.v1.json`;
- `attention_concepts.v1.csv`;
- `attention_queries.v1.csv`;
- `relationship_edges.v1.csv`;
- review records or hash inventories.

The graph hash is recorded on evidence files for provenance. A validation
summary may exclude evidence whose recorded graph hash does not match the
current graph hash, but it must not rewrite or delete that evidence.

## Summary view

`vali kg evidence-summary --graph GRAPH --out SUMMARY` renders a human-readable
summary containing:

- total experiments;
- passing and failing counts;
- status counts;
- key numeric metrics by concept or target node.

The summary is descriptive only. It makes no automatic rejection,
no recommendation, no alpha claim, and no trading-readiness claim. It is
not alpha evidence and not trading-readiness evidence.

## Non-goals

This schema does not:

- integrate evidence into `vali backtest`;
- traverse the graph at signal time;
- select features dynamically;
- change VALI formulas;
- authorize live trading;
- submit orders;
- introduce `P_flow`;
- use private/proprietary data.
