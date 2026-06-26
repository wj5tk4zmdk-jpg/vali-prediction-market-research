# Regime Confirmation Panel

## Purpose

`vali confirmation-panel` is a compact execution-sensitivity report for the
regime-confirmation overlay. It asks a narrow question: if the raw VALI regime
classifier flips for a noisy day, does a predeclared confirmation buffer reduce
whipsaw, or does it merely delay losses?

The panel is not a new signal, not classifier tuning, and not alpha evidence.
It keeps the same public `A`, public/executable `P`, `S_t`, `M_t`, raw regimes,
folds, data, market mappings, and provider behavior. Only the simulated
execution decision overlay varies.

## What it compares

The default grid is fixed and predeclared:

| Arm | Interpretation | What changes |
|---|---|---|
| `1/1` | Baseline | Existing unbuffered entry and exit behavior. |
| `1/2` | Exit-only buffer | Entries remain immediate; regime-change exits require two confirming periods. |
| `2/1` | Entry-only buffer | Attention-leading entries require two confirming periods; exits remain immediate. |
| `2/2` | Symmetric buffer | Both entry and regime-change exit confirmation require two periods. |
| `3/3` | Stronger symmetric buffer | Both sides require three periods. |

If the active config specifies a different entry/exit pair, the command includes
that pair as an additional arm without replacing the default grid.

## How to run it

The command is explicit; it does not run inside ordinary `vali backtest`.

```powershell
& '.\.venv\Scripts\python.exe' -m vali confirmation-panel --config configs/experiments/fed_easing_v1.toml --out reports/confirmation-panel
```

Optional local experimentation can override the grid:

```powershell
& '.\.venv\Scripts\python.exe' -m vali confirmation-panel --config configs/experiments/fed_easing_v1.toml --out reports/confirmation-panel --grid 1/1,1/2,2/1,2/2,3/3
```

The command writes only to the requested output directory. It does not contact
live providers, submit orders, or infer missing data. A canonical empirical
confirmation report should not be generated until the point-in-time attention
history and reconstructed Kalshi market tiers pass the repeated data-readiness
audit.

## Outputs

The panel emits machine-readable files plus a small HTML report:

| Output | Purpose |
|---|---|
| `regime_confirmation_panel.csv` / `.parquet` | Per-arm metrics for the fixed confirmation grid. |
| `regime_confirmation_deltas.csv` / `.parquet` | Pairwise deltas versus the `1/1` baseline arm. |
| `regime_confirmation_delayed_exit_summary.csv` / `.parquet` | Desk-friendly delayed-exit rollup. |
| `regime_confirmation_delayed_exits.csv` / `.parquet` | Per-trade delayed-exit decomposition. |
| `regime_confirmation_manifest.json` | Inputs, config, grid, outputs, and research-warning metadata. |
| `regime_confirmation_report.html` | Offline human-readable summary of the same artifacts. |

## Delayed-exit summary

The delayed-exit summary is the first diagnostic to read when a buffer looks
better or worse. It aggregates the per-trade decomposition into:

| Field | Meaning |
|---|---|
| `delayed_exits_total` | Number of baseline regime-change exits that were delayed by a buffered arm. |
| `delayed_exits_helped` | Delayed exits where the buffered outcome improved versus the baseline exit. |
| `delayed_exits_hurt` | Delayed exits where the buffered outcome worsened versus the baseline exit. |
| `net_delay_pnl` | Sum of `net_pnl_delta` across delayed exits. |
| `helped_pct` | Helped delayed exits divided by total delayed exits. |
| `hurt_pct` | Hurt delayed exits divided by total delayed exits. |

This is the “whipsaw versus delayed pain” table. A positive rollup can suggest
that the buffer reduced noisy exits in that run. A negative rollup can suggest
that the buffer deferred losses. Either result is descriptive unless it is
backed by valid out-of-sample, execution-aware data.

## Per-trade decomposition

The per-trade delayed-exit table keeps the underlying evidence visible:

- baseline exit time, reason, and exit probability;
- buffered exit time, reason, and exit probability;
- `delay_days`;
- `gross_exit_value_delta`;
- `net_pnl_delta`;
- `saved_exit`;
- `bad_delayed_exit`.

The summary must reconcile to this table. The per-trade table remains the audit
trail; the summary is a reviewer-friendly rollup.

## Claim boundary

Regime confirmation is an optional execution sensitivity overlay. It is not a
new signal, not classifier tuning, not alpha evidence, and not a trading
readiness claim. The raw regime classifier, including the positive-lag
attention-leading convention, remains methodology-locked.

The report uses no private Kalshi data, proprietary order flow, client data,
pending orders, credentials, live trading, order submission, or `P_flow`.
Paired deltas are descriptive unless backed by predeclared out-of-sample,
execution-aware tests with realistic fees, spreads, closures, rejected trades,
and observed executable depth.
