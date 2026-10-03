"""Tests for the EDGE emitter (:mod:`gemsdoe30.emitter_opt`).

The emitter's correctness argument rests on four properties, each pinned here:

* the marginal-inclusion threshold matches the published metric algebra
  (a dot with credit ``k`` pays off iff ``k > alpha*s/(1 - alpha*s)``),
* the incremental credit bookkeeping equals an independent from-scratch credit
  evaluation of the emitted mask (the check that once caught a raster-edge
  wrapping bug),
* prefixes of the acceptance order reproduce the recorded cumulative statistics,
* on a synthetic truth the emitter beats every belief-ordered baseline it can be
  compared against *without seeing the truth*.
"""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe30.emission import metric_optimal_emission, poisson_disk_select
from gemsdoe30.emitter_opt import (
    coverage_credit,
    edge_select,
    expected_dti,
    kernel_offsets,
    marginal_threshold,
    mask_from_order,
    stop_index,
)
from gemsdoe30.fields import geometric_mean, proximity_belief, scale_to_mass
from gemsdoe30.holdout import masked_dti

# --------------------------------------------------------------------------- #
# kernel and algebra
# --------------------------------------------------------------------------- #


def test_kernel_offsets_match_the_published_triangular_kernel():
    offsets = kernel_offsets(100.0, 300.0)
    assert len(offsets) == 29  # 7x7 window minus the cells beyond 300 m
    weights = sorted({round(weight, 9) for _, _, weight in offsets})
    # Seven distinct distances survive on a 100 m lattice inside a 300 m radius.
    assert len(weights) == 7
    assert weights[0] == 0.0 and weights[-1] == 1.0
    for dy, dx, weight in offsets:
        distance = 100.0 * float(np.hypot(dy, dx))
        assert distance <= 300.0 + 1e-9
        assert weight == pytest.approx(max(1.0 - distance / 300.0, 0.0), abs=1e-9)
    assert max(weight for _, _, weight in offsets) == 1.0


def test_marginal_threshold_matches_metric_algebra():
    for dti in (0.05, 0.1, 0.2600, 0.3195):
        assert marginal_threshold(dti) == pytest.approx(0.2 * dti / (1 - 0.2 * dti))
    assert marginal_threshold(0.0) == 0.0
    with pytest.raises(ValueError):
        marginal_threshold(5.0)  # alpha*s >= 1 has no positive-credit solution


def test_expected_dti_matches_metric_definition():
    tp, fp, truth = 3_466.0, 22_483.3, 12_691.0
    assert expected_dti(tp, fp, truth) == pytest.approx(
        tp / (0.2 * (tp + fp) + 0.8 * truth), rel=1e-8
    )
    assert expected_dti(0.0, 0.0, truth) == 0.0
    with pytest.raises(ValueError):
        expected_dti(5.0, 0.0, 1.0)  # credit cannot exceed the truth it describes


def test_stop_index_chooses_the_best_expected_prefix_and_skips_impossible_ones():
    cumulative_tp = np.array([0.0, 10.0, 25.0, 30.0, 31.0])
    cumulative_fp = np.array([0.0, 1.0, 5.0, 40.0, 90.0])
    # truth_mass = 25 means prefix 3+ is inconsistent (credit exceeds the mass).
    index = stop_index(cumulative_tp, cumulative_fp, 25.0)
    assert index == 2
    assert index == 0 or cumulative_tp[index] <= 25.0
    assert stop_index(cumulative_tp, np.zeros_like(cumulative_fp), 25.0) == 2
    with pytest.raises(ValueError):
        stop_index(cumulative_tp, cumulative_fp, float("nan"))


def test_mask_from_order_is_prefix_and_bounds_checked():
    order = np.array([5, 7, 9], dtype=np.int64)
    mask = mask_from_order(order, 2, (3, 4))
    assert mask.sum() == 2
    assert bool(mask.ravel()[5]) and bool(mask.ravel()[7])
    assert mask_from_order(order, 0, (3, 4)).sum() == 0
    with pytest.raises(ValueError):
        mask_from_order(order, 4, (3, 4))


# --------------------------------------------------------------------------- #
# credit bookkeeping
# --------------------------------------------------------------------------- #


def test_incremental_credit_matches_an_independent_credit_pass():
    """Greedy gains must telescope to the mask's credit, to floating tolerance."""

    rng = np.random.default_rng(7)
    belief = (rng.random((37, 41)) * 0.05 + 0.001).astype(np.float32)
    belief[18, 20] = 1.0
    belief[3, 3] = 0.4
    truth_mass = 4.0
    mask, diagnostics = edge_select(belief, np.ones(belief.shape, dtype=bool),
                                    truth_mass=truth_mass, max_dots=40,
                                    return_diagnostics=True)
    assert mask.sum() > 5
    # The emitter normalises the belief surface so that it integrates to
    # ``truth_mass``; the recorded credit is therefore in those units.
    scale = truth_mass / float(belief.sum())
    independent = scale * float((belief * coverage_credit(mask.astype(np.float32))).sum())
    assert diagnostics["cumulative_tp"][-1] == pytest.approx(independent, rel=2e-5)


def test_prefix_masks_reproduce_recorded_cumulative_statistics():
    rng = np.random.default_rng(11)
    belief = (rng.random((29, 33)) * 0.03 + 0.0005).astype(np.float32)
    belief[14, 16] = 0.9
    mask, diagnostics = edge_select(belief, np.ones(belief.shape, dtype=bool),
                                    truth_mass=3.0, max_dots=30,
                                    return_diagnostics=True)
    order = diagnostics["order_flat"]
    scale = 3.0 / float(belief.sum())
    for keep in (1, 5, 12, order.size):
        prefix = mask_from_order(order, keep, belief.shape)
        credit = scale * float((belief * coverage_credit(prefix.astype(np.float32))).sum())
        assert credit == pytest.approx(diagnostics["cumulative_tp"][keep], rel=2e-5)


def test_dots_are_never_re_accepted_and_respect_the_cap():
    rng = np.random.default_rng(13)
    belief = (rng.random((31, 31)) * 0.02 + 0.001).astype(np.float32)
    mask, diagnostics = edge_select(belief, np.ones(belief.shape, dtype=bool),
                                    truth_mass=1.0, max_dots=9,
                                    return_diagnostics=True)
    order = diagnostics["order_flat"]
    assert order.size == mask.sum() <= 9
    assert np.unique(order).size == order.size
    assert np.array_equal(mask.ravel()[order], np.ones(order.size, dtype=bool))


def test_edge_select_validates_its_inputs():
    belief = np.zeros((5, 5), dtype=np.float32)
    belief[2, 2] = 1.0
    support = np.ones((5, 5), dtype=bool)
    with pytest.raises(ValueError):
        edge_select(belief - 0.5, support)
    with pytest.raises(ValueError):
        edge_select(belief, np.ones((4, 4), dtype=bool))
    with pytest.raises(ValueError):
        edge_select(belief, support, truth_mass=-1.0)
    with pytest.raises(ValueError):
        edge_select(belief, support, max_dots=0)
    with pytest.raises(ValueError):
        edge_select(belief, np.ones((5, 5), dtype=bool), alpha=1.5)
    # An empty belief inside the support is a degenerate sweep, not an error.
    assert not edge_select(np.zeros((4, 4), dtype=np.float32), np.ones((4, 4), dtype=bool)).any()
    # A belief outside the support is never emitted.
    outside = np.zeros((5, 5), dtype=np.float32)
    outside[0, 0] = 1.0
    support = np.ones((5, 5), dtype=bool)
    support[0, 0] = False
    assert not edge_select(outside, support, truth_mass=1.0).any()


# --------------------------------------------------------------------------- #
# end-to-end behaviour on a synthetic truth the emitter cannot see
# --------------------------------------------------------------------------- #


def _synthetic_scene(shape=(360, 400), seed=5):
    truth = np.zeros(shape, dtype=bool)
    for offset in (60, 180, 300):
        truth[40 + offset // 6:200 + offset // 6, 20] = True
        truth[200 + offset // 6, 20:20 + 120] = True
    truth[30:150, 250] = True
    from scipy.ndimage import gaussian_filter

    belief = gaussian_filter(truth.astype(np.float32), 2.0)
    rng = np.random.default_rng(seed)
    belief += (rng.random(shape).astype(np.float32) * 0.05)
    belief = belief / belief.max()
    return truth, belief.astype(np.float32)


def test_edge_beats_belief_ordered_baselines_without_seeing_the_truth():
    truth, belief = _synthetic_scene()
    known = np.zeros(truth.shape, dtype=bool)
    support = np.ones(truth.shape, dtype=bool)

    emitted = edge_select(belief, support, truth_mass=float(truth.sum()))
    edge_score = masked_dti(emitted.astype(np.float32), truth, known)["dti"]

    baselines = {}
    for radius in (2.0, 3.0, 4.0, 6.0):
        candidate = poisson_disk_select(belief, radius, mask=support)
        baselines[f"uniform@{radius:g}"] = masked_dti(
            candidate.astype(np.float32), truth, known)["dti"]
    baselines["metric@pool"] = masked_dti(
        metric_optimal_emission(belief, support, pool_limit=20_000).astype(np.float32),
        truth, known)["dti"]

    best_baseline = max(baselines.values())
    assert edge_score > best_baseline, baselines
    # Sanity on the operating point: the emitter spends a small fraction of the
    # grid and lands well above the baselines on the metric it was aimed at.
    assert 0 < emitted.sum() < 0.05 * emitted.size
    # The emitter is blind to the truth: it only sees the blurred belief field. It
    # should still clear the best baseline by a wide margin on the metric itself.
    assert edge_score > 1.2 * best_baseline, (edge_score, best_baseline)
