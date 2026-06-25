# VALI Knowledge Graph Freeze Policy

Status: documentation and registry-governance policy. This file defines review,
freeze, and deterministic hash expectations for VALI knowledge graph registry
objects. It does not implement runtime graph parsing, market ingestion,
attention acquisition, empirical validation, live APIs, credentials, order
submission, live trading, or `P_flow`.

## Purpose

The knowledge graph exists to represent Kalshi markets, contract templates,
event families, public attention concepts, and claim boundaries as reviewed,
versioned research objects. A frozen graph records the pre-validation research
claim before outcomes and validation results are known.

This policy answers:

- when a graph object is still a draft;
- when human review is required;
- when a graph object may be frozen;
- how frozen graph files are identified;
- how changes are tracked; and
- how later execution, reporting, or code changes can be shown not to have
  quietly altered the original research claim.

Hashes prove provenance and change detection. They are not evidence of empirical
validity, alpha, tradability, or trading readiness.

## Lifecycle

```text
draft
  -> human_review_required
  -> reviewed
  -> frozen
  -> validation_eligible
  -> retired / superseded
```

### `draft`

A draft graph object is a working research artifact. It may contain unresolved
contract rules, missing source hierarchy, draft Clear Horizon fields,
hypothesized attention concepts, candidate queries, or unresolved contamination
risks.

Draft graph objects are not research inputs. They must not be used as canonical
validation inputs, frozen attention manifests, trading signals, alpha evidence,
or trading-readiness evidence.

### `human_review_required`

Human review is required when any methodology-critical field is unresolved,
ambiguous, newly introduced, or claim-sensitive. This includes terminal
measures, settlement sources, contract-template applicability, comparison
operators, thresholds, time periods, Clear Horizons, attention concepts,
attention queries, contamination risks, and claim boundaries.

`human_review_required` is a blocking status. It allows documentation and
discussion, but it does not allow the graph to be treated as frozen or
validation eligible.

### `reviewed`

Reviewed means the relevant fields have been checked against public rules,
public source documentation, and VALI methodology boundaries. Reviewed does not
mean validated. It does not prove that a concept leads a market, that a query is
useful, or that a strategy is tradable.

### `frozen`

Frozen means the graph object represents the pre-validation research claim. The
frozen object may be used for later validation only after the freeze checklist
passes and the object receives a stable version and hash inventory.

Original frozen hypotheses must not be rewritten after outcomes are known.
Validation evidence is appended, linked, or versioned separately. Any material
change creates a new version rather than mutating the frozen claim.
Any material change creates a new version.

Material changes include changes to terminal measure, settlement source,
contract-template applicability, comparison operator, threshold, time period,
Clear Horizon, event-family membership, attention concept, query wording,
polarity, lag window, contamination risk, falsification gate, claim boundary, or
file membership.

### `validation_eligible`

Validation eligible means the frozen graph has passed the review and freeze
criteria and may be referenced by a later point-in-time validation plan.
Validation eligibility is not empirical validation. It is not an alpha claim and
not a trading-readiness claim.

### `retired` / `superseded`

A retired or superseded graph remains part of the provenance record. It must not
be silently edited or deleted. A replacement graph links to the prior version
through `supersedes` / `superseded_by` metadata.

## Freeze eligibility checklist

A graph cannot be frozen until all applicable checks pass:

- graph manifest exists;
- all files referenced by the manifest exist;
- node and edge registries parse;
- status values parse;
- template mappings parse;
- event family object parses;
- attention concepts are explicitly non-validated or frozen;
- attention queries are explicitly non-validated or frozen;
- relationship edges identify pre-validation or post-validation phase;
- human review status is not missing;
- claim status prohibits alpha and trading-readiness claims unless separately
  validated under VALI methodology;
- private inputs are prohibited;
- proprietary order flow is prohibited;
- order-flow features and `P_flow` are prohibited;
- credentials, live trading, and order submission are prohibited;
- Clear Horizon is identified or marked review-required;
- terminal measure is identified or marked review-required; and
- settlement source is identified or marked review-required.

If a field is unresolved but explicitly marked review-required, the graph may
remain a documented draft. It may not be frozen or validation eligible until the
review-required condition is resolved or formally excluded.

## Deterministic hash policy

KG-3 uses a lightweight deterministic hash policy for provenance:

- files are UTF-8 text;
- line endings are normalized by repository policy;
- JSON files should be serialized with sorted keys for canonical hash
  generation when generated by tooling;
- CSV files preserve header order and row order;
- file-level SHA256 hashes are acceptable for KG-3;
- a graph-level hash may be computed by hashing a sorted list of
  `relative_path:sha256` entries;
- changing any file in the frozen graph changes the graph hash;
- hash inventories should record the relative path, SHA256 hash, and file role;
- graph hashes are for provenance and change detection, not empirical validity.

For self-referential manifests, hash tooling should either hash the manifest
with graph-hash fields set to `null` or exclude the inventory field itself under
a documented rule. KG-3 does not implement hashing; it documents the policy and
inventory format.

## Change tracking

Frozen graph changes are tracked by version rather than by mutation. A later
version must state:

- the prior version it supersedes;
- the files that changed;
- why the change was required;
- whether the change affects research eligibility, attention definition, label
  definition, Clear Horizon, or claim boundary; and
- whether prior validation evidence still applies.

Execution code, reporting templates, provider adapters, and analysis scripts may
evolve after a graph is frozen. Those later changes must not quietly alter the
frozen graph files or the pre-validation research claim. Comparing recorded
file hashes and graph hashes is the lightweight proof that the claim itself did
not move.
Later execution changes must not quietly alter the frozen graph files.

## Claim and data boundaries

This policy preserves VALI 1.0 boundaries:

- no alpha claim without later out-of-sample, execution-aware validation;
- no trading-readiness claim without later execution-aware validation and
  explicitly approved scope;
- no private data;
- no proprietary order flow;
- no credentials;
- no live trading;
- no order submission;
- no `P_flow`; and
- no automated legal interpretation without human review.

Human review and a frozen graph are prerequisites for validation, not substitutes
for validation. Honest null and negative results remain valid outcomes.
