# VALI Artifact Inventory

Inventory date: 2026-06-23  
Migration step: 4J  
Deletion policy: classify and quarantine; no files deleted in this step.

## Classification summary

| Original path | Current/proposed path | Classification | Files / bytes | Moved | Deleted | Reproducible | Empirical/public | Reason |
| --- | --- | --- | ---: | :---: | :---: | :---: | :---: | --- |
| `build/` | `artifacts/quarantine/build/` | `duplicate_or_stale_artifact` | 17 / 119,220 | Yes | No | Yes | No | Stale generated `build/lib` source copy; it must not participate in imports. |
| `dist/` | `artifacts/quarantine/` if later created | `package_build_artifact` | Absent | No | No | Yes | No | No root distribution directory existed. |
| `src/vali_research.egg-info/` | `artifacts/quarantine/vali_research.egg-info/` | `package_build_artifact` | 6 / 5,979 | Yes | No | Yes | No | Generated editable/build metadata, not source. |
| `outputs/*.whl`, `outputs/*.zip` | `artifacts/quarantine/legacy-outputs/` | `package_build_artifact` | 5 / 996,691 | Yes | No | Yes | No | Historical wheels, source bundles, and a synthetic-run bundle. |
| `outputs/README.md` | `artifacts/quarantine/legacy-outputs/README.md` | `duplicate_or_stale_artifact` | 1 / 2,545 | Yes | No | Yes | No | README snapshot bundled with earlier package outputs; canonical root README remains unchanged. |
| `work/dist/`, `work/dist-v020/` | `artifacts/quarantine/packages/` | `duplicate_or_stale_artifact` | 2 / 68,086 | Yes | No | Yes | No | Exact duplicate wheel builds already present in legacy outputs. |
| `outputs/vali-synthetic-run/` | `reports/runs/vali-synthetic-run/` | `generated_report` | 22 / 2,528,974 | Yes | No | Yes | No | Deterministic synthetic research run with CSV/Parquet/report mirrors. |
| `work/{synthetic,signal_run,backtest_run,final_run,regression-backtest-v020}/` | `reports/quarantine/legacy-work/` | `generated_report` | 65 / 9,903,760 | Yes | No | Yes | No | Older generated runs have not been reviewed for archival status. |
| `outputs/KALSHI_ADAPTER_VERIFICATION.md` | `reports/archive/KALSHI_ADAPTER_VERIFICATION.md` | `generated_report` | 1 / 1,480 | Yes | No | No | Yes | Reviewed historical verification note; text and filename preserved. |
| `outputs/kalshi-live-snapshot-2026-06-23/` | `data/interim/kalshi/kalshi-live-snapshot-2026-06-23/` | `normalized_interim_data` | 7 / 69,633 | Yes | No | Partly | Yes | Clearly normalized public ladder, order-book, quote, and manifest outputs. |
| `work/kalshi-hourly-backfill*`, `work/kalshi-live-*` | `data/quarantine/kalshi/` | `needs_review` | 706 / 26,259,220 | Yes | No | Partly | Yes | Mixed immutable raw API archives and normalized provider tables; retained together pending tier review. |
| `work/trends_acceptance_v03/` | `data/quarantine/google_trends/trends_acceptance_v03/` | `needs_review` | 9 / 15,177 | Yes | No | Yes | Fixture-derived | Mixed plan, raw archive, normalized tables, and acceptance outputs. |
| `tests/fixtures/providers/kalshi/` | unchanged | `test_fixture` | 5 files | No | No | Yes | Recorded public fixture | Committed deterministic provider fixtures remain authoritative and byte-unchanged. |
| `tests/fixtures/providers/google_trends/interest.json` | unchanged | `test_fixture` | 1 file | No | No | Yes | Recorded fixture | Authoritative relocated fixture remains byte-unchanged. |
| `tests/fixtures/google_trends/interest.json` | unchanged | `compatibility_copy` | 1 file | No | No | Yes | Recorded fixture | Byte-identical copy retained for the documented README path. |
| `data/raw/` | unchanged | `raw_public_data` | Empty | No | No | N/A | Yes | Reserved for clearly separated immutable public responses; no ambiguous mixed capture was placed here. |
| `data/processed/` | unchanged | `processed_dataset` | Empty | No | No | N/A | Potentially | Reserved for frozen analysis-ready datasets. |
| `.pytest_cache/` | unchanged | `local_cache` | 5 / 33,556 | No | No | Yes | No | Ignored cache; safe to delete later, retained because Step 4J performs no deletion. |
| `.coverage` | unchanged | `local_cache` | 1 / 53,248 | No | No | Yes | No | Ignored test coverage output; retained in this no-deletion step. |
| `.venv/` | unchanged | `local_environment` | 861 / 11,966,558 | No | No | Yes | No | Local environment; ignored and not used as source. |
| `work/.venv/` | unchanged | `local_environment` | 2,792 / 115,354,465 | No | No | Yes | No | Required by the documented migration test command. |
| `work/tools/` | unchanged | `local_environment` | 10,511 / 471,438,907 | No | No | Yes | No | Contains the portable Git installation used for repository operations. |
| `.git.invalid-*`, `.git.partial-init-*` | unchanged | `needs_review` | Empty metadata directories | No | No | No | No | Previously quarantined invalid repository metadata; retained and ignored pending a later explicit deletion review. |
| `outputs/` | unchanged, now empty | `duplicate_or_stale_artifact` | 0 | Contents moved | No | N/A | No | Compatibility directory left in place; all classified contents were relocated. |
| `work/` | unchanged | `local_environment` | Environment/tooling only after moves | Partial | No | Yes | No | Operational environment remains ignored; empirical and generated run contents were removed to classified tiers. |

## Package and archive hashes

SHA-256 values were calculated before or after relocation from unchanged bytes:

| Artifact | SHA-256 |
| --- | --- |
| `vali_research-0.1.0-py3-none-any.whl` | `0304cc17cb9e396fa433a16421719eebdf6b24b132c61c9cb579b9b3a35c9a66` |
| Duplicate `work-dist` 0.1.0 wheel | `0304cc17cb9e396fa433a16421719eebdf6b24b132c61c9cb579b9b3a35c9a66` |
| `vali_research-0.2.0-py3-none-any.whl` | `d2524e495364a5c112e5bb7dd77df5369df0b23c42cabbecca8602d63ca612c32` |
| Duplicate `work-dist-v020` 0.2.0 wheel | `d2524e495364a5c112e5bb7dd77df5369df0b23c42cabbecca8602d63ca612c32` |
| `vali-research-0.2.0-source.zip` | `780ced3f6aefbeea0fbb6bdae3b89bb8e068b8423eca7e7c315418cf6ff89681` |
| `vali-research-source.zip` | `beaad1be6ae147c1f7876b612530ad1d525f25a6ae1fe9a45db4618afc6d717b` |
| `VALI_synthetic_run_outputs.zip` | `35411b833fa229f342755983098de28e1ca093a0407ff30abe62c2439b1fb444` |
| Legacy output README | `e7e7037bf6e9fa17241b1666925746452d10d028ddd1958ce741f8e5a47a357e` |
| `KALSHI_ADAPTER_VERIFICATION.md` | `0f66cf5749a97ca9b6fae8c8b197ba79ff9b76951c4ffeba71c6f0c1dbc2f26c` |

## Import and preservation controls

- `src/vali/` remains the only project source package location used by tests.
- Quarantined `build/lib/vali` is ignored and must never be added to `PYTHONPATH`.
- No fixture, public/empirical response, normalized table, report, archive, or
  compatibility copy was deleted.
- Data quarantine is deliberately mixed until raw envelopes and normalized
  tables can be separated with manifest-aware tooling in a later reviewed step.
- Local environment and cache directories remain ignored and outside the
  authoritative repository contents.
