# Evidence Review and Supersession Schema v1

Status: governance and implementation contract. This document describes the
human-reviewed layer after append-only validation evidence.

The purpose of this layer is to let researchers review accumulated evidence,
record explicit human recommendations, and create draft superseding graph
versions without rewriting frozen graph files.

## Implemented commands

```text
vali kg review-packet --graph GRAPH --out REVIEW
vali kg review-packet --graph GRAPH --out REVIEW --recommendations RECOMMENDATIONS --reviewer REVIEWER
vali kg supersede --graph GRAPH --review REVIEW --out-dir OUT_DIR
```

## Review packet

`vali kg review-packet` writes a `kg_evidence_review.v1` artifact. It includes:

- evidence summary;
- target-level recommendation rows;
- claim boundaries;
- human-review status;
- explicit flags showing that recommendations, rejection, and graph version
  bumps are not automatic.

When no human recommendations are supplied, every target remains
`human_review_required`.

Allowed review actions are:

- `human_review_required`
- `retain_for_research`
- `needs_more_evidence`
- `quarantine_pending_review`
- `revise_in_superseding_version`
- `retire_in_superseding_version`

Any action other than `human_review_required` requires:

- explicit reviewer identity;
- `review_status` of `reviewed` or `approved`;
- explicit rationale.

The review layer must not contain production, alpha, trading-readiness, live
trading, or order-submission claims.

## Superseding graph copy

`vali kg supersede` creates a draft superseding graph copy only from an explicit
human-reviewed review packet. It does not mutate the source graph. It does not
delete, prune, or rewrite concepts automatically.

The copied graph manifest records:

- `supersedes`;
- source graph hash;
- review packet path;
- human-reviewed actions;
- `automatic_pruning = false`;
- `automatic_recommendations = false`;
- `automatic_graph_version_bump = false`;
- claim boundaries.

The new copied graph is `draft` and `human_review_required`. It is not frozen,
not validation eligible, not alpha evidence, and not trading-readiness evidence.

## Boundaries

This layer preserves:

- no automatic rejection;
- no automatic recommendations;
- no automatic graph version bumping;
- no mutation of frozen graph files;
- no private data;
- no proprietary order flow;
- no credentials;
- no live trading;
- no order submission;
- no `P_flow`;
- no alpha claim;
- no trading-readiness claim.

## Non-goals

This layer does not:

- integrate evidence back into the backtest engine;
- dynamically exclude failed concepts;
- select future experiments automatically;
- mark a graph as production-ready;
- create trading authorization;
- weaken VALI 1.0 methodology boundaries.
