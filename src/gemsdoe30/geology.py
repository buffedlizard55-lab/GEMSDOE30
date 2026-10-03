"""Label-free finite-support geological interactions for the registered pilot."""
from __future__ import annotations
import numpy as np
from scipy.ndimage import uniform_filter, binary_erosion

REQUIRED_BANDS = ('geod_dilaterate', 'cond_surf', 'depth_to_base_surf')


def band_indices(descriptions):
    names = [name.split(' - ', 1)[0] for name in descriptions]
    if len(set(names)) != len(names):
        raise ValueError('ambiguous repeated band names')
    missing = set(REQUIRED_BANDS) - set(names)
    if missing:
        raise ValueError(f'missing required geological bands: {sorted(missing)}')
    return {name: names.index(name) for name in REQUIRED_BANDS}


def gradient(band, size):
    """Box smoothing + central derivatives, with strictly finite 500 m max support."""
    finite = np.isfinite(band)
    smooth = uniform_filter(np.where(finite, band, 0).astype(np.float32), size=size, mode='constant')
    gy, gx = np.gradient(smooth, 100.0)
    radius = size // 2 + 1
    supported = binary_erosion(finite, structure=np.ones((2*radius+1, 2*radius+1)), border_value=0)
    gy[~supported] = np.nan
    gx[~supported] = np.nan
    return gy, gx


def interaction_features(raw, descriptions):
    """Return H and generic-context C feature arrays; no labels, fitting, or scaling."""
    idx = band_indices(descriptions)
    dilation = np.maximum(np.asarray(raw[idx['geod_dilaterate']]), 0)
    conductance = raw[idx['cond_surf']]
    depth = raw[idx['depth_to_base_surf']]
    cy, cx = gradient(conductance, 3)
    by, bx = gradient(conductance, 9)
    dy, dx = gradient(depth, 9)
    fine = np.hypot(cy, cx)
    coarse = np.hypot(by, bx)
    depth_mag = np.hypot(dy, dx)
    dot = by*dy + bx*dx
    denom = coarse * depth_mag
    axial = np.zeros_like(denom)
    np.divide(dot, denom, out=axial, where=denom > 1e-12)
    axial = np.clip(axial, -1, 1)**2
    axial[~np.isfinite(denom)] = np.nan
    persistent = np.minimum(fine, coarse)
    h = np.stack([dilation*persistent, dilation*fine*axial, persistent*axial]).astype(np.float32)
    c = np.stack([fine, coarse, depth_mag]).astype(np.float32)
    return h, c
