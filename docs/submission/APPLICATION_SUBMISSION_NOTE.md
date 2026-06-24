# VALI Application Submission Note

## Suggested application note

I am submitting VALI, a prediction-market research-engine artifact that
demonstrates end-to-end ownership of a disciplined, public-data research
framework. The repository covers point-in-time ingestion, leakage controls,
frozen feature manifests, prior-only transformations, meeting-grouped
walk-forward validation, execution-aware caveats, benchmark comparison, and
predeclared falsification gates.

The repository passed a clean-clone installation test, its full deterministic
test suite, and 15 CLI smoke checks. It is intentionally bounded: no empirical
alpha claim or trading-readiness claim is made, and the system contains no
private or proprietary inputs, proprietary order flow, order submission, live
trading, or `P_flow`.

Canonical empirical validation remains blocked until a business/data partner
can supply documented point-in-time attention history with suitable provenance
and revision semantics. That stop decision is part of the research result: the
engine preserves honest null, negative, and insufficient-data outcomes rather
than manufacturing a claim from incomplete evidence.

Repository:
`https://github.com/wj5tk4zmdk-jpg/vali-prediction-market-research`

Recommended review path:

1. [`VALI_EXPLORER.html`](VALI_EXPLORER.html)
2. [`REVIEWER_GUIDE.md`](REVIEWER_GUIDE.md)
3. [`KALSHI_QUANT_RESEARCHER_CASE_STUDY.md`](KALSHI_QUANT_RESEARCHER_CASE_STUDY.md)
4. [`CLEAN_CLONE_INSTALL_TEST.md`](CLEAN_CLONE_INSTALL_TEST.md)

## Claim boundary

VALI is a research-engine submission artifact, not evidence of proven alpha,
trading readiness, or production investment capability. It authorizes no live
collection, credentials, trading, or order submission.
