# VALI Research MVP

VALI is an offline research package for measuring divergence between behavioral
activity and executable market-implied conviction. Version zero models the
binary question: **will the Federal Reserve target range be lower after the
next scheduled FOMC meeting?**

The package is deliberately conservative. It enforces point-in-time feature
availability, prior-only normalization, liquidity filters, event-grouped
walk-forward evaluation, and complete exclusion/no-trade logs. It does not
claim alpha and does not connect to live data or trading venues.

Version 0.2 adds a strictly read-only Kalshi adapter for the `KXFED` series.
Version 0.3 adds offline-complete readiness for the official Google Trends API
alpha. Neither integration contains order-placement functionality.

## Install and run

```powershell
python -m pip install -e ".[dev,notebook]"
vali sample-data --out work/synthetic
vali validate --config work/synthetic/config.toml
vali signal --config work/synthetic/config.toml --out work/signals
vali backtest --config work/synthetic/config.toml --out work/backtest
vali report --run-dir work/backtest
pytest
```

## Kalshi market-data ingestion

Public discovery, historical backfill, and order-book snapshots do not require
credentials:

```powershell
vali kalshi discover --out data/kalshi/discovery
vali kalshi backfill --out data/kalshi/backfill --min-events 16 --candle-interval 60
vali kalshi snapshot --out data/kalshi
```

Every source response is retained as immutable gzip JSON under
`<out>/raw/kalshi/YYYY/MM/DD/`. Normalized CSV/Parquet outputs include venue,
source ticker, source side, threshold strike, event, and mapping rationale.
Snapshot runs are append-only under `<out>/snapshots/YYYY-MM-DD/HHMMSSZ/`.
Backfills also emit `vali_config.template.toml` and an empty behavioral-manifest
template. The pipeline must not be run empirically until that candidate feature
universe, rationale, polarity, availability lag, and source are frozen.

The adapter maps the internal easing outcome to the Kalshi NO side of the
`KXFED` threshold immediately below the pre-meeting upper bound. Unsafe or
ambiguous ladders are excluded rather than guessed. Historical candlesticks
provide price quotes but not book depth, so historical outputs set
`depth_observed=false` and cannot produce capacity or tradability claims.
The backfill defaults to hourly candles so VALI can select the final quote at
or before its 16:00 ET research cutoff without treating a daily exchange-boundary
candle as a contemporaneous observation.

To capture the 15:55-16:05 ET cutoff window, schedule
`scripts/run_kalshi_snapshot_window.ps1` daily at 15:55 ET. The script refuses
to run outside that window. Accumulate 30 days with at least 99% completeness
before enabling execution-aware paper simulation.

## Google Trends API alpha readiness

Google has publicly documented a rolling 1,800-day window, daily through yearly
aggregation, consistently scaled search-interest values, and data available
through approximately T-2. The endpoint, authentication, response schema, and
quota documentation remain limited to approved alpha testers. VALI therefore
provides a typed gateway boundary without guessing the private wire protocol or
using an unofficial scraping fallback.

Prepare and inspect the candidate query plan without credentials:

```powershell
vali trends plan --out data/google_trends/plan
vali trends status --out data/google_trends
```

Exercise the complete adapter offline with the recorded contract fixture:

```powershell
vali trends backfill --out work/trends-fixture `
  --fixture tests/fixtures/google_trends/interest.json `
  --as-of 2026-06-23 --days 7
vali trends status --out work/trends-fixture
```

`vali trends backfill` and `vali trends collect` fail closed without either a
fixture or the future official client. Raw responses are archived under
`raw/google_trends/YYYY/MM/DD/`; credentials are recursively redacted before
persistence. Normalized active features use `log1p`, a two-day availability
lag, and the existing prior-only 90-day standardization. General Fed-attention
and economic-stress queries are retained as diagnostics but are not included in
the initial signed easing-minus-tightening index.

`scripts/run_google_trends_collection.ps1` is deliberately disabled unless
`VALI_ENABLE_GOOGLE_TRENDS_COLLECTION=1`. Do not enable it until the private
authentication and quota requirements have been implemented and verified.

The example configuration documents the real-data input contract but
intentionally does not ship invented historical observations. The `sample-data`
command and `notebooks/fed_rate_pilot.ipynb` provide a deterministic synthetic
end-to-end demonstration.

## Input contracts

All timestamps must be ISO-8601 values with timezone offsets.

- `events.csv`: `event_id`, `contract_id`, `open_at`, `meeting_at`,
  `settlement_at`, `yes_label`, `outcome`. Outcome is `0`, `1`, or blank for an
  unresolved event.
- `quotes.csv`: `contract_id`, `observed_at`, `bid`, `ask`, `last`, `volume`,
  `bid_depth`, `ask_depth`. Prices are probabilities in `[0, 1]`; depths are
  executable dollar depth.
- `features.csv`: `feature_id`, `observation_at`, `available_at`, `vintage`,
  `source`, `value`.
- Optional `trades.csv`: `trade_id`, `contract_id`, `observed_at`, `price`,
  `size`.
- `feature_manifest.csv`: `feature_id`, `rationale`, `transformation`,
  `polarity`, `availability_lag_days`, `missing_policy`, `max_age_days`,
  `required`, `source`. Transformations are `level`, `diff`, `pct_change`, and
  `log_diff`; missing policies are `reject` and `asof`.

Paths in a TOML configuration are resolved relative to that configuration.
Every empirical run records configuration and input hashes in `run_manifest.json`.

## Research outputs

`vali backtest` writes signals, forecasts, calibration bins, trades, metrics,
sensitivity results, exclusions, regime diagnostics, CSV/Parquet mirrors, a
machine-readable manifest, and `report.html`. Parquet output requires the
declared `pyarrow` dependency; CSV output is always written.
