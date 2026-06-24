"""Application orchestration for configuration and input validation."""

from __future__ import annotations

import json
from typing import Any

from ..config import ValiConfig
from ..pipeline import validate_inputs


def run_validation_command(args: Any) -> None:
    config = ValiConfig.from_toml(args.config)
    bundle = validate_inputs(config)
    print(json.dumps(bundle.validation.as_dict(), indent=2))


__all__ = ["run_validation_command"]
