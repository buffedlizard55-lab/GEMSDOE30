import numpy as np

from gemsdoe30.emission import dti_from_components
from gemsdoe30.holdout import masked_dti_by_blocks, masked_tile_sums


def test_pooled_tile_sums_reproduce_pooled_dti_exactly():
    rng = np.random.default_rng(5)
    shape = (90, 100)
    valid = np.ones(shape, dtype=bool)
    valid[:, -7:] = False
    known = rng.random(shape) < 0.05
    truth = (rng.random(shape) < 0.02) & ~known
    prediction = np.where(rng.random(shape) < 0.01, rng.random(shape), 0.0).astype(np.float64)
    prediction[~valid] = 0.0
    prediction[known] = 0.0

    pooled = masked_dti_by_blocks(prediction, truth, known, valid)["pooled"]
    sums = masked_tile_sums(prediction, truth, known, valid, tile_px=32)
    tp, fp, n = sums["tp"].sum(), sums["fp"].sum(), sums["truth"].sum()
    assert np.isclose(tp, pooled["tp_weight"], rtol=1e-12)
    assert np.isclose(fp, pooled["fp_weight"], rtol=1e-12)
    assert n == pooled["truth_pixels"]
    assert np.isclose(dti_from_components(tp, fp, n), pooled["dti"], rtol=1e-12)
