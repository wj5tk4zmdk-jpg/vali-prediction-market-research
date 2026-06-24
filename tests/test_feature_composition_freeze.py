import unittest

import pandas as pd

from vali.config import FeatureConfig
from vali.features import build_attention_index


def frozen_feature_inputs():
    cutoffs = pd.date_range("2025-01-01 21:00", periods=10, freq="D", tz="UTC")
    rows = []
    for feature_id in ("required-search", "optional-search"):
        for index, cutoff in enumerate(cutoffs):
            if feature_id == "optional-search" and index == 6:
                continue
            rows.append(
                {
                    "feature_id": feature_id,
                    "observation_at": cutoff - pd.Timedelta(hours=2),
                    "available_at": cutoff - pd.Timedelta(hours=1),
                    "vintage": "initial",
                    "source": "public_search",
                    "value": float(index + (2 if feature_id == "optional-search" else 0)),
                }
            )
    manifest = pd.DataFrame(
        [
            {
                "feature_id": "required-search",
                "rationale": "frozen required feature",
                "transformation": "level",
                "polarity": 1,
                "availability_lag_days": 0,
                "missing_policy": "asof",
                "max_age_days": 1,
                "required": True,
                "source": "public_search",
            },
            {
                "feature_id": "optional-search",
                "rationale": "frozen optional feature",
                "transformation": "level",
                "polarity": -1,
                "availability_lag_days": 0,
                "missing_policy": "asof",
                "max_age_days": 1,
                "required": False,
                "source": "public_search",
            },
        ]
    )
    return cutoffs, pd.DataFrame(rows), manifest


class FeatureCompositionFreezeTests(unittest.TestCase):
    def test_missing_optional_feature_does_not_silently_reweight_attention(self):
        cutoffs, features, manifest = frozen_feature_inputs()
        attention, audit = build_attention_index(
            features,
            manifest,
            cutoffs,
            FeatureConfig(standardization_window=3, min_periods=3),
        )

        missing_day = attention.loc[attention["cutoff_at"] == cutoffs[6]].iloc[0]
        self.assertTrue(pd.isna(missing_day["attention"]))
        self.assertEqual(missing_day["attention_rejection_reason"], "missing_optional_feature")
        self.assertFalse(missing_day["composition_complete"])
        self.assertEqual(missing_day["feature_composition_policy"], "reject")
        optional_audit = audit.loc[
            (audit["cutoff_at"] == cutoffs[6])
            & (audit["feature_id"] == "optional-search")
        ].iloc[0]
        self.assertTrue(optional_audit["missing_for_signal"])

    def test_frozen_equal_weights_are_stable_across_dates(self):
        cutoffs, features, manifest = frozen_feature_inputs()
        _, audit = build_attention_index(
            features,
            manifest,
            cutoffs,
            FeatureConfig(standardization_window=3, min_periods=3),
        )

        self.assertEqual(set(audit["frozen_weight"]), {0.5})
        self.assertTrue(
            (audit.groupby("feature_id")["frozen_weight"].nunique() == 1).all()
        )

    def test_dynamic_reweighting_requires_explicit_configuration_and_is_reported(self):
        cutoffs, features, manifest = frozen_feature_inputs()
        attention, _ = build_attention_index(
            features,
            manifest,
            cutoffs,
            FeatureConfig(
                standardization_window=3,
                min_periods=3,
                optional_feature_policy="dynamic_reweight",
            ),
        )

        missing_day = attention.loc[attention["cutoff_at"] == cutoffs[6]].iloc[0]
        self.assertTrue(pd.notna(missing_day["attention"]))
        self.assertEqual(
            missing_day["feature_composition_policy"], "dynamic_reweight"
        )

    def test_feature_outside_frozen_manifest_is_rejected_before_composition(self):
        cutoffs, features, manifest = frozen_feature_inputs()
        added = features.iloc[[0]].copy()
        added["feature_id"] = "post-freeze-feature"
        added["available_at"] = cutoffs[-1] - pd.Timedelta(minutes=30)

        with self.assertRaisesRegex(ValueError, "outside the frozen manifest"):
            build_attention_index(
                pd.concat([features, added], ignore_index=True),
                manifest,
                cutoffs,
                FeatureConfig(standardization_window=3, min_periods=3),
            )


if __name__ == "__main__":
    unittest.main()
