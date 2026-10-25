import numpy as np
import pytest
from gemsdoe30.novelty import compare, decision


def test_encoding_change_is_not_novel():
    a = np.zeros((9, 9)); a[4, 4] = 1
    mask = np.ones_like(a, dtype=bool); mask[0] = False
    b = a.copy(); b[0] = np.nan
    row = compare(a, b, mask)
    assert row['identical_inside_footprint']
    assert decision([row], stage='dots', registry_complete=False) == 'duplicate-stop'


def test_distance_boundary_and_direction():
    a = np.zeros((12, 12)); b = a.copy()
    a[3, 3] = 1; b[3, 6] = 1; b[10, 10] = 1
    mask = np.ones_like(a, dtype=bool)
    assert compare(a, b, mask)['candidate_fraction_within_3px_of_reference'] == 1
    assert compare(b, a, mask)['candidate_fraction_within_3px_of_reference'] == .5
    b[3, 6] = 0; b[4, 6] = 1
    assert compare(a, b, mask)['candidate_fraction_within_3px_of_reference'] == 0


def test_thresholds_strict_and_stage_specific():
    row = dict(identical_inside_footprint=False, spearman_full_footprint=.2,
               candidate_fraction_within_3px_of_reference=.8,
               correlation_duplicate=False, dot_duplicate=True)
    assert decision([row], stage='surface', registry_complete=True).startswith('novelty-check')
    assert decision([row], stage='dots', registry_complete=True) == 'duplicate-stop'
    assert decision([row], stage='surface', registry_complete=False).startswith('blocked')
    assert decision([], stage='surface', registry_complete=True).startswith('blocked')
    with pytest.raises(ValueError): decision([], stage='typo', registry_complete=True)


def test_constant_and_invalid_data_fail_closed():
    a = np.zeros((5, 5)); mask = np.ones_like(a, dtype=bool)
    b = np.arange(25).reshape(5, 5)
    row = compare(a, b, mask)
    assert row['spearman_full_footprint'] is None
    assert decision([row], stage='surface', registry_complete=True).startswith('blocked')
    a[1, 1] = np.inf
    with pytest.raises(ValueError): compare(a, b, mask)
    with pytest.raises(ValueError): compare(b, b, ~mask)


def test_rescaling_has_identical_rank():
    a = np.arange(25).reshape(5, 5)
    row = compare(a, a / 24, np.ones_like(a, dtype=bool))
    assert row['correlation_duplicate']


def test_cli_checks_grid_and_pins(tmp_path):
    import json
    import rasterio
    from rasterio.transform import from_origin
    from scripts.check_novelty import audit, digest
    profile = dict(driver='GTiff', width=6, height=6, count=1, dtype='float32',
                   crs='EPSG:32611', transform=from_origin(0, 600, 100, 100))
    a = np.zeros((6, 6), dtype='float32'); a[2, 2] = 1
    paths = [tmp_path / name for name in ['template.tif', 'a.tif', 'b.tif']]
    for path in paths:
        with rasterio.open(path, 'w', **profile) as ds: ds.write(a, 1)
    registry = tmp_path / 'registry.json'
    registry.write_text(json.dumps({'complete': True, 'rasters': [
        {'path': str(paths[2]), 'sha256': digest(paths[2])}]}))
    assert audit(paths[1], paths[0], registry, 'dots')['decision'] == 'duplicate-stop'
    registry.write_text(json.dumps({'complete': True, 'rasters': [
        {'path': str(paths[2]), 'sha256': 'wrong'}]}))
    report = audit(paths[1], paths[0], registry, 'dots')
    assert report['decision'].startswith('blocked') and report['errors']
    profile['transform'] = from_origin(100, 600, 100, 100)
    with rasterio.open(paths[1], 'w', **profile) as ds: ds.write(a, 1)
    with pytest.raises(ValueError): audit(paths[1], paths[0], registry, 'dots')
