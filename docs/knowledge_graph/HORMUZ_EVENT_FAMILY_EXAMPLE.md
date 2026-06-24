# Hormuz Event-Family Knowledge Graph Example

Status: `draft`, `hypothesized`, `not_validated`,
`human_review_required`. This is a conceptual example, not empirical evidence.

KG-2 provides a machine-readable, non-validated version of this example under
`configs/knowledge_graph/examples/hormuz_normalization/`, including:

- `event_family.v1.json`
- `attention_concepts.v1.csv`
- `attention_queries.v1.csv`
- `relationship_edges.v1.csv`
- `graph_manifest.v1.json`

These files are not a frozen attention manifest, not canonical validation
inputs, and not trading signals.

## Family identity

| Field | Draft value |
|---|---|
| `event_family_id` | `maritime_chokepoint_normalization` |
| Kalshi category | `Politics` |
| Kalshi tag/subcategory | `International` |
| Kalshi series | `KXHORMUZNORM` |
| Terminal measure | Strait of Hormuz traffic normalization |
| Settlement source | Contract-defined settlement source; unresolved pending rule review |
| Contract template | Unresolved; do not assume `POLITICALSTAT` applies |
| Clear Horizon | Draft only; must be anchored to the reviewed terminal and trading cutoffs |
| Mapping status | `draft` |
| Evidence status | `not_validated` |
| Review status | `human_review_required` |

## Conceptual graph

```text
KalshiCategory:Politics
  -> has_tag -> KalshiTag:International
  -> contains -> KalshiSeries:KXHORMUZNORM
  -> contains_event -> KalshiEvent:<unresolved>
  -> contains_market -> KalshiMarket:<unresolved>
  -> uses_template -> ContractTemplate:<unresolved>
  -> normalizes_to -> NormalizedContract:<draft>
  -> settles_by -> TerminalMeasure:hormuz_traffic_normalization
  -> uses_source_agency -> SourceAgency:<contract-defined, unresolved>
  -> has_clear_horizon -> ClearHorizon:<draft>
  -> belongs_to_event_family -> EventFamily:maritime_chokepoint_normalization
```

No event ticker, market ticker, threshold, operator, source hierarchy, or
settlement rule may be filled by inference from the series name. Missing fields
force human review and exclusion from validation or simulation.

## Likely normalized contract fields

```json
{
  "template_type": null,
  "series_ticker": "KXHORMUZNORM",
  "event_ticker": null,
  "market_ticker": null,
  "underlying": "Strait of Hormuz traffic normalization",
  "terminal_measure": "hormuz_traffic_normalization",
  "source_agencies": [],
  "operator": null,
  "threshold_value": null,
  "time_period": null,
  "clear_horizon_rule": null,
  "first_release_only": null,
  "revision_rule": null,
  "last_trading_rule": null,
  "expiration_rule": null,
  "fallback_resolution_rule": null,
  "settlement_uncertainty_flag": true,
  "human_review_required": true,
  "mapping_status": "draft",
  "mapping_hash": null
}
```

## Hypothesized attention concepts

| Concept | Rationale | Expected direction toward normalization | Candidate lag | Candidate query examples | Contamination risks | Status |
|---|---|---|---|---|---|---|
| `oil_supply_disruption` | Energy-supply concern may reflect perceived persistence of passage disruption. | Negative | 1-14 days | `oil supply disruption`; `Hormuz oil supply` | Other producers, prices, refinery outages, consumer gasoline news | `hypothesized` |
| `maritime_traffic_disruption` | Shipping-focused attention may track operational blockage or restoration. | Negative while disruption dominates | 1-7 days | `Strait of Hormuz shipping`; `Hormuz vessel traffic` | Weather, unrelated ports, global container delays | `hypothesized` |
| `military_escalation` | Escalation may reduce expected near-term normalization. | Negative | 1-14 days | `Hormuz military escalation`; `Iran Strait conflict` | Broad regional conflict and partisan media cycles | `hypothesized` |
| `deescalation_or_reopening` | Reopening or de-escalation attention may precede higher normalization conviction. | Positive | 1-10 days | `Hormuz reopening`; `Strait deescalation` | Announcements without operational change; diplomacy elsewhere | `hypothesized` |
| `settlement_source_awareness` | Attention to the named source may cluster around terminal observations. | Unknown until source and measure are reviewed | 0-3 days | No query may be activated before source review | Reflexive market coverage, ambiguous source name, release spikes | `hypothesized` |

These strings are candidate query examples only. None is active, frozen, or
validated. The concept must be reviewed before the query; a query may not be
selected because it happens to correlate after the outcome.

## Expected relationships and contamination

- `oil_supply_disruption likely_leads hormuz_traffic_normalization` is a
  pre-validation theory edge, not a finding.
- `deescalation_or_reopening likely_leads hormuz_traffic_normalization` is also
  theory and may fail.
- Queries that mainly track oil prices, market commentary, or unrelated conflict
  may `contaminate` the family and must be excluded or separately controlled.
- Price-related searches may be reflexive to public Priced Conviction `P`; they
  must not be mislabeled as independent Behavioral Attention `A`.
- Source ambiguity, no observed depth, inconsistent settlement rules, or a
  missed last-trading cutoff creates a no-trade/claim-limitation condition.

## Freeze and evidence state

Before any empirical run, reviewers must resolve the market lineage and rules,
freeze the terminal measure, source hierarchy, operator, threshold, period,
Clear Horizon, concepts, queries, polarities, lag windows, contamination risks,
falsification gates, and claim boundaries. The frozen graph receives a version
and hash. Later `ValidationEvidence` is appended without rewriting this theory.

## Claim boundaries

This Hormuz example is not empirically validated. It makes no empirical alpha
claim and no trading-readiness claim. The graph does not prove alpha and does
not authorize trading. It uses no private data, proprietary order flow,
credentials, live trading, order submission, or `P_flow`. All contract and
attention mappings remain `human_review_required`.
