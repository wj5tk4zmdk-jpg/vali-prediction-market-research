# Hormuz Draft KG Operationalization Pilot Run

Status: non-empirical operational pilot. This record documents a workflow
check, not validation evidence, not alpha evidence, and not trading-readiness
evidence.

Date: 2026-06-26

Graph under test:

```text
configs/knowledge_graph/examples/hormuz_normalization/graph_manifest.v1.json
```

## Commands attempted

```powershell
.\work\.venv\Scripts\python.exe -m vali kg preflight `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --out tmp_hormuz_preflight.json

.\work\.venv\Scripts\python.exe -m vali kg compile `
  --graph configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --preflight tmp_hormuz_preflight.json `
  --out tmp_hormuz_compiled.json

.\work\.venv\Scripts\python.exe -m vali backtest `
  --manifest tmp_hormuz_compiled.json `
  --out tmp_hormuz_backtest
```

## Observed result

Preflight completed:

- `graph_id`: `example_graph:hormuz_normalization:v1`
- `overall_status`: `unknown`
- checks: 13
- blockers: none

Compile completed:

- `manifest_id`: `compiled:example_graph:hormuz_normalization:v1`
- A-side features: 8
- `preflight_status`: `unknown`

Backtest did not run. It stopped before execution with:

```text
KnowledgeGraphError: Compiled manifest is missing object field: runtime_inputs
```

## Interpretation

This is the correct stop. The Hormuz draft graph can be preflighted and
compiled into a flat handoff artifact, but it is not a runnable manifest because
it lacks explicit local public runtime inputs and runtime parameters.

No Hormuz events, quotes, trades, or point-in-time attention observations were invented.
No empirical result was produced. No evidence file, review packet, or
superseding graph was created from this pilot because the backtest stage did
not execute.

## Pilot conclusion

The KG-Handoff infrastructure is wired, but the current Hormuz draft graph is a
schema/UX pilot fixture rather than a runnable research dataset. The next
researcher-facing improvement is to make the distinction between
compileable and runnable manifests very explicit.

The compile note was updated during this pilot so scaffolded compiled manifests
now tell users to add `runtime_inputs` and `runtime_parameters` before using
`vali backtest --manifest`.

## Claim boundary

This pilot:

- does not validate the Hormuz hypothesis;
- does not use point-in-time attention data;
- does not produce performance metrics;
- does not prove alpha;
- does not prove trading readiness;
- does not authorize trading;
- no private data;
- does not use private data, proprietary order flow, credentials, live trading,
  order submission, or `P_flow`.
