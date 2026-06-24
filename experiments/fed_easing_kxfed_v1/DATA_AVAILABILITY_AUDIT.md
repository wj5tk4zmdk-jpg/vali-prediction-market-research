# Data Availability Audit: `fed_easing_kxfed_v1`

## A. Scope

Audit date: `2026-06-24`.

This audit is limited to local repository files: committed fixtures, existing
raw/interim/processed/quarantined data, retained reports, configuration, and
artifact inventories. It made no live provider call, used no credential, and
generated no provider data.

## B. Data locations inspected

| Location | Finding |
|---|---|
| `tests/fixtures/providers/kalshi/` | Five small deterministic provider fixtures for events, markets, candles, trades, and order book. |
| `tests/fixtures/providers/google_trends/` | One deterministic `fixture-v1` response. |
| `tests/fixtures/google_trends/interest.json` | Byte-identical compatibility copy of the Trends fixture. |
| `data/raw/` | Empty except `.gitkeep`; no promoted immutable public corpus. |
| `data/interim/` | One normalized Kalshi ladder/order-book snapshot from 2026-06-23. |
| `data/processed/` | Empty except `.gitkeep`; no frozen analysis-ready dataset. |
| `data/quarantine/kalshi/` | Multiple mixed raw-archive and normalized-table runs, including discovery, backfills, trades, and one snapshot. |
| `data/quarantine/google_trends/` | Fixture-derived request plan, raw envelope, and normalized acceptance tables. |
| `reports/archive/` | Reviewed Kalshi adapter verification note. |
| `reports/quarantine/` | Legacy synthetic runs only; not empirical evidence. |
| `reports/runs/` | Deterministic synthetic run only. |
| `artifacts/quarantine/` | Stale builds/packages and generated artifacts; never an input source. |
| `configs/` | Canonical experiment TOML and frozen Trends query manifest. |
| `work/` | Local Python and Git tooling only after prior outputs were tiered. |

The previously discussed five-year Google Trends CSV is not present inside the
audited repository and is not counted as canonical attention history.

The canonical TOML currently resolves its four configured input paths beneath
`configs/experiments/data/`; `events.csv`, `quotes.csv`, `features.csv`, and
`feature_manifest.csv` do not exist there.

## C. Event roster availability

The most complete local normalized Kalshi roster is quarantined at
`data/quarantine/kalshi/kalshi-hourly-backfill-v2/events.csv`.

- 39 settled KXFED events appear in the public discovery capture.
- 34 events map to stable internal `event_id:EASING` contracts.
- Scheduled meetings span `2022-05-04T18:00:00Z` through
  `2026-06-17T18:00:00Z`.
- Declared settlements span `2022-05-11T18:05:00Z` through
  `2026-06-24T18:05:00Z`.
- All 34 normalized rows contain outcomes: 28 outcome `0`, 6 outcome `1`.
- Five earlier event tickers are represented by nine exclusion rows for
  unresolved ladders or missing pre-meeting upper bounds.

Mapped event IDs:

`FED-22MAY`, `FED-22JUN`, `FED-22JUL`, `FED-22SEP`, `FED-22NOV`,
`FED-22DEC`, `FED-23FEB`, `FED-23MAR`, `FED-23MAY`, `FED-23JUN`,
`FED-23JUL`, `FED-23SEP`, `FED-23NOV`, `FED-23DEC`, `FED-24JAN`,
`FED-24MAR`, `FED-24MAY`, `FED-24JUN`, `FED-24JUL`, `FED-24SEP`,
`FED-24NOV`, `FED-24DEC`, `FED-25JAN`, `FED-25MAR`, `FED-25MAY`,
`FED-25JUN`, `FED-25JUL`, `FED-25SEP`, `FED-25OCT`, `FED-25DEC`,
`KXFED-26JAN`, `KXFED-26MAR`, `KXFED-26APR`, and `KXFED-26JUN`.

Outcomes reside in the event/evaluation table; the 66,465-row quotes table has
no outcome column. Existing label-isolation contracts prevent outcomes from
entering pre-decision frames. Event identity is stable in the inspected tables.
Thirty-four events exceed the configured minimum of 16 earlier resolved
meetings, so the market-side roster is large enough in principle. However, the
last row's declared settlement occurs after the capture creation time and must
be provenance-checked or excluded before training.

## D. Kalshi market data availability

The public, read-only captures are empirical-looking provider records with raw
archives and normalized mirrors, not test fixtures. They remain quarantined
because each run mixes raw envelopes with normalized tables.

- The preferred hourly capture contains 66,465 bid/ask quote rows across all 34
  mapped contracts, from `2021-12-27T16:00:00Z` through
  `2026-06-17T18:00:00Z`.
- Bid and ask are present on every normalized hourly row.
- Historical candlesticks contain no observed depth: all 66,465 rows have
  `depth_observed=False`, with blank bid and ask depth.
- A separate public capture contains 42,168 normalized trades; the preferred
  hourly run itself contains no trades.
- The primary hourly run retains 118 gzip JSON raw archives. Other duplicate or
  exploratory capture runs remain quarantined rather than silently combined.
- One snapshot at `2026-06-23T18:22:31.501907Z` contains an 11-market ladder,
  96 order-book levels, and one mapped quote with observed depth. It is not a
  complete daily series and was not captured at the configured 16:00 ET cutoff.

Therefore executable-snapshot completeness is false. Historical capacity and
tradability claims remain disabled; volume and open interest are not treated as
book depth. The single snapshot is useful only for adapter and normalization
validation.

The deterministic Kalshi fixtures are much smaller: three event identifiers,
one candle, one trade, and one order book. They support tests, not empirical
claims.

## E. Google Trends and public-attention availability

- Frozen manifest: `configs/features/google_trends_candidate_v1.csv`.
- Frozen hash:
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`.
- Active easing IDs: `rate_cut`, `federal_reserve_rate_cut`,
  `interest_rates_down`.
- Active tightening IDs: `rate_hike`, `federal_reserve_rate_hike`,
  `interest_rates_up`.
- Inactive controls/stress IDs: `federal_reserve`, `fomc`, `jerome_powell`,
  `unemployment_benefits`, `laid_off`, `recession`.

The only local attention observations come from `fixture-v1`. They cover three
dates, `2026-06-19` through `2026-06-21`, with one UTC retrieval time,
`2026-06-23T15:30:00Z`. The normalized output contains 24 observations, 22
usable rows, 18 active-feature rows, and two explicit inactive-query exclusions
(`low_volume` and `suppressed`). `retrieved_at` is consistently serialized in
UTC. The run manifest states `live_access_used=false`,
`historical_point_in_time_claims_enabled=false`, and `api_versions=[fixture-v1]`.

This is deterministic fixture coverage, not empirical Google Trends history.
It is far below the 30 prior observations needed for normalization and does not
span the event universe. Official API revision, vintage, availability, and
protocol guarantees remain unavailable.

## F. Point-in-time validity

Local contracts prove the implementation can enforce prior-only normalization,
label isolation, event-date cutoffs, and grouped walk-forward folds on
deterministic data. The Kalshi rows carry observation and event timestamps, and
the fixture attention rows carry observation, availability, retrieval, and
vintage information.

The existing empirical-looking data do not yet support a canonical point-in-time
run. There is no historical empirical attention series or documented revision
behavior across the resolved events; the configured analysis-ready files are
absent; and the latest outcome requires settlement-availability review.

## G. Common intersection

The 34-event market/outcome history spans meetings from May 2022 through June
2026. The attention fixture spans only June 19–21, 2026—after the June 17
meeting—and the lone observed-depth snapshot is June 23, 2026. There is no
pre-decision common intersection of empirical attention, resolved outcomes,
market history, and executable depth.

- **Fixture-only validation:** sufficient. Deterministic fixtures and synthetic
  data exercise schemas, point-in-time guards, signals, and backtests.
- **Exploratory empirical validation:** insufficient for the registered
  `A`/`P` hypothesis because empirical `A` is absent.
- **Proper walk-forward empirical validation:** insufficient. Market/outcome
  coverage alone cannot evaluate signed attention/price divergence.

## H. Missing data register

| Missing item | Why it matters | Source needed | Blocks 5C? | Claim effect | Recommended next action |
|---|---|---|---|---|---|
| Empirical history for all six active attention queries | Required to construct `A`, prior-only z-scores, velocities, and pre-meeting folds | Official Google Trends alpha API or another separately approved frozen public source | Yes | Blocks the primary hypothesis | Obtain a documented historical backfill with retrieval/vintage semantics; do not substitute the fixture. |
| Documented Trends revision and availability behavior | Historical point-in-time claims require knowing what was available when | Official API documentation and retained vintages | Yes for strict point-in-time claims | Limits all attention-based conclusions | Record protocol/version and revision policy before accepting history. |
| Analysis-ready canonical input files | Current TOML resolves to four nonexistent files | Reviewed promotion/reconstruction from audited sources into a frozen experiment dataset | Yes | Prevents a canonical run | Build a manifest-hashed dataset only after the attention gap is resolved. |
| Kalshi quarantine review and tier separation | Raw archives and normalized tables are mixed across duplicate runs | Existing local public captures | Yes before canonical ingestion | Provenance ambiguity | Select one source run, verify hashes/mappings, and separate raw, interim, and processed tiers without deleting originals. |
| Latest outcome settlement-availability verification | The latest declared settlement is later than capture creation | Existing raw settlement record or later public settlement record | For that event | Could introduce outcome-timing leakage | Verify and timestamp eligibility or exclude the event. |
| Historical observed depth | Required for capacity and executable historical simulation | Archived cutoff order books, which are not locally available | No for forecast-only 5C | Disables capacity/tradability and most P&L claims | Keep execution claims disabled; accumulate future cutoff snapshots separately. |
| Complete cutoff snapshot series | One off-cutoff snapshot cannot establish completeness | Future public read-only snapshots under a separately authorized collection step | No for forecast-only 5C | Prevents execution-aware paper claims | Require the predeclared 30-day/99% completeness gate before paper simulation. |
| Final fee specification | Current fee model is provisional | Public venue fee schedule frozen to an effective date | No for forecast-only 5C | Makes simulated returns provisional | Freeze and sensitivity-test fees before execution interpretation. |

## I. Step 5B conclusion

Decision: **`insufficient_due_to_missing_attention_history`**.

The repository is sufficient for deterministic fixture validation and contains
substantial public Kalshi market/outcome history. It is not sufficient for 5C:
the registered experiment cannot construct empirical `A`, satisfy its
normalization history, or establish a pre-decision common intersection. Data
collection or reconstruction and a repeat availability audit are required
before the empirical validation run.

This decision makes no alpha claim and no trading-readiness claim.
