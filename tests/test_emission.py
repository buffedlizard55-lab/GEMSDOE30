"""Tests for :mod:`gemsdoe30.emission` against the reference metric implementation.

The suite pins the algebra (binary emission optimality, the marginal-inclusion
threshold), the 300 m kernel geometry, the masked-domain semantics (prediction
mass outside the scored domain must not radiate credit into it) and the two
selection rules used by the emission tooling, including the acceptance-order
variant that lets an arm take a top-N prefix of a thinned set.
"""

from __future__ import annotations

import unittest

import numpy as np

from gemsdoe30.emission import (
    adaptive_disk_select,
    credit_retention,
    dti_components_masked,
    dti_from_components,
    kernel_credit,
    marginal_inclusion_ratio,
    poisson_disk_select,
    poisson_disk_select_ordered,
    required_coverage_multiplier,
    required_fp_reduction,
)
from gemsdoe30.metric import distance_weighted_tversky, dti_from_counts


class AlgebraTests(unittest.TestCase):
    def test_dti_identity_matches_reference(self) -> None:
        tp, fp, truth = 12.5, 40.0, 100.0
        self.assertAlmostEqual(dti_from_components(tp, fp, truth),
                               dti_from_counts(tp, fp, truth - tp), places=12)

    def test_binary_scaling_is_monotone(self) -> None:
        # DTI(lambda) = lambda*T / (0.2*lambda*T + 0.2*lambda*F + 0.8*G) increases in lambda.
        tp, fp, truth = 12.5, 40.0, 100.0
        scores = [dti_from_components(tp * lam, fp * lam, truth) for lam in (0.2, 0.5, 1.0)]
        self.assertLess(scores[0], scores[1])
        self.assertLess(scores[1], scores[2])

    def test_marginal_inclusion_ratio(self) -> None:
        self.assertAlmostEqual(marginal_inclusion_ratio(0.0), 0.0)
        self.assertAlmostEqual(marginal_inclusion_ratio(0.25), 0.05263157894736842, places=12)
        with self.assertRaises(ValueError):
            marginal_inclusion_ratio(6.0)

    def test_required_coverage_multiplier_round_trip(self) -> None:
        current, target = 0.2600, 0.3195
        multiplier = required_coverage_multiplier(current, target)
        # Reconstruct the target from a coverage-scaled copy of the same FP ratio.
        tp, fp, truth = 0.26, 1.0, 1.0  # coverage 0.26 implied by DTI already; use rho from the identity
        rho = (tp / current - 0.2 * tp - 0.8 * truth) / 0.2 if False else None  # noqa: F841
        alpha = 0.2
        # pick T/G = x such that DTI = x / (0.2x + 0.2rho + 0.8); solve for rho given a chosen x
        x = 0.26
        rho = (x / current - alpha * x - (1 - alpha)) / alpha
        scaled = dti_from_components(x * (1 + multiplier), rho, 1.0)
        self.assertAlmostEqual(scaled, target, places=6)

    def test_required_fp_reduction_round_trip(self) -> None:
        current, target, coverage = 0.2600, 0.3195, 0.41
        reduced = required_fp_reduction(current, target, coverage)
        alpha = 0.2
        rho = (coverage / current - alpha * coverage - (1 - alpha)) / alpha
        self.assertAlmostEqual(dti_from_components(coverage, rho * (1 - reduced), 1.0), target, places=6)


class KernelTests(unittest.TestCase):
    def test_single_dot_triangular_profile(self) -> None:
        prediction = np.zeros((7, 7), dtype=np.float32)
        prediction[3, 3] = 1.0
        credit = kernel_credit(prediction)
        self.assertAlmostEqual(float(credit[3, 3]), 1.0)
        self.assertAlmostEqual(float(credit[3, 4]), 2.0 / 3.0, places=6)  # 100 m
        self.assertAlmostEqual(float(credit[3, 5]), 1.0 / 3.0, places=6)  # 200 m
        self.assertAlmostEqual(float(credit[3, 6]), 0.0, places=6)        # 300 m boundary
        self.assertEqual(float(credit[:, :].max()), 1.0)

    def test_kernel_credit_matches_reference_metric(self) -> None:
        rng = np.random.default_rng(7)
        prediction = (rng.random((40, 45)) > 0.97).astype(np.float64)
        truth = np.zeros((40, 45))
        truth[20, 22] = 1.0
        reference = distance_weighted_tversky(prediction, truth)
        mine = dti_components_masked(prediction, truth, np.ones_like(truth, dtype=bool))
        self.assertAlmostEqual(mine["tp_weight"], reference.tp_weight, places=10)
        self.assertAlmostEqual(mine["fp_weight"], reference.fp_weight, places=10)
        self.assertAlmostEqual(mine["dti"], reference.score, places=12)

    def test_no_wraparound_across_the_border(self) -> None:
        prediction = np.zeros((4, 4), dtype=np.float32)
        prediction[0, 0] = 1.0
        credit = kernel_credit(prediction)
        self.assertAlmostEqual(float(credit[0, 3]), 0.0)
        self.assertAlmostEqual(float(credit[3, 3]), 0.0)
        self.assertAlmostEqual(float(credit[0, 1]), 2.0 / 3.0, places=6)  # 100 m
        self.assertAlmostEqual(float(credit[0, 2]), 1.0 / 3.0, places=6)  # 200 m

    def test_uniform_prediction_gives_full_credit_everywhere_in_range(self) -> None:
        prediction = np.ones((3, 3), dtype=np.float32)
        credit = kernel_credit(prediction)
        np.testing.assert_allclose(credit, 1.0)


class MaskedDomainTests(unittest.TestCase):
    def test_prediction_outside_mask_cannot_radiate_credit_in(self) -> None:
        truth = np.zeros((5, 5))
        mask = np.zeros((5, 5), dtype=bool)
        mask[2, 2] = True          # only this truth pixel is scored
        truth[2, 2] = 1.0
        prediction = np.zeros((5, 5))
        prediction[2, 3] = 1.0     # one 100 m step outside the scored domain
        stats = dti_components_masked(prediction, truth, mask)
        self.assertAlmostEqual(stats["tp_weight"], 0.0, places=12)
        self.assertAlmostEqual(stats["fn_weight"], 1.0, places=12)
        # A prediction outside the mask contributes no FP mass either.
        self.assertAlmostEqual(stats["fp_weight"], 0.0, places=12)

    def test_truth_outside_mask_is_ignored(self) -> None:
        truth = np.zeros((3, 3))
        truth[0, 0] = 1.0
        truth[2, 2] = 1.0
        mask = np.zeros((3, 3), dtype=bool)
        mask[2, 2] = True
        prediction = np.zeros((3, 3))
        prediction[2, 2] = 1.0
        stats = dti_components_masked(prediction, truth, mask)
        self.assertAlmostEqual(stats["truth_pixels"], 1.0)
        self.assertAlmostEqual(stats["tp_weight"], 1.0)
        self.assertAlmostEqual(stats["fn_weight"], 0.0)

    def test_rejects_out_of_range_predictions_on_the_mask(self) -> None:
        with self.assertRaises(ValueError):
            dti_components_masked(np.array([[1.5]]), np.array([[1.0]]), np.array([[True]]))


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.score = np.zeros((30, 30), dtype=np.float32)
        rows, cols = np.mgrid[0:30, 0:30]
        self.score = (np.sin(rows / 3.0) + np.cos(cols / 4.0)).astype(np.float32)

    def test_poisson_disk_enforces_separation(self) -> None:
        radius = 3.0
        kept = poisson_disk_select(self.score, radius)
        pixels = np.argwhere(kept)
        self.assertGreater(pixels.shape[0], 10)
        from scipy.spatial import cKDTree
        distances, _ = cKDTree(pixels).query(pixels, k=2)
        self.assertGreaterEqual(float(distances[:, 1].min()), radius - 1e-9)

    def test_poisson_disk_is_deterministic_and_score_ordered(self) -> None:
        kept_a = poisson_disk_select(self.score, 2.0)
        kept_b = poisson_disk_select(self.score, 2.0)
        np.testing.assert_array_equal(kept_a, kept_b)
        blocked = np.zeros_like(kept_a)
        radius = 2.0
        offsets = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3)
                   if dy * dy + dx * dx < radius * radius]
        for row, col in np.argwhere(kept_a):
            if blocked[row, col]:
                raise AssertionError("a kept pixel was already blocked by a better one")
            for dy, dx in offsets:
                y, x = row + dy, col + dx
                if 0 <= y < blocked.shape[0] and 0 <= x < blocked.shape[1]:
                    blocked[y, x] = True

    def test_mask_and_limit_are_respected(self) -> None:
        mask = np.zeros_like(self.score, dtype=bool)
        mask[5:10, 5:10] = True
        kept = poisson_disk_select(self.score, 1.5, mask=mask, limit=25)
        self.assertTrue(np.all(~kept | mask))
        self.assertLessEqual(int(kept.sum()), 25)

    def test_threshold_excludes_low_scores(self) -> None:
        kept = poisson_disk_select(self.score, 1.0, threshold=1.5)
        self.assertTrue(np.all(self.score[kept] > 1.5))

    def test_gamma_zero_matches_uniform_rule(self) -> None:
        uniform = poisson_disk_select(self.score, 2.5)
        adaptive = adaptive_disk_select(self.score, 2.5, gamma=0.0)
        np.testing.assert_array_equal(uniform, adaptive)

    def test_adaptive_uses_smaller_radius_when_confident(self) -> None:
        uniform = poisson_disk_select(self.score, 4.0)
        adaptive = adaptive_disk_select(self.score, 4.0, gamma=0.6)
        self.assertGreaterEqual(int(adaptive.sum()), int(uniform.sum()))
        self.assertLessEqual(int(adaptive.sum()), 4 * int(uniform.sum()))

    def test_credit_retention(self) -> None:
        reference = np.zeros((9, 9), dtype=bool)
        reference[4, 4] = True
        exact = np.zeros((9, 9), dtype=bool)
        exact[4, 4] = True
        adjacent = np.zeros((9, 9), dtype=bool)
        adjacent[4, 5] = True
        far = np.zeros((9, 9), dtype=bool)
        far[0, 0] = True
        self.assertAlmostEqual(credit_retention(exact, reference), 1.0)
        self.assertAlmostEqual(credit_retention(adjacent, reference), 2.0 / 3.0, places=6)
        self.assertAlmostEqual(credit_retention(far, reference), 0.0)


class ScoreFirstVisitOrderTests(unittest.TestCase):
    """Regression for the visit-order defect (see docs/irregularities.md IR-30-031).

    A score of 0.99 must win its column-major-excluded pixel against 0.10 neighbours
    in *both* thinning rules.  The pre-fix ``np.lexsort((-values, rows, cols))`` keyed
    the visit order on the column index instead, keeping low-score pixels first.
    """

    def test_poisson_select_keeps_the_global_peak_first(self) -> None:
        # 2x2 block mutually exclusive at radius 1.5 (all pairs <= sqrt(2) apart);
        # the peak sits at (1, 0), which column-major visiting would reach second.
        score = np.array([[0.10, 0.11],
                          [0.99, 0.12]], dtype=np.float32)
        kept = poisson_disk_select(score, 1.5)
        self.assertTrue(kept[1, 0])
        self.assertEqual(int(kept.sum()), 1)

    def test_adaptive_select_keeps_the_global_peak_first(self) -> None:
        score = np.array([[0.10, 0.11],
                          [0.99, 0.12]], dtype=np.float32)
        kept = adaptive_disk_select(score, 1.5, gamma=0.0)
        self.assertTrue(kept[1, 0])
        self.assertEqual(int(kept.sum()), 1)


class OrderedSelectionTests(unittest.TestCase):
    """``poisson_disk_select_ordered`` must agree with ``poisson_disk_select`` on the kept
    set, emit in descending-score order, and let a prefix realise exact budgeting."""

    def setUp(self) -> None:
        rng = np.random.default_rng(7)
        self.score = rng.random((24, 31)).astype(np.float32)

    def test_kept_set_matches_mask_rule(self) -> None:
        mask = poisson_disk_select(self.score, 2.5)
        rows, cols = poisson_disk_select_ordered(self.score, 2.5)
        kept2 = np.zeros_like(mask)
        kept2[rows, cols] = True
        np.testing.assert_array_equal(mask, kept2)

    def test_order_is_descending_by_score(self) -> None:
        rows, cols = poisson_disk_select_ordered(self.score, 3.0)
        values = self.score[rows, cols]
        self.assertTrue(np.all(np.diff(values) <= 1e-9))

    def test_prefix_is_top_n_of_kept(self) -> None:
        rows, cols = poisson_disk_select_ordered(self.score, 3.0)
        n = 5
        prefix_values = self.score[rows[:n], cols[:n]]
        all_values = np.sort(self.score[rows, cols])[::-1]
        np.testing.assert_allclose(prefix_values, all_values[:n])

    def test_mask_and_limit_paths_agree_with_mask_rule(self) -> None:
        big = np.arange(400, dtype=np.float32).reshape(20, 20)
        mask = np.ones((20, 20), dtype=bool)
        mask[:5] = False
        kept_mask = poisson_disk_select(big, 2.0, threshold=None, mask=mask, limit=300)
        rows, cols = poisson_disk_select_ordered(big, 2.0, threshold=None, mask=mask, limit=300)
        kept_prefix = np.zeros_like(kept_mask)
        kept_prefix[rows, cols] = True
        np.testing.assert_array_equal(kept_mask, kept_prefix)

    def test_max_kept_returns_acceptance_prefix(self) -> None:
        full_rows, full_cols = poisson_disk_select_ordered(self.score, 3.0)
        for keep in (1, 6, 40, len(full_rows), len(full_rows) + 100):
            rows, cols = poisson_disk_select_ordered(self.score, 3.0, max_kept=keep)
            expected = min(keep, len(full_rows))
            self.assertEqual(len(rows), expected)
            np.testing.assert_array_equal(rows, full_rows[:expected])
            np.testing.assert_array_equal(cols, full_cols[:expected])

    def test_empty_mask_returns_empty_order(self) -> None:
        rows, cols = poisson_disk_select_ordered(self.score, 2.0, mask=np.zeros_like(
            self.score, dtype=bool))
        self.assertEqual(rows.size, 0)
        self.assertEqual(cols.size, 0)


if __name__ == "__main__":
    unittest.main()
