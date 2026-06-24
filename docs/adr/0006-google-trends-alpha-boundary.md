# ADR 0006: Google Trends Alpha Boundary

## Status

Accepted - 2026-06-23

## Context

Search-interest data may provide a public behavioral-attention proxy, but it is
normalized, potentially revised or suppressed, sensitive to media coverage,
and vulnerable to reaction effects and query-selection bias. The official API
alpha has not exposed its complete public wire protocol.

## Decision

Google Trends data is hypothesis-bearing public evidence, not magical
mind-reading or a direct measure of beliefs. Queries, direction, transformations,
availability assumptions, and inclusion rules must be frozen before evaluation.
Suppressed or low-volume observations are not zeros. General Fed attention and
economic-stress searches remain diagnostics until explicitly approved. Only the
official API may be integrated; scraping and unofficial fallbacks are excluded.

## Consequences

Historical and forward vintages must be archived. Contamination and
attention-following-market explanations must be reported. The current fixture
gateway remains research scaffolding; live integration waits for official
authentication, schema, revision, and quota documentation.

