from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HAS_NUMPY_SCIPY = bool(importlib.util.find_spec("numpy") and importlib.util.find_spec("scipy"))


@unittest.skipUnless(HAS_NUMPY_SCIPY, "optional NumPy/SciPy holdout dependencies are not installed")
class SpatialHoldoutTests(unittest.TestCase):
    def test_checkpoint_cannot_be_relabelled_as_another_holdout_fold(self) -> None:
        from gemsdoe30.cv import validate_checkpoint_fold

        validate_checkpoint_fold(2, 2)
        validate_checkpoint_fold(None, None)
        for checkpoint_fold, requested_fold in ((0, 1), (None, 0), (3, None)):
            with self.subTest(checkpoint_fold=checkpoint_fold, requested_fold=requested_fold), self.assertRaisesRegex(
                ValueError, "fold"
            ):
                validate_checkpoint_fold(checkpoint_fold, requested_fold)

    def test_full_grid_pool_keeps_near_miss_across_quadrant_boundary(self) -> None:
        import numpy as np

        from gemsdoe30.cv import compare_spatial_holdout
        from gemsdoe30.metric import distance_weighted_tversky

        truth = np.zeros((8, 8), dtype=np.uint8)
        truth[3, 2] = 1  # Last row of the top-left quadrant.
        baseline = np.zeros((8, 8), dtype=np.float32)
        candidate = np.zeros((8, 8), dtype=np.float32)
        candidate[4, 2] = 1.0  # One 100 m cell across the quadrant boundary.
        valid = np.ones((8, 8), dtype=bool)

        comparison = compare_spatial_holdout(truth, baseline, candidate, valid)
        exact = distance_weighted_tversky(candidate, truth, valid)
        self.assertAlmostEqual(comparison["pooled_candidate"]["dti"], exact.score, places=12)
        self.assertAlmostEqual(comparison["pooled_candidate"]["tp_weight"], 2.0 / 3.0, places=12)
        self.assertAlmostEqual(comparison["pooled_delta_dti"], 2.0 / 3.0, places=6)
        # If quadrant counts were summed independently, this one-cell near miss
        # would be lost: both isolated quadrant scores are zero.
        self.assertTrue(all(row["fold_isolated_candidate_dti"] == 0.0 for row in comparison["folds"]))
        self.assertIn("cross-quadrant kernel interactions retained", comparison["aggregation"])


@unittest.skipUnless(importlib.util.find_spec("numpy"), "optional NumPy dependency is not installed")
class OOFProvenanceTests(unittest.TestCase):
    def test_oof_loader_requires_sidecar_and_matching_array_hash(self) -> None:
        import numpy as np

        from scripts.evaluate_loss_ablation import EXPECTED_HOLDOUT_PROTOCOL, OOF_SCOPE, _read_oof

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "regional-oof.npy"
            footprint = np.ones((8, 8), dtype=bool)
            footprint[0, 0] = False
            values = np.full((8, 8), 0.25, dtype=np.float32)
            values[~footprint] = np.nan
            np.save(path, values)
            grid_signature = {
                "shape_hw": [8, 8],
                "epsg": 32611,
                "transform_gdal": [0.0, 100.0, 0.0, 0.0, 0.0, -100.0],
                "valid_mask_sha256": hashlib.sha256(np.packbits(footprint).tobytes()).hexdigest(),
                "dataset_signature": "d" * 64,
            }
            manifest = {
                "schema_version": 1,
                "output_file": path.name,
                "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "shape": [8, 8],
                "valid_pixels": int(footprint.sum()),
                "grid_signature": grid_signature,
                "training_recipe": {
                    "loss_mode": "regional",
                    "boundary_weight": 0.0,
                    "seed": 30,
                    "epochs": 1,
                    "steps_per_epoch": 1,
                    "batch_size": 1,
                    "patch_size": 16,
                    "learning_rate": 0.001,
                    "base_channels": 24,
                    "pixel_size_x_m": 100.0,
                    "pixel_size_y_m": 100.0,
                    "metric_radius_m": 300.0,
                    "metric_alpha": 0.2,
                    "metric_beta": 0.8,
                    "weight_decay": 0.0001,
                    "optimizer": "AdamW",
                    "patch_radius_halo_pixels": 3,
                },
                "folds": [
                    {
                        "fold": fold,
                        "checkpoint_fold": fold,
                        "finite_heldout_pixels": 15 if fold == 0 else 16,
                        "checkpoint_sha256": "a" * 64,
                    }
                    for fold in range(4)
                ],
                "holdout_protocol": EXPECTED_HOLDOUT_PROTOCOL,
                "scope": OOF_SCOPE,
                "not_a_score": True,
            }
            path.with_suffix(".json").write_text(json.dumps(manifest), encoding="utf-8")

            loaded, _ = _read_oof(path, footprint, grid_signature, "regional")
            self.assertTrue(np.allclose(loaded[footprint], 0.25))
            with self.assertRaisesRegex(ValueError, "checksum"):
                np.save(path, np.where(footprint, 0.75, np.nan).astype(np.float32))
                _read_oof(path, footprint, grid_signature, "regional")


if __name__ == "__main__":
    unittest.main()
