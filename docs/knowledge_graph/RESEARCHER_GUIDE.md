# VALI KG-Handoff Researcher Guide

Status: operational guide for the KG-Handoff pipeline. This guide explains how
to run the workflow and where to stop. It does not make empirical claims, alpha
claims, trading-readiness claims, or production-trading claims.

## What the KG-Handoff pipeline does

The KG-Handoff pipeline turns a reviewed knowledge-graph claim into a flat,
auditable VALI research run and then appends evidence without rewriting the
claim.

```text
Frozen or draft KG
  -> vali kg preflight
  -> vali kg compile
  -> vali backtest --manifest
  -> append-only ValidationEvidence
  -> vali kg review-packet
  -> vali kg supersede
```

The VALI engine remains responsible for `A`, `P`, `gA`, `gP`, `S_t`, `M_t`,
regimes, walk-forward validation, and execution-aware simulation. The engine
does not traverse the graph at signal time.

## Core boundaries

Every KG-Handoff run must preserve:

- no runtime graph traversal;
- no learned weights;
- no dynamic query selection;
- no use of expected lag metadata for signal construction;
- no private data;
- no proprietary order flow;
- no credentials;
- no live trading;
- no order submission;
- no `P_flow`;
- no alpha claim;
- no trading-readiness claim.

Expected lead/lag metadata is documentation and falsification metadata only.
It must not tune rolling windows, regime settings, thresholds, entries, exits,
position sizing, or execution timing.

## Step 1 — Preflight a graph

Use preflight to check whether the graph has enough declared availability
metadata for review.

```powershell
.\work\.venv\Scripts\python.exe -m vali kg preflight `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --out outputs\kg_preflight.json
```

Expected output:

- `overall_status`;
- check count;
- blockers;
- warnings.

Preflight is availability-only. It is not performance validation.

## Step 2 — Compile a flat manifest

Compile converts the reviewed local graph files into a flat
`compiled_vali_manifest.v1` artifact.

```powershell
.\work\.venv\Scripts\python.exe -m vali kg compile `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --preflight outputs\kg_preflight.json `
  --out outputs\compiled_manifest.json
```

Compile does not invent market data, attention observations, trades, depth, or
outcomes. A compiled manifest can be schema-valid but not runnable.

## Step 3 — Confirm whether the manifest is runnable

A manifest is runnable by:

```powershell
.\work\.venv\Scripts\python.exe -m vali backtest `
  --manifest outputs\compiled_manifest.json `
  --out outputs\backtest_run
```

only when it includes explicit local public runtime files and parameters:

- `runtime_inputs.events`;
- `runtime_inputs.quotes`;
- `runtime_inputs.features`;
- optional `runtime_inputs.trades`;
- `runtime_parameters.run`;
- `runtime_parameters.market`;
- optional `runtime_parameters.features`;
- optional `runtime_parameters.signal`;
- optional `runtime_parameters.regime`;
- optional `runtime_parameters.backtest`.

If `runtime_inputs` are missing, the correct result is a blocking error. Do not
patch around this by inventing data.

Do not patch around this by inventing data.

## Step 4 — Backtest from a runnable manifest

When a manifest is runnable, `vali backtest --manifest`:

1. validates runtime constraints;
2. converts `a_side.features` into the existing frozen feature-manifest table;
3. loads local public input files;
4. runs the unchanged VALI backtest pipeline;
5. appends `ValidationEvidence` beside the graph manifest.

This does not mutate the graph. Evidence is appended separately.

## Step 5 — Summarize evidence

After evidence files exist, summarize them for human review:

```powershell
.\work\.venv\Scripts\python.exe -m vali kg evidence-summary `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --out outputs\evidence_summary.md
```

The summary is descriptive. It makes no recommendation and no automatic
rejection.

## Step 6 — Create a human-review packet

Without a recommendation file, every target remains `human_review_required`:

```powershell
.\work\.venv\Scripts\python.exe -m vali kg review-packet `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --out outputs\review_packet.json
```

To record explicit human-reviewed actions, provide recommendations and a
reviewer:

```powershell
.\work\.venv\Scripts\python.exe -m vali kg review-packet `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --out outputs\review_packet.json `
  --recommendations outputs\recommendations.json `
  --reviewer "reviewer.name"
```

Allowed actions:

- `human_review_required`;
- `retain_for_research`;
- `needs_more_evidence`;
- `quarantine_pending_review`;
- `revise_in_superseding_version`;
- `retire_in_superseding_version`.

Any non-default action requires reviewer identity, `review_status` of
`reviewed` or `approved`, and rationale.

## Step 7 — Create a draft superseding graph copy

Supersession is a governance action, not an evidence conclusion:

```powershell
.\work\.venv\Scripts\python.exe -m vali kg supersede `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --review outputs\review_packet.json `
  --out-dir outputs\hormuz_v2_draft `
  --graph-id example_graph:hormuz_normalization:v2 `
  --version v2
```

This creates a draft copy. It does not mutate the source graph, does not prune
concepts automatically, and does not mark the new graph as frozen.

## Hormuz pilot result

The current Hormuz draft graph is useful as a workflow pilot, but it is not a
runnable empirical manifest.

Observed pilot result:

- preflight completed with `overall_status = unknown`;
- compile completed and produced 8 A-side features;
- backtest stopped because the compiled manifest lacked `runtime_inputs`.

This is the correct stop. The graph remains draft, not validated, and
human-review-required.

See:

- `reports/kg_handoff_pilot/HORMUZ_DRAFT_PILOT_RUN.md`
- `docs/knowledge_graph/OPERATIONALIZATION_PILOT_FRICTION_LOG.md`

## Common pitfalls

### Pitfall: treating compile success as validation readiness

Compile success only means a flat manifest could be produced. It does not mean
the manifest has data, is runnable, or has been validated.

### Pitfall: filling missing runtime inputs with synthetic data

Synthetic data is allowed only when clearly labeled fixture-only. It must not be
used to make empirical claims.

### Pitfall: using expected lead days to tune VALI

Do not do this. Expected lead days are documentation and falsification metadata
only.

### Pitfall: using review packets as automatic recommendations

Review packets require human judgment. The system intentionally does not
recommend, reject, prune, or version-bump automatically.

## Final reminder

The KG-Handoff pipeline is operational infrastructure. It is not a proof of
alpha, not a trading system, not a production deployment, and not a substitute
for point-in-time empirical validation.
