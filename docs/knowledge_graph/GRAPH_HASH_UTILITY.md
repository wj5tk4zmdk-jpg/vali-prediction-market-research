# VALI Knowledge Graph Hash Utility

Status: standalone developer utility. This is not runtime VALI integration, not
graph parsing for research execution, not market ingestion, not attention
acquisition, and not empirical validation.

## Purpose

`tools/knowledge_graph/compute_graph_hash.py` computes deterministic file-level
and graph-level SHA256 hashes for a knowledge graph manifest. The utility exists
so future frozen graph manifests can prove provenance and change detection.

Hashes do not prove empirical validity. Hashes do not prove alpha. Hashes do
not authorize trading or trading-readiness claims.

## Command usage

Read-only mode:

```powershell
.\work\.venv\Scripts\python.exe tools\knowledge_graph\compute_graph_hash.py `
  configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json
```

Optional draft inventory write mode:

```powershell
.\work\.venv\Scripts\python.exe tools\knowledge_graph\compute_graph_hash.py `
  configs\knowledge_graph\examples\hormuz_normalization\graph_manifest.v1.json `
  --write-inventory configs\knowledge_graph\examples\hormuz_normalization\HASH_INVENTORY.v1.md
```

The default command is read-only. It does not modify the manifest, graph files,
VALI source code, research outputs, providers, CLI behavior, or empirical
artifacts.

## File discovery rules

The graph manifest is the source of truth. The utility reads
`graph_manifest.v1.json` and uses the manifest's `graph_files` list. Paths are
interpreted relative to the manifest directory.

KG-5 may include review artifacts such as `REVIEW_RECORD.v1.json` in
`graph_files` when the manifest explicitly treats them as part of the draft
graph provenance. Review records are documented in
`docs/knowledge_graph/GRAPH_REVIEW_RECORDS.md` and are not empirical validation.

The utility rejects absolute paths and parent-directory traversal. It does not
discover files by walking directories. It does not include generated reports,
tests, docs, raw data, provider outputs, or other files unless the manifest
explicitly lists them.

## Deterministic hash policy

- file hash: SHA256 of raw bytes;
- graph hash input: sorted lines of `relative_path:sha256`;
- graph hash: SHA256 of the UTF-8 encoded graph hash input;
- CSV header order and row order are preserved by file bytes;
- JSON is hashed as stored in the repository;
- changing any listed graph file changes the graph hash.

When tooling later generates canonical JSON, it should use sorted keys as
described in `GRAPH_FREEZE_POLICY.md`. KG-4 does not canonicalize or rewrite
existing graph files.

## Draft hash versus frozen graph hash

The utility can compute a hash for any manifest, including a draft manifest.
For the Hormuz example, that output is only a draft hash. It is not a frozen
graph hash because the graph remains:

- draft;
- human-review-required;
- not validated;
- not frozen;
- not a trading signal;
- not an alpha claim; and
- not a canonical validation input.

A future freeze step may record a frozen graph hash only after human review and
freeze criteria pass.

## Boundaries

The utility:

- performs no network calls;
- uses no APIs;
- uses no credentials;
- inspects only manifest-listed local files;
- does not inspect private data;
- does not use proprietary order flow;
- does not implement `P_flow`;
- does not perform live trading or order submission;
- does not run VALI research logic;
- does not change provider, CLI, formula, or methodology behavior.

The hash report includes the explicit warning that hash output is for
provenance/change detection only and does not prove empirical validity, alpha,
or trading authorization.
