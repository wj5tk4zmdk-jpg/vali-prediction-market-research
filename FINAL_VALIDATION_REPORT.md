# VALI Final 4-Series Validation Report

## Validation identity

- Validation date: `2026-06-24`
- Repository: `vali-prediction-market-research`
- Branch: `main`
- Commit under validation: `0493e9a358e59a491116d3bdf4af529a2ee44e79`
- Python: `3.12.13`
- Package version: `0.3.0`
- Migration release-candidate label: `v0.1`
- Submission status: **research-engine submission artifact**

## Automated test validation

Reviewer reproduction command after completing the fresh-clone installation in
`README.md`:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q
```

Result: **186 passed, 0 failed**.

The repository-local `.venv` was not provisioned when this identity was
refreshed, so the passing result above was produced in an established ignored
Python 3.12.13 environment with VALI and its declared development dependencies
already installed. A subsequent clean-clone installation test passed at commit
`3f1329e2708d6e8ab24eecfeefb5c8f5ccaa9e70`; see
[`docs/submission/CLEAN_CLONE_INSTALL_TEST.md`](docs/submission/CLEAN_CLONE_INSTALL_TEST.md).
The machine-local interpreter path is intentionally omitted from reviewer-facing
documentation.

## CLI smoke validation

The following 15 deterministic, help-only command surfaces returned exit code
0. They did not contact live APIs, require credentials, or write research data.
After installation, they may be reproduced as:

```powershell
python -m vali --help
python -m vali validate --help
python -m vali signal --help
python -m vali backtest --help
python -m vali report --help
python -m vali sample-data --help
python -m vali kalshi --help
python -m vali kalshi discover --help
python -m vali kalshi backfill --help
python -m vali kalshi snapshot --help
python -m vali trends --help
python -m vali trends plan --help
python -m vali trends backfill --help
python -m vali trends collect --help
python -m vali trends status --help
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
lockfile exists. The clean-clone installation test passed; see
[`docs/submission/CLEAN_CLONE_INSTALL_TEST.md`](docs/submission/CLEAN_CLONE_INSTALL_TEST.md).
Quarantined artifacts and mixed Kalshi captures require later review. Canonical
empirical validation remains blocked pending documented point-in-time attention
history. Kalshi historical depth is unobserved, so capacity and tradability
claims remain disabled; venue configuration is embedded and the fee model is
provisional. Google has not supplied an implemented official alpha protocol or
documented revision guarantees. No empirical alpha claim or trading-readiness
claim has been validated. No trading-readiness claim is made.

## Conclusion

**Pass as a research-engine submission artifact.** The repository passes its
deterministic test and CLI contracts at the stated commit, subject to the
caveats above. Canonical empirical validation is not authorized. This conclusion
does not mean VALI alpha is proven, trading-ready, or production investment
infrastructure.
