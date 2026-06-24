import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from vali.artifacts.manifests import build_run_manifest, sha256_file
from vali.artifacts.metrics import (
    divergence_half_lives,
    forecast_metrics,
    regime_confusion,
    trade_metrics,
)
from vali.artifacts.reports import (
    WARNING as artifact_warning,
    rebuild_report as artifact_rebuild_report,
    render_html_report,
)
from vali.artifacts.serialization import write_dataframe
from vali.config import ValiConfig
from vali.reporting import (
    WARNING as legacy_warning,
    divergence_half_lives as legacy_divergence_half_lives,
    forecast_metrics as legacy_forecast_metrics,
    regime_confusion as legacy_regime_confusion,
    render_html_report as legacy_render_html_report,
    trade_metrics as legacy_trade_metrics,
    write_dataframe as legacy_write_dataframe,
)
from vali.research.pipeline import (
    _manifest as legacy_pipeline_manifest,
    _sha256 as legacy_pipeline_sha256,
    rebuild_report as research_rebuild_report,
)
from vali.sample import make_synthetic_dataset


class ArtifactReportingCompatibilityTests(unittest.TestCase):
    def test_old_and_new_artifact_imports_are_available(self):
        self.assertEqual(legacy_warning, artifact_warning)
        for function in (
            forecast_metrics,
            trade_metrics,
            divergence_half_lives,
            regime_confusion,
            write_dataframe,
            build_run_manifest,
            sha256_file,
            render_html_report,
            artifact_rebuild_report,
            research_rebuild_report,
        ):
            self.assertTrue(callable(function))

    def test_metric_wrappers_match_artifact_boundary(self):
        forecasts = pd.DataFrame(
            {
                "outcome": [0, 1, 1],
                "market_probability": [0.20, 0.60, 0.80],
                "historical_probability": [0.40, 0.40, 0.50],
                "vali_calibrated_probability": [0.25, 0.70, 0.75],
            }
        )
        trades = pd.DataFrame(
            {
                "exit_at": pd.to_datetime(
                    ["2025-01-02", "2025-01-03", "2025-01-04"], utc=True
                ),
                "net_pnl": [10.0, -5.0, 2.0],
                "hit": [True, False, True],
                "capacity_used": [50.0, 75.0, 100.0],
            }
        )

        legacy_forecast, legacy_calibration = legacy_forecast_metrics(forecasts)
        artifact_forecast, artifact_calibration = forecast_metrics(forecasts)
        pd.testing.assert_frame_equal(legacy_forecast, artifact_forecast)
        pd.testing.assert_frame_equal(legacy_calibration, artifact_calibration)
        pd.testing.assert_frame_equal(
            legacy_trade_metrics(trades), trade_metrics(trades)
        )

    def test_diagnostic_wrappers_match_artifact_boundary(self):
        signals = pd.DataFrame(
            {
                "contract_id": ["c1", "c1", "c1", "c2"],
                "cutoff_at": pd.to_datetime(
                    ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-01"],
                    utc=True,
                ),
                "divergence_magnitude": [2.1, 1.5, 0.4, 0.2],
                "regime": [
                    "attention_leading",
                    "attention_leading",
                    "coupled",
                    "unstable",
                ],
                "realized_regime": [
                    "attention_leading",
                    "coupled",
                    "coupled",
                    "unstable",
                ],
            }
        )

        pd.testing.assert_frame_equal(
            legacy_divergence_half_lives(signals, 2.0, 0.5),
            divergence_half_lives(signals, 2.0, 0.5),
        )
        pd.testing.assert_frame_equal(
            legacy_regime_confusion(signals), regime_confusion(signals)
        )

    def test_serialization_preserves_names_rows_and_csv_content(self):
        frame = pd.DataFrame(
            {
                "cutoff_at": pd.to_datetime(
                    ["2025-01-01 16:00", "2025-01-02 16:00"], utc=True
                ),
                "value": [1.25, 2.50],
            }
        )
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy_result = legacy_write_dataframe(frame, "signals", root / "legacy")
            artifact_result = write_dataframe(frame, "signals", root / "artifact")

            self.assertEqual(legacy_result, artifact_result)
            self.assertEqual(artifact_result["csv"], "signals.csv")
            self.assertEqual(artifact_result["rows"], 2)
            self.assertEqual(
                (root / "legacy" / "signals.csv").read_bytes(),
                (root / "artifact" / "signals.csv").read_bytes(),
            )

    def test_manifest_hashes_and_keys_are_unchanged(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = make_synthetic_dataset(root / "data", seed=11, event_count=3)
            config = ValiConfig.from_toml(config_path)

            self.assertEqual(legacy_pipeline_sha256(config_path), sha256_file(config_path))
            self.assertEqual(legacy_pipeline_manifest(config), build_run_manifest(config))
            self.assertEqual(
                set(build_run_manifest(config)),
                {
                    "package_version",
                    "methodology_version",
                    "parameter_freeze_date",
                    "config_path",
                    "config_sha256",
                    "input_sha256",
                    "research_warning",
                },
            )

    def test_report_wrapper_and_rebuild_preserve_html_and_artifact_names(self):
        frames = {
            "metrics": pd.DataFrame([{"model": "market", "metric": "brier_score", "value": 0.2}]),
            "forecasts": pd.DataFrame([{"event_id": "e1", "outcome": 1}]),
            "trades": pd.DataFrame(),
            "sensitivity": pd.DataFrame([{"velocity_window": 7}]),
            "exclusions": pd.DataFrame([{"stage": "decision", "reason": "below_threshold"}]),
            "calibration": pd.DataFrame(),
            "regime_confusion": pd.DataFrame(),
        }
        manifest = {
            "methodology_version": "1.0",
            "parameter_freeze_date": "2026-06-23",
            "execution_validation": {
                "status": "unvalidated_incomplete_execution_snapshots"
            },
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy_report = root / "legacy.html"
            artifact_report = root / "artifact.html"
            report_arguments = (
                frames["metrics"],
                frames["forecasts"],
                frames["trades"],
                frames["sensitivity"],
                frames["exclusions"],
                frames["calibration"],
                frames["regime_confusion"],
                manifest,
            )
            legacy_render_html_report(legacy_report, *report_arguments)
            render_html_report(artifact_report, *report_arguments)
            self.assertEqual(legacy_report.read_bytes(), artifact_report.read_bytes())

            run_dir = root / "run"
            run_dir.mkdir()
            for name, frame in frames.items():
                frame.to_csv(run_dir / f"{name}.csv", index=False)
            (run_dir / "run_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            self.assertEqual(artifact_rebuild_report(run_dir), run_dir / "report.html")
            first_report = (run_dir / "report.html").read_bytes()
            self.assertEqual(research_rebuild_report(run_dir), run_dir / "report.html")
            self.assertEqual(first_report, (run_dir / "report.html").read_bytes())


if __name__ == "__main__":
    unittest.main()
