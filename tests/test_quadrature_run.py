"""Safety gates for the QPC runner; no experiment is executed by these tests."""
import json

import pytest

from gemsdoe30.experiments import contract
from scripts.run_quadrature_phase import (
    DuplicateStop, assert_audit_research_only, assert_block_parity,
    assert_pooled_parity, lock_once, novelty_summary, validate_frozen_inputs,
)


def test_start_marker_cannot_be_overwritten_or_resumed(tmp_path):
    path = tmp_path / 'started.json'
    lock_once(path, {'seed': 3041})
    with pytest.raises(FileExistsError):
        lock_once(path, {'seed': 9999})
    assert json.loads(path.read_text()) == {'seed': 3041}


def test_duplicate_stops_even_if_a_report_decision_was_overridden():
    report = {'stage': 'dots', 'decision': 'blocked-incomplete-evidence', 'errors': [],
              'comparisons': [{'spearman_full_footprint': .1,
                               'candidate_fraction_within_3px_of_reference': .7001}]}
    with pytest.raises(DuplicateStop):
        assert_audit_research_only(report)
    report['comparisons'][0]['candidate_fraction_within_3px_of_reference'] = .70
    report['comparisons'][0]['spearman_full_footprint'] = .901
    with pytest.raises(DuplicateStop):
        assert_audit_research_only(report)


def test_only_malformed_value_reference_may_remain_unknown_for_research():
    report = {'stage': 'surface', 'decision': 'blocked-incomplete-evidence',
              'errors': ['invalid.tif: non-finite values inside footprint'],
              'comparisons': [{'spearman_full_footprint': .1,
                               'candidate_fraction_within_3px_of_reference': None}]}
    assert_audit_research_only(report)
    assert novelty_summary(report)['max_spearman'] == .1
    report['errors'] = ['missing.tif: file not found']
    with pytest.raises(ValueError, match='I/O/hash/grid'):
        assert_audit_research_only(report)
    report['comparisons'] = []
    with pytest.raises(ValueError, match='no registry'):
        assert_audit_research_only(report)


def test_historical_controls_require_block_and_pooled_parity():
    row = {'block_row': 0, 'block_col': 1, 'truth_pixels': 2, 'scored_pixels': 9}
    assert_block_parity([row], [dict(row)])
    with pytest.raises(ValueError, match='blocks'):
        assert_block_parity([row], [{**row, 'truth_pixels': 3}])
    pooled = {'tp_weight': 2., 'fp_weight': 5., 'truth_pixels': 9., 'emitted_pixels': 12}
    assert_pooled_parity(pooled, dict(pooled), 'test')
    with pytest.raises(ValueError, match='replay mismatch'):
        assert_pooled_parity(pooled, {**pooled, 'fp_weight': 5.01}, 'test')


def test_fixed_comparator_sources_and_contract_exist():
    msdb, ffl = validate_frozen_inputs()
    assert len(msdb['folds']) == len(ffl['folds']) == 4
    spec = contract({'experiment_spec': 'qpc1'})
    assert len(spec['features']) == 23
    assert 'ffl_confirm' in spec['required_positive_deltas']
    assert spec['support_px'] + 3 <= spec['guard_px']
