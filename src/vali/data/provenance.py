"""Public-source provenance and forbidden-input boundary helpers."""

from __future__ import annotations

import re
from typing import Type

import pandas as pd

from .contracts import DataValidationError


def canonical_boundary_value(value: object) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def forbidden_public_input_marker(value: object) -> str | None:
    """Return the forbidden marker present in a config or provenance value."""
    canonical = canonical_boundary_value(value)
    collapsed = canonical.replace("_", "")
    compound_markers = {
        "p_flow": "P_flow",
        "pflow": "P_flow",
        "flow_probability": "flow_probability",
        "flowprobability": "flow_probability",
        "order_flow": "order_flow",
        "orderflow": "order_flow",
        "pending_order": "pending_order",
        "pendingorder": "pending_order",
        "product_launch": "product_launch",
        "productlaunch": "product_launch",
        "client_data": "client_data",
        "clientdata": "client_data",
        "credentialed_trading": "credentialed_trading",
        "credentialedtrading": "credentialed_trading",
        "execution_api": "execution_api",
        "executionapi": "execution_api",
        "order_submission": "order_submission",
        "ordersubmission": "order_submission",
        "trading_credentials": "trading_credentials",
        "tradingcredentials": "trading_credentials",
        "live_trading": "live_trading",
        "livetrading": "live_trading",
        "non_public": "non_public",
        "nonpublic": "non_public",
        "api_secret": "api_secret",
        "apisecret": "api_secret",
        "private_key": "private_key",
        "privatekey": "private_key",
    }
    for candidate, label in compound_markers.items():
        target = collapsed if "_" not in candidate else canonical
        if candidate in target:
            return label
    tokens = set(canonical.split("_"))
    for token in ("private", "proprietary", "client"):
        if canonical == token or token in tokens:
            return token
    return None


def validate_public_research_config(
    raw: dict,
    error_type: Type[ValueError] = ValueError,
) -> None:
    """Reject private-data and trading interfaces from core research config."""

    def visit(value: object, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                marker = forbidden_public_input_marker(key)
                if marker:
                    raise error_type(
                        f"Core public-input boundary rejects {marker!r} at {child_path}"
                    )
                visit(child, child_path)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        elif isinstance(value, str):
            marker = forbidden_public_input_marker(value)
            if marker:
                raise error_type(
                    f"Core public-input boundary rejects {marker!r} at {path}"
                )

    visit(raw, "")


def validate_public_input_boundary(**frames: pd.DataFrame | None) -> None:
    """Reject prohibited private/proprietary inputs using auditable metadata."""
    provenance_names = {
        "feature_id",
        "source",
        "source_class",
        "source_classification",
        "data_classification",
        "visibility",
        "access_class",
        "provider_metadata",
        "provenance",
    }
    for label, frame in frames.items():
        if frame is None:
            continue
        for column in frame.columns:
            marker = forbidden_public_input_marker(column)
            if marker:
                raise DataValidationError(
                    f"Core public-input boundary rejects {marker!r} in {label}.{column}"
                )
            canonical_column = str(column).strip().lower()
            inspect_values = (
                canonical_column in provenance_names
                or "metadata" in canonical_column
                or "classification" in canonical_column
                or canonical_column.endswith("_class")
                or "provenance" in canonical_column
                or "visibility" in canonical_column
            )
            if not inspect_values:
                continue
            for value in frame[column].dropna():
                marker = forbidden_public_input_marker(value)
                if marker:
                    raise DataValidationError(
                        f"Core public-input boundary rejects {marker!r} in {label}.{column}"
                    )
