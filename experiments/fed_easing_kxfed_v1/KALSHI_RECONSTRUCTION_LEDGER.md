# Kalshi Reconstruction Ledger

## A. Purpose

This local-only ledger separates raw public responses, normalized quotes,
trades, candles, depth snapshots, fixtures, reports, and uncertain mixed
captures. It identifies what may eventually support market-probability history
and what cannot support execution or capacity claims. No file was moved,
deleted, combined, or re-normalized.

## B. Data locations inspected

- `tests/fixtures/providers/kalshi/`
- `data/raw/kalshi/` (absent; `data/raw/` contains only `.gitkeep`)
- `data/interim/kalshi/`
- `data/processed/kalshi/` (absent; `data/processed/` contains only `.gitkeep`)
- `data/quarantine/kalshi/`
- `reports/archive/`
- `reports/quarantine/`
- `artifacts/quarantine/`
- the compatibility locations recorded in `ARTIFACT_INVENTORY.md`

## C. Capture inventory

Sizes are local directory totals from the Step 5B-1 inspection. “Conditional”
means usable only after raw/normalized tier separation, provenance verification,
duplicate resolution, mapping validation, and a frozen dataset manifest.

| Path/group | Classification | Count/size | Date and coverage | Safe for 5C? | Reason |
|---|---|---:|---|---|---|
| `tests/fixtures/providers/kalshi/` | `fixture` | 5 files / 2,493 bytes | Three fixture event IDs; one May 2025 candle/trade and one order book | No empirical use | Deterministic provider contracts only. |
| `data/raw/kalshi/` | `unknown` | Absent | None | No | No promoted immutable raw corpus exists. |
| `data/interim/kalshi/kalshi-live-snapshot-2026-06-23/` | `depth_snapshot` | 7 files / 69,633 bytes; 11 ladder rows, 96 levels, 1 quote | `KXFED-26JUL`, 2026-06-23 18:22:31Z | No historical execution use | One observed-depth snapshot, off the 16:00 ET cutoff and not a completeness series. |
| `data/processed/kalshi/` | `unknown` | Absent | None | No | No canonical processed market dataset exists. |
| `data/quarantine/kalshi/kalshi-hourly-backfill/` | `raw_public_response` | 51 gzip files / 129,525 bytes | Public capture dated 2026-06-23; contents not promoted | No | Raw-only partial capture requires request/provenance reconciliation. |
| `data/quarantine/kalshi/kalshi-hourly-backfill-v2/` | `mixed_raw_normalized` | 129 files / 13,074,145 bytes; 118 raw archives, 34 events, 66,465 quotes | Quotes 2021-12-27 through 2026-06-17; 34 contracts | Conditional for market probability | Best hourly bid/ask candidate, but raw and normalized data are mixed; no historical depth and zero trades in this run. |
| `data/quarantine/kalshi/kalshi-live-backfill/` | `mixed_raw_normalized` | 87 files / 413,902 bytes; 76 raw, 576 quotes | Two contracts, 2025-08-07 through 2026-06-17 | No canonical selection yet | Incomplete/early backfill variant. |
| `data/quarantine/kalshi/kalshi-live-backfill-v2/` | `mixed_raw_normalized` | 87 files / 1,684,835 bytes; 76 raw, 7,429 quotes | 34 contracts, 2021-12-28 through 2026-06-17 | Conditional secondary comparison | Daily-style duplicate candidate; must be reconciled with hourly source. |
| `data/quarantine/kalshi/kalshi-live-backfill-with-trades/` | `mixed_raw_normalized` | 315 files / 10,676,083 bytes; 304 raw, 7,429 quotes, 42,168 trades | 34 contracts; trades 2021-12-27 through 2026-06-17 | Conditional for secondary activity context | Trade history exists, but the run mixes raw, quotes, trades, mappings, and outcomes. Trades do not replace bid/ask or depth. |
| `data/quarantine/kalshi/kalshi-live-discovery/` | `mixed_raw_normalized` | 13 files / 190,559 bytes; 4 raw archives | 39 settled events, 7 open events, 98 open markets as of 2026-06-23 | Conditional for roster verification | Useful discovery evidence after provenance review, not a price history. |
| `data/quarantine/kalshi/kalshi-live-snapshots/` | `mixed_raw_normalized` | 24 files / 90,171 bytes; 17 raw plus one normalized snapshot | One `KXFED-26JUL` snapshot on 2026-06-23 | No capacity use | Duplicate/mixed source of the interim snapshot; not a daily cutoff series. |
| `reports/archive/KALSHI_ADAPTER_VERIFICATION.md` | `report` | 1 file / 1,480 bytes | Verification dated 2026-06-23 | Documentation only | Summarizes public checks but is not source data. |
| `reports/quarantine/` | `report` | 66 files / 9,903,761 bytes | Synthetic/legacy runs | No | Generated synthetic outputs are not empirical Kalshi inputs. |
| `artifacts/quarantine/` | `unknown` | 32 files / 1,192,522 bytes | Stale builds/packages | No | Never an input or import source. |

The hourly and trade counts agree with the reviewed adapter verification note.
No single hash is assigned to a mixed directory; future reconstruction must
hash every selected source file and the resulting frozen dataset manifest.

## D. Execution evidence

Bid and ask evidence exists for all 66,465 rows in the preferred hourly
candidate. None of those historical rows contains observed bid or ask depth;
all have `depth_observed=False`. A single order-book snapshot contains observed
depth, but it is off-cutoff and cannot establish historical executable
conditions or completeness.

Complete executable snapshots do not exist. Capacity and tradability remain
disabled without historical observed depth. Volume, open interest, and trades
must not be substituted for book depth. Forecast-only market-probability work
may eventually use verified bid/ask history, while P&L, capacity, and execution
claims remain unavailable.

## E. Outcome and settlement status

The normalized event table contains 34 labels: 28 outcome `0` and 6 outcome
`1`. Contract IDs consistently use the internal `event_id:EASING` identity, and
outcomes are absent from normalized quote rows.

The latest event, `KXFED-26JUN`, declares settlement at
`2026-06-24T18:05:00Z`, after the local capture was created on June 23. Its
label eligibility is not verified by a later local settlement record. It must
be verified with timestamped public evidence or excluded before training. Five
earlier tickers remain excluded for unresolved ladders or missing prior bounds.

## F. Reconstruction decisions

- `quotes_can_support_market_probability_history` — conditionally, after
  provenance review and canonical tiering.
- `trades_can_support_secondary_market_activity_context` — conditionally; they
  are not `P`, depth, or order flow.
- `depth_insufficient_for_capacity_claims` — yes.
- `mixed_captures_require_manual_tiering` — yes.
- `canonical_processed_inputs_not_ready` — yes.

Nothing in this ledger authorizes Step 5C. Reconstruction must preserve the raw
archives, select one canonical quote lineage, record file hashes and exclusions,
verify outcome eligibility, and repeat the Step 5B availability audit.
