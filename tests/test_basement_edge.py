"""Tests for the H-32-05 basement-edge harness helpers (determinism + edge physics)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HAS_NUMPY = bool(importlib.util.find_spec("numpy") and importlib.util.find_spec("scipy"))
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "basement_edge_holdout.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("basement_edge_holdout", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAS_NUMPY, "optional numpy/scipy dependencies are not installed")
class BasementEdgeHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_harness()

    def test_descending_rank_is_zero_based_and_deterministic(self):
        import numpy as np

        field = np.array([[5.0, 1.0, 3.0], [4.0, 4.0, 0.0]])
        support = np.ones_like(field, dtype=bool)
        support[1, 2] = False

        rank = self.mod.descending_rank(field, support)
        # Largest value gets rank 0; the unsupported cell stays +inf.
        self.assertEqual(rank[0, 0], 0.0)
        self.assertTrue(np.isinf(rank[1, 2]))
        finite = rank[np.isfinite(rank)]
        self.assertEqual(sorted(finite.tolist()), list(range(int(support.sum()))))
        # Exact ties break deterministically by ascending flat index.
        self.assertLess(rank[1, 0], rank[1, 1])
        self.assertTrue(np.array_equal(rank, self.mod.descending_rank(field, support)))

    def test_top_n_emission_takes_lowest_scores_inside_support_only(self):
        import numpy as np

        score = np.arange(20, dtype=np.float64).reshape(4, 5)
        support = np.ones_like(score, dtype=bool)
        support[0, :] = False  # the lowest five scores are excluded by support

        emission = self.mod.top_n_emission(score, support, 3)
        self.assertEqual(int(emission.sum()), 3)
        self.assertFalse(emission[0].any())
        picked = sorted(score[emission].tolist())
        self.assertEqual(picked, [5.0, 6.0, 7.0])
        self.assertTrue(np.array_equal(emission, self.mod.top_n_emission(score, support, 3)))

    def test_top_n_emission_clamps_to_support_size(self):
        import numpy as np

        score = np.zeros((3, 3), dtype=np.float64)
        support = np.zeros_like(score, dtype=bool)
        support[1, 1] = True
        # Asking for more than the support holds yields exactly the support.
        self.assertEqual(int(self.mod.top_n_emission(score, support, 100).sum()), 1)
        # An empty support yields an empty emission (no crash, no fallback to all pixels).
        empty = np.zeros_like(support)
        self.assertEqual(int(self.mod.top_n_emission(score, empty, 5).sum()), 0)

    def test_constant_basement_surface_has_no_edge_and_coherence_is_bounded(self):
        import numpy as np

        features = np.zeros((2, 21, 21), dtype=np.float32)
        features[0] = 500.0  # depth_to_base_surf: perfectly flat
        features[1] = 0.25   # iso_grav_anom_hg: constant
        footprint = np.ones((21, 21), dtype=bool)

        edge, coherence, grav, finite = self.mod.edge_fields(features, 0, 1, footprint)
        self.assertTrue(finite.all())
        self.assertLess(float(np.abs(edge).max()), 1e-6)
        self.assertGreaterEqual(float(coherence.min()), 0.0)
        self.assertLessEqual(float(coherence.max()), 1.0)
        self.assertTrue(np.allclose(grav, 0.25))

    def test_step_in_basement_surface_localises_the_edge_and_is_oriented(self):
        import numpy as np

        features = np.zeros((2, 21, 21), dtype=np.float32)
        depth = np.full((21, 21), 200.0, dtype=np.float32)
        depth[:, 12:] = 1200.0  # a 1 km basement step: a buried range-front pinch-out
        features[0] = depth
        footprint = np.ones((21, 21), dtype=bool)

        edge, coherence, _, finite = self.mod.edge_fields(features, 0, 1, footprint)
        peak_col = int(np.argmax(edge.mean(axis=0)))
        self.assertIn(peak_col, (11, 12))
        self.assertGreater(float(edge.mean(axis=0)[peak_col]), 100.0)
        # A straight step is maximally oriented, so coherence must be high along it.
        self.assertGreater(float(coherence[:, 11:13].max()), 0.9)

    def test_nonfinite_band_cells_are_excluded_from_the_finite_mask(self):
        import numpy as np

        features = np.zeros((2, 9, 9), dtype=np.float32)
        features[0] = 300.0
        features[0][4, 4] = np.nan
        footprint = np.ones((9, 9), dtype=bool)

        _, _, _, finite = self.mod.edge_fields(features, 0, 1, footprint)
        self.assertFalse(finite[4, 4])
        self.assertEqual(int(finite.sum()), 80)

    def test_gate_budget_is_enforced(self):
        """The registered gate is defined at N=15000; the harness must refuse other budgets."""

        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--budgets", "5000"],
            capture_output=True, text=True,
            cwd=str(SCRIPT.parents[1]), timeout=120,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("15000", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
