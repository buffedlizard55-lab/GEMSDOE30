"""No human override, no green format check masquerading as promotion."""
from copy import deepcopy
from gemsdoe30.readiness import assess, EXPECTED_FEATURES


def evidence():
    card = {'raster_sha256': 'synthetic', 'externally_assigned_lane_verified': True,
            'experiments_run': 1, 'experimental_elapsed_seconds': 10,
            'submission_name': 'synthetic-only', 'note': 'unit test',
            'historical_best_rerun': {'verified': True, 'evaluator_version': 'v',
                                      'protocol_version': 'p', 'candidate_beats_best_with_paired_ci': True}}
    arms = {name: {'label': 'HOLDOUT-DTI', 'value': .2, 'ci95': [.1, .3], 'withheld_positives': 40}
            for name in ('tdx6', 'physics3', 'core19')}
    features = [{'fold': f, 'features': [
        {'feature': name, 'raw_auc': .6, 'univariate_training_only_hgb_auc': .65,
         'alarm_above_0_90': False} for name in EXPECTED_FEATURES]} for f in range(4)]
    results = {'summary': {'arms': arms, 'evaluator_version': 'v', 'protocol_version': 'p',
                          'candidate_minus': {n: {'value': .05, 'ci95': [.01, .09]}
                                              for n in ('physics3', 'core19')}},
               'feature_canaries': features,
               'folds': [{'fold': f, 'dot_budget_each_arm': 10,
                          'arms': {name: {'emitted_pixels': 10} for name in arms}} for f in range(4)]}
    row = {'spearman_full_footprint': .1, 'candidate_fraction_within_3px_of_reference': .2,
           'correlation_duplicate': False, 'dot_duplicate': False, 'identical_inside_footprint': False}
    audit = {'comparisons': [row], 'errors': []}
    return card, results, audit


def decide(card, results, audit, *, complete=True, valid=True):
    return assess(card, results, format_passed=valid, hash_matches=valid,
                  surface_audit=audit, dots_audit=audit, registry={'complete': complete})


def gate(result, name):
    return next(g for g in result['gates'] if g['name'] == name)['status']


def test_research_promotion_does_not_select_or_approve_a_competition_slot():
    card, results, audit = evidence()
    r = decide(card, results, audit)
    assert r['research_verdict'] == 'promote'
    assert r['submission_approved'] is False and r['slot_selected'] is False


def test_unknown_inventory_and_missing_lane_are_not_passed():
    card, results, audit = evidence(); card.pop('externally_assigned_lane_verified')
    r = decide(card, results, audit, complete=False)
    assert r['download_ok'] and r['research_verdict'] == 'negative'
    assert gate(r, 'complete_parallel_registry') == 'unknown'
    assert gate(r, 'assigned_lane') == 'unknown'


def test_format_cannot_rescue_failed_holdout_and_missing_ci():
    card, results, audit = evidence()
    results['summary']['candidate_minus']['core19']['ci95'] = [-.1, .1]
    r = decide(card, results, audit)
    assert r['download_ok'] and r['research_verdict'] == 'negative'
    results['summary']['arms']['tdx6']['ci95'] = None
    assert gate(decide(card, results, audit), 'labelled_holdout_evidence') == 'failed'


def test_numeric_canary_overrides_false_alarm_boolean_and_duplicate_features_fail():
    card, results, audit = evidence()
    results['feature_canaries'][0]['features'][0]['raw_auc'] = .99
    assert gate(decide(card, results, audit), 'single_feature_leakage_canaries') == 'failed'
    card, results, audit = evidence()
    results['feature_canaries'][0]['features'][0] = deepcopy(results['feature_canaries'][0]['features'][1])
    assert gate(decide(card, results, audit), 'single_feature_leakage_canaries') == 'failed'


def test_numeric_novelty_overrides_mutable_boolean_and_count_shortfall_fails():
    card, results, audit = evidence()
    audit['comparisons'][0]['spearman_full_footprint'] = .91
    assert gate(decide(card, results, audit), 'surface_observed_registry') == 'failed'
    card, results, audit = evidence()
    audit['comparisons'][0]['candidate_fraction_within_3px_of_reference'] = .701
    assert gate(decide(card, results, audit), 'dots_observed_registry') == 'failed'
    card, results, audit = evidence()
    results['folds'][0]['arms']['tdx6']['emitted_pixels'] = 9
    assert gate(decide(card, results, audit), 'count_matched_construction') == 'failed'


def test_invalid_hash_budget_and_long_notes_do_not_release():
    card, results, audit = evidence()
    assert not decide(card, results, audit, valid=False)['download_ok']
    card['experiments_run'] = 4
    assert gate(decide(card, results, audit), 'experimental_budget') == 'failed'
    card['note'] = 'x' * 141
    assert not decide(card, results, audit)['download_ok']


def test_boolean_counts_and_nonstring_artifact_names_are_not_valid_evidence():
    card, results, audit = evidence(); card['experiments_run'] = True
    assert gate(decide(card, results, audit), 'experimental_budget') == 'failed'
    card, results, audit = evidence(); results['folds'][0]['dot_budget_each_arm'] = True
    for row in results['folds'][0]['arms'].values(): row['emitted_pixels'] = True
    assert gate(decide(card, results, audit), 'count_matched_construction') == 'failed'
    card, results, audit = evidence(); card['submission_name'] = 42
    assert not decide(card, results, audit)['download_ok']


def test_format_valid_duplicate_is_not_even_a_downloadable_research_release():
    card, results, audit = evidence()
    audit['comparisons'][0]['candidate_fraction_within_3px_of_reference'] = .71
    result = decide(card, results, audit)
    assert gate(result, 'file_contract') == 'passed'
    assert result['research_verdict'] == 'negative' and result['download_ok'] is False


def test_new_contract_requires_every_matched_control_and_all_28_canaries():
    from gemsdoe30.experiments import contract
    card, results, audit = evidence(); card['experiment_spec'] = 'tdxc2'
    spec = contract(card)
    results['summary']['arms'] = {name: deepcopy(next(iter(results['summary']['arms'].values()))) for name in spec['arms']}
    results['summary']['candidate_minus'] = {n: {'value': .05, 'ci95': [.01, .09]}
                                            for n in spec['arms'] if n != spec['candidate']}
    for fold in results['feature_canaries']:
        fold['features'] = [{'feature': name, 'raw_auc': .6, 'univariate_training_only_hgb_auc': .65,
                             'alarm_above_0_90': False} for name in spec['features']]
    for fold in results['folds']:
        fold['arms'] = {name: {'emitted_pixels': 10} for name in spec['arms']}
    assert decide(card, results, audit)['research_verdict'] == 'promote'
    results['summary']['candidate_minus'].pop('phase22')
    assert gate(decide(card, results, audit), 'paired_improvement') == 'failed'
    results['feature_canaries'][0]['features'].pop()
    assert gate(decide(card, results, audit), 'single_feature_leakage_canaries') == 'failed'


def test_private_artifact_receipts_cannot_imply_a_current_public_file_inspection():
    card, results, audit = evidence()
    result = assess(card, results, format_passed=True, hash_matches=True,
                    surface_audit=audit, dots_audit=audit, registry={'complete': True}, artifact_public=False)
    assert gate(result, 'file_contract') == 'unknown'
    assert not result['download_ok'] and result['research_verdict'] == 'negative'
