"""Label-free LiDAR scarp-morphology and geophysical-edge layers (lane G30-LSM).

Every layer here is a deterministic function of the 19 GeoDAWN bands or of the
owner-mirrored 3DEP-derived 100 m LiDAR descriptor stack. No catalogue geometry,
registry raster, template value or label enters any computation, so the layers
cannot leak withheld faults. The decode follows the stack's published rule
``q = 1 + round(254 * t(clip(x/xmax, 0, 1)))`` with ``t`` in {sqrt, linear} and
``q = 0`` meaning "no LiDAR" (``docs/research/lidar-scarp-stack-owner-metadata.json``).
"""
from __future__ import annotations

from typing import Any

TRANSFORM_VERSION = "lsm-layers-v1-20261025"

LIDAR_BANDS = ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
               "upface_max", "cross_max", "relief", "coh100", "strike", "valid")
QUANTISATION = {
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"), "downface_max": (1.0, "sqrt"),
    "upface_max": (1.0, "sqrt"), "cross_max": (1.0, "sqrt"), "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"), "strike": (180.0, "linear"), "valid": (1.0, "linear"),
}
LIDAR_LAYERS = ("lidar_valid", "step_max", "ex_max", "ex_mean", "lapneg_max", "lappos_max",
                "downface_max", "upface_max", "cross_max", "relief", "coh100",
                "scarp_dipole", "scarp_face", "face_vs_channel", "strike_persistence_5x5",
                "scarp_face_max3", "scarp_dipole_smooth")
GEO_LAYERS = ("gradmag_rtp", "gradmag_iso_grav_anom", "gradmag_det_elev",
              "gradmag_depth_to_base_surf", "tensor_coherence_rtp", "abslap_det_elev")
# 0-based band indices in the prepared 19-band cache (manifest order).
BAND = {"rtp": 1, "det_elev": 11, "iso_grav_anom": 12, "depth_to_base_surf": 14}


def decode(q: Any, name: str) -> Any:
    """Decode one quantised channel; ``q == 0`` (no LiDAR) becomes NaN."""
    import numpy as np

    if name not in QUANTISATION:
        raise KeyError(f"unknown LiDAR channel {name}")
    xmax, mode = QUANTISATION[name]
    q = np.asarray(q)
    if q.dtype != np.uint8:
        raise ValueError("LiDAR descriptor stack must be uint8")
    t = np.clip(q.astype(np.float32) - 1.0, 0.0, 254.0) / 254.0
    x = np.float32(xmax) * (t * t if mode == "sqrt" else t)
    return np.where(q > 0, x, np.float32(np.nan)).astype(np.float32)


def axial_persistence(theta_deg: Any, weight: Any, size: int = 5) -> Any:
    """Weighted axial consensus |<w e^{2i theta}>| / <w> over a size x size window.

    Axial (0 == 180 degrees) and invariant to the unknown angle convention, because
    only angle *differences* inside the window matter. Missing weight -> NaN.
    """
    import numpy as np
    from scipy.ndimage import uniform_filter

    if size < 1 or size % 2 == 0:
        raise ValueError("window size must be a positive odd integer")
    theta = np.deg2rad(np.asarray(theta_deg, dtype=np.float64)) * 2.0
    w = np.where(np.isfinite(theta) & np.isfinite(weight), np.asarray(weight, dtype=np.float64), 0.0)
    w = np.clip(w, 0.0, None)
    c = uniform_filter(np.where(w > 0, w * np.cos(np.nan_to_num(theta)), 0.0), size, mode="constant")
    s = uniform_filter(np.where(w > 0, w * np.sin(np.nan_to_num(theta)), 0.0), size, mode="constant")
    m = uniform_filter(w, size, mode="constant")
    out = np.where(m > 1e-9, np.hypot(c, s) / np.maximum(m, 1e-9), np.nan)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def lidar_layers(stack: Any, valid: Any):
    """Yield ``(name, float32 layer)`` for the 17 LiDAR morphology layers, one at a time.

    ``stack`` is the (12, H, W) uint8 descriptor stack in ``LIDAR_BANDS`` order.
    Yielding keeps peak memory to a few layers on the 3 GB research box.
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter, maximum_filter

    if stack.shape[0] != len(LIDAR_BANDS):
        raise ValueError("expected the 12-channel LiDAR descriptor stack")
    valid = np.asarray(valid, dtype=bool)
    index = {name: i for i, name in enumerate(LIDAR_BANDS)}

    def channel(name):
        return np.where(valid, decode(np.asarray(stack[index[name]]), name), np.float32(np.nan))

    coverage = channel("valid")
    yield "lidar_valid", np.where(valid, np.nan_to_num(coverage, nan=0.0), 0.0).astype(np.float32)
    has = np.isfinite(coverage)
    for name in ("step_max", "ex_max", "ex_mean", "lapneg_max", "lappos_max", "downface_max",
                 "upface_max", "cross_max", "relief", "coh100"):
        yield name, channel(name)
    neg, pos = channel("lapneg_max"), channel("lappos_max")
    dipole = np.sqrt(np.clip(neg, 0, None) * np.clip(pos, 0, None)).astype(np.float32)
    del neg, pos
    yield "scarp_dipole", dipole
    step = channel("step_max")
    up, down, cross = channel("upface_max"), channel("downface_max"), channel("cross_max")
    face = np.sqrt(np.clip(step, 0, None) * np.clip(np.fmax(up, down), 0, None)).astype(np.float32)
    ratio = (np.fmax(up, down) / (np.clip(cross, 0, None) + np.float32(0.01))).astype(np.float32)
    del step, up, down, cross
    yield "scarp_face", face
    yield "face_vs_channel", ratio
    del ratio
    strike = channel("strike")
    yield "strike_persistence_5x5", np.where(has, axial_persistence(strike, coverage, 5), np.nan).astype(np.float32)
    del strike
    filled = np.nan_to_num(face, nan=0.0)
    yield "scarp_face_max3", np.where(has, maximum_filter(filled, size=3), np.nan).astype(np.float32)
    del filled, face
    weight = gaussian_filter(has.astype(np.float32), 1.0)
    smooth = gaussian_filter(np.nan_to_num(dipole, nan=0.0), 1.0) / np.maximum(weight, 1e-6)
    yield "scarp_dipole_smooth", np.where(has, smooth, np.nan).astype(np.float32)


def _robust(band: Any, valid: Any) -> Any:
    import numpy as np

    values = band[valid & np.isfinite(band)]
    if not values.size:
        raise ValueError("band has no finite valid pixels")
    med = float(np.median(values))
    q1, q3 = np.percentile(values, [25, 75])
    scale = float(q3 - q1) or 1.0
    return np.clip(np.where(np.isfinite(band), (band - med) / scale, 0.0), -8, 8).astype(np.float32)


def geo_layers(base: Any, valid: Any):
    """Yield ``(name, float32 layer)`` for the 6 label-free geophysical edge layers.

    Robust scaling uses whole-footprint statistics of each raw band (label-free,
    so identical in every fold); models standardise their own inputs again.
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter, laplace, sobel

    valid = np.asarray(valid, dtype=bool)

    def norm(name):
        return gaussian_filter(_robust(np.asarray(base[BAND[name]], dtype=np.float32), valid), 1.0)

    for name in ("rtp", "iso_grav_anom", "det_elev", "depth_to_base_surf"):
        x = norm(name)
        g = np.hypot(sobel(x, axis=1), sobel(x, axis=0)).astype(np.float32)
        yield f"gradmag_{name}", np.where(valid, g, np.nan).astype(np.float32)
        if name == "rtp":
            gx, gy = sobel(x, axis=1), sobel(x, axis=0)
            jxx, jyy, jxy = gaussian_filter(gx * gx, 2.0), gaussian_filter(gy * gy, 2.0), gaussian_filter(gx * gy, 2.0)
            del gx, gy
            coherence = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4 * jxy ** 2, 0)) / (jxx + jyy + 1e-6)
            del jxx, jyy, jxy
            rtp_coherence = np.where(valid, coherence, np.nan).astype(np.float32)
            del coherence
        if name == "det_elev":
            det_lap = np.where(valid, np.abs(laplace(x)), np.nan).astype(np.float32)
        del x, g
    yield "tensor_coherence_rtp", rtp_coherence
    yield "abslap_det_elev", det_lap


class StackedFeatures:
    """Read-only channel concatenation of two (C, H, W) arrays without copying.

    Supports the indexing patterns used by the shared sampler/predictor:
    ``x[:, rows, cols]`` (fancy) and ``x[:, r0:r1, c0:c1]`` (blocks), plus ``x[j]``.
    """

    def __init__(self, *parts: Any, names: list[str] | None = None):
        if not parts or any(p.shape[1:] != parts[0].shape[1:] for p in parts):
            raise ValueError("parts must share spatial shape")
        self.parts = parts
        self.shape = (sum(p.shape[0] for p in parts),) + tuple(parts[0].shape[1:])
        self.names = names
        if names is not None and len(names) != self.shape[0]:
            raise ValueError("names must match channel count")

    def __len__(self) -> int:
        return self.shape[0]

    def __getitem__(self, key):
        import numpy as np

        if isinstance(key, (int, np.integer)):
            k = int(key)
            if k < 0:
                k += self.shape[0]
            for p in self.parts:
                if k < p.shape[0]:
                    return p[k]
                k -= p.shape[0]
            raise IndexError(key)
        if isinstance(key, tuple) and key and key[0] == slice(None):
            return np.concatenate([np.asarray(p[key]) for p in self.parts], axis=0)
        raise TypeError("StackedFeatures supports x[j] and x[:, ...] indexing only")
