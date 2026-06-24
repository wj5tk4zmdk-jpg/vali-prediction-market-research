"""Application orchestration for deterministic report reconstruction."""

from __future__ import annotations

import json
from typing import Any

from ..pipeline import rebuild_report


def run_report_command(args: Any) -> None:
    report = rebuild_report(args.run_dir)
    print(json.dumps({"report": str(report)}, indent=2))


__all__ = ["run_report_command"]
