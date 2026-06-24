# VALI Final 4-Series Validation Report

## Validation identity

- Validation date: `2026-06-23`
- Branch: `main`
- Commit under validation: `3639580d81d4b6b2e7039f36771b7e6f785c74b5`
- Python: `3.12.13`
- Package version: `0.3.0`
- Migration release-candidate label: `v0.1`

## Automated test validation

Command:

```powershell
& '.\work\.venv\Scripts\python.exe' -m pytest -q
```

Result: **149 passed, 0 failed**.

## CLI smoke validation

The following deterministic, help-only commands returned exit code 0. They did
not contact live APIs, require credentials, or write research data:

```powershell
& '.\work\.venv\Scripts\python.exe' -m vali --help
& '.\work\.venv\Scripts\python.exe' -m vali validate --help
& '.\work\.venv\Scripts\python.exe' -m vali signal --help
& '.\work\.venv\Scripts\python.exe' -m vali backtest --help
& '.\work\.venv\Scripts\python.exe' -m vali report --help
& '.\work\.venv\Scripts\python.exe' -m vali sample-data --help
& '.\work\.venv\Scripts\python.exe' -m vali kalshi --help
& '.\work\.venv\Scripts\python.exe' -m vali kalshi discover --help
& '.\work\.venv\Scripts\python.exe' -m vali kalshi backfill --help
& '.\work\.venv\Scripts\python.exe' -m vali kalshi snapshot --help
& '.\work\.venv\Scripts\python.exe' -m vali trends --help
& '.\work\.venv\Scripts\python.exe' -m vali trends plan --help
& '.\work\.venv\Scripts\python.exe' -m vali trends backfill --help
& '.\work\.venv\Scripts\python.exe' -m vali trends collect --help
& '.\work\.venv\Scripts\python.exe' -m vali trends status --help
```

## Contract validation

- Frozen Google Trends manifest hash:
  `f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a`
- Import-source validation: **pass**. Public, boundary, and compatibility
  modules resolve from `src/vali`, not quarantined build artifacts.
- Prohibited-surface validation: **pass**. Repository search occurrences are
  confined to prohibition documentation, input-rejection contracts, and tests;
  no executable or public API implements `P_flow`, private client data,
  proprietary order flow, order submission, credentialed trading, or live
  trading.
- Config-path validation: **pass**. Both
  `configs/experiments/fed_easing_v1.toml` and `examples/config.toml` load while
  preserving their established relative-path resolution behavior.
- Fixture-path validation: **pass**. Canonical provider fixtures and the old
  Google Trends compatibility fixture remain present and deterministic.

## Known caveats

The migration label/package version ambiguity remains documented. No dependency
lockfile exists. Quarantined artifacts and mixed Kalshi captures require later
review. Kalshi historical depth is unobserved, venue configuration is embedded,
and the fee model is provisional. Google has not supplied an implemented
official alpha protocol or documented revision guarantees. No empirical alpha
claim has been validated.

## Conclusion

**Pass.** The repository is ready to exit 4-series migration and enter 5-series
operational research readiness, subject to the caveats listed. This conclusion
does not mean VALI alpha is proven, trading-ready, or production investment
infrastructure.
