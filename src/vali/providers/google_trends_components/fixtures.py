"""Deterministic offline gateway for recorded Google Trends fixtures."""

from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any

from .contracts import (
    ALLOWED_STATUSES,
    TrendsDataError,
    TrendsGatewayResponse,
    TrendsObservation,
    TrendsRequest,
    parse_bool,
    parse_datetime,
    sha256_value,
)


class FixtureTrendsGateway:
    """Offline provider used for contract tests and environment exercises."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def fetch(self, request: TrendsRequest) -> TrendsGatewayResponse:
        if not self.path.exists():
            raise TrendsDataError(
                f"Google Trends fixture does not exist: {self.path}"
            )
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise TrendsDataError(
                f"Invalid Google Trends fixture: {self.path}"
            ) from exc
        retrieved = parse_datetime(
            payload.get("retrieved_at"), "fixture.retrieved_at"
        )
        allowed_queries = {query.query_id for query in request.queries}
        observations: list[TrendsObservation] = []
        raw_rows: list[dict[str, Any]] = []
        for row in payload.get("observations", []):
            query_id = str(row.get("query_id", ""))
            try:
                observation_date = date.fromisoformat(
                    str(row.get("date", ""))
                )
            except ValueError as exc:
                raise TrendsDataError(
                    "Invalid fixture observation date: "
                    f"{row.get('date')!r}"
                ) from exc
            if (
                query_id not in allowed_queries
                or observation_date < request.start_date
                or observation_date > request.end_date
            ):
                continue
            status = str(row.get("status", "available"))
            if status not in ALLOWED_STATUSES:
                raise TrendsDataError(
                    f"Unsupported fixture status: {status}"
                )
            raw_value = row.get("value")
            value = None if raw_value in (None, "") else float(raw_value)
            if status == "available" and (
                value is None or not math.isfinite(value) or value < 0
            ):
                raise TrendsDataError(
                    "Available Trends observations require finite "
                    "non-negative values"
                )
            if status != "available" and value is not None:
                raise TrendsDataError(
                    "Suppressed, low-volume, or missing observations cannot "
                    "carry a value"
                )
            observation = TrendsObservation(
                query_id=query_id,
                observation_date=observation_date,
                value=value,
                status=status,
                partial=parse_bool(
                    row.get("partial", False), "observation.partial"
                ),
            )
            observations.append(observation)
            raw_rows.append(dict(row))
        filtered_payload = {
            "fixture_schema": payload.get(
                "fixture_schema", "vali-google-trends-fixture-v1"
            ),
            "api_version": payload.get("api_version", "fixture-v1"),
            "retrieved_at": retrieved.isoformat(),
            "request_id": payload.get(
                "request_id", sha256_value(request.as_dict())[:16]
            ),
            "observations": raw_rows,
        }
        return TrendsGatewayResponse(
            observations=tuple(observations),
            retrieved_at=retrieved,
            request_id=str(filtered_payload["request_id"]),
            api_version=str(filtered_payload["api_version"]),
            raw_payload=filtered_payload,
        )


__all__ = ["FixtureTrendsGateway"]
