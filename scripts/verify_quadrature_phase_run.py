#!/usr/bin/env python3
"""Recheck QPC-1's frozen evidence and negative decision without fitting or uploading.

CI can verify hash-bound pre-placement receipts; the ignored continuous surface
is reopened only when its bytes are still locally available. Stopped lanes are
valid negative findings, not permission to resume or claim uniqueness.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
from scipy.spatial import cKDTree
from gemsdoe30.experiments import CORE_FEATURES, contract
from gemsdoe30.holdout import EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION, spatial_bootstrap
from gemsdoe30.lidar_morphology import LIDAR_LAYERS
from gemsdoe30.msdb import MSDB_FEATURE_NAMES
from gemsdoe30.novelty import decision
from gemsdoe30.quadrature_phase import FEATURE_NAMES, GUARD_PX, SUPPORT_PX
from gemsdoe30.readiness import assess, with_current_inventory
from gemsdoe30.submission import valid_template_mask, validate_submission_file
from scripts.verify_current_run import check_equal

REPORT = ROOT / 'docs/research/2026-10-26-qpc'
INVALID = '774c7c5aa3784d7c52dc67870e1cc8b0e0a34d1697092ad9f3b08c33dcaf2546'
MSDB = ROOT / 'docs/research/msdb-piedmont/results.json'
FFL = ROOT / 'docs/research/2026-10-26-fflidar/results-confirmation.json'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def audit_receipt(audit, registry, started, template_sha, stage, expected_candidate=None):
    require(audit.get('stage') == stage and audit.get('registry_sha256') == started['registry_sha256']
            and audit.get('template_sha256') == template_sha and audit.get('registry_complete') is False
            and audit.get('submission_approved') is False, 'novelty stage/grid/registry binding failed')
    if expected_candidate is not None:
        require(audit.get('candidate_sha256') == expected_candidate, 'novelty candidate hash mismatch')
    require(isinstance(audit.get('candidate_sha256'), str) and len(audit['candidate_sha256']) == 64,
            'novelty candidate hash missing')
    expected = {r['sha256']: r for r in registry['rasters']}
    rows = audit.get('comparisons', [])
    observed = {r.get('reference_sha256') for r in rows}
    require(len(expected) == len(registry['rasters']) and len(observed) == len(rows),
            'duplicate registry identities or comparison rows')
    require(observed == set(expected) - {INVALID}, 'comparison coverage / malformed reference identity changed')
    errors = audit.get('errors', [])
    bad_path = expected[INVALID]['path']
    require(len(errors) == 1 and errors[0].startswith(bad_path + ':')
            and 'non-finite values inside footprint' in errors[0], 'unexpected novelty error or missing malformed reference')
    for row in rows:
        ref = expected[row['reference_sha256']]
        require(row.get('reference') == ref['path'] and row.get('stage') == stage,
                'novelty reference path or stage mismatch')
        rho = row.get('spearman_full_footprint')
        overlap = row.get('candidate_fraction_within_3px_of_reference')
        require(isinstance(rho, (int, float)) and math.isfinite(rho) and -1 <= rho <= 1
                and not row.get('undefined'), 'undefined novelty correlation')
        require(row.get('correlation_duplicate') == (rho > .90), 'novelty correlation flag disagrees with value')
        if stage == 'dots':
            require(isinstance(overlap, (int, float)) and math.isfinite(overlap) and 0 <= overlap <= 1,
                    'undefined directional dot overlap')
        else:
            require(overlap is None, 'surface receipt substituted a dot statistic')
        require(row.get('dot_duplicate') == (stage == 'dots' and overlap is not None and overlap > .70),
                'novelty dot flag disagrees with value')
    require(audit.get('decision') == decision(rows, stage=stage, registry_complete=False),
            'novelty decision disagrees with rows')
    return audit['decision']


def inspect_saved_surface(saved, template, expected_sha):
    """When available, re-open the actual continuous pre-placement score surface."""
    saved = Path(saved)
    if not saved.is_file():
        return False  # CI verifies the historical receipt, not unavailable bytes.
    require(sha(saved) == expected_sha, 'saved continuous surface hash changed')
    with rasterio.open(saved) as source, rasterio.open(template) as tpl:
        require(source.count == 1 and (source.shape, source.crs, source.transform) == (tpl.shape, tpl.crs, tpl.transform),
                'saved continuous surface grid mismatch')
        values = source.read(1)
        valid = valid_template_mask(tpl, np)
    inside = values[valid]
    require(np.isfinite(inside).all() and np.all((inside >= 0) & (inside <= 1))
            and len(np.unique(inside[::4096])) > 2 and np.isnan(values[~valid]).all(),
            'saved pre-placement surface is not a finite, non-binary probability surface')
    return True


def check_canaries(folds, names, truth_by_fold, *, complete):
    require(len({f['fold'] for f in folds}) == len(folds) and all(f['fold'] in range(4) for f in folds),
            'invalid canary fold inventory')
    if complete:
        require({f['fold'] for f in folds} == set(range(4)), 'missing canary fold')
    alarms = []
    max_auc = .5
    for fold in folds:
        features = fold['features']
        require(len(features) == len(names) and {r['feature'] for r in features} == set(names),
                'missing/duplicate individual-feature canary')
        for row in features:
            raw, uni = row['raw_auc'], row['univariate_training_only_hgb_auc']
            require(all(isinstance(x, (int, float)) and math.isfinite(x) and 0 <= x <= 1 for x in (raw, uni)),
                    'invalid canary AUC')
            if truth_by_fold is not None:
                require(row['heldout_positives'] == truth_by_fold[fold['fold']], 'canary held-out truth mismatch')
            maximum = max(raw, 1 - raw, uni, 1 - uni)
            require(row['alarm_above_0_90'] == (maximum > .90), 'canary alarm contradicts AUC')
            max_auc = max(max_auc, maximum)
            if maximum > .90:
                alarms.append(row['feature'])
    return alarms, max_auc


def validate_results(results, started, msdb, ffl):
    require(results.get('experiment_spec') == 'qpc1' and results.get('preregistration_sha256') == started['preregistration_sha256'],
            'results unbound to frozen plan')
    spec = contract({'experiment_spec': 'qpc1'})
    require(set(results['bootstrap_sufficient_statistics']) == set(spec['arms']), 'wrong bootstrap arms')
    summary = spatial_bootstrap(results['bootstrap_sufficient_statistics'], candidate='qpc23', replicates=2000, seed=3071)
    check_equal(summary, results['summary'], 'recomputed spatial-block bootstrap')
    require(summary['evaluator_version'] == EVALUATOR_VERSION and summary['protocol_version'] == SEGMENT_PROTOCOL_VERSION,
            'unknown evaluator/protocol')
    folds = results['folds']
    require(len(folds) == 4 and {f['fold'] for f in folds} == set(range(4))
            and sum(f['withheld_positives'] for f in folds) == 60988, 'incomplete fault holdout')
    hidden = [h for f in folds for h in f['hidden_component_ids']]
    require(len(hidden) == len(set(hidden)), 'a whole fault component was withheld twice')
    truth_by_fold = {f['fold']: f['withheld_positives'] for f in folds}
    identity_keys = ('protocol_version', 'fold', 'buffer_px', 'metric_halo_px', 'withheld_components',
                     'withheld_positives', 'visible_positives', 'guard_positives_not_truth',
                     'training_pixels', 'scored_pixels', 'hidden_component_ids', 'dot_budget_each_arm')
    for fold in folds:
        n = fold['fold']
        check_equal({k: fold[k] for k in identity_keys}, {k: msdb['folds'][n][k] for k in identity_keys},
                    f'archived MSDB fold {n} identity')
        require(fold['buffer_px'] == GUARD_PX and fold['metric_halo_px'] == 3
                and set(fold['arms']) == set(spec['arms']), 'fold guard/arm mismatch')
        for name, row in fold['arms'].items():
            require(row['emitted_pixels'] == fold['dot_budget_each_arm']
                    and row['truth_pixels'] == fold['withheld_positives'], 'unequal arm budget or truth')
        for key in ('tp_weight', 'fp_weight', 'truth_pixels', 'emitted_pixels'):
            require(abs(fold['arms']['ffl_confirm'][key] - ffl['folds'][n]['arms']['fusion_edge'][key]) <= 1e-6,
                    f'FFL confirmation fold {n} {key} did not reproduce')
        check_equal(fold['arms']['msdb_edge'], msdb['folds'][n]['arms']['msdb_edge'], f'MSDB fold {n}')
    check_equal(results['bootstrap_sufficient_statistics']['msdb_edge'],
                msdb['bootstrap_sufficient_statistics']['msdb_edge'], 'archived MSDB blocks')
    for name in spec['arms']:
        for key in ('tp_weight', 'fp_weight', 'truth_pixels'):
            require(abs(sum(b[key] for b in results['bootstrap_sufficient_statistics'][name])
                        - sum(f['arms'][name][key] for f in folds)) < 1e-7, 'fold/block pooled sum mismatch')
    alarms, candidate_auc = check_canaries(results['feature_canaries'], spec['features'], truth_by_fold, complete=True)
    baseline_names = CORE_FEATURES + MSDB_FEATURE_NAMES + LIDAR_LAYERS
    other_alarms, ffl_auc = check_canaries(results['ffl_feature_canaries'], baseline_names, truth_by_fold, complete=True)
    require(not alarms and not other_alarms, 'a feature-alone leakage canary exceeded 0.90')
    require(results.get('strongest_replay_matches_receipt') is True and results.get('msdb_archive_block_parity') is True,
            'comparator parity flags absent')
    wins = all(summary['candidate_minus'][n]['ci95'][0] > 0 for n in spec['required_positive_deltas'])
    require(results.get('scientific_gate_passed') == wins, 'preregistered paired gate misreported')
    return summary, max(candidate_auc, ffl_auc)


def verify(directory=REPORT, template=None):
    directory = Path(directory)
    template = Path(template or ROOT / 'data/raw/sample_submission.tif')
    started, card = load(directory / 'started.json'), load(directory / 'run-card.json')
    require(started['preregistration_sha256'] == sha(directory / 'preregistration.md')
            and started['registry_sha256'] == sha(directory / 'registry.json')
            and started['runner_sha256'] == sha(ROOT / 'scripts/run_quadrature_phase.py')
            and started['transform_sha256'] == sha(ROOT / 'src/gemsdoe30/quadrature_phase.py'),
            'frozen source / runner / transform hash changed')
    require(started.get('externally_assigned_lane_verified') is False and started.get('experiment_cap') == 3
            and 0 < started['max_seconds'] <= 7200, 'frozen lane assignment/budget incorrect')
    start, end = datetime.fromisoformat(started['started_utc']), datetime.fromisoformat(card['created_utc'])
    require(0 < card['experimental_elapsed_seconds'] <= started['max_seconds'] <= 7200
            and abs((end - start).total_seconds() - card['experimental_elapsed_seconds']) < 5
            and 0 < card['experiments_run'] <= card['experiment_cap'] == 3, 'lane timer/budget mismatch')
    require(card.get('experiment_spec') == 'qpc1' and card.get('verdict') == 'negative'
            and all(card.get(k) is False for k in ('ok_to_submit', 'submission_approved', 'slot_selected'))
            and card.get('organizer_score') is None and card.get('leaderboard_estimate') is None
            and 0 < len(card.get('note', '')) <= 140, 'decision or score class incorrectly upgraded')
    registry = load(directory / 'registry.json')
    require(registry.get('complete') is False, 'private/parallel registry cannot be declared complete')
    template_sha = sha(template)
    cache_path, feature_path = directory / 'cache-verification.json', directory / 'feature-receipt.json'
    if cache_path.is_file():
        cache = load(cache_path)
        require(cache.get('all_cells_match_raw_sources') is True and cache.get('organizer_authenticated') is False
                and cache['raw_source_sha256']['sample_submission'] == template_sha, 'cache/source identity invalid')
    if feature_path.is_file():
        feature = load(feature_path)
        require(feature['transform_sha256'] == started['transform_sha256']
                and feature['feature_names'] == list(CORE_FEATURES + FEATURE_NAMES)
                and feature['physical_support_px'] == SUPPORT_PX and feature['guard_px'] == GUARD_PX
                and SUPPORT_PX + 3 <= GUARD_PX and feature['catalogue_or_template_values_used_as_features'] is False,
                'feature/support contract mismatch')
        feature_file = ROOT / 'outputs/qpc1/qpc-features.npy'
        if feature_file.is_file():
            require(sha(feature_file) == feature['derived_array_sha256'], 'saved QPC feature array changed')
    surface_path, dots_path = directory / 'novelty-surface.json', directory / 'novelty-dots.json'
    surface = load(surface_path) if surface_path.is_file() else None
    dots = load(dots_path) if dots_path.is_file() else None
    saved_surface_reopened = False
    if surface:
        audit_receipt(surface, registry, started, template_sha, 'surface', card.get('surface_sha256'))
        saved_surface_reopened = inspect_saved_surface(ROOT / 'outputs/qpc1/qpc1-preplacement-surface.tif',
                                                       template, surface['candidate_sha256'])
    if dots:
        require(surface is not None, 'dots cannot be audited before surface')
        audit_receipt(dots, registry, started, template_sha, 'dots', card.get('raster_sha256'))
        require(surface['candidate_sha256'] != dots['candidate_sha256'], 'binary dots substituted for pre-placement surface')
    results_path = directory / 'results.json'
    results = load(results_path) if results_path.is_file() else None
    summary = None
    if results:
        require(sha(MSDB) == 'aa303c861dcaea1e3ccceb5f143f0df1b1e2564255e93795bee69fd3f5087842'
                and sha(FFL) == '6d310609524ec5d4ff0e129db6354a7731dedc1fb9c902d4be619a324f1e4b99',
                'historical comparator receipt changed')
        summary, max_auc = validate_results(results, started, load(MSDB), load(FFL))
        h = card['holdout']
        check_equal({k: h[k] for k in summary['arms']['qpc23']}, summary['arms']['qpc23'], 'card candidate HOLDOUT-DTI')
        check_equal(h['comparators'], {k: v for k, v in summary['arms'].items() if k != 'qpc23'}, 'card comparator HOLDOUT-DTI')
        check_equal(h['candidate_minus'], summary['candidate_minus'], 'card paired deltas')
    else:
        require(card['holdout']['value'] is None, 'holdout value claimed without pooled evidence')
    if not card.get('published_tiff'):
        require(card.get('download_ok') is False and (directory / 'failure.json').is_file(),
                'stopped lane published or lacks stop receipt')
        failure = load(directory / 'failure.json')
        require(failure['reason'] == card['reason'] and failure['no_resume'] is True, 'stop receipt mismatch')
        if card['reason'].startswith('duplicate-stop'):
            require(any(a and a['decision'] == 'duplicate-stop' for a in (surface, dots)),
                    'duplicate stop lacks an auditable duplicate')
        if 'leakage-canary alarm' in card['reason']:
            part = load(directory / 'canaries-partial.json')
            alarms, _ = check_canaries(part['candidate'], CORE_FEATURES + FEATURE_NAMES, None, complete=False)
            extra, _ = check_canaries(part['ffl'], CORE_FEATURES + MSDB_FEATURE_NAMES + LIDAR_LAYERS, None, complete=False)
            require(alarms or extra, 'leakage stop lacks an alarm')
        return {'research_verdict': 'negative', 'download_ok': False, 'submission_approved': False,
                'slot_selected': False, 'reason': card['reason'], 'global_uniqueness': 'unknown',
                'saved_surface_reopened': saved_surface_reopened}
    require(results and surface and dots and surface['decision'] != 'duplicate-stop' and dots['decision'] != 'duplicate-stop',
            'published file lacks required scientific or novelty receipts')
    raster = (ROOT / card['published_tiff']).resolve()
    require(raster.is_relative_to(ROOT / 'docs') and raster.stem == card['submission_name']
            and sha(raster) == card['raster_sha256'], 'published raster identity mismatch')
    sidecar = load(raster.with_suffix('.json'))
    require(sidecar.get('output_sha256') == card['raster_sha256'] and sidecar.get('run_name') == card['submission_name']
            and sidecar.get('note') == card['note']
            and all(sidecar.get(k) is False for k in ('ok_to_submit', 'submission_approved', 'slot_selected')),
            'download sidecar identity/decision mismatch')
    report = validate_submission_file(raster, template)
    require(report.passed, 'shared submission format check failed')
    check_equal(report.to_dict()['checks'], load(directory / 'validation.json')['checks'], 'stored/current format checks')
    with rasterio.open(raster) as ds, rasterio.open(template) as tpl:
        a = ds.read(1)
        valid = valid_template_mask(tpl, np)
        require(ds.dtypes == ('float32',) and np.isfinite(a[valid]).all() and np.isnan(a[~valid]).all()
                and set(np.unique(a[valid])) == {0, 1} and np.count_nonzero(a[valid]) == 44090,
                'binary [0,1] raster/footprint/dot-count contract failed')
    label_path = ROOT / 'data/raw/labels.tif'
    require(sha(label_path) == cache['raw_source_sha256']['labels'], 'catalogue source hash mismatch')
    with rasterio.open(label_path) as source, rasterio.open(template) as tpl:
        require((source.shape, source.crs, source.transform) == (tpl.shape, tpl.crs, tpl.transform), 'catalogue grid mismatch')
        catalogue = (source.read(1) > .5) & valid
    xy = np.column_stack(np.nonzero((a > 0) & valid))
    require(np.count_nonzero(catalogue) == 60988 and not np.any((a > 0) & catalogue)
            and cKDTree(xy).query(xy, k=2)[0][:, 1].min() >= 3, 'pixel-exact catalogue mask / dot spacing failed')
    validator = card['validator_output']
    require(validator['status'] == 'passed' and all(validator[k] is True for k in ('no_nan_inside_footprint',
            'values_in_0_1', 'crs_match', 'shape_match', 'transform_match', 'single_float32_band',
            'nan_nodata_outside_footprint')) and validator['positive_catalogue_pixels'] == 0
            and validator['emitted_dots'] == 44090 and validator['organizer_acceptance_confirmed'] is False,
            'card validator contradicts reopened TIFF')
    ready = assess(card, results, format_passed=True, hash_matches=True,
                   surface_audit=surface, dots_audit=dots, registry=registry)
    check_equal(ready, load(directory / 'readiness.json'), 'readiness decision')
    require(card['download_ok'] is ready['download_ok'] is True and ready['research_verdict'] == 'negative',
            'invalid publication or research promotion')
    known = {r['sha256'] for r in registry['rasters']} | {card['raster_sha256']}
    current = {sha(p) for p in (ROOT / 'docs').rglob('*') if p.is_file() and p.suffix.lower() in ('.tif', '.tiff')}
    ready = with_current_inventory(ready, recorded_hashes=known, current_hashes=current)
    ready.update(global_uniqueness='unknown', max_canary_auc=max_auc,
                 verification_scope='CI verifies frozen continuous-surface receipt, not unavailable original bytes',
                 saved_surface_reopened=saved_surface_reopened)
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=REPORT)
    parser.add_argument('--template', type=Path, default=ROOT / 'data/raw/sample_submission.tif')
    parser.add_argument('--require-promote', action='store_true')
    args = parser.parse_args()
    try:
        ready = verify(args.directory, args.template)
    except (ValueError, KeyError, OSError, TypeError, AssertionError) as exc:
        print(f'QPC verification failed: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(ready, indent=2))
    return 2 if args.require_promote and ready['research_verdict'] != 'promote' else 0


if __name__ == '__main__':
    raise SystemExit(main())
