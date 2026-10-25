import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt, label
from gemsdoe30.holdout import spatial_segment_folds, masked_dti_by_blocks, spatial_bootstrap
from gemsdoe30.metric import distance_weighted_tversky


def catalogue_fixture():
    cat = np.zeros((80, 80), dtype=bool)
    for r, c in [(10, 10), (10, 60), (60, 10), (60, 60)]:
        cat[r:r + 4, c] = True
    cat[30:45, 33] = True  # component crosses a quadrant boundary
    return cat


def test_whole_components_unique_and_buffered():
    cat = catalogue_fixture(); valid = np.ones_like(cat)
    all_hidden = np.zeros(cat.shape, dtype=int)
    labs, count = label(cat, np.ones((3, 3)))
    for f in spatial_segment_folds(cat, valid, buffer_px=5):
        hidden, visible = f['hidden'], f['visible']
        all_hidden += hidden
        assert not (hidden & visible).any()
        assert (cat == (hidden | visible | f['guard'])).all()
        assert not (hidden & ~f['score_valid']).any()
        distance = distance_transform_edt(~f['score_valid'])
        # Score-valid excludes guard pixels, making this check only weaker than
        # the construction's unmodified regional guard, never stronger.
        assert np.all(distance[f['train_mask']] > 5)
        for component in range(1, count + 1):
            values = hidden[labs == component]
            assert values.all() or not values.any()
    assert np.array_equal(all_hidden, cat.astype(int))


def test_segment_folds_reject_invalid_inputs():
    cat = catalogue_fixture()
    with pytest.raises(ValueError): list(spatial_segment_folds(cat, ~cat))
    with pytest.raises(ValueError): list(spatial_segment_folds(cat, np.ones_like(cat), buffer_px=1))
    with pytest.raises(ValueError): list(spatial_segment_folds(np.zeros_like(cat), np.ones_like(cat)))


def test_block_sufficient_statistics_pool_and_match_independent_metric():
    rng = np.random.default_rng(12)
    valid = rng.random((30, 31)) > .1
    known = valid & (rng.random(valid.shape) < .1)
    truth = valid & ~known & (rng.random(valid.shape) < .05)
    pred = rng.random(valid.shape)
    r = masked_dti_by_blocks(pred, truth, known, valid, block_size_px=7)
    official_geometry = distance_weighted_tversky(pred, truth, valid & ~known)
    assert r['pooled']['dti'] == pytest.approx(official_geometry.score)
    assert sum(x['fp_weight'] for x in r['spatial_blocks']) == pytest.approx(r['pooled']['fp_weight'])
    assert sum(x['tp_weight'] for x in r['spatial_blocks']) == pytest.approx(r['pooled']['tp_weight'])
    assert sum(x['truth_pixels'] for x in r['spatial_blocks']) == r['pooled']['truth_pixels']
    with pytest.raises(ValueError): masked_dti_by_blocks(pred, truth, known, valid, block_size_px=0)


def test_bootstrap_pairs_blocks_and_retains_empty_truth_fp():
    rows = [{'block_row': i, 'block_col': 0, 'tp_weight': 1 if i == 0 else 0,
             'fp_weight': 2, 'truth_pixels': 2 if i == 0 else 0} for i in range(4)]
    report = spatial_bootstrap({'a': rows, 'b': rows}, candidate='a', replicates=100)
    assert report['arms']['a']['fp_weight'] == 8
    assert report['candidate_minus']['b']['ci95'] == [0, 0]
    with pytest.raises(ValueError): spatial_bootstrap({'a': rows, 'b': rows[:-1]}, candidate='a')
