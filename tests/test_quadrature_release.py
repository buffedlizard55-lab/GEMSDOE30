"""Regression checks for the frozen QPC negative finding; never fit a model."""
import json
from pathlib import Path
import shutil

import pytest

from scripts.verify_quadrature_phase_run import REPORT, verify

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'data/raw/sample_submission.tif'
LABELS = ROOT / 'data/raw/labels.tif'
requires_mirrors = pytest.mark.skipif(not (TEMPLATE.is_file() and LABELS.is_file()), reason='pinned template/labels not restored')


def load(path):
    return json.loads(path.read_text())


def change(path, edit):
    value = load(path)
    edit(value)
    path.write_text(json.dumps(value, indent=2) + '\n')


@pytest.fixture
def copied_receipts(tmp_path):
    for path in REPORT.iterdir():
        if path.suffix in {'.json', '.md'}:
            shutil.copyfile(path, tmp_path / path.name)
    return tmp_path


@requires_mirrors
def test_frozen_qpc_result_is_verified_negative_and_never_downloadable():
    ready = verify(template=TEMPLATE)
    assert ready['research_verdict'] == 'negative'
    assert ready['reason'] == 'duplicate-stop at dots; no perturbation or publication'
    assert ready['download_ok'] is False and ready['submission_approved'] is False
    card = load(REPORT / 'run-card.json')
    assert card['published_tiff'] is None and card['validator_output'] is None
    assert card['registry']['dots']['max_fraction_within_3px'] > .70
    assert card['holdout']['candidate_minus']['ffl_confirm']['ci95'][1] < 0
    results = load(REPORT / 'results.json')
    assert sum(len(f['features']) for key in ('feature_canaries', 'ffl_feature_canaries') for f in results[key]) == 308


@requires_mirrors
def test_verifier_rejects_forged_submission_approval(copied_receipts):
    change(copied_receipts / 'run-card.json', lambda c: c.update(submission_approved=True))
    with pytest.raises(ValueError, match='score class'):
        verify(copied_receipts, TEMPLATE)


@requires_mirrors
def test_verifier_rejects_disguised_duplicate(copied_receipts):
    def falsify(a):
        hit = next(r for r in a['comparisons'] if r['dot_duplicate'])
        hit['dot_duplicate'] = False
    change(copied_receipts / 'novelty-dots.json', falsify)
    with pytest.raises(ValueError, match='dot flag'):
        verify(copied_receipts, TEMPLATE)


@requires_mirrors
def test_verifier_rejects_a_forged_pooled_score(copied_receipts):
    change(copied_receipts / 'results.json', lambda r: r['summary']['arms']['qpc23'].update(value=.9))
    with pytest.raises(ValueError, match='recomputed spatial-block bootstrap'):
        verify(copied_receipts, TEMPLATE)


def test_front_page_offers_only_the_earlier_negative_research_artifact():
    qpc = load(REPORT / 'run-card.json')
    gdx = load(ROOT / 'docs/research/2026-10-26-gdx/run-card.json')
    csr = load(ROOT / 'docs/research/2026-10-26-csr/run-card.json')
    assert qpc['published_tiff'] is None
    qpc_page = (ROOT / 'geothermal-quadrature-review.html').read_text()
    assert 'NOT APPROVED FOR SUBMISSION' in qpc_page
    assert gdx['published_tiff'] in qpc_page and 'previous' in qpc_page.lower()
    assert qpc['submission_name'] not in qpc_page
    assert '78.9159%' in qpc_page and '25 public open-PR heads' in qpc_page
    assert 'not independently reproduced or paired' in qpc_page
    for page in ('index.html', 'executive-summary.html'):
        text = (ROOT / page).read_text()
        assert 'NOT APPROVED FOR SUBMISSION' in text
        assert csr['published_tiff'] in text
        assert qpc['submission_name'] not in text  # do not offer stopped QPC as an upload name
        assert '78.9159%' in text and '25 public open-PR heads' in text
        assert 'not independently reproduced or paired' in text


def test_parallel_pr_observation_is_not_treated_as_matched_clearance():
    p = load(REPORT / 'parallel-inventory.json')
    assert p['pull_request'] == 41 and p['qpc_guard_px'] == [17] and p['pr41_guard_px'] == [20]
    assert p['same_visible_labels_and_train_masks'] is False and p['submission_approval'] is False
    assert 'not performed' in p['novelty_comparison_to_qpc']
    heads = load(REPORT / 'parallel-heads-inventory.json')
    assert heads['repositories_scanned'] == 9 and heads['count'] == len(heads['heads']) == 25
    assert heads['complete_parallel_registry'] is False
    assert all('not scanned or compared' in h['comparison_status'] for h in heads['heads'])
