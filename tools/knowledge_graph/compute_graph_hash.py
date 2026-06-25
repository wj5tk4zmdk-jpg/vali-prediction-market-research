"""Compute deterministic hashes for VALI knowledge-graph manifest files.

This is a standalone developer utility. It is not imported by the VALI runtime,
does not execute research logic, does not fetch network data, and does not
authorize validation, alpha claims, or trading.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROVENANCE_NOTICE = (
    "Hash meaning: provenance/change detection only; does not prove empirical "
    "validity, does not prove alpha, and does not authorize trading."
)


def _load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("Graph manifest must be a JSON object.")
    return manifest


def _manifest_file_list(manifest: dict[str, Any]) -> list[str]:
    raw_files = manifest.get("graph_files", manifest.get("files_included"))
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("Graph manifest must define a non-empty graph_files list.")

    files: list[str] = []
    for value in raw_files:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Graph manifest file entries must be non-empty strings.")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Graph file path must be relative and local: {value}")
        files.append(value.replace("\\", "/"))
    return files


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_graph_hash(manifest_path: Path) -> tuple[dict[str, Any], list[tuple[str, str]], str]:
    manifest_path = manifest_path.resolve()
    manifest = _load_manifest(manifest_path)
    manifest_dir = manifest_path.parent
    graph_files = _manifest_file_list(manifest)

    file_hashes: list[tuple[str, str]] = []
    for relative_path in graph_files:
        file_path = manifest_dir / relative_path
        if not file_path.is_file():
            raise FileNotFoundError(f"Graph file listed by manifest does not exist: {relative_path}")
        file_hashes.append((relative_path, _sha256_file(file_path)))

    graph_hash_input = "".join(f"{path}:{digest}\n" for path, digest in sorted(file_hashes))
    graph_hash = hashlib.sha256(graph_hash_input.encode("utf-8")).hexdigest()
    return manifest, file_hashes, graph_hash


def _report(manifest_path: Path, manifest: dict[str, Any], file_hashes: list[tuple[str, str]], graph_hash: str) -> str:
    lines = [
        f"Graph manifest: {manifest_path.as_posix()}",
        f"Graph status: {manifest.get('freeze_status', manifest.get('status', 'unknown'))}",
        f"Graph hash status: {manifest.get('graph_hash_status', 'unknown')}",
        "Files:",
    ]
    lines.extend(f"  {relative_path}  {digest}" for relative_path, digest in file_hashes)
    lines.extend(
        [
            "Graph hash:",
            f"  {graph_hash}",
            PROVENANCE_NOTICE,
        ]
    )
    return "\n".join(lines) + "\n"


def _inventory_text(
    manifest_path: Path,
    manifest: dict[str, Any],
    file_hashes: list[tuple[str, str]],
    graph_hash: str,
) -> str:
    lines = [
        "# Knowledge Graph Hash Inventory",
        "",
        "Status: draft hash only; not frozen, not validated, not a trading signal,",
        "not an alpha claim, and not a trading-readiness claim.",
        "",
        PROVENANCE_NOTICE,
        "",
        f"Graph manifest: `{manifest_path.as_posix()}`",
        f"Graph status: `{manifest.get('freeze_status', manifest.get('status', 'unknown'))}`",
        f"Graph hash status: `{manifest.get('graph_hash_status', 'unknown')}`",
        f"Draft graph hash: `{graph_hash}`",
        "",
        "| relative_path | sha256 | role |",
        "|---|---|---|",
    ]
    lines.extend(f"| {relative_path} | {digest} | graph file |" for relative_path, digest in file_hashes)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute a deterministic provenance hash for a VALI knowledge-graph manifest."
    )
    parser.add_argument("manifest", type=Path, help="Path to graph_manifest.v1.json")
    parser.add_argument(
        "--write-inventory",
        type=Path,
        default=None,
        help="Optional path for writing a draft hash inventory markdown file.",
    )
    args = parser.parse_args()

    manifest_path = args.manifest
    manifest, file_hashes, graph_hash = compute_graph_hash(manifest_path)
    print(_report(manifest_path, manifest, file_hashes, graph_hash), end="")

    if args.write_inventory is not None:
        args.write_inventory.write_text(
            _inventory_text(manifest_path, manifest, file_hashes, graph_hash),
            encoding="utf-8",
            newline="\n",
        )
        print(f"Wrote draft hash inventory: {args.write_inventory.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
