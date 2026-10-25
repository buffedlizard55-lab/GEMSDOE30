"""Regression coverage for IR-30-050; no historical metrics silently relabelled."""
import numpy as np
import pytest
from gemsdoe30.holdout import masked_dti_by_blocks


def fixture():
    truth = np.zeros((12, 12), dtype=bool); truth[6, 6] = True
    known = np.zeros_like(truth)
    valid = np.ones_like(truth); valid[:6] = False
    return truth, known, valid


def test_outside_emission_cannot_cover_inside_truth():
    truth, known, valid = fixture()
    pred = np.zeros(truth.shape); pred[5, 6] = 1
    r = masked_dti_by_blocks(pred, truth, known, valid)
    assert r['pooled']['tp_weight'] == 0
    assert r['pooled']['fp_weight'] == 0
    assert r['pooled']['emitted_pixels'] == 0


def test_outside_nan_and_truth_do_not_change_score():
    truth, known, valid = fixture()
    pred = truth.astype(float)
    baseline = masked_dti_by_blocks(pred, truth, known, valid)['pooled']
    pred[~valid] = np.nan; truth[~valid] = True
    assert masked_dti_by_blocks(pred, truth, known, valid)['pooled'] == baseline
    with pytest.raises(ValueError):
        masked_dti_by_blocks(pred, truth, known, valid, fp_weight=np.ones(truth.shape))


def test_empty_truth_quadrant_retains_false_positive_mass():
    truth, known, valid = fixture()
    pred = truth.astype(float); pred[10, 1] = 1
    r = masked_dti_by_blocks(pred, truth, known, valid)
    quads = [v for k, v in r.items() if k.startswith('quadrant_')]
    assert sum(q['fp_weight'] for q in quads) == r['pooled']['fp_weight']
    assert r['quadrant_2']['fp_weight'] == 1
    assert r['quadrant_2']['dti'] == 0


def test_bad_predictions_fail_closed_and_visible_pixels_masked():
    truth, known, valid = fixture(); pred = truth.astype(float)
    pred[8, 8] = 2
    with pytest.raises(ValueError): masked_dti_by_blocks(pred, truth, known, valid)
    known[8, 8] = True
    assert masked_dti_by_blocks(pred, truth, known, valid)['pooled']['emitted_pixels'] == 1
    with pytest.raises(ValueError): masked_dti_by_blocks(pred, truth, known, valid, radius_m=0)
