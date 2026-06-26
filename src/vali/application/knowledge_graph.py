"""Application orchestration for KG-handoff scaffolding commands."""

from __future__ import annotations

import json
from typing import Any

from ..knowledge_graph import compile_graph_manifest, preflight_graph
from ..knowledge_graph.evidence import write_evidence_summary


def run_kg_command(args: Any) -> None:
    if args.kg_command == "preflight":
        report = preflight_graph(args.graph, args.out)
        print(
            json.dumps(
                {
                    "output": str(args.out),
                    "graph_id": report["graph_id"],
                    "overall_status": report["overall_status"],
                    "checks": len(report["checks"]),
                },
                indent=2,
            )
        )
        return
    if args.kg_command == "compile":
        manifest = compile_graph_manifest(args.graph, args.preflight, args.out)
        print(
            json.dumps(
                {
                    "output": str(args.out),
                    "manifest_id": manifest["manifest_id"],
                    "features": len(manifest["a_side"]["features"]),
                    "preflight_status": manifest["preflight_status"],
                },
                indent=2,
            )
        )
        return
    if args.kg_command == "evidence-summary":
        summary = write_evidence_summary(args.graph, args.out)
        print(
            json.dumps(
                {
                    "output": str(args.out),
                    "total_experiments": summary["total_experiments"],
                    "passing_count": summary["passing_count"],
                    "failing_count": summary["failing_count"],
                },
                indent=2,
            )
        )


__all__ = ["run_kg_command"]
