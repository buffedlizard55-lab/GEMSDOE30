import numpy as np

from gemsdoe30.holdout import masked_dti
from scripts.concealment_holdout import bootstrap_ci, exact_binary_dti


def test_binary_distance_transform_matches_shared_holdout_evaluator():
    footprint = np.ones((17, 19), dtype=bool)
    footprint[:2, :] = False
    hidden = np.zeros_like(footprint)
    hidden[7, 8:11] = True
    hidden[12, 14:16] = True
    known = np.zeros_like(footprint)
    known[7, 8] = True
    pred = np.zeros_like(footprint)
    pred[7, 10] = True
    pred[12, 12] = True
    pred[4, 4] = True

    actual, _ = exact_binary_dti(pred, hidden, known, footprint)
    expected = masked_dti(pred, hidden, known)
    assert np.isclose(actual["dti"], expected["dti"], rtol=0, atol=2e-8)
    assert actual["hidden_positive_pixels"] == expected["hidden_truth_pixels"]
    assert actual["emitted_pixels"] == expected["emitted_pixels"]


def test_component_bootstrap_ci_is_reproducible_and_contains_point_dti():
    stats = np.array([[1.0, 2.0, 10.0], [3.0, 1.0, 20.0], [0.5, 4.0, 5.0]])
    ci1 = bootstrap_ci(stats, seed=7, draws=500)
    ci2 = bootstrap_ci(stats, seed=7, draws=500)
    tp, fp, positives = stats.sum(axis=0)
    point = tp / (0.2 * tp + 0.2 * fp + 0.8 * positives)
    assert ci1 == ci2
    assert ci1[0] <= point <= ci1[1]
