# Hormuz Normalization Graph Freeze Checklist

Status: draft, human-review-required, not validated, not frozen.

This Hormuz graph is not a trading signal, not an alpha claim, not a
trading-readiness claim, not a frozen attention manifest, and not a canonical
validation input.
It is not a canonical validation input.

## Current state

- [x] Example graph exists for documentation and review discussion.
- [x] Evidence status remains `not_validated` or `hypothesized`.
- [x] Human review is required before empirical use.
- [x] Claim boundaries prohibit alpha and trading-readiness claims.
- [x] Private data, proprietary order flow, credentials, live trading, order
  submission, and `P_flow` remain prohibited.
- [ ] Graph is frozen.
- [ ] Graph hash is computed.
- [ ] Graph is validation eligible.

## Required before freezing

- [ ] Verify exact Kalshi contract rules.
- [ ] Verify exact contract template applicability.
- [ ] Confirm `POLITICALSTAT` is not applied unless contract review supports it.
- [ ] Verify settlement source and source hierarchy.
- [ ] Verify terminal measure.
- [ ] Verify Clear Horizon.
- [ ] Verify market/date-bucket mapping.
- [ ] Verify comparison operator, threshold, and time period.
- [ ] Verify last-trading, expiration, and settlement-review rules.
- [ ] Review attention concepts.
- [ ] Review candidate queries.
- [ ] Review expected direction and lag windows.
- [ ] Review contamination risks.
- [ ] Confirm all attention observations would be public and point-in-time.
- [ ] Confirm no private or proprietary inputs.
- [ ] Confirm no proprietary order flow.
- [ ] Confirm no `P_flow`.
- [ ] Confirm no credentials are required for this graph object.
- [ ] Confirm no live trading or order submission is introduced.
- [ ] Confirm claim boundaries.
- [ ] Create or update the hash inventory.
- [ ] Record `frozen_at`, `frozen_by`, graph version, and graph hash.

Until every required item is resolved, the Hormuz graph remains draft,
human-review-required, and not validated.
