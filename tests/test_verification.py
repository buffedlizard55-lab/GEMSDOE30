"""Unit tests for the standing three-check verification protocol (src/gemsdoe30/verification.py)."""

from __future__ import annotations

import unittest

import numpy as np

from gemsdoe30.verification import (
    apply_bin_calibrator,
    evaluate_oof_calibration_across_folds,
    evaluate_perturbation_stability,
    evaluate_probability_calibration,
    extract_qualitative_atlas,
    fit_bin_calibrator,
)


class CalibrationCheckTests(unittest.TestCase):
    def test_fit_and_apply_bin_calibrator_is_monotone_and_improves_slope(self) -> None:
        rng = np.random.default_rng(42)
        n = 20000
        raw_score = rng.uniform(0.0, 1.0, size=(100, 200))
        true_prob = 0.01 + 0.08 * (raw_score ** 2)
        truth = (rng.uniform(0.0, 1.0, size=raw_score.shape) < true_prob).astype(np.float64)

        train_mask = np.zeros(raw_score.shape, dtype=bool)
        train_mask[:50, :] = True
        val_mask = ~train_mask

        uncal = evaluate_probability_calibration(
            raw_score, truth, train_mask, val_mask, n_bins=10, min_bin_pixels=100
        )
        self.assertFalse(uncal["slope_in_0_8_to_1_2"])

        cal = fit_bin_calibrator(raw_score, truth, train_mask, n_bins=15)
        # Values must be monotonically non-decreasing and inside [0, 1]
        vals = np.asarray(cal["values"])
        self.assertTrue(np.all(np.diff(vals) >= -1e-12))
        self.assertTrue(np.all((vals >= 0.0) & (vals <= 1.0)))

        calibrated = apply_bin_calibrator(cal, raw_score)
        self.assertTrue(np.all((calibrated >= 0.0) & (calibrated <= 1.0)))
        cal_eval = evaluate_probability_calibration(
            calibrated, truth, train_mask, val_mask, n_bins=10, min_bin_pixels=100
        )
        self.assertTrue(cal_eval["slope_in_0_8_to_1_2"])
        self.assertTrue(cal_eval["top_bin_stability_ge_0_70"])
        self.assertTrue(cal_eval["check2_pass"])

    def test_oof_calibration_across_folds_runs_cleanly(self) -> None:
        rng = np.random.default_rng(7)
        raw_score = rng.uniform(0.0, 1.0, size=(120, 120))
        true_prob = 0.02 + 0.15 * raw_score
        truth = (rng.uniform(0.0, 1.0, size=raw_score.shape) < true_prob).astype(np.float64)
        domain = np.ones(raw_score.shape, dtype=bool)

        res = evaluate_oof_calibration_across_folds(
            raw_score, truth, domain, buffer_m=200.0, n_bins=8, min_bin_pixels=50
        )
        self.assertTrue(res["slope_in_0_8_to_1_2"])
        self.assertTrue(res["top_bin_stability_pass"])
        self.assertTrue(res["check2_pass"])
        self.assertEqual(len(res["per_fold"]), 4)

    def test_empty_train_mask_raises(self) -> None:
        s = np.zeros((4, 4))
        m = np.zeros((4, 4), dtype=bool)
        with self.assertRaises(ValueError):
            fit_bin_calibrator(s, s, m)


class PerturbationStabilityTests(unittest.TestCase):
    def test_perturbation_stability_detects_real_and_spurious_features(self) -> None:
        rng = np.random.default_rng(11)
        signal = rng.uniform(0.0, 1.0, size=(40, 40))
        noise = rng.uniform(0.0, 1.0, size=(40, 40))
        target = signal > 0.8
        mask = np.ones((40, 40), dtype=bool)

        def score_fn(fdict: dict[str, np.ndarray]) -> float:
            pred = fdict["signal"] > 0.8
            return float((pred & target).sum() / max(target.sum(), 1))

        fdict = {"signal": signal, "noise": noise}
        cand_dti = score_fn(fdict)
        base_dti = 0.20

        res_pass = evaluate_perturbation_stability(
            score_fn,
            fdict,
            mask,
            baseline_dti=base_dti,
            candidate_dti=cand_dti,
            own_family=["signal"],
            unrelated_family=["noise"],
            per_fold_deltas=[0.1, 0.2, 0.15, 0.05],
            seed=5,
        )
        self.assertTrue(res_pass["own_family_removes_ge_50pct"])
        self.assertTrue(res_pass["unrelated_family_retains_positive_gain"])
        self.assertTrue(res_pass["fold_sign_consistency_ge_3_of_4"])
        self.assertTrue(res_pass["check3_pass"])

        # If a candidate claims "noise" is its own family, permuting "noise" removes 0% -> fails
        res_fail = evaluate_perturbation_stability(
            score_fn,
            fdict,
            mask,
            baseline_dti=base_dti,
            candidate_dti=cand_dti,
            own_family=["noise"],
            unrelated_family=["signal"],
            per_fold_deltas=[0.1, 0.2, 0.15, 0.05],
            seed=5,
        )
        self.assertFalse(res_fail["own_family_removes_ge_50pct"])
        self.assertFalse(res_fail["check3_pass"])


class QualitativeAtlasTests(unittest.TestCase):
    def test_extract_qualitative_atlas_returns_ordered_blocks(self) -> None:
        cand = np.zeros((128, 128), dtype=np.float64)
        ctrl = np.zeros((128, 128), dtype=np.float64)
        truth = np.zeros((128, 128), dtype=bool)
        valid = np.ones((128, 128), dtype=bool)

        # Block (0, 0): candidate helps
        truth[10:25, 10:12] = True
        cand[10:25, 10:12] = 0.9
        ctrl[10:25, 10:12] = 0.1

        # Block (1, 1): candidate fails
        truth[80:95, 80:82] = True
        cand[80:95, 80:82] = 0.0
        ctrl[80:95, 80:82] = 0.8

        transform_gdal = [243350.0, 100.0, 0.0, 4508550.0, 0.0, -100.0]
        atlas = extract_qualitative_atlas(
            cand, ctrl, truth, valid, transform_gdal, block_size_px=64, top_k=1
        )
        self.assertEqual(len(atlas["where_it_helps"]), 1)
        self.assertEqual(len(atlas["where_it_fails"]), 1)
        self.assertGreater(atlas["where_it_helps"][0]["delta_tp_weight"], 0.0)
        self.assertLess(atlas["where_it_fails"][0]["delta_tp_weight"], 0.0)
        self.assertEqual(atlas["where_it_helps"][0]["row_bounds"], [0, 64])
        self.assertEqual(atlas["where_it_fails"][0]["row_bounds"], [64, 128])


if __name__ == "__main__":
    unittest.main()
