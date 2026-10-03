from __future__ import annotations

import importlib.util
import unittest

TORCH_AND_SCIPY = bool(importlib.util.find_spec("torch") and importlib.util.find_spec("scipy"))


@unittest.skipUnless(TORCH_AND_SCIPY, "optional torch/scipy training dependencies are not installed")
class BoundaryLossTests(unittest.TestCase):
    def test_boundary_term_ranks_near_misses_by_kernel_distance(self) -> None:
        import torch

        from gemsdoe30.losses import GEMSBoundaryAwareLoss

        target = torch.zeros((1, 1, 15, 15), dtype=torch.float32)
        target[0, 0, 7, 7] = 1.0
        valid = torch.ones_like(target, dtype=torch.bool)
        criterion = GEMSBoundaryAwareLoss(boundary_weight=1.0)
        results = []
        for offset in (0, 1, 2, 4):
            logits = torch.full_like(target, -20.0)
            logits[0, 0, 7, 7 + offset] = 20.0
            parts = criterion(logits, target, valid, return_components=True)
            results.append(parts)
        self.assertLess(float(results[0]["boundary"]), float(results[1]["boundary"]))
        self.assertLess(float(results[1]["boundary"]), float(results[2]["boundary"]))
        self.assertLess(float(results[2]["boundary"]), float(results[3]["boundary"]))
        self.assertAlmostEqual(float(results[1]["regional"]), float(results[2]["regional"]), places=5)

    def test_geometry_term_matches_reference_metric_on_full_scored_grid(self) -> None:
        import torch

        from gemsdoe30.losses import GEMSBoundaryAwareLoss
        from gemsdoe30.metric import distance_weighted_tversky

        logits = torch.linspace(-2.5, 2.5, 15 * 17, dtype=torch.float64).reshape(1, 1, 15, 17)
        target = torch.zeros_like(logits)
        target[0, 0, 4, 5] = 1.0
        target[0, 0, 10, 11] = 1.0
        valid = torch.ones_like(target, dtype=torch.bool)
        valid[0, 0, 0, :] = False
        valid[0, 0, :, 0] = False
        probabilities = torch.sigmoid(logits)

        criterion = GEMSBoundaryAwareLoss(boundary_weight=1.0, epsilon=1e-7)
        parts = criterion(logits, target, valid, return_components=True)
        reference = distance_weighted_tversky(
            probabilities[0, 0].numpy(),
            target[0, 0].numpy(),
            valid[0, 0].numpy(),
        )
        self.assertAlmostEqual(float(parts["boundary"]), 1.0 - reference.score, places=10)

    def test_nonfinite_loss_parameters_are_rejected(self) -> None:
        import math

        from gemsdoe30.losses import GEMSBoundaryAwareLoss

        for kwargs in (
            {"radius_m": math.nan},
            {"pixel_size_x_m": math.inf},
            {"boundary_weight": math.nan},
            {"epsilon": math.inf},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GEMSBoundaryAwareLoss(**kwargs)

    def test_combined_loss_has_finite_gradient(self) -> None:
        import torch

        from gemsdoe30.losses import GEMSBoundaryAwareLoss

        logits = torch.zeros((1, 1, 9, 9), dtype=torch.float32, requires_grad=True)
        target = torch.zeros_like(logits)
        target[0, 0, 4, 4] = 1.0
        loss = GEMSBoundaryAwareLoss()(logits, target)
        loss.backward()
        self.assertTrue(torch.isfinite(loss))
        self.assertTrue(torch.all(torch.isfinite(logits.grad)))
        self.assertGreater(float(logits.grad.abs().sum()), 0.0)

    def test_negative_only_batch_uses_region_term_without_nan(self) -> None:
        import torch

        from gemsdoe30.losses import GEMSBoundaryAwareLoss

        logits = torch.zeros((1, 1, 7, 7), dtype=torch.float32, requires_grad=True)
        target = torch.zeros_like(logits)
        parts = GEMSBoundaryAwareLoss()(logits, target, return_components=True)
        self.assertTrue(torch.isfinite(parts["total"]))
        self.assertEqual(float(parts["boundary"].detach()), 0.0)
        parts["total"].backward()
        self.assertTrue(torch.all(torch.isfinite(logits.grad)))


if __name__ == "__main__":
    unittest.main()
