from __future__ import annotations

import unittest

import numpy as np

from gemsdoe30.holdout import (
    distance_matched_draw,
    fp_weight_field,
    masked_dti,
    masked_dti_by_blocks,
    split_components,
)


class SplitComponentsTests(unittest.TestCase):
    def _catalogue(self) -> np.ndarray:
        cat = np.zeros((64, 64), dtype=bool)
        cat[10:12, 5:40] = True      # horizontal strand
        cat[20:22, 20:55] = True     # second strand
        cat[40:55, 42:44] = True     # vertical strand
        return cat

    def test_split_is_deterministic_and_disjoint(self) -> None:
        cat = self._catalogue()
        h1, k1, n1 = split_components(cat, seed=7)
        h2, k2, n2 = split_components(cat, seed=7)
        self.assertEqual(n1, n2)
        self.assertTrue(np.array_equal(h1, h2))
        self.assertTrue(np.array_equal(k1, k2))
        self.assertFalse(np.any(h1 & k1))
        self.assertTrue(np.array_equal(h1 | k1, cat))
        self.assertGreater(int(h1.sum()), 0)
        self.assertGreater(int(k1.sum()), 0)

    def test_different_seeds_can_change_assignment(self) -> None:
        cat = self._catalogue()
        h1, _, _ = split_components(cat, seed=7)
        h3, _, _ = split_components(cat, seed=8)
        self.assertGreater(int(np.count_nonzero(h1 != h3)), 0)

    def test_empty_catalogue_rejected(self) -> None:
        with self.assertRaises(ValueError):
            split_components(np.zeros((8, 8), dtype=bool))


class MaskedDtiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.truth = np.zeros((41, 41), dtype=bool)
        self.truth[20, 20] = True
        self.truth[20, 21] = True
        self.known = np.zeros_like(self.truth)
        self.known[5, 5] = True

    def test_perfect_prediction_scores_one(self) -> None:
        pred = self.truth.copy()
        result = masked_dti(pred, self.truth, self.known)
        self.assertAlmostEqual(result["dti"], 1.0, places=6)

    def test_near_miss_beats_far_miss(self) -> None:
        near = np.zeros_like(self.truth)
        near[20, 22] = True  # 100 m from truth
        far = np.zeros_like(self.truth)
        far[20, 25] = True  # 400+ m from truth
        r_near = masked_dti(near, self.truth, self.known)
        r_far = masked_dti(far, self.truth, self.known)
        self.assertGreater(r_near["dti"], r_far["dti"])
        self.assertGreater(r_near["hidden_credit_fraction"], r_far["hidden_credit_fraction"])

    def test_known_pixels_are_masked(self) -> None:
        pred = np.zeros_like(self.truth)
        pred[5, 5] = True  # emission on a masked known fault: must not help or hurt
        result = masked_dti(pred, self.truth, self.known)
        self.assertAlmostEqual(result["dti"], 0.0, places=6)
        self.assertAlmostEqual(result["fp_weight"], 0.0, places=6)

    def test_fp_weight_field_matches_inline(self) -> None:
        fpw = fp_weight_field(self.truth, self.known)
        pred = np.zeros_like(self.truth)
        pred[20, 25] = True
        r = masked_dti(pred, self.truth, self.known, fp_weight=fpw)
        self.assertTrue(np.isfinite(r["dti"]))

    def test_blocks_sum_consistent_with_pooled(self) -> None:
        pred = np.zeros_like(self.truth)
        pred[20, 22] = True
        pred[30, 30] = True
        valid = np.ones_like(self.truth)
        result = masked_dti_by_blocks(pred, self.truth, self.known, valid)
        quad_tp = sum(v.get("tp_weight", 0.0) for k, v in result.items() if k.startswith("quadrant_"))
        self.assertAlmostEqual(quad_tp, result["pooled"]["tp_weight"], places=6)
        quad_truth = sum(v.get("truth_pixels", 0.0) for k, v in result.items() if k.startswith("quadrant_"))
        self.assertAlmostEqual(quad_truth, result["pooled"]["truth_pixels"], places=6)


class DistanceMatchedDrawTests(unittest.TestCase):
    def test_draw_matches_target_distance_profile(self) -> None:
        rng = np.random.default_rng(0)
        grid = np.arange(1000, dtype=np.float64)  # monotone distance proxy
        target = np.arange(0, 100)  # near-valued targets
        pool = np.arange(1000)
        mask = distance_matched_draw(pool, target, grid, count=50, rng=rng)
        drawn = np.flatnonzero(mask)
        self.assertEqual(drawn.size, 50)
        # drawn distances should concentrate where target distances are (0-99)
        self.assertLess(float(np.median(grid[drawn])), 300.0)

    def test_empty_inputs_return_empty_mask(self) -> None:
        rng = np.random.default_rng(0)
        out = distance_matched_draw(np.array([], dtype=np.int64), np.arange(5), np.arange(10), 3, rng)
        self.assertEqual(int(out.sum()), 0)


if __name__ == "__main__":
    unittest.main()
