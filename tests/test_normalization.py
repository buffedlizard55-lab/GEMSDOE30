from __future__ import annotations

import importlib.util
import unittest

HAS_NUMPY = importlib.util.find_spec("numpy") is not None


@unittest.skipUnless(HAS_NUMPY, "optional NumPy training dependency is not installed")
class FoldLocalNormalizationTests(unittest.TestCase):
    def test_heldout_values_do_not_influence_fold_statistics(self) -> None:
        import numpy as np

        from gemsdoe30.normalization import (
            fit_robust_feature_stats,
            normalize_feature_block,
        )

        features = np.array(
            [[[1.0, 2.0, 1000.0, 2000.0], [3.0, 4.0, 3000.0, 4000.0]]],
            dtype=np.float32,
        )
        train_mask = np.array([[True, True, False, False], [True, True, False, False]])
        stats = fit_robust_feature_stats(
            features,
            train_mask,
            seed=30,
            tile_size=2,
            max_samples_per_tile=512,
        )
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]["sample_count"], 4)
        self.assertAlmostEqual(stats[0]["median"], 2.5)
        self.assertAlmostEqual(stats[0]["sampled_max"], 4.0)

        normalized = normalize_feature_block(features, stats)
        self.assertAlmostEqual(float(normalized[0, 0, 0]), -1.0)
        self.assertAlmostEqual(float(normalized[0, 0, 2]), 8.0)

    def test_missing_feature_values_map_to_zero_after_scaling(self) -> None:
        import numpy as np

        from gemsdoe30.normalization import normalize_feature_block

        block = np.array([[[1.0, float("nan")], [float("inf"), 3.0]]], dtype=np.float32)
        normalized = normalize_feature_block(block, [{"median": 2.0, "iqr": 1.0}])
        self.assertEqual(normalized.tolist(), [[[-1.0, 0.0], [0.0, 1.0]]])

    def test_fit_rejects_empty_mask_or_channel(self) -> None:
        import numpy as np

        from gemsdoe30.normalization import fit_robust_feature_stats

        with self.assertRaises(ValueError):
            fit_robust_feature_stats(np.zeros((1, 2, 2)), np.zeros((2, 2), dtype=bool))
        with self.assertRaises(ValueError):
            fit_robust_feature_stats(
                np.full((1, 2, 2), np.nan),
                np.ones((2, 2), dtype=bool),
            )


if __name__ == "__main__":
    unittest.main()
