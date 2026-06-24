"""Current explicitly provisional basis-point fee assumptions."""

from __future__ import annotations


FEE_MODEL = "provisional_bps"


def fee_rate(fee_bps: float) -> float:
    return fee_bps / 10_000


def provisional_fee(value: float, fee_bps: float) -> float:
    return value * fee_rate(fee_bps)


def provisional_fee_metadata(fee_bps: float) -> dict:
    return {
        "fee_model": FEE_MODEL,
        "fee_bps": fee_bps,
        "fee_assumption_provisional": True,
    }


__all__ = [
    "FEE_MODEL",
    "fee_rate",
    "provisional_fee",
    "provisional_fee_metadata",
]
