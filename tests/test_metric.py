from __future__ import annotations

import unittest

from gemsdoe30.metric import (
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    DTIComponents,
    distance_weighted_tversky,
    dti_from_counts,
    score_dti,
    triangular_kernel,
)


class MetricTests(unittest.TestCase):
    def test_official_worked_example_arithmetic(self) -> None:
        score = dti_from_counts(3.0, 1.89, 2.0, alpha=0.2, beta=0.8)
        self.assertAlmostEqual(score, 0.60, places=2)

    def test_kernel_has_three_hundred_metre_support(self) -> None:
        self.assertEqual(triangular_kernel(0), 1.0)
        self.assertAlmostEqual(triangular_kernel(100), 2.0 / 3.0)
        self.assertAlmostEqual(triangular_kernel(200), 1.0 / 3.0)
        self.assertEqual(triangular_kernel(300), 0.0)
        self.assertEqual(triangular_kernel(400), 0.0)

    def test_exact_match_and_probability_scaling(self) -> None:
        truth = [[0, 0, 0], [0, 1, 0], [0, 0, 0]]
        pred = [[0, 0, 0], [0, 1, 0], [0, 0, 0]]
        result = distance_weighted_tversky(pred, truth)
        self.assertIsInstance(result, DTIComponents)
        self.assertAlmostEqual(result.tp_weight, 1.0)
        self.assertAlmostEqual(result.fp_weight, 0.0)
        self.assertAlmostEqual(result.fn_weight, 0.0)
        self.assertGreater(result.score, 0.999999)

        half = [[0, 0, 0], [0, 0.5, 0], [0, 0, 0]]
        self.assertAlmostEqual(score_dti(half, truth), 5.0 / 9.0, places=6)

    def test_one_and_two_pixel_near_misses_get_fractional_credit(self) -> None:
        size, center = 11, 5
        truth = [[0.0] * size for _ in range(size)]
        truth[center][center] = 1.0
        scores = []
        for offset in (0, 1, 2, 3, 4):
            pred = [[0.0] * size for _ in range(size)]
            pred[center][center + offset] = 1.0
            result = distance_weighted_tversky(pred, truth)
            scores.append(result)

        self.assertAlmostEqual(scores[0].tp_weight, 1.0)
        self.assertAlmostEqual(scores[1].tp_weight, 2.0 / 3.0)
        self.assertAlmostEqual(scores[2].tp_weight, 1.0 / 3.0)
        self.assertAlmostEqual(scores[3].tp_weight, 0.0)
        self.assertAlmostEqual(scores[4].tp_weight, 0.0)
        self.assertGreater(scores[1].score, scores[2].score)
        self.assertGreater(scores[2].score, scores[3].score)

    def test_regional_overlap_ties_nonoverlapping_shifts_but_metric_resolves_them(self) -> None:
        from scripts.loss_geometry_probe import run_probe

        result = run_probe()
        rows = result["rows"]
        nonoverlap_regional = [row["regional_loss"] for row in rows[1:]]
        self.assertLess(max(nonoverlap_regional) - min(nonoverlap_regional), 1e-6)
        self.assertLess(rows[1]["metric_geometry_loss"], rows[2]["metric_geometry_loss"])
        self.assertLess(rows[2]["metric_geometry_loss"], rows[3]["metric_geometry_loss"])
        self.assertIn("not_holdout", result["status"])

    def test_nodata_outside_footprint_is_ignored(self) -> None:
        truth = [[0, 1, float("nan")]]
        pred = [[0, 0.5, float("nan")]]
        valid = [[True, True, False]]
        result = distance_weighted_tversky(pred, truth, valid)
        self.assertAlmostEqual(result.tp_weight, 0.5)
        self.assertAlmostEqual(result.fn_weight, 0.5)

    def test_invalid_prediction_or_truth_inside_footprint_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            distance_weighted_tversky([[float("nan")]], [[1]])
        with self.assertRaises(ValueError):
            distance_weighted_tversky([[1.01]], [[1]])
        with self.assertRaises(ValueError):
            distance_weighted_tversky([[0.5]], [[float("nan")]], [[True]])

    def test_no_truth_has_zero_dti_and_probability_is_false_positive_mass(self) -> None:
        result = distance_weighted_tversky([[0.0, 0.5]], [[0, 0]])
        self.assertAlmostEqual(result.tp_weight, 0.0)
        self.assertAlmostEqual(result.fp_weight, 0.5)
        self.assertAlmostEqual(result.fn_weight, 0.0)
        self.assertEqual(result.score, 0.0)

    def test_parameters_and_binary_truth_are_checked(self) -> None:
        with self.assertRaises(ValueError):
            triangular_kernel(1.0, 0.0)
        with self.assertRaises(ValueError):
            distance_weighted_tversky([[0]], [[0.25]])
        self.assertEqual(DEFAULT_ALPHA, 0.2)
        self.assertEqual(DEFAULT_BETA, 0.8)


if __name__ == "__main__":
    unittest.main()
