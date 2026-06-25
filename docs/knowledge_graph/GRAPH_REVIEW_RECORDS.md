# VALI Knowledge Graph Review Records

Status: documentation and registry-governance format. Review records are not
runtime VALI inputs, not empirical validation, and not trading authorization.

## Purpose

A review record documents human review of a knowledge graph object before that
object can move from `draft` toward `reviewed`, `frozen`, or
`validation_eligible`.

The review record answers:

- what graph object was reviewed;
- which files were reviewed;
- who or what reviewer role reviewed it;
- what contract-template assumptions were checked;
- what terminal measure was checked;
- what Clear Horizon was checked;
- what settlement source was checked;
- what attention concepts were reviewed;
- what candidate queries were reviewed;
- what contamination risks remain;
- what claim boundaries apply; and
- whether freeze eligibility is approved, blocked, or deferred.

## What a review record is not

A review record is not empirical validation. It does not prove alpha. It does
not authorize trading. It does not prove trading readiness. It does not replace
contract, legal, regulatory, or venue-rule review where such review is needed.
A review record does not authorize trading.
A review record does not replace contract, legal, regulatory, or venue-rule review where needed.

A review record also does not make the knowledge graph a runtime research input.
It records governance state only.

## Required review scope

A minimal review record should include:

- `review_id`;
- `graph_id`;
- `graph_version`;
- `review_status`;
- `reviewed_files`;
- `reviewer_role`;
- `review_checks`;
- `open_items`;
- `claim_boundaries`;
- `human_review_required`;
- `evidence_status`; and
- `freeze_recommendation`.

The review checks should cover contract-template applicability, terminal
measure, settlement source, Clear Horizon, market/date-bucket mapping,
attention concepts, candidate queries, contamination risks, public-input
boundaries, and claim boundaries.

## Status meanings

- `draft`: review artifact is incomplete or only illustrative.
- `review_in_progress`: review has started but unresolved checks remain.
- `reviewed_with_open_items`: reviewer has documented checks and blockers.
- `approved_for_freeze`: reviewer approves freeze eligibility, subject to the
  separate freeze/hash process.
- `blocked`: unresolved issues prevent freeze eligibility.
- `rejected`: object should not proceed without a new version or replacement.

Ambiguous fields must remain `review_required` or `blocked`. They must not be
silently upgraded to reviewed, frozen, validation eligible, or claim-bearing.

## Freeze recommendations

- `not_ready`: graph cannot be frozen.
- `ready_after_open_items`: graph may become freeze-ready after listed items are
  resolved.
- `approved_for_freeze`: graph can proceed to the freeze checklist and hash
  process.
- `blocked`: graph cannot proceed without a material correction or new version.

## Claim and data boundaries

Review records must preserve VALI 1.0 boundaries:

- no alpha claim;
- no trading-readiness claim;
- no private data;
- no proprietary order flow;
- no credentials;
- no live trading;
- no order submission; and
- no `P_flow`.

Review records may document that these prohibited scopes were checked. They must
not introduce them as allowed behavior.
