"""Compatibility facade for the VALI application command boundary."""

from __future__ import annotations

import argparse
from datetime import date

from .application.commands import (
    build_parser as _application_build_parser,
    iso_date as _application_iso_date,
    main as _application_main,
)


def _iso_date(value: str) -> date:
    return _application_iso_date(value)


def _parser() -> argparse.ArgumentParser:
    return _application_build_parser()


def main(argv: list[str] | None = None) -> None:
    return _application_main(argv)


__all__ = ["main"]
