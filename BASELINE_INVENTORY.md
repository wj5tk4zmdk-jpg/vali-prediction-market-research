# VALI Baseline Inventory

Baseline captured at **2026-06-23T22:50:10.6344839Z** from:

`C:\Users\matte\Documents\Codex\2026-06-23\sdfas`

This inventory records the pre-refactor working state. No Git repair, source
refactor, file move, formula change, execution change, provider change, or
artifact deletion was performed while creating it.

## Version-control status

Git is not valid or usable in this workspace. Both the workspace and its parent
returned:

```text
fatal: not a git repository (or any of the parent directories): .git
```

The local `.git` directory is empty. No repair or initialization was attempted.
This inventory is the baseline preservation mechanism until version control is
explicitly established.

## Environment and package versions

Baseline test environment:

```text
Python:    3.12.13
Executable: work\.venv\Scripts\python.exe
vali:      0.3.0
numpy:     2.3.5
pandas:    3.0.1
pyarrow:   24.0.0
pytest:    9.1.1
```

All listed imports succeeded in `work/.venv`. The separate root `.venv` is not
the certified baseline environment and previously lacked the complete declared
test/Parquet dependency set.

## Directory summary

Counts include generated and ignored material present at capture time.

| Entry | Type | Files | Bytes |
|---|---:|---:|---:|
| `.agents/` | directory | 0 | 0 |
| `.codex/` | directory | 0 | 0 |
| `.git/` | directory | 0 | 0 |
| `.pytest_cache/` | directory | 5 | 4,774 |
| `.venv/` | directory | 861 | 11,966,558 |
| `build/` | directory | 17 | 119,220 |
| `examples/` | directory | 1 | 898 |
| `notebooks/` | directory | 1 | 2,150 |
| `outputs/` | directory | 36 | 3,599,323 |
| `scripts/` | directory | 2 | 1,404 |
| `src/` | directory | 43 | 374,059 |
| `tests/` | directory | 38 | 196,166 |
| `work/` | directory | 3,574 | 151,600,708 |

Top-level files at capture time were `.coverage`, `.gitignore`,
`pyproject.toml`, and `README.md`. Governance files in this change are additions
and are not included in the counts above.

## Source files

```text
src/vali/__init__.py
src/vali/__main__.py
src/vali/backtest.py
src/vali/calibration.py
src/vali/cli.py
src/vali/config.py
src/vali/decisions.py
src/vali/features.py
src/vali/io.py
src/vali/market.py
src/vali/pipeline.py
src/vali/regimes.py
src/vali/reporting.py
src/vali/sample.py
src/vali/signals.py
src/vali/providers/__init__.py
src/vali/providers/google_trends.py
src/vali/providers/kalshi.py
src/vali/data/google_trends_query_manifest.v1.csv
```

## Tests and committed fixtures

```text
tests/__init__.py
tests/test_backtest.py
tests/test_decisions.py
tests/test_features.py
tests/test_google_trends.py
tests/test_kalshi.py
tests/test_market.py
tests/test_pipeline.py
tests/test_regimes.py
tests/test_signals.py
tests/test_validation.py
tests/fixtures/google_trends/interest.json
tests/fixtures/kalshi/candlesticks.json
tests/fixtures/kalshi/events.json
tests/fixtures/kalshi/markets.json
tests/fixtures/kalshi/orderbook.json
tests/fixtures/kalshi/trades.json
```

## Generated, build, and artifact locations

- `build/`: generated, stale package copy.
- `src/vali_research.egg-info/`: generated package metadata.
- `.pytest_cache/`, `.coverage`, `__pycache__/`: generated test/runtime state.
- `.venv/` and `work/.venv/`: local environments.
- `work/dist*`: historical wheel builds.
- `work/backtest_run`, `final_run`, `regression-backtest-v020`, and
  `signal_run`: generated research runs.
- `work/synthetic`: regenerable synthetic inputs.
- `work/kalshi-*`: public Kalshi discovery, raw responses, normalized
  backfills, trades, and snapshots; retained pending provenance review.
- `work/trends_acceptance_v03`: fixture-derived Google Trends acceptance output.
- `outputs/`: historical wheels, source archives, verification notes, public
  snapshot output, and synthetic report output.

No generated artifact was deleted.

## Baseline test result

Command:

```powershell
& '.\work\.venv\Scripts\python.exe' -m pytest -q
```

Result:

```text
42 tests collected
41 passed
1 failed
```

Failure:

```text
tests/test_google_trends.py::GoogleTrendsGatewayTests::
test_fixture_backfill_emits_only_active_features_and_complete_audit

pyarrow.lib.ArrowTypeError:
object of type <class 'str'> cannot be converted to int
Conversion failed for column retrieved_at with type object
```

The failure occurs during fixture `collect` output when
`trends_exclusions.retrieved_at` contains mixed representations that PyArrow
cannot serialize. It was recorded without changing source logic or test
expectations.

## Important SHA-256 hashes

| Path | SHA-256 |
|---|---|
| `pyproject.toml` | `60237fb6056406a86d8906d9febd7f13b80593248a2a659b259146b9c57b5e00` |
| `README.md` | `f7b805030fe317e11348fde6c8a5d27765910a70db488edb84026a00081941d0` |
| `examples/config.toml` | `9a8397295a0a61a986cee723a1c91824efb0184cb31a6e7102e903e2267be843` |
| `src/vali/config.py` | `cdb15eafe0c7452d48edaa8b546eb7fcea5534e43451e0ec85e486436ce9e057` |
| `src/vali/io.py` | `659941766b294922a8622eaca85fe506661a43e4ecbf4a84548c35ecc6212e32` |
| `src/vali/features.py` | `6c263a95abe770d563888a5c631fb94598d0720c59c4a1caebab7bb429f56b78` |
| `src/vali/signals.py` | `a028fd7d8121b0193952906eadee67d4e75068e4ba9ca711579b3cf46403f405` |
| `src/vali/regimes.py` | `951b761327343039f48b95a3f703cd4cb56eea3896c71bcec213d3edad70e7bb` |
| `src/vali/market.py` | `533b5cbfe407cbfa61273c0dc04d124a1ec8fb4a3f023a6b05c2c2b406531f9d` |
| `src/vali/decisions.py` | `76a252ba3a768471f59270b6bc4405937ca8512cecee86be532674e1cb4d0dc9` |
| `src/vali/calibration.py` | `d0ae3f06c18145e07ce2935a0ab346b8f9db4d7de7c9a749434ddb108c654d2f` |
| `src/vali/backtest.py` | `f0f5dc1d81587b2ab5b97836fc8218d84a1138a04df16203b458333b8071280e` |
| `src/vali/pipeline.py` | `b9fa36ab18a03816ecbac2c5add5a78cdc2527735f6ecc38f9cf72ea2a3ffb76` |
| `src/vali/reporting.py` | `94d52e0281cf298dc2ebab373fb2e03ee7585c5b5f19184857d92ffa67e8b5df` |
| `src/vali/providers/kalshi.py` | `bf115dfec75a86c42d4c3891f9669064f42c608a5ea2e25ab33cd739fcc48958` |
| `src/vali/providers/google_trends.py` | `f7a26c49ac0da8dbffdf8881c75f1330920115b52989eee566527a74e9ce5334` |
| `src/vali/data/google_trends_query_manifest.v1.csv` | `86ba16b0f447193fbc3053fc7094294611ba11baa9889ade55ec75ad5d125b95` |
| `tests/test_features.py` | `5ac82c82a259cee280ea9fa201f382e1c08e62ea7a6c15022f84d9aafac3952a` |
| `tests/test_signals.py` | `da8ba0a8458e31fda803854242a76083bdd78c74e9453a4905cd306d2f04f685` |
| `tests/test_regimes.py` | `f922fc3b956560d22ae8e89f6afb6b1f32ed3460268936896fefc4de29d2b761` |
| `tests/test_market.py` | `c334a39f3b74f1cab1e692e0fef50aa7a6e69d990e61435678d1a4e65c86f9d9` |
| `tests/test_backtest.py` | `b5e6ef3a8244dc7c7165701947c3defd03a9f84afa7c78190e266341a4a5baf4` |
| `tests/test_validation.py` | `152a292e05544ef9d9236ed65c9099067331b648fe6ab0b86694d6450dbe1f54` |
| `tests/test_pipeline.py` | `86bff8a89755f3b5b6e6f345406676769abf013804aca875761e07948f966c73` |
| `tests/test_kalshi.py` | `5e9c3e6e6601fa558443f4e096b65915e987b1b646e0f36936fb135d178f52f5` |
| `tests/test_google_trends.py` | `a79ffd5d5b9df2562c4e87a457e62ceb8cfae3b80d908869d2ed42fd37c5550c` |

