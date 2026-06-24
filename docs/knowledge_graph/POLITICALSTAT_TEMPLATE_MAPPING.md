# POLITICALSTAT Contract-Template Mapping

Status: reviewed documentation example based on the supplied POLITICALSTAT rule
document. This is not automated legal interpretation or runtime support.

| POLITICALSTAT rule element | Normalized VALI field | Research significance |
|---|---|---|
| Scope | `template_type: POLITICALSTAT`; `template_version`; `rule_source` | Limits the mapping to contracts governed by this reviewed template version. |
| Underlying | `underlying_definition` | Combines `<value>`, `<political stat>`, and `<time period>`; prevents ticker-only interpretation. |
| Source Agency | `source_agencies[]` with ordered `priority` | Preserves the hierarchical official outcome source and label provenance. |
| Type | `contract_type: EventContract` | Distinguishes payout structure from ordinary assets. |
| Issuance | `issuance_rule: as_needed_exchange_discretion` | Warns that strikes/iterations are venue-selected and should not be inferred as a stable universe. |
| `<political stat>` | `terminal_measure` plus entity, organization, population, unit, and qualifications | Defines the exact resolving statistic. Examples include approval, polling, vote share, seats, turnout, and legislative metrics. |
| `<value>` | `threshold_value`, `threshold_unit`, `threshold_precision`, `text_value` | Supports numeric, percentage, index, textual, or `None` values without coercing suppressed/text outcomes to zero. |
| Comparison operators | `operator` and boundary fields | `above` `>`, `below` `<`, `exactly` `=`, `at least` `>=`, `between` lower-inclusive/upper-exclusive unless overridden. |
| `<time period>` | `time_period` with `basis`, timezone, and boundary semantics | Represents measurement, publication, distribution, event, relative, multiple, or exact capture periods; `before`/`after` exclude the named date unless stated otherwise. |
| Payout Criterion | `payout_criterion` | Binds measure, operator, value, and period to YES/NO resolution. Exact statistic in the contract title governs when multiple values appear. |
| First-release rule | `first_release_only: true` by default | Only the first official or non-preliminary publication resolves unless explicitly stated otherwise. |
| Revision rule | `revisions_after_expiration_ignored: true` | Later revisions, corrections, or updates do not rewrite the point-in-time settlement label. |
| No-data contingency | `fallback_resolution_rule: exchange_last_fair_price`; `settlement_uncertainty_flag: true` | No release by expiration invokes an Exchange-determined last fair price, requiring review and bounded claims. |
| Examples resolving YES | `template_examples.positive[]` | Approval above 40%, certified vote share at least 51%, a polling average in a defined range, or an exact-time capture illustrate operator/period semantics only. |
| Examples not resolving YES | `template_examples.negative[]` | Pre-issuance values, later revisions, failed exact equality, and unofficial projections demonstrate eligibility exclusions. |
| Minimum Tick | `minimum_tick: 0.01` | Execution price increment; it is not a liquidity or depth observation. |
| Position Accountability Level | `position_accountability_level: 25000`; `basis: per_strike_per_member` | Venue risk/capacity constraint; it must not be represented as executable capacity. |
| Last Trading Date | `last_trading_rule: one_minute_before_expected_release_or_capture` | Defines the execution cutoff. If release time is unknown, trading closes at expiration time on expiration date. |
| Settlement Date | `settlement_date_rule: no_later_than_day_after_expiration_unless_rule_7_1_review` | Defines expected label availability while preserving review delays. |
| Expiration Date | `expiration_rule` | Latest default is three months after scheduled release or period end; Rule 7.2 and data delay/nonrelease can alter timing. |
| Expiration Time | `expiration_time: 10:00 AM ET` | Supplies timezone-specific cutoff unless a market-specific rule supersedes it. |
| Settlement Value | `settlement_value: 1.0` | Defines the YES payout amount, not probability or alpha. |
| Expiration Value | `expiration_value_rule: source_documented_underlying_at_expiration` | Binds the terminal label to the source-documented underlying at expiration date/time. |
| Contingencies / Rule 7.1 | `settlement_uncertainty_flag`; `outcome_review_rule` | An Exchange outcome review or indeterminate expiration value requires human review and may alter timing/payout determination. |

## Operator and rounding notes

`exactly` defaults to equality after rounding to two decimal places unless the
contract states otherwise. More generally, percentages and non-integers follow
the Source Agency's reporting convention: one decimal remains one decimal, and
whole-number reporting uses nearest-whole-number precision. Contract-specific
qualifications override generic defaults.

## Clear Horizon and label implications

The `<time period>`, expected release/capture, last-trading cutoff, expiration,
and settlement/review windows are separate temporal objects. A VALI Clear
Horizon must specify which one anchors the research question. The first-release
and revision rules belong only in outcome/evaluation contexts after the relevant
horizon; outcome labels remain physically separated from signal-time tables.

## Review boundary

POLITICALSTAT is one template example, not coverage of every Kalshi market.
Every market mapping requires the contract title, rule version, source hierarchy,
statistic qualifications, operator, threshold, period, and contingency review.
Ambiguity sets `human_review_required: true` and blocks validation/trading claims.

This mapping makes no empirical alpha claim and no trading-readiness claim. It
does not prove alpha or authorize trading. It uses no private data, proprietary
order flow, credentials, live trading, order submission, or `P_flow`.

