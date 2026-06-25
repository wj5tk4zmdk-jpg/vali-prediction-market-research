# Hormuz Normalization Hash Inventory

Status: intended format only. Hashes are not computed in KG-3 because the graph
is not frozen.

The future frozen graph hash may be computed by hashing a sorted list of
`relative_path:sha256` entries. File hashes are for provenance and change
detection, not empirical validity.

| relative_path | sha256 | role |
|---|---:|---|
| event_family.v1.json | not_computed | event family object |
| attention_concepts.v1.csv | not_computed | hypothesized attention concepts |
| attention_queries.v1.csv | not_computed | candidate attention queries |
| relationship_edges.v1.csv | not_computed | hypothesized relationship edges |
| graph_manifest.v1.json | not_computed | graph manifest |
| FREEZE_CHECKLIST.v1.md | not_computed | freeze checklist |

The graph remains draft, human-review-required, and not validated. No graph hash
should be treated as proof of alpha, trading readiness, or empirical validity.
