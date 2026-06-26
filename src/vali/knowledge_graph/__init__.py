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
    "preflight_graph",
    "read_evidence",
    "summarize_evidence",
    "write_evidence",
]
