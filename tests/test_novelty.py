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


@pytest.mark.parametrize('positive_fraction', [.001, .1, .5, .999])
def test_binary_rank_fast_path_matches_full_average_tie_spearman(positive_fraction):
    from scipy.stats import spearmanr
    from gemsdoe30.novelty import rank_cache
    rng = np.random.default_rng(232)
    a = rng.integers(0, 8, size=(80, 100)).astype(float)  # candidate ties too
    b = (rng.random(a.shape) < positive_fraction).astype(float)
    mask = rng.random(a.shape) > .1
    row = compare(a, b, mask, stage='surface', cached_ranks=rank_cache(a, mask))
    assert row['spearman_full_footprint'] == pytest.approx(
        spearmanr(a[mask], b[mask]).statistic, abs=1e-12)


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


def test_cached_ranks_and_stage_surface_match_scipy():
    from scipy.stats import spearmanr
    from gemsdoe30.novelty import rank_cache
    rng = np.random.default_rng(17)
    a = rng.normal(size=(35, 40))
    b = rng.integers(0, 4, size=a.shape).astype(float)
    mask = rng.random(a.shape) > .2
    row = compare(a, b, mask, stage='surface', cached_ranks=rank_cache(a, mask))
    assert row['spearman_full_footprint'] == pytest.approx(spearmanr(a[mask], b[mask]).statistic)
    assert row['candidate_dots'] is None
    assert row['candidate_fraction_within_3px_of_reference'] is None
    assert row['undefined'] is False
    with pytest.raises(ValueError): compare(a, b, mask, stage='invalid')


def test_negative_rank_and_stale_flags_stop_conservatively():
    a = np.arange(100, dtype=float).reshape(10, 10)
    row = compare(a, 99 - a, np.ones_like(a, dtype=bool), stage='surface')
    assert row['spearman_full_footprint'] == pytest.approx(-1)
    assert row['correlation_duplicate']
    row['correlation_duplicate'] = False  # numerical evidence is authoritative
    assert decision([row], stage='surface', registry_complete=True) == 'duplicate-stop'
    row['spearman_full_footprint'] = float('nan')
    assert decision([row], stage='surface', registry_complete=True).startswith('blocked')


def test_dot_budget_bound_is_a_strict_proof_not_a_pass():
    from gemsdoe30.novelty import dot_budget_bound
    footprint = np.ones((5, 5), dtype=bool)
    lattice = np.zeros((5, 5)); lattice[2, 2] = 1
    # Radius 0 covers exactly one cell; 24 cells are beyond it.
    below = dot_budget_bound(lattice, footprint, 24, radius_px=0)
    assert below['uncovered_pixels'] == 24
    assert below['minimum_overlapping_dots'] == 0
    assert below['decision'] == 'not-proven'  # not an assertion of uniqueness
    assert below['first_provably_stopped_budget'] is None
    # A real 70% equality case: 3 uncovered pixels, 10 candidate dots.
    mask = np.ones((1, 10), dtype=bool)
    ref = np.ones((1, 10)); ref[0, 7:] = 0
    exact = dot_budget_bound(ref, mask, 10, radius_px=0)
    assert exact['minimum_fraction_within_radius'] == pytest.approx(.70)
    assert exact['decision'] == 'not-proven'
    ref[0, 7] = 1
    assert dot_budget_bound(ref, mask, 10, radius_px=0)['decision'] == 'duplicate-stop'
    with pytest.raises(ValueError): dot_budget_bound(ref, mask, True)
    with pytest.raises(ValueError): dot_budget_bound(ref, mask, 11)
    ref[0, 0] = np.nan
    with pytest.raises(ValueError): dot_budget_bound(ref, mask, 5)
    with pytest.raises(ValueError): dot_budget_bound(np.zeros((1, 10)), mask, 5)


def test_malformed_reference_can_prove_a_duplicate_but_never_clear_coverage(tmp_path):
    import json
    import rasterio
    from rasterio.transform import from_origin
    from scripts.check_novelty import audit, digest
    profile = dict(driver='GTiff', width=10, height=10, count=1, dtype='float32',
                   crs='EPSG:32611', transform=from_origin(0, 1000, 100, 100))
    template = np.zeros((10, 10), dtype='float32')
    # Candidate and the valid portion of a broken reference share 8 dots;
    # one candidate dot is in the broken portion. Full lower bound is 8/9.
    candidate = template.copy(); candidate[2, 0:9] = 1
    reference = candidate.copy(); reference[:, 8:] = np.nan
    paths = [tmp_path / n for n in ('template.tif', 'candidate.tif', 'malformed.tif', 'valid.tif')]
    distant = template.copy(); distant[9, 9] = 1
    for path, array in zip(paths, (template, candidate, reference, distant)):
        with rasterio.open(path, 'w', **profile) as ds: ds.write(array, 1)
    manifest = tmp_path / 'registry.json'
    def registry(ref):
        return {'complete': True,
                'rasters': [{'path': str(paths[3]), 'sha256': digest(paths[3])}],
                'exclusions': [{'path': str(paths[2]), 'sha256': digest(paths[2]),
                                'aligned': True, 'footprint_complete': False}]}
    manifest.write_text(json.dumps(registry(reference)))
    result = audit(paths[1], paths[0], manifest, 'dots')
    proof = result['malformed_exclusions_audited'][0]
    assert proof['known_matching_candidate_dots'] == 8
    assert proof['candidate_total_dots'] == 9
    assert proof['full_candidate_overlap_lower_bound'] == pytest.approx(8 / 9)
    assert result['decision'] == 'duplicate-stop'
    assert result['registry_complete'] is False
    surface = audit(paths[1], paths[0], manifest, 'surface')
    assert surface['decision'].startswith('blocked')
    assert surface['malformed_exclusions_audited'][0]['partial_correlation_is_full_footprint_evidence'] is False

    # A misleading 100% finite-subset overlap is only 1/9 of *all* candidate
    # dots and cannot prove a stop. The malformed exclusion still blocks a pass.
    reference = np.full((10, 10), np.nan, dtype='float32'); reference[2, 0] = 1
    with rasterio.open(paths[2], 'w', **profile) as ds: ds.write(reference, 1)
    manifest.write_text(json.dumps(registry(reference)))
    result = audit(paths[1], paths[0], manifest, 'dots')
    assert result['malformed_exclusions_audited'][0]['full_candidate_overlap_lower_bound'] == pytest.approx(1 / 9)
    assert result['decision'].startswith('blocked')
