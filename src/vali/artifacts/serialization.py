"""Stable machine-readable research artifact serialization."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_dataframe(frame: pd.DataFrame, name: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{name}.csv"
    parquet_path = output_dir / f"{name}.parquet"
    frame.to_csv(csv_path, index=False, date_format="%Y-%m-%dT%H:%M:%S%z")
    parquet_written = False
    try:
        frame.to_parquet(parquet_path, index=False)
        parquet_written = True
    except (ImportError, ModuleNotFoundError):
        pass
    return {"csv": csv_path.name, "parquet": parquet_path.name if parquet_written else None, "rows": len(frame)}


__all__ = ["write_dataframe"]
