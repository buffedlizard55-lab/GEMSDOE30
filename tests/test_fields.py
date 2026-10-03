"""Tests for the belief-field builders (:mod:`gemsdoe30.fields`).

Belief fields are the *input* to the emitter, so their contract is what the whole
emission pipeline rests on: a distance in metres, a monotone decay with a hard
cutoff, a fusion that cannot be dominated by one field's dynamic range, and a
normaliser that reproduces a requested mass exactly.
"""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe30.fields import (
    distance_to_mask,
    geometric_mean,
    layer_belief,
    proximity_belief,
    scale_to_mass,
)


def test_distance_to_mask_is_in_metres_and_infinite_without_sources():
    mask = np.zeros((11, 11), dtype=bool)
    mask[5, 5] = True
    distance = distance_to_mask(mask, pixel_m=100.0)
    assert distance[5, 5] == 0.0
    assert distance[5, 8] == pytest.approx(300.0)
    assert distance[0, 5] == pytest.approx(500.0)
    # A diagonal step is sqrt(2) * 100 m in a Euclidean distance transform.
    assert distance[6, 6] == pytest.approx(100.0 * 2 ** 0.5, rel=1e-6)
    assert np.isinf(distance_to_mask(np.zeros((4, 4), dtype=bool))).all()
    scaled = distance_to_mask(mask, pixel_m=30.0)
    assert scaled[5, 8] == pytest.approx(90.0)


def test_proximity_belief_decays_pairwise_and_cuts_off():
    mask = np.zeros((41, 41), dtype=bool)
    mask[20, 20] = True
    belief = proximity_belief(mask, decay_m=1000.0, cutoff_m=2000.0)
    assert belief[20, 20] == pytest.approx(1.0)
    assert belief[20, 30] == pytest.approx(np.exp(-1.0), rel=1e-5)
    assert belief[20, 40] == pytest.approx(np.exp(-2.0), rel=1e-5)
    # The corner is 2.83 km away (a diagonal of the grid), beyond the 2 km cutoff.
    assert belief[0, 0] == 0.0
    # Values are non-increasing with distance and never negative.
    assert np.all(np.diff(belief[20, 20:]) <= 1e-6)
    assert float(belief.min()) >= 0.0
    # A footprint restricts the *sources*: excluding the only source zeroes the field.
    footprint = np.zeros_like(mask)
    footprint[18:23, :] = True
    restricted = proximity_belief(mask, footprint=footprint, decay_m=1000.0, cutoff_m=2000.0)
    assert restricted[20, 30] == pytest.approx(belief[20, 30], rel=1e-6)
    assert float(proximity_belief(mask, footprint=np.zeros_like(mask)).max()) == 0.0


def test_layer_belief_fuses_evidence_and_rejects_empty_input():
    first = np.zeros((21, 21), dtype=bool)
    first[10, 5] = True
    second = np.zeros((21, 21), dtype=bool)
    second[10, 6] = True
    fused = layer_belief({"a": first}, decay_m=500.0, cutoff_m=1500.0)
    both = layer_belief({"a": first, "b": second}, decay_m=500.0, cutoff_m=1500.0)
    assert both[10, 5] > fused[10, 5]  # independent corroboration raises belief
    assert float(fused.max()) <= float(both.max())
    with pytest.raises(ValueError):
        layer_belief({})


def test_geometric_mean_requires_both_sides_and_keeps_a_floor():
    left = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    right = np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
    combined = geometric_mean(left, right, floor=1e-6)
    assert combined[0, 0] == pytest.approx(1.0, abs=1e-5)   # both supported
    assert combined[0, 1] == pytest.approx(1e-6, rel=1e-3)  # neither supported
    assert combined[1, 0] == pytest.approx(np.sqrt(1e-6), rel=1e-3)  # one side only
    assert combined[1, 1] == pytest.approx(np.sqrt(1e-6), rel=1e-3)  # other side only
    assert float(combined.min()) > 0.0
    with pytest.raises(ValueError):
        geometric_mean(left, np.ones((3, 3), dtype=np.float32))


def test_scale_to_mass_reproduces_the_requested_mass_and_validates():
    field = np.array([[1.0, 0.0], [0.0, 3.0]], dtype=np.float32)
    scaled = scale_to_mass(field, 20.0)
    assert float(scaled.sum()) == pytest.approx(20.0, rel=1e-6)
    assert scaled[1, 1] / scaled[0, 0] == pytest.approx(3.0, rel=1e-6)
    support = np.array([[True, False], [False, True]])
    restricted = scale_to_mass(field, 8.0, support=support)
    assert float(restricted.sum()) == pytest.approx(8.0, rel=1e-6)
    assert restricted[0, 1] == 0.0 and restricted[1, 0] == 0.0
    with pytest.raises(ValueError):
        scale_to_mass(np.zeros((3, 3), dtype=np.float32), 5.0)
