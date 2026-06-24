# ADR 0002: Public Data and Forbidden Inputs

## Status

Accepted - 2026-06-23

## Context

VALI is intended to test whether public behavioral information and public
market prices diverge. Private desk information would change the research
question, impair reproducibility, and create governance and compliance risk.

## Decision

Core inputs are limited to public behavioral data, public quotes, public trades,
public settlement records, and public order-book snapshots used for liquidity
or execution research. The core must not ingest `P_flow`, proprietary order
flow, client data, pending orders, confidential venue data, product-launch
information, or other non-public desk information. Live order submission and
order management are prohibited.

## Consequences

Every source must carry public provenance. Future schemas and tests will reject
forbidden source classes. Public order-book depth remains permissible for
execution validation but is not a proprietary predictive feature.

