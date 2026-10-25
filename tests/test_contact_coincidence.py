"""Regression tests for the H-CC1 contact-coincidence helpers (no raster data needed)."""
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "contact_coincidence_holdout",
    Path(__file__).resolve().parents[1] / "scripts" / "contact_coincidence_holdout.py",
)
cc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cc)


def test_greedy_dispersed_enforces_minimum_spacing():
    rng = np.random.default_rng(0)
    score = rng.random((120, 120))
    eligible = np.ones_like(score, dtype=bool)
    mask = cc.greedy_dispersed(score, eligible, pool_fraction=0.5, budget=400, min_spacing_px=3.0)
    pts = np.argwhere(mask)
    assert 0 < len(pts) <= 400
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            assert math.dist(pts[i], pts[j]) >= 3.0


def test_greedy_dispersed_takes_highest_score_first():
    score = np.zeros((10, 10))
    score[5, 5] = 9.0
    score[5, 6] = 8.0  # adjacent to the best cell: must be rejected at 3-px spacing
    score[0, 0] = 7.0
    eligible = np.ones_like(score, dtype=bool)
    mask = cc.greedy_dispersed(score, eligible, pool_fraction=1.0, budget=2, min_spacing_px=3.0)
    assert mask[5, 5] and mask[0, 0] and not mask[5, 6]


def test_auc_perfect_and_reversed():
    rng = np.random.default_rng(1)
    labels = np.zeros(200, dtype=bool)
    labels[:50] = True
    scores = np.where(labels, 1.0, 0.0) + rng.random(200) * 0.1
    assert cc.auc(scores, labels, rng) == pytest.approx(1.0)
    assert cc.auc(-scores, labels, rng) == pytest.approx(0.0)


def test_select_top_budget_and_probability_range():
    rng = np.random.default_rng(2)
    score = rng.random((200, 200))
    eligible = np.ones_like(score, dtype=bool)
    prob, thr = cc.select_top(score, eligible, fraction=0.01, floor_p=0.5)
    selected = prob > 0
    assert abs(selected.sum() - 400) <= 2
    assert prob[selected].min() >= 0.5 and prob[selected].max() <= 1.0
    assert np.all(score[selected] >= thr)


def test_robust_z_rejects_degenerate_field():
    field = np.ones((10, 10))
    with pytest.raises(ValueError):
        cc.robust_z(field, np.ones_like(field, dtype=bool))
