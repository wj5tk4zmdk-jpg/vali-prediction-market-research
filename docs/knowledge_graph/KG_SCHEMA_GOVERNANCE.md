# KG-Handoff Schema Governance

Status: schema-governance contract only. This document does not implement graph
parsing, preflight checks, manifest compilation, provider ingestion, empirical
validation, live APIs, credentials, order submission, live trading, or `P_flow`.
It does not implement graph parsing. It does not implement runtime graph traversal.

## Purpose

The KG-handoff schemas define how a reviewed VALI knowledge graph may later be
translated into flat, auditable inputs for the methodology-locked VALI research
engine. They exist to prevent schema drift before implementation exists.

The governing separation is:

```text
Knowledge Graph = frozen claim layer
Preflight Report = availability attestation, not performance validation
Compiled Manifest = flat runtime handoff, not graph inference
VALI Engine = deterministic signal math layer
Validation Evidence = appended result layer
```

Schemas are contracts. They are not empirical evidence, alpha evidence,
trading-readiness evidence, or authorization to trade.

## Versioning

KG-handoff schema identifiers use explicit major versions such as
`kg_preflight.v1` and `compiled_vali_manifest.v1`.

- `v1` required fields are immutable after freeze. In other words, v1 required fields are immutable once the schema is frozen.
- Breaking changes require a new major version, such as `v2`.
- Non-breaking clarifications may be documented as patch revisions when they do
  not remove required fields, change field meaning, weaken claim boundaries, or
  broaden runtime authority.
- A compiled manifest must state the schema version it implements.
- A preflight report must state the schema version it implements.

Breaking changes include removing required fields, changing required field
semantics, relaxing public-data boundaries, allowing dynamic query selection,
allowing learned weights, allowing runtime graph traversal in the VALI engine,
or changing the meaning of lag metadata.

## Backward compatibility

A schema change is backward compatible only when older valid documents remain
valid and their methodology meaning is unchanged.

Compatible changes may include:

- adding optional metadata fields;
- adding new non-blocking preflight checks with `severity: "info"` or
  `severity: "warning"`;
- clarifying examples without changing required fields; and
- adding stricter warnings that do not make existing frozen claims ambiguous.

Incompatible changes include:

- removing or renaming required fields;
- changing `polarity` semantics;
- changing hash or freeze requirements;
- treating expected lag metadata as an optimization input;
- adding private, proprietary, credentialed, live-trading, or order-submission
  fields; and
- allowing the VALI engine to traverse the graph directly at runtime.

## Schema lifecycle

Schema lifecycle mirrors the broader knowledge-graph freeze lifecycle:

```text
draft -> review -> frozen -> retired / superseded
```

### `draft`

The schema is being discussed and may change. Draft schemas are not canonical
runtime contracts and must not be used to make empirical claims.

### `review`

The schema is stable enough for human review. Review checks should verify
required fields, examples, prohibited behaviors, public-data boundaries, and
compatibility with VALI 1.0.

### `frozen`

The schema is a versioned handoff contract. Frozen schemas are changed only by
patch clarification or by issuing a new major version.

### `retired` / `superseded`

Old schemas remain part of provenance. They must not be silently edited or
deleted. A replacement schema should identify the version it supersedes and why.

## Claim boundaries

KG-handoff schemas make no alpha claim and no trading-readiness claim. A schema
can say what a valid preflight report or compiled manifest must contain; it
cannot say that a hypothesis works.

Every schema must preserve these boundaries:

- no empirical alpha claim;
- no trading-readiness claim;
- no private data;
- no proprietary order flow;
- no credentials;
- no live trading;
- no order submission;
- no `P_flow`;
- no automatic legal interpretation; and
- no automatic rejection of failed concepts without human review and a
  superseding graph version.

## Forbidden behaviors

KG-handoff schemas must explicitly prohibit:

- learned attention weights unless separately predeclared and validated under a
  future approved methodology;
- dynamic query selection after observing performance;
- runtime graph traversal by the VALI signal engine;
- using expected lag metadata to tune rolling windows, regime settings, entries,
  exits, or execution timing;
- private or proprietary inputs;
- credentials, live APIs, live trading, and order submission;
- `P_flow`; and
- rewriting frozen graph hypotheses after validation evidence is known.

## Relationship to VALI

The schemas define the handoff seam. They do not change VALI formulas.

The compiled manifest may provide:

- A-side feature eligibility, query identity, polarity, transform, missingness,
  and provenance metadata;
- P-side market and normalized-contract mapping metadata;
- Clear Horizon identity;
- graph and preflight hashes;
- exclusions and claim boundaries; and
- expected relationship metadata for documentation and falsification.

The VALI engine remains responsible for computing public Behavioral Attention
`A`, public/executable Priced Conviction `P`, attention velocity `gA`, price
velocity `gP`, signed divergence `S_t`, divergence magnitude `M_t`, regimes,
walk-forward validation, and execution-aware simulation under VALI 1.0.

Expected lag metadata is not a runtime tuning input.
