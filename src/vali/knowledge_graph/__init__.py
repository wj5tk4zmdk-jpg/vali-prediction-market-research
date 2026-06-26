"""Knowledge-graph handoff scaffolding.

This package only compiles reviewed local graph artifacts into schema-shaped
handoff documents. It does not run VALI signal math, traverse graphs at
backtest time, fetch providers, validate performance, or authorize trading.
"""

from .handoff import (
    KG_PRECHECKS,
    KnowledgeGraphError,
    compile_graph_manifest,
    compute_graph_hash,
    preflight_graph,
)
from .runtime import (
    feature_manifest_from_compiled_manifest,
    load_compiled_manifest_runtime,
    load_inputs_from_compiled_manifest,
)
from .evidence import (
    EVIDENCE_STATUSES,
    append_evidence,
    read_evidence,
    summarize_evidence,
    write_evidence,
)

__all__ = [
    "EVIDENCE_STATUSES",
    "KG_PRECHECKS",
    "KnowledgeGraphError",
    "append_evidence",
    "compile_graph_manifest",
    "compute_graph_hash",
    "feature_manifest_from_compiled_manifest",
    "load_compiled_manifest_runtime",
    "load_inputs_from_compiled_manifest",
    "preflight_graph",
    "read_evidence",
    "summarize_evidence",
    "write_evidence",
]
