"""Patch sampler and one-arm trainer for a fair regional-vs-boundary ablation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .normalization import fit_robust_feature_stats, normalize_feature_block


def _training_dependencies() -> tuple[Any, Any, Any]:
    try:
        import numpy as np
        import torch
        from torch.utils.data import Dataset
    except ImportError as exc:  # pragma: no cover - optional training dependency
        raise RuntimeError("Install the training extra: `pip install -e '.[train]'`") from exc
    return np, torch, Dataset


_np, _torch, _Dataset = _training_dependencies()


class RandomPatchDataset(_Dataset):
    """Deterministic index-addressed sampler with positive-centred patches.

    Half of the patches are centred on an available positive label and half are
    drawn uniformly from the trainable footprint. Every patch carries a metric
    radius halo; its outer halo is supplied to the loss for distance calculations,
    while only the core contributes to loss sums.
    """

    def __init__(
        self,
        features: Any,
        labels: Any,
        label_valid: Any,
        train_mask: Any,
        *,
        patch_size: int = 256,
        radius_pixels: int = 3,
        samples: int = 2000,
        seed: int = 17,
        feature_stats: list[dict[str, Any]] | None = None,
    ) -> None:
        self.features = features
        self.feature_stats = feature_stats
        self.labels = labels
        self.label_valid = _np.asarray(label_valid, dtype=bool)
        self.train_mask = _np.asarray(train_mask, dtype=bool)
        if self.features.ndim != 3 or self.labels.ndim != 2:
            raise ValueError("features must be [C,H,W] and labels [H,W]")
        if self.features.shape[1:] != self.labels.shape:
            raise ValueError("features and labels have different spatial shapes")
        if self.feature_stats is not None and len(self.feature_stats) != self.features.shape[0]:
            raise ValueError("feature_stats must contain one entry per feature channel")
        if self.label_valid.shape != self.labels.shape or self.train_mask.shape != self.labels.shape:
            raise ValueError("label_valid and train_mask must match labels")
        if patch_size < 2 * radius_pixels + 8:
            raise ValueError("patch_size is too small for the requested metric halo")
        if patch_size > min(self.labels.shape):
            raise ValueError("patch_size cannot exceed either raster dimension")
        if samples < 1 or radius_pixels < 0:
            raise ValueError("samples must be positive and radius_pixels non-negative")
        self.patch_size = int(patch_size)
        self.radius_pixels = int(radius_pixels)
        self.samples = int(samples)
        self.seed = int(seed)
        self._domain = self.label_valid & self.train_mask
        self._positive_coords = _np.argwhere((self.labels > 0.5) & self._domain)
        if not _np.any(self._domain):
            raise ValueError("the selected training fold contains no valid labelled pixels")
        if not len(self._positive_coords):
            raise ValueError("the selected training fold contains no positive labels")
        self._epoch = 0

    def __len__(self) -> int:
        return self.samples

    def set_epoch(self, epoch: int) -> None:
        self._epoch = int(epoch)

    def _random_valid_center(self, rng: Any) -> tuple[int, int]:
        height, width = self.labels.shape
        for _ in range(10_000):
            y, x = int(rng.integers(0, height)), int(rng.integers(0, width))
            if self._domain[y, x]:
                return y, x
        # A deterministic fallback for very fragmented masks.
        ys, xs = _np.nonzero(self._domain)
        index = int(rng.integers(0, len(ys)))
        return int(ys[index]), int(xs[index])

    def __getitem__(self, index: int) -> tuple[Any, Any, Any, Any]:
        rng = _np.random.default_rng(self.seed + self._epoch * self.samples + int(index))
        if rng.random() < 0.5:
            y_center, x_center = self._positive_coords[int(rng.integers(0, len(self._positive_coords)))]
            y_center, x_center = int(y_center), int(x_center)
        else:
            y_center, x_center = self._random_valid_center(rng)

        patch = self.patch_size
        height, width = self.labels.shape
        y0 = min(max(y_center - patch // 2, 0), height - patch)
        x0 = min(max(x_center - patch // 2, 0), width - patch)
        ys, xs = slice(y0, y0 + patch), slice(x0, x0 + patch)

        x = _np.asarray(self.features[:, ys, xs], dtype=_np.float32).copy()
        if self.feature_stats is None:
            _np.nan_to_num(x, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        else:
            x = normalize_feature_block(x, self.feature_stats)
        label_valid = self._domain[ys, xs].copy()
        target = _np.where(label_valid, self.labels[ys, xs], 0.0).astype(_np.float32, copy=False)

        # Ignore the patch edge in the loss, but leave those labels visible to the
        # distance transform as a halo around the central scoring core.
        core = _np.zeros((patch, patch), dtype=bool)
        margin = self.radius_pixels
        if margin == 0:
            core[:] = True
        else:
            core[margin:-margin, margin:-margin] = True
        loss_mask = label_valid & core

        return (
            _torch.from_numpy(x),
            _torch.from_numpy(target[None, ...]),
            _torch.from_numpy(label_valid[None, ...]),
            _torch.from_numpy(loss_mask[None, ...]),
        )


def train_one_arm(
    features: Any,
    labels: Any,
    label_valid: Any,
    train_mask: Any,
    *,
    loss_mode: str,
    output_path: str | Path,
    dataset_signature: str,
    fold: int | None = None,
    seed: int = 17,
    epochs: int = 5,
    steps_per_epoch: int = 100,
    batch_size: int = 4,
    patch_size: int = 256,
    learning_rate: float = 1e-3,
    boundary_weight: float = 0.5,
    device: str | None = None,
) -> dict[str, Any]:
    """Fit one controlled model arm and save a checkpoint plus run metadata."""

    np, torch, _ = _training_dependencies()
    from torch.utils.data import DataLoader

    from .losses import GEMSBoundaryAwareLoss
    from .model import SmallUNet

    if loss_mode not in {"regional", "combined"}:
        raise ValueError("loss_mode must be 'regional' or 'combined'")
    if fold not in (None, 0, 1, 2, 3):
        raise ValueError("fold must be 0, 1, 2, 3, or None for a full-label fit")
    if not isinstance(dataset_signature, str) or len(dataset_signature) != 64:
        raise ValueError("dataset_signature must be a full SHA-256 string")
    try:
        int(dataset_signature, 16)
    except ValueError as exc:
        raise ValueError("dataset_signature must be hexadecimal SHA-256") from exc
    if epochs < 1 or steps_per_epoch < 1 or batch_size < 1:
        raise ValueError("epochs, steps_per_epoch, and batch_size must be positive")
    if learning_rate <= 0 or boundary_weight < 0:
        raise ValueError("learning_rate must be positive and boundary_weight non-negative")

    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device_name = device or ("cuda" if torch.cuda.is_available() else "cpu")
    target_device = torch.device(device_name)

    normalization_mask = np.asarray(train_mask, dtype=bool) & np.asarray(label_valid, dtype=bool)
    feature_stats = fit_robust_feature_stats(features, normalization_mask, seed=seed)
    dataset = RandomPatchDataset(
        features,
        labels,
        label_valid,
        train_mask,
        patch_size=patch_size,
        radius_pixels=3,
        samples=steps_per_epoch * batch_size,
        seed=seed,
        feature_stats=feature_stats,
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0, drop_last=True)
    model = SmallUNet(in_channels=int(features.shape[0])).to(target_device)
    criterion = GEMSBoundaryAwareLoss(
        pixel_size_x_m=100.0,
        pixel_size_y_m=100.0,
        radius_m=300.0,
        alpha=0.2,
        beta=0.8,
        regional_weight=1.0,
        boundary_weight=boundary_weight if loss_mode == "combined" else 0.0,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    history: list[dict[str, float]] = []

    for epoch in range(epochs):
        dataset.set_epoch(epoch)
        model.train()
        total_loss = 0.0
        total_regional = 0.0
        total_boundary = 0.0
        batches = 0
        for x, y, valid, scored in loader:
            x = x.to(target_device, non_blocking=True)
            y = y.to(target_device, non_blocking=True)
            valid = valid.to(target_device, non_blocking=True)
            scored = scored.to(target_device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            components = criterion(logits, y, valid, scored, return_components=True)
            components["total"].backward()
            optimizer.step()
            total_loss += float(components["total"].detach().cpu())
            total_regional += float(components["regional"].detach().cpu())
            total_boundary += float(components["boundary"].detach().cpu())
            batches += 1
        if batches == 0:
            raise RuntimeError("no training batches were produced")
        history.append(
            {
                "epoch": float(epoch + 1),
                "total_loss": total_loss / batches,
                "regional_loss": total_regional / batches,
                "boundary_loss": total_boundary / batches,
            }
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "state_dict": model.state_dict(),
        "in_channels": int(features.shape[0]),
        "fold": fold,
        "dataset_signature": dataset_signature,
        "base_channels": 24,
        "feature_stats": feature_stats,
        "normalization_note": "fit on training-fold feature pixels only; held-out pixels excluded",
        "loss_mode": loss_mode,
        "boundary_weight": boundary_weight if loss_mode == "combined" else 0.0,
        "radius_m": 300.0,
        "alpha": 0.2,
        "beta": 0.8,
        "seed": seed,
        "epochs": epochs,
        "steps_per_epoch": steps_per_epoch,
        "batch_size": batch_size,
        "patch_size": patch_size,
        "learning_rate": learning_rate,
        "weight_decay": 1e-4,
        "optimizer": "AdamW",
        "history": history,
        "training_note": "validation and leaderboard scores are not included; evaluate on frozen spatial folds",
    }
    torch.save(checkpoint, output)
    return checkpoint
