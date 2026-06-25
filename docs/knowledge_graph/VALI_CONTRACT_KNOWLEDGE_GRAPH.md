# VALI Contract and Event-Family Knowledge Graph

Status: design-only, pre-validation infrastructure. This document defines no
runtime parser, empirical result, or trading authority.

## A. Purpose

VALI should not treat markets as isolated ticker strings, arbitrary tags, or
keyword prompts. A market should be a structured, reviewed, versioned research
object connecting:

`KalshiCategory / KalshiTag -> KalshiSeries -> KalshiEvent -> KalshiMarket -> ContractTemplate -> NormalizedContract -> TerminalMeasure / SourceAgency -> ClearHorizon -> EventFamily -> AttentionConcept -> AttentionQuery -> expected relationship -> contamination risk -> ValidationEvidence -> ClaimBoundary`.

This graph supports future alpha capture only indirectly. It can improve market
onboarding speed, terminal-event precision, discipline against post-hoc keyword
selection, evidence transfer across related event families, risk control through
no-trade and ambiguity flags, and validation through frozen hypotheses and
evidence tracking. The graph does not create alpha by itself. The graph does not
prove alpha. The graph does not authorize trading.

## B. Terminal condition for this branch

This branch is complete when VALI has a coherent design for representing Kalshi
categories, tags, series, events, markets, contract templates, normalized
contracts, source agencies, terminal measures, comparison operators, values or
thresholds, time periods, Clear Horizons, event families, attention concepts,
attention queries, expected relationships, contamination risks, validation
evidence, falsification gates, and claim boundaries.

Completion means the concepts, review requirements, freeze rules, and example
schemas are documented. It does not mean every Kalshi template is operationally
supported, parsed, or legally interpreted.

## C. Core graph node types

All identifiers are stable within a namespace. A frozen node is immutable;
corrections create a new version linked by provenance rather than rewriting the
old object.

| Node type | Purpose | Minimum fields | Human review | Frozen/versioned | VALI relationship |
|---|---|---|---|---|---|
| `KalshiCategory` | Preserve the venue's broad taxonomy. | `id`, `name`, `source`, `observed_at` | Confirm unusual or changed categories. | Yes | Discovery and family context, never a feature by itself. |
| `KalshiTag` | Preserve venue tags or subcategories independently of category. | `id`, `label`, `source`, `observed_at` | Confirm ambiguous tag meaning. | Yes | Adds routing context without becoming a query prompt. |
| `KalshiSeries` | Represent the recurring venue series. | `series_ticker`, `title`, `category_id`, `source`, `version` | Required before family mapping. | Yes | Parent identity for event grouping and market lineage. |
| `KalshiEvent` | Represent one resolution occasion containing markets. | `event_ticker`, `series_ticker`, `title`, `scheduled_time`, `source` | Required for event identity and schedule ambiguity. | Yes | Unit kept intact in walk-forward folds where applicable. |
| `KalshiMarket` | Preserve a specific listed binary contract and public metadata. | `market_ticker`, `event_ticker`, `title`, `rules_source`, `open_time`, `close_time` | Required before normalization. | Yes | Source for public executable `P`, not a terminal definition by itself. |
| `ContractTemplate` | Capture reusable rule structure such as `POLITICALSTAT`. | `template_type`, `version`, `rule_source`, `field_definitions`, `review_status` | Always required for a new template. | Yes | Prevents one-off ticker hardcoding. |
| `NormalizedContract` | Bind one market to common research primitives. | market identity, template version, underlying, measure, operator, threshold, period, settlement rules, mapping hash | Always required. | Yes | Defines label eligibility, cutoff, settlement review, and exclusions. |
| `TerminalMeasure` | Define exactly what observable resolves the contract. | `id`, `name`, `unit`, `definition`, `release_rule`, `source_agency_ids` | Always required. | Yes | Anchors the outcome label and prevents query-first research. |
| `SourceAgency` | Identify the official or contract-defined settlement source hierarchy. | `id`, `name`, `source_role`, `priority`, `public_reference` | Required when hierarchy or authority is ambiguous. | Yes | Governs point-in-time label provenance and revision rules. |
| `ComparisonOperator` | Give machine-readable semantics to contract language. | `id`, `symbol`, `lower_inclusive`, `upper_inclusive`, `rounding_rule` | Required for nonstandard qualifications. | Yes | Determines how a terminal value maps to YES or NO. |
| `TimePeriod` | Define the measurement, publication, capture, or event window. | `id`, `start`, `end`, `timezone`, `boundary_semantics`, `basis` | Required for relative, event-based, or multiple periods. | Yes | Separates observation window from settlement and execution cutoffs. |
| `ClearHorizon` | Define when attention-price divergence must resolve to count. | `id`, `anchor`, `start_rule`, `end_rule`, `exclusions`, `version` | Always required before validation. | Yes | Methodology-critical horizon for evaluating resolution latency. |
| `EventFamily` | Group contracts sharing a terminal mechanism and research logic. | `event_family_id`, `name`, `definition`, `terminal_measure_ids`, `status` | Always required. | Yes | Unit for reusable theory, manifests, exclusions, and evidence transfer. |
| `AttentionConcept` | Represent a theory-level public behavior, distinct from wording. | `id`, `event_family_id`, `rationale`, `polarity`, `expected_lag`, `contamination_risks` | Always required before queries. | Yes | Candidate component of public Behavioral Attention `A`. |
| `AttentionQuery` | Represent a frozen public query mapped to one concept. | `id`, `concept_id`, `query_text`, `geo`, `source_id`, `availability_rule`, `status` | Required before activation. | Yes | Raw public observation request; never validated merely by inclusion. |
| `AttentionSource` | Define a public attention provider and point-in-time contract. | `id`, `name`, `public_access`, `availability_semantics`, `revision_semantics` | Required before empirical use. | Yes | Establishes whether an attention observation is eligible for `A`. |
| `ValidationEvidence` | Preserve results without rewriting hypotheses. | `id`, `target_ids`, `experiment_id`, `folds`, `status`, `metrics`, `artifact_hashes` | Required before any evidence claim. | Yes | Records exploratory, out-of-sample, failed, or quarantined evidence. |
| `FalsificationGate` | Declare conditions that fail or limit a hypothesis. | `id`, `event_family_id`, `criterion`, `threshold`, `decision`, `frozen_at` | Always required before testing. | Yes | Enforces honest null and negative outcomes. |
| `ClaimBoundary` | State what evidence does and does not permit. | `id`, `scope`, `allowed_claims`, `prohibited_claims`, `evidence_requirements` | Always required. | Yes | Prevents graph presence from becoming an alpha or trading claim. |

## D. Core graph edge types

`Theory` edges are frozen before validation. `Evidence` edges may only be added
after the relevant experiment; they never overwrite the original theory edge.

| Edge type | Source node type | Target node type | Meaning | Stage |
|---|---|---|---|---|
| `belongs_to_category` | `KalshiSeries` | `KalshiCategory` | Venue taxonomy membership. | Metadata, pre-validation |
| `has_tag` | `KalshiSeries`, `KalshiEvent`, or `KalshiMarket` | `KalshiTag` | Venue-supplied tag context. | Metadata, pre-validation |
| `belongs_to_series` | `KalshiEvent` or `KalshiMarket` | `KalshiSeries` | Stable series lineage. | Metadata, pre-validation |
| `contains_event` | `KalshiSeries` | `KalshiEvent` | Series contains a resolution occasion. | Metadata, pre-validation |
| `contains_market` | `KalshiEvent` | `KalshiMarket` | Event contains a listed contract. | Metadata, pre-validation |
| `uses_template` | `KalshiMarket` | `ContractTemplate` | Market rules are reviewed against a template version. | Theory/mapping, pre-validation |
| `normalizes_to` | `KalshiMarket` | `NormalizedContract` | Venue contract maps to common primitives. | Theory/mapping, pre-validation |
| `settles_by` | `NormalizedContract` | `TerminalMeasure` | The measure whose value determines payout. | Theory/mapping, pre-validation |
| `uses_source_agency` | `NormalizedContract` or `TerminalMeasure` | `SourceAgency` | Official source or ordered outcome-source hierarchy. | Theory/mapping, pre-validation |
| `has_operator` | `NormalizedContract` | `ComparisonOperator` | Comparison applied to the terminal value. | Theory/mapping, pre-validation |
| `has_threshold` | `NormalizedContract` | Typed threshold/value literal | Strike, range, text value, or `None` used by the operator. | Theory/mapping, pre-validation |
| `has_time_period` | `NormalizedContract` | `TimePeriod` | Measurement/publication/capture window. | Theory/mapping, pre-validation |
| `has_clear_horizon` | `NormalizedContract` or `EventFamily` | `ClearHorizon` | Frozen latency evaluation window. | Theory, pre-validation |
| `belongs_to_event_family` | `NormalizedContract` | `EventFamily` | Reviewed family membership. | Theory/mapping, pre-validation |
| `is_measured_by` | `EventFamily` | `TerminalMeasure` | Family's terminal phenomenon. | Theory, pre-validation |
| `likely_leads` | `AttentionConcept` | `TerminalMeasure` | Attention is hypothesized to move before priced conviction/terminal resolution. | Theory, pre-validation |
| `likely_lags` | `AttentionConcept` | `TerminalMeasure` | Concept is expected to react too late to lead. | Theory, pre-validation |
| `proxy_for` | `AttentionQuery` | `AttentionConcept` | Query operationalizes a concept without equating wording to theory. | Theory, pre-validation |
| `contaminates` | `AttentionConcept` or `AttentionQuery` | `EventFamily` | Public behavior may be driven by unrelated news, seasonality, ambiguity, or reflexive price coverage. | Theory/risk, pre-validation |
| `excluded_from` | `AttentionQuery`, `KalshiMarket`, or `NormalizedContract` | `EventFamily` | Candidate is barred from a frozen run with an auditable reason. | Governance, pre-validation or evidence-triggered |
| `validated_for` | `ValidationEvidence` | `AttentionConcept`, `AttentionQuery`, or `EventFamily` | Evidence met a declared gate for the stated scope. | Evidence, post-validation |
| `failed_for` | `ValidationEvidence` | `AttentionConcept`, `AttentionQuery`, `EventFamily`, or `FalsificationGate` | Evidence failed or falsified the scoped hypothesis/gate. | Evidence, post-validation |
| `requires_human_review` | `NormalizedContract`, `TerminalMeasure`, or `AttentionQuery` | `ClaimBoundary` | Ambiguity prevents automatic eligibility or broad claims. | Governance, pre-validation |
| `frozen_as` | Any versionable node | Same logical node in a frozen version | Records immutable version, hash, and freeze time. | Governance, pre-validation |

Every edge carries `id`, `version`, `source`, `created_at`,
`human_review_status`, `evidence_status`, and `hash`. Expected lag, direction,
contamination rationale, and experiment scope belong on the edge when they
describe the relationship rather than either endpoint.

## E. Pre-validation theory versus post-validation evidence

Expected relationships begin as hypotheses. For example:

`AttentionConcept: oil_supply_disruption -> likely_leads -> TerminalMeasure: hormuz_traffic_normalization`

Before validation this is theory, not evidence. The edge is frozen with its
rationale, expected sign, lag window, contamination risks, and falsification
gate. After testing, a separate `ValidationEvidence` node and `validated_for` or
`failed_for` edge may be added. The original theory remains preserved and
frozen.

Allowed evidence statuses are `hypothesized`, `candidate`, `not_validated`,
`validated_exploratory`, `validated_out_of_sample`, `failed`, `quarantined`, and
`retired`. Only `validated_out_of_sample` can describe qualifying held-out
evidence; even that status does not authorize an alpha or trading claim without
execution-aware evidence and the governing `ClaimBoundary`.

## F. Contract-template normalization

VALI should normalize reviewed contract templates rather than hardcode one-off
markets. Common research primitives are:

- template type and version;
- underlying;
- source agency or settlement-source hierarchy;
- terminal measure;
- comparison operator;
- threshold/value/range;
- time period;
- first-release and revision rules;
- expiration and last-trading rules;
- payout criterion and settlement contingency;
- risk/capacity constraints;
- human-review status; and
- frozen mapping hash.

Contract-template normalization is not automated legal interpretation. The
contract title, market-specific rules, official source, and applicable venue
rules govern. Missing, conflicting, or ambiguous mappings require human review
and default to exclusion/no trade until resolved.

## G. POLITICALSTAT worked template example

The supplied `POLITICALSTAT` rule document is the first worked template, not a
universal Kalshi schema.

| Template element | Graph mapping | Research consequence |
|---|---|---|
| `<political stat>` | `TerminalMeasure` | Defines the exact political metric, entity, organization, population, unit, and qualifications. |
| `<value>` | `threshold_value` or strike/range literal | May be numeric, textual, or `None`; precision follows the contract and source convention. |
| above / below / exactly / at least / between | `ComparisonOperator` | Maps the observed terminal value to the payout condition. |
| `<time period>` | `TimePeriod` plus a Clear Horizon component | Distinguishes measurement, publication, distribution, capture, event, and relative boundaries. |
| Source Agency | Ordered `SourceAgency` nodes | Defines the outcome-source hierarchy; only official contract-relevant data are label eligible. |
| First official or non-preliminary release | `first_release_only: true` | Defines label timing and blocks later vintages from signal-time or settlement substitution. |
| Revisions after expiration ignored | `revisions_after_expiration_ignored: true` | Freezes point-in-time settlement semantics. |
| No data released | `fallback_resolution_rule` | Last fair price is determined solely by the Exchange; flag as nonstandard fallback and settlement uncertainty. |
| Last trading one minute before release/capture | `last_trading_rule` | Defines the execution cutoff; no simulated entry may cross it. |
| Settlement Value `$1.00` | `settlement_value: 1.0` | Defines the YES payout, not an observed probability. |
| Position Accountability Level `$25,000` per strike/member | `position_accountability_level` | Venue risk/capacity constraint; not evidence of executable depth. |
| Rule 7.1 review | `settlement_uncertainty_flag` | Outcome review or indeterminate expiration value requires review and may delay settlement. |

Additional mapped rules include a `$0.01` minimum tick, settlement no later than
the day after expiration unless under Rule 7.1 review, default expiration at
`10:00 AM ET`, and contract-specific earlier/later expiration under the cited
venue rules. POLITICALSTAT does not cover every market type. New templates must
enter through reviewed, versioned mappings.

## H. Operator semantics

- `above` means `>`.
- `below` means `<`.
- `exactly` means `=`, rounded to two decimal places unless the contract or
  source-agency convention specifies otherwise.
- `at least` means `>=`.
- `between` means lower-bound inclusive and upper-bound exclusive (`>= lower`
  and `< upper`) unless otherwise specified.

Source-agency precision, rounding conventions, and contract-specific
qualifications govern when present. The normalized operator stores those rules;
it does not silently impose generic floating-point behavior.

## I. Normalized contract schema

This documentation-only sketch is not a runtime schema:

```json
{
  "template_type": "POLITICALSTAT",
  "template_version": "draft-v1",
  "series_ticker": null,
  "event_ticker": null,
  "market_ticker": null,
  "underlying": null,
  "terminal_measure": null,
  "source_agencies": [],
  "operator": null,
  "threshold_value": null,
  "time_period": null,
  "clear_horizon_rule": null,
  "first_release_only": true,
  "revisions_after_expiration_ignored": true,
  "last_trading_rule": null,
  "expiration_rule": null,
  "settlement_value": 1.0,
  "fallback_resolution_rule": null,
  "minimum_tick": 0.01,
  "position_accountability_level": null,
  "settlement_uncertainty_flag": false,
  "human_review_required": true,
  "mapping_status": "draft",
  "mapping_hash": null
}
```

## J. Hormuz-style event-family example

The conceptual event family `maritime_chokepoint_normalization` uses Kalshi
category `Politics`, tag/subcategory `International`, and series ticker
`KXHORMUZNORM`. Its terminal measure is Strait of Hormuz traffic normalization
from the contract-defined settlement source. All mappings are `draft`,
`hypothesized`, `not_validated`, and `human_review_required`.

The contract template is intentionally unresolved: POLITICALSTAT must not be
applied merely because both examples sit near political subject matter. The
actual KXHORMUZNORM rules must be reviewed to establish its terminal measure,
normalization threshold, source hierarchy, time window, Clear Horizon,
last-trading cutoff, settlement contingency, and claim boundary.

| Attention concept | Rationale | Expected direction | Expected lag window | Contamination risk | Candidate query examples | Status |
|---|---|---|---|---|---|---|
| `oil_supply_disruption` | Public concern may rise when disruption affects energy supply. | Positive toward continued disruption; negative toward normalization. | Candidate 1-14 days before price adjustment. | Oil-price news, unrelated producers, consumer fuel concerns. | `oil supply disruption`, `Hormuz oil supply` | `hypothesized` |
| `maritime_traffic_disruption` | Shipping attention may track observable passage constraints. | Positive toward disruption. | Candidate 1-7 days. | Unrelated port closures, container delays, weather. | `Strait of Hormuz shipping`, `Hormuz vessel traffic` | `hypothesized` |
| `military_escalation` | Escalation attention may imply lower near-term normalization probability. | Negative toward normalization. | Candidate 1-14 days. | General regional conflict, casualty news, partisan media cycles. | `Hormuz military escalation`, `Iran Strait conflict` | `hypothesized` |
| `deescalation_or_reopening` | Reopening or ceasefire attention may precede normalization expectations. | Positive toward normalization. | Candidate 1-10 days. | Diplomatic announcements without operational change. | `Hormuz reopening`, `Strait deescalation` | `hypothesized` |
| `settlement_source_awareness` | Searches for the named settlement source may reveal public attention to the terminal evidence itself. | Direction depends on source observation. | Candidate 0-3 days. | Reflexive market coverage, source-name ambiguity, release-day spikes. | Placeholder queries derived only after the source is reviewed. | `hypothesized` |

Candidate queries are examples, not active features and not validated. See the
worked example document for the corresponding exclusions and claim boundaries.

## K. Proposed storage layout

KG-2 adds a lightweight, documentation-only schema registry under
`configs/knowledge_graph/`. These files are plain JSON/CSV review artifacts, not
runtime graph infrastructure:

```text
configs/knowledge_graph/node_types.v1.json
configs/knowledge_graph/edge_types.v1.json
configs/knowledge_graph/status_values.v1.json
configs/knowledge_graph/politicalstat_template.v1.json
configs/knowledge_graph/review_record_schema.v1.json
configs/knowledge_graph/examples/hormuz_normalization/event_family.v1.json
configs/knowledge_graph/examples/hormuz_normalization/attention_concepts.v1.csv
configs/knowledge_graph/examples/hormuz_normalization/attention_queries.v1.csv
configs/knowledge_graph/examples/hormuz_normalization/relationship_edges.v1.csv
configs/knowledge_graph/examples/hormuz_normalization/graph_manifest.v1.json
configs/knowledge_graph/examples/hormuz_normalization/REVIEW_RECORD.v1.json
configs/knowledge_graph/examples/hormuz_normalization/FREEZE_CHECKLIST.v1.md
configs/knowledge_graph/examples/hormuz_normalization/HASH_INVENTORY.v1.md
```

KG-1 documents these paths only. It creates no runtime config or authoritative
mapping file. KG-2 converts the design into reviewable registry artifacts, but
still creates no parser, provider behavior, empirical input, CLI behavior, or
trading capability.

KG-3 adds `docs/knowledge_graph/GRAPH_FREEZE_POLICY.md`, which defines the
draft, review, freeze, validation-eligible, retired/superseded lifecycle and the
deterministic graph hash policy. The Hormuz example remains draft and
human-review-required under its freeze checklist.

KG-5 adds `docs/knowledge_graph/GRAPH_REVIEW_RECORDS.md` and the lightweight
`configs/knowledge_graph/review_record_schema.v1.json` format. The Hormuz
`REVIEW_RECORD.v1.json` documents open review items and keeps the graph
`not_ready` for freezing.

## L. Review and freeze workflow

1. Ingest public Kalshi market metadata.
2. Identify category, tag, series, event, and market.
3. Identify the governing contract template and market-specific rules.
4. Produce a draft normalized contract.
5. Map the contract to an event family.
6. Define the terminal measure and Clear Horizon.
7. Propose theory-level attention concepts.
8. Map concepts to candidate public queries.
9. Require a human to review ambiguous fields and exclusions.
10. Freeze the graph version.
11. Compute and record the graph hash.
12. Run research only from the frozen graph.
13. Add validation evidence after testing without rewriting the original hypothesis.

A material change to a terminal measure, source hierarchy, query, polarity, lag,
operator, threshold, or horizon creates a new graph version and hash.
The graph hash proves provenance and change detection, not empirical validity,
alpha, or trading readiness.

## M. How the graph integrates with VALI

- **Experiment registry:** supplies stable graph version/hash and permitted
  event families.
- **Event-family manifests:** defines family membership, terminal mechanisms,
  exclusions, and evidence status.
- **Frozen attention manifests:** selects reviewed concepts and public queries
  without keyword fishing.
- **Clear Horizon:** provides the predeclared resolution window and anchors.
- **Label isolation:** makes terminal labels, releases, revisions, and eligible
  evaluation contexts explicit and separate from signal-time data.
- **Outcome settlement review:** routes Rule 7.1, fallback, source conflict, and
  revision ambiguity to human review.
- **Data availability audit:** tests whether each frozen node has eligible
  point-in-time observations.
- **Walk-forward folds:** groups by reviewed event identity and applies only
  prior evidence.
- **No-trade rules:** exclude ambiguous mappings, missing sources, failed
  liquidity, expired cutoffs, and settlement uncertainty.
- **Claim boundaries:** bind results to the evidence actually observed.

Public Behavioral Attention `A`, public executable Priced Conviction `P`,
signed divergence `S_t`, magnitude `M_t`, regimes, leakage controls, and
execution-aware testing remain governed by VALI 1.0. The graph describes inputs
and hypotheses; it does not alter those formulas.

## N. How the graph aids future alpha capture

The graph may improve future alpha research through:

- **Speed:** reusable templates and families reduce market-onboarding time.
- **Precision:** explicit terminal measures and source hierarchies reduce label
  and horizon ambiguity.
- **Discipline:** concepts precede frozen queries, preventing post-hoc keyword
  fishing.
- **Transfer:** evidence can be scoped and reused across genuinely related
  contracts without pretending every ticker is equivalent.
- **Risk control:** ambiguity, contamination, source conflict, no-trade, and
  settlement flags are first-class objects.
- **Validation:** original hypotheses remain frozen while later evidence is
  appended transparently.

The graph does not prove alpha. The graph does not authorize trading. Any alpha
claim requires later out-of-sample validation, execution-aware testing, and
paper trading under a separately approved plan.

## O. Claim boundaries

- No empirical alpha claim.
- No trading-readiness claim.
- No private data.
- No proprietary order flow.
- No order submission.
- No live trading.
- No credentials.
- No `P_flow`.
- No automated legal interpretation without review.
- All ambiguous contract mappings require human review and default to
  exclusion/no trade until resolved.
