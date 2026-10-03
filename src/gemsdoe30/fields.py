"""Belief fields for the EDGE emitter: pure geometry, no competition labels.

The GEMS metric credits a truth pixel from the best nearby prediction, so what an
emitter needs is not a class probability but a *belief surface*: the expected
number of hidden (scored) truth pixels near each location.  This module builds
such surfaces from inputs a competitor legitimately has:

* the mapped catalogue/known-fault geometry (the training labels themselves;
  distance to the nearest *known* trace is a structural prior),
* free, official external layers already derived onto the competition grid by
  ``scripts/fetch_external_layers.py`` (USGS SGMC state geologic maps, GDR
  geothermal/volcanic products).

Every field here is built from data that *excludes* the stand-in hidden truth of
a holdout split, so holdout evaluation is not circular in the sense the
repository's protocol requires.  A catalogue-based holdout remains a biased proxy
for the organizer's expert-labelled new faults, and nothing here is a score.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

DEFAULT_PIXEL_M = 100.0


def distance_to_mask(mask: Any, *, pixel_m: float = DEFAULT_PIXEL_M) -> Any:
    """Euclidean distance (metres) from every cell to the nearest ``True`` cell."""

    import numpy as np
    from scipy.ndimage import distance_transform_edt

    values = np.asarray(mask, dtype=bool)
    if values.ndim != 2:
        raise ValueError("mask must be two-dimensional")
    if not math.isfinite(float(pixel_m)) or pixel_m <= 0:
        raise ValueError("pixel_m must be finite and positive")
    if not values.any():
        return np.full(values.shape, np.inf, dtype=np.float64)
    return distance_transform_edt(~values, sampling=(pixel_m, pixel_m))


def proximity_belief(
    known: Any,
    *,
    footprint: Any | None = None,
    decay_m: float = 1000.0,
    cutoff_m: float = 3000.0,
    pixel_m: float = DEFAULT_PIXEL_M,
) -> Any:
    """Belief proportional to ``exp(-d/decay)`` around mapped traces, cut off at ``cutoff``.

    The prior encodes one specific, documented geological statement: newly mapped
    geometry of an *existing* fault system is a large part of what counts as a new
    fault (DrivenData community clarification 11536), so the neighbourhood of a
    mapped trace is where un-mapped geometry is most likely.
    """

    import numpy as np

    if decay_m <= 0 or cutoff_m <= 0:
        raise ValueError("decay_m and cutoff_m must be positive")
    distance = distance_to_mask(known, pixel_m=pixel_m)
    belief = np.exp(-distance / float(decay_m))
    belief[distance > float(cutoff_m)] = 0.0
    if footprint is not None:
        footprint_array = np.asarray(footprint, dtype=bool)
        if footprint_array.shape != belief.shape:
            raise ValueError("footprint shape differs from mask")
        belief = np.where(footprint_array, belief, 0.0)
    return belief.astype(np.float32)


def layer_belief(
    layers: Mapping[str, Any],
    *,
    footprint: Any | None = None,
    decay_m: float = 700.0,
    cutoff_m: float = 2100.0,
    pixel_m: float = DEFAULT_PIXEL_M,
) -> Any:
    """Distance-decayed belief around every positive cell of each supplied layer.

    Layers are combined by a linear sum of per-layer decays with equal weight, so a
    cell supported by two independent layers outranks a cell supported by one.  The
    inputs are boolean or non-negative rasters on the competition grid.
    """

    import numpy as np

    if not layers:
        raise ValueError("at least one layer is required")
    if decay_m <= 0 or cutoff_m <= 0:
        raise ValueError("decay_m and cutoff_m must be positive")
    total: Any = None
    for name, values in layers.items():
        array = np.asarray(values)
        if array.ndim != 2:
            raise ValueError(f"layer {name!r} must be two-dimensional")
        positive = array > 0
        if not positive.any():
            continue
        distance = distance_to_mask(positive, pixel_m=pixel_m)
        contribution = np.exp(-distance / float(decay_m))
        contribution[distance > float(cutoff_m)] = 0.0
        total = contribution if total is None else total + contribution
    if total is None:
        reference = np.asarray(next(iter(layers.values())))
        total = np.zeros(reference.shape, dtype=np.float64)
    if footprint is not None:
        footprint_array = np.asarray(footprint, dtype=bool)
        if footprint_array.shape != total.shape:
            raise ValueError("footprint shape differs from layers")
        total = np.where(footprint_array, total, 0.0)
    return total.astype(np.float32)


def geometric_mean(left: Any, right: Any, *, floor: float = 1e-6) -> Any:
    """Scale-free combination of two non-negative belief surfaces.

    A geometric mean requires *both* surfaces to support a cell, which is the
    behaviour wanted when one surface is a structural prior and the other an
    independent evidence layer: the product cannot be dominated by a single field's
    dynamic range.  ``floor`` is added *inside* the root, so a cell supported by only
    one surface keeps a small baseline ``sqrt(floor)`` and a cell supported by
    neither keeps ``floor``; the returned map is therefore strictly positive and
    directly comparable across fields.
    """

    import numpy as np

    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("surfaces must share a shape")
    if np.any(a < 0) or np.any(b < 0):
        raise ValueError("surfaces must be non-negative")
    if not 0.0 <= floor < 1.0:
        raise ValueError("floor must be in [0, 1)")
    if float(a.max()) > 0 and float(b.max()) > 0:
        a = a / float(a.max())
        b = b / float(b.max())
    combined = np.sqrt((a + floor) * (b + floor))
    return np.clip(combined, 0.0, None).astype(np.float32)


def scale_to_mass(field: Any, mass: float, *, support: Any | None = None) -> Any:
    """Rescale a belief surface so its sum equals ``mass`` inside ``support``."""

    import numpy as np

    values = np.asarray(field, dtype=np.float64)
    if mass <= 0 or not math.isfinite(float(mass)):
        raise ValueError("mass must be finite and positive")
    if support is not None:
        support_array = np.asarray(support, dtype=bool)
        if support_array.shape != values.shape:
            raise ValueError("support shape differs from field")
        values = np.where(support_array, values, 0.0)
    total = float(values.sum())
    if total <= 0:
        raise ValueError("belief surface is empty inside the support")
    return (values * (float(mass) / total)).astype(np.float32)
