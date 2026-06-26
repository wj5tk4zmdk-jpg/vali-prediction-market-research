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

__all__ = [
    "KG_PRECHECKS",
    "KnowledgeGraphError",
    "compile_graph_manifest",
    "compute_graph_hash",
    "preflight_graph",
]
