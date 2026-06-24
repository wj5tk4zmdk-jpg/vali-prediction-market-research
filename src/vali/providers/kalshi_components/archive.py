"""Content-addressed immutable Kalshi response archiving."""

from __future__ import annotations

from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import API_SPEC_VERSION, utc_now


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class ArchiveStore:
    """Content-addressed immutable gzip archive for source API responses."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def record(
        self,
        *,
        url: str,
        payload: Any,
        retrieved_at: datetime | None = None,
    ) -> Path:
        retrieved = retrieved_at or utc_now()
        content = canonical_bytes(payload)
        digest = hashlib.sha256(content).hexdigest()
        directory = (
            self.root
            / "raw"
            / "kalshi"
            / retrieved.strftime("%Y/%m/%d")
        )
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest}.json.gz"
        if path.exists():
            return path
        envelope = {
            "api_spec_version": API_SPEC_VERSION,
            "content_sha256": digest,
            "retrieved_at": retrieved.isoformat(),
            "source_url": url,
            "payload": payload,
        }
        temporary = path.with_suffix(".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8") as handle:
            json.dump(envelope, handle, sort_keys=True, separators=(",", ":"))
        temporary.replace(path)
        return path


__all__ = ["ArchiveStore", "canonical_bytes"]
