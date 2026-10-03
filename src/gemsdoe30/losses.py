"""GEMS-specific loss that adds the competition's 300 m geometry to a regional loss.

This is *inspired by* Kervadec et al.'s recommendation to combine a boundary
term with a region term. It is not a verbatim implementation of their signed-
distance surface loss. Instead, its geometry term differentiably follows the
published GEMS distance-weighted Tversky equations: a ground-truth pixel receives
the best nearby probability times the official triangular kernel, and false
positive probability is weighted using a Euclidean distance transform to truth.
"""

from __future__ import annotations

import math
from typing import Any

from .metric import DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_RADIUS_M

try:  # Training dependencies are optional for the lightweight metric utilities.
    import numpy as np
    import torch
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - exercised on minimal installations
    np = None  # type: ignore[assignment]
    torch = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]


if torch is None:  # pragma: no cover - behavior tested only when torch is installed

    class GEMSBoundaryAwareLoss:
        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError(
                "GEMSBoundaryAwareLoss requires the optional training dependencies. "
                "Install with `pip install -e '.[train]'`."
            )

else:

    class GEMSBoundaryAwareLoss(torch.nn.Module):
        """Regional soft-Tversky plus a metric-aligned, truncated boundary term.

        Args:
            pixel_size_x_m: Pixel width in projected metres.
            pixel_size_y_m: Pixel height in projected metres.
            radius_m: Support radius of the triangular kernel (300 m for GEMS).
            alpha: False-positive coefficient in the Tversky denominator (0.2).
            beta: False-negative coefficient in the Tversky denominator (0.8).
            regional_weight: Weight for the standard, exact-pixel regional loss.
            boundary_weight: Weight for ``1 - DTI`` using the GEMS distance kernel.
            epsilon: Numerical stabilizer in both soft Tversky ratios.

        ``forward`` accepts logits and binary targets in ``[H,W]``, ``[B,H,W]``
        or ``[B,1,H,W]`` form. ``valid_mask`` marks pixels with real labels/data;
        ``loss_mask`` may select a core area while leaving an input halo available
        to the distance transform. This avoids artificial patch-edge misses when
        training on tiles: provide at least ceil(radius / pixel size) halo pixels.

        The geometry ratio is evaluated only for samples with at least one scored
        positive. Empty-label patches are still handled by the regional term,
        which can penalize false positives; the official DTI is degenerate when its
        truth set is empty and would otherwise provide no useful training signal.
        """

        def __init__(
            self,
            *,
            pixel_size_x_m: float = 100.0,
            pixel_size_y_m: float = 100.0,
            radius_m: float = DEFAULT_RADIUS_M,
            alpha: float = DEFAULT_ALPHA,
            beta: float = DEFAULT_BETA,
            regional_weight: float = 1.0,
            boundary_weight: float = 0.5,
            epsilon: float = 1e-6,
        ) -> None:
            super().__init__()
            if pixel_size_x_m <= 0 or pixel_size_y_m <= 0 or radius_m <= 0:
                raise ValueError("pixel sizes and radius_m must be positive")
            if alpha < 0 or beta < 0:
                raise ValueError("alpha and beta must be non-negative")
            if regional_weight < 0 or boundary_weight < 0:
                raise ValueError("loss weights must be non-negative")
            if regional_weight == 0 and boundary_weight == 0:
                raise ValueError("at least one loss weight must be positive")
            if epsilon <= 0:
                raise ValueError("epsilon must be positive")
            self.pixel_size_x_m = float(pixel_size_x_m)
            self.pixel_size_y_m = float(pixel_size_y_m)
            self.radius_m = float(radius_m)
            self.alpha = float(alpha)
            self.beta = float(beta)
            self.regional_weight = float(regional_weight)
            self.boundary_weight = float(boundary_weight)
            self.epsilon = float(epsilon)
            self._offsets = self._make_offsets()

        def _make_offsets(self) -> list[tuple[int, int, float]]:
            ry = math.ceil(self.radius_m / self.pixel_size_y_m)
            rx = math.ceil(self.radius_m / self.pixel_size_x_m)
            offsets: list[tuple[int, int, float]] = []
            for dy in range(-ry, ry + 1):
                for dx in range(-rx, rx + 1):
                    distance = math.hypot(
                        dy * self.pixel_size_y_m,
                        dx * self.pixel_size_x_m,
                    )
                    if distance <= self.radius_m:
                        weight = max(1.0 - distance / self.radius_m, 0.0)
                        offsets.append((dy, dx, weight))
            return offsets

        @staticmethod
        def _as_4d(value: Any, name: str) -> Any:
            if value.ndim == 2:
                value = value.unsqueeze(0).unsqueeze(0)
            elif value.ndim == 3:
                value = value.unsqueeze(1)
            if value.ndim != 4 or value.shape[1] != 1:
                raise ValueError(f"{name} must have shape [H,W], [B,H,W], or [B,1,H,W]")
            return value

        def _fp_weights(self, labels: Any, label_valid: Any) -> Any:
            """Build the official triangular false-positive weight from an EDT."""
            try:
                from scipy.ndimage import distance_transform_edt
            except ImportError as exc:  # pragma: no cover - optional training dependency
                raise RuntimeError("SciPy is required for the 300 m EDT boundary term") from exc

            distances = []
            for batch_index in range(labels.shape[0]):
                positive = (
                    (labels[batch_index, 0].detach().cpu().numpy() >= 0.5)
                    & label_valid[batch_index, 0].detach().cpu().numpy().astype(bool)
                )
                if positive.any():
                    d = distance_transform_edt(
                        ~positive,
                        sampling=(self.pixel_size_y_m, self.pixel_size_x_m),
                    )
                else:
                    d = np.full(positive.shape, np.inf, dtype=np.float32)
                distances.append(np.minimum(d / self.radius_m, 1.0).astype(np.float32))
            stacked = np.stack(distances, axis=0)[:, None, :, :]
            return torch.as_tensor(stacked, device=labels.device, dtype=labels.dtype)

        def _nearby_credit(self, probabilities: Any, label_valid: Any) -> Any:
            """For every truth cell, take max_x p(x) k(distance(x, truth))."""
            height, width = probabilities.shape[-2:]
            rx = math.ceil(self.radius_m / self.pixel_size_x_m)
            ry = math.ceil(self.radius_m / self.pixel_size_y_m)
            source = probabilities * label_valid.to(probabilities.dtype)
            padded = F.pad(source, (rx, rx, ry, ry), mode="constant", value=0.0)
            credit = torch.zeros_like(probabilities)
            for dy, dx, kernel_weight in self._offsets:
                shifted = padded[
                    :,
                    :,
                    ry + dy : ry + dy + height,
                    rx + dx : rx + dx + width,
                ]
                credit = torch.maximum(credit, shifted * kernel_weight)
            return credit

        def forward(
            self,
            logits: Any,
            targets: Any,
            valid_mask: Any | None = None,
            loss_mask: Any | None = None,
            *,
            return_components: bool = False,
        ) -> Any:
            logits = self._as_4d(logits, "logits")
            targets = self._as_4d(targets, "targets").to(device=logits.device, dtype=logits.dtype)
            if logits.shape != targets.shape:
                raise ValueError("logits and targets must have the same shape")

            finite_targets = torch.isfinite(targets)
            if valid_mask is None:
                label_valid = finite_targets
            else:
                label_valid = self._as_4d(valid_mask, "valid_mask").to(device=logits.device).bool()
                if label_valid.shape != logits.shape:
                    raise ValueError("valid_mask shape differs from logits")
                label_valid = label_valid & finite_targets
            labels = torch.nan_to_num(targets, nan=0.0, posinf=0.0, neginf=0.0)
            if torch.any(label_valid & ((labels < 0.0) | (labels > 1.0))):
                raise ValueError("targets must lie in [0, 1] on valid pixels")
            if torch.any(label_valid & (torch.abs(labels - labels.round()) > 1e-6)):
                raise ValueError("GEMS ground-truth targets must be binary")
            labels = labels * label_valid.to(labels.dtype)

            if loss_mask is None:
                scored = label_valid
            else:
                scored = self._as_4d(loss_mask, "loss_mask").to(device=logits.device).bool()
                if scored.shape != logits.shape:
                    raise ValueError("loss_mask shape differs from logits")
                scored = scored & label_valid

            probabilities = torch.sigmoid(logits)
            mask = scored.to(probabilities.dtype)
            y = labels * mask
            p = probabilities * mask
            dims = (1, 2, 3)
            tp_reg = torch.sum(p * y, dim=dims)
            fp_reg = torch.sum(p * (1.0 - y), dim=dims)
            fn_reg = torch.sum((1.0 - p) * y, dim=dims)
            regional_score = (tp_reg + self.epsilon) / (
                tp_reg + self.alpha * fp_reg + self.beta * fn_reg + self.epsilon
            )
            regional_loss = (1.0 - regional_score).mean()

            if self.boundary_weight == 0.0:
                # A true regional-only control: no EDT or neighborhood-max work.
                boundary_loss = probabilities.sum() * 0.0
            else:
                # The distance transform uses every known label in the input patch,
                # including its halo. Only the loss mask contributes to TP/FN/FP sums.
                distance_fp_weight = self._fp_weights(labels, label_valid)
                credit = self._nearby_credit(probabilities, label_valid)
                positive_scored = (labels >= 0.5) & scored
                positive_count = positive_scored.sum(dim=dims)
                tp_geom = torch.sum(credit * positive_scored.to(credit.dtype), dim=dims)
                fn_geom = torch.sum((1.0 - credit) * positive_scored.to(credit.dtype), dim=dims)
                fp_geom = torch.sum(
                    probabilities * distance_fp_weight * mask,
                    dim=dims,
                )
                geometry_score = tp_geom / (
                    tp_geom + self.alpha * fp_geom + self.beta * fn_geom + self.epsilon
                )
                has_truth = positive_count > 0
                if torch.any(has_truth):
                    boundary_loss = (1.0 - geometry_score[has_truth]).mean()
                else:
                    # Preserve a valid zero gradient path for a batch of negative-only patches.
                    boundary_loss = probabilities.sum() * 0.0

            total = self.regional_weight * regional_loss + self.boundary_weight * boundary_loss
            if return_components:
                return {
                    "total": total,
                    "regional": regional_loss,
                    "boundary": boundary_loss,
                }
            return total
