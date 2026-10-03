"""Tests for the H-33-01 placement-policy harness helpers (quota algebra + band geometry).

The harness itself (``scripts/placement_policy_holdout.py``) is deterministic given its
inputs; these unit tests pin the three pieces the preregistered gates depend on: the exact
per-band quota split, the frozen shortfall order, and the band masks' distance geometry.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HAS_NUMPY = bool(importlib.util.find_spec("numpy") and importlib.util.find_spec("scipy"))
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "placement_policy_holdout.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("placement_policy_holdout", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAS_NUMPY, "optional numpy/scipy dependencies are not installed")
class PlacementHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np = np
        cls.mod = load_harness()

    def test_quota_split_is_exact(self) -> None:
        np = self.np
        mod = self.mod
        for budget, frac in [(80_000, 0.25), (80_000, 0.5), (79_999, 0.75), (41, 0.25)]:
            quotas = mod.quotas_for(frac, budget)
            self.assertEqual(sum(quotas.values()), budget, (budget, frac, quotas))
            self.assertEqual(quotas["near"], int(round(frac * budget)))

    def test_fill_quotas_shortfall_order(self) -> None:
        np = self.np
        mod = self.mod
        pools = {
            "near": (np.arange(4), np.zeros(4, dtype="int64")),
            "mid": (np.arange(50), np.ones(50, dtype="int64")),
            "far": (np.arange(60), np.full(60, 2, dtype="int64")),
        }
        quotas = {"near": 20, "mid": 10, "far": 10}  # near is short by 16
        rows, cols, taken, overflow = mod.fill_quotas(pools, quotas, 40)
        self.assertEqual(rows.size, 40)
        self.assertEqual(taken["near"], 4)
        # frozen order: shortfall goes mid first, then far
        self.assertEqual(overflow["mid"], 16)
        self.assertEqual(overflow["far"], 0)
        self.assertNotIn("unfilled", overflow)

    def test_fill_quotas_records_unfillable_shortfall(self) -> None:
        np = self.np
        mod = self.mod
        pools = {
            "near": (np.arange(2), np.zeros(2, dtype="int64")),
            "mid": (np.arange(2), np.ones(2, dtype="int64")),
            "far": (np.arange(2), np.full(2, 2, dtype="int64")),
        }
        rows, _cols, _taken, overflow = mod.fill_quotas(pools, {"near": 5, "mid": 5, "far": 5}, 15)
        self.assertEqual(rows.size, 6)
        self.assertEqual(overflow["unfilled"], 9)

    def test_band_masks_geometry(self) -> None:
        np = self.np
        mod = self.mod
        catalogue = np.zeros((25, 25), dtype=bool)
        catalogue[12, 12] = True
        domain = np.ones_like(catalogue)
        domain[0] = False
        bands, distance = mod.build_band_masks(catalogue, domain)
        self.assertEqual(float(distance[12, 12]), 0.0)
        # near = (3, 6], mid = (6, 12], far = >12 by Euclidean pixels
        self.assertTrue(bands["near"][12, 16])
        self.assertFalse(bands["near"][12, 15])   # d = 3 is inside the mask, not near
        self.assertTrue(bands["mid"][12, 19])     # d = 7
        self.assertTrue(bands["far"][1, 1])       # d = sqrt(121+121) ~ 15.6
        self.assertFalse(bands["mid"][0, 12])     # masked-out rows are excluded from every band
        covered = np.zeros_like(domain)
        for band in bands.values():
            self.assertEqual(int((covered & band).sum()), 0)  # disjoint
            covered |= band
        self.assertEqual(int(covered.sum()), int((domain & (distance > 3)).sum()))

    def test_score_emitter_exact_stats(self) -> None:
        """A single dot 3 px from a single truth pixel: credit 1 - 300/300*3px... at 100 m/px,
        d = 300 m gives zero credit; d = 200 m gives 1/3. FP weight of an uncovered dot is
        min(d/R, 1)."""
        np = self.np
        mod = self.mod
        shape = (15, 15)
        domain = np.ones(shape, dtype=bool)
        truth = np.zeros(shape, dtype=bool)
        truth[7, 7] = True
        fp_weight = np.minimum(__import__("scipy.ndimage", fromlist=["x"]).distance_transform_edt(
            ~truth, sampling=(100.0, 100.0)) / 300.0, 1.0)
        rec = mod.score_emitter(np.array([7]), np.array([9]), shape, domain, truth, fp_weight, 1.0)
        self.assertAlmostEqual(rec["tp_weight"], 1.0 / 3.0, places=6)   # k(200 m) = 1/3
        self.assertAlmostEqual(rec["fp_weight"], 2.0 / 3.0, places=6)   # 1 - k(200 m)
        self.assertAlmostEqual(rec["dti"],
                               (1 / 3) / (0.2 * (1 / 3) + 0.2 * (2 / 3) + 0.8 * 1.0), places=6)
        self.assertEqual(rec["dots"], 1)


if __name__ == "__main__":
    unittest.main()
