import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from vali.config import ValiConfig
from vali.pipeline import run_signal_pipeline, validate_inputs
from vali.sample import make_synthetic_dataset


class PipelineIntegrationTests(unittest.TestCase):
    def test_synthetic_signal_run_is_deterministic_and_writes_mirrors(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = make_synthetic_dataset(root / "data", seed=42, event_count=3)
            config = ValiConfig.from_toml(config_path)
            bundle = validate_inputs(config)
            self.assertEqual(bundle.validation.rows["events"], 3)
            first = run_signal_pipeline(config, root / "run_one")
            second = run_signal_pipeline(config, root / "run_two")
            pd.testing.assert_frame_equal(first.signals, second.signals)
            self.assertTrue((root / "run_one" / "signals.csv").exists())
            self.assertTrue((root / "run_one" / "signals.parquet").exists())
            manifest = json.loads((root / "run_one" / "run_manifest.json").read_text())
            self.assertEqual(manifest["input_sha256"], json.loads((root / "run_two" / "run_manifest.json").read_text())["input_sha256"])


if __name__ == "__main__":
    unittest.main()
