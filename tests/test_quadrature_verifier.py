import copy

import pytest

from gemsdoe30.readiness import assess
from scripts.verify_quadrature_phase_run import INVALID, audit_receipt, check_canaries


def fixture_audit(stage='surface'):
    reg = {'rasters': [{'path': 'bad.tif', 'sha256': INVALID}, {'path': 'ok.tif', 'sha256': 'x' * 64}]}
    started = {'registry_sha256': 'r' * 64}
    row = {'reference': 'ok.tif', 'reference_sha256': 'x' * 64, 'stage': stage,
           'spearman_full_footprint': .2, 'candidate_fraction_within_3px_of_reference': .5 if stage == 'dots' else None,
           'identical_inside_footprint': False, 'correlation_duplicate': False, 'dot_duplicate': False, 'undefined': False}
    audit = {'stage': stage, 'registry_sha256': 'r' * 64, 'template_sha256': 't' * 64,
             'registry_complete': False, 'submission_approved': False, 'candidate_sha256': 'c' * 64,
             'comparisons': [row], 'errors': ['bad.tif: non-finite values inside footprint'],
             'decision': 'blocked-incomplete-evidence'}
    return audit, reg, started


def test_novelty_receipt_unknown_not_passed():
    audit, reg, start = fixture_audit()
    assert audit_receipt(audit, reg, start, 't' * 64, 'surface') == 'blocked-incomplete-evidence'
    audit['errors'] = []
    with pytest.raises(ValueError, match='unexpected novelty error'):
        audit_receipt(audit, reg, start, 't' * 64, 'surface')


def test_verifier_catches_disguised_dot_duplicate():
    audit, reg, start = fixture_audit('dots')
    audit['comparisons'][0]['candidate_fraction_within_3px_of_reference'] = .71
    with pytest.raises(ValueError, match='dot flag'):
        audit_receipt(audit, reg, start, 't' * 64, 'dots')
    audit['comparisons'][0]['dot_duplicate'] = True
    with pytest.raises(ValueError, match='decision'):
        audit_receipt(audit, reg, start, 't' * 64, 'dots')
    audit['decision'] = 'duplicate-stop'
    assert audit_receipt(audit, reg, start, 't' * 64, 'dots') == 'duplicate-stop'


def test_canary_bidirectional_threshold_and_inventory():
    row = {'feature': 'x', 'raw_auc': .09, 'univariate_training_only_hgb_auc': .52,
           'alarm_above_0_90': True, 'heldout_positives': 3}
    folds = [{'fold': 0, 'features': [row]}]
    alarms, maximum = check_canaries(folds, ('x',), {0: 3}, complete=False)
    assert alarms == ['x'] and maximum == pytest.approx(.91)
    forged = copy.deepcopy(folds)
    forged[0]['features'][0]['alarm_above_0_90'] = False
    with pytest.raises(ValueError, match='contradicts'):
        check_canaries(forged, ('x',), {0: 3}, complete=False)
    with pytest.raises(ValueError, match='missing canary fold'):
        check_canaries(folds, ('x',), {0: 3}, complete=True)


def test_qpc_readiness_explains_exactly_the_three_preregistered_controls():
    ready = assess({'experiment_spec': 'qpc1'}, {}, format_passed=False, hash_matches=False,
                   surface_audit={}, dots_audit={}, registry={})
    detail = next(g['detail'] for g in ready['gates'] if g['name'] == 'paired_improvement')
    for name in ('persistence21', 'msdb_edge', 'ffl_confirm'):
        assert name in detail
    assert 'three preregistered controls' in detail and 'core19 is descriptive' in detail
