# Playbook: Knowledge Graph Handoff Work

Use this for `src/vali/knowledge_graph/`, `docs/knowledge_graph/`, and KG CLI
commands.

## Lifecycle

```text
Graph -> preflight -> compile -> backtest --manifest -> evidence -> review -> supersede
```

Commands:

```powershell
.\work\.venv\Scripts\python.exe -m vali kg preflight --graph GRAPH --out PREFLIGHT
.\work\.venv\Scripts\python.exe -m vali kg compile --graph GRAPH --preflight PREFLIGHT --out MANIFEST
.\work\.venv\Scripts\python.exe -m vali backtest --manifest MANIFEST --out RUN_DIR
.\work\.venv\Scripts\python.exe -m vali kg evidence-summary --graph GRAPH --out SUMMARY
.\work\.venv\Scripts\python.exe -m vali kg review-packet --graph GRAPH --out REVIEW
.\work\.venv\Scripts\python.exe -m vali kg supersede --graph GRAPH --review REVIEW --out-dir OUT_DIR
```

## Boundaries

- Runtime consumes flat compiled manifests only.
- Runtime does not traverse the graph.
- Expected lead/lag metadata is not a runtime tuning input.
- Evidence is append-only.
- Review packets are human-review governance artifacts.
- Supersession creates draft copies; it does not mutate frozen graphs.

## Current pilot finding

The Hormuz draft graph is compileable but not runnable until explicit
`runtime_inputs` and `runtime_parameters` are supplied. Do not invent these.

See:

- `docs/knowledge_graph/RESEARCHER_GUIDE.md`
- `docs/knowledge_graph/OPERATIONALIZATION_PILOT_FRICTION_LOG.md`
- `reports/kg_handoff_pilot/HORMUZ_DRAFT_PILOT_RUN.md`

## Tests

Start with:

```powershell
.\work\.venv\Scripts\python.exe -m pytest tests\contract -k knowledge_graph -q
```

Then run full suite when changing runtime adapters, CLI, or schema docs.
