# VALI Data Contracts

All timestamps must be timezone-aware. All research rows must be attributable
to public sources and reproducible from immutable raw material. Outcome labels
are stored separately from signal-time inputs.

## Behavioral attention inputs

Observation rows require:

- `feature_id`: stable identifier;
- `observation_at`: time represented by the observation;
- `available_at`: earliest time it was publicly usable;
- `vintage`: revision or retrieval identifier;
- `source`: public source identifier;
- `value`: finite numeric value.

The frozen feature manifest requires:

- `feature_id`, `rationale`, `transformation`, and easing polarity;
- `availability_lag_days`, `missing_policy`, and `max_age_days`;
- `required` status and expected `source`;
- manifest version, freeze date, and content hash in the run metadata.

Suppressed or unavailable observations are exclusions, not numeric zeroes.

## Priced conviction inputs

Market quote rows require:

- `contract_id`, `observed_at`, `bid`, and `ask`;
- `last` and `volume` when provided;
- `bid_depth`, `ask_depth`, and `depth_observed`;
- venue, source event, source ticker, source side, and mapping rationale in
  normalized venue data.

Bid and ask are probabilities in `[0, 1]`, with `bid <= ask`. Depth must use an
explicit unit. Historical price quality must remain distinct from execution
liquidity.

Public trade rows require `trade_id`, `contract_id`, `observed_at`, `price`, and
`size`. Trade-derived prices are non-executable unless matched to observed
contemporaneous depth.

## Outcomes

Outcome records require:

- `event_id` and `contract_id`;
- meeting/event time and settlement time;
- binary outcome or unresolved status;
- resolution/publication time and public source when available;
- the exact settlement rule and normalized target definition.

Outcomes may be joined only inside walk-forward scoring, calibration training,
settlement simulation, and post-run reporting. They must not appear in
signal-time feature, market, regime, or decision tables.

## Execution and liquidity snapshots

Execution snapshots require:

- `contract_id`, venue, source ticker, and `observed_at`;
- side-correct executable bid and ask;
- observed bid and ask depth with units and depth band;
- spread, quote age, market/closure status, and `depth_observed`;
- fee-model identifier and version used by simulation;
- raw-response hash and normalization version.

Capacity or tradability claims require contemporaneous observed depth and a
documented snapshot-completeness gate. Volume and open interest are not depth.

