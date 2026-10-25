"""Explicit supported experiment contracts; unknown experiment IDs fail closed.

Contracts are code-reviewed, not arbitrary mutable JSON that can redefine a failed
promotion gate. Old TDX-1 receipts keep their original schema and expectations.
"""
from __future__ import annotations

CORE_FEATURES = (
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15", "cond_surf",
    "iso_grav_anom_hg", "det_elev_slope",
)
TDX_FEATURES = ("mag_texture", "rtp_texture", "texture_consensus")
CONTROL_FEATURES = ("zero_mag", "zero_rtp", "zero_consensus", "phase_mag", "phase_rtp", "phase_consensus")


def contract(card: dict) -> dict:
    name = card.get("experiment_spec", "tdx1")
    if name == "tdx1":
        return {"id": name, "candidate": "tdx6", "arms": ("physics3", "core19", "tdx6"),
                "features": CORE_FEATURES + TDX_FEATURES, "support_px": 17,
                "transform_path": "src/gemsdoe30/texture.py",
                "transform_version": "tdx1-profiles-v2-euclidean-support-20261025",
                "label": "TDX-1", "image_name": "tdx1-support.png"}
    if name == "tdxc2":
        return {"id": name, "candidate": "tdx22", "arms": ("core19", "tdx22", "zero22", "phase22"),
                "features": CORE_FEATURES + TDX_FEATURES + CONTROL_FEATURES, "support_px": 17,
                "transform_path": "src/gemsdoe30/texture_controls.py",
                "parent_transform_path": "src/gemsdoe30/texture.py",
                "parent_transform_version": "tdx1-profiles-v2-euclidean-support-20261025",
                "transform_version": "tdxc2-local-profile-controls-v1-20261025",
                "label": "TDX-C2", "image_name": "tdxc2-support.png"}
    raise ValueError(f"unknown research experiment contract: {name!r}")


class LayerStack:
    """A zero-copy channel view over cached arrays for the existing sampler/predictor.

    Only requested pixel batches are stacked. This avoids materializing another
    gigabyte-sized 22/28-channel raster while retaining NumPy indexing semantics
    used by the shared feature sampler and blockwise predictor.
    """
    def __init__(self, layers):
        self.layers = tuple(layers)
        if not self.layers or len(self.layers[0].shape) != 2:
            raise ValueError("at least one 2D layer required")
        if any(layer.shape != self.layers[0].shape for layer in self.layers):
            raise ValueError("all layer shapes must match")
        self.shape = (len(self.layers), *self.layers[0].shape)

    def __getitem__(self, key):
        import numpy as np
        if not isinstance(key, tuple) or len(key) != 3:
            raise IndexError("channel, row and column selectors required")
        channel, row, col = key
        if isinstance(channel, (int, np.integer)):
            return self.layers[channel][row, col]
        indices = np.arange(len(self.layers))[channel]
        return np.stack([self.layers[int(i)][row, col] for i in indices])
