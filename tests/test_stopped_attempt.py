"""A stopped, format-valid duplicate can never become a public submission."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/research/texture-controls"


def load(path):
    return json.loads(path.read_text())


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    from scripts import verify_stopped_attempt as verifier
    directory = tmp_path / 'docs/research/texture-controls'
    shutil.copytree(REPORT, directory)
    for name in ('texture.py', 'texture_controls.py'):
        dest = tmp_path / 'src/gemsdoe30' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / 'src/gemsdoe30' / name, dest)
    template = tmp_path / 'template.tif'
    template.write_bytes(b'synthetic template identity, no raster IO in receipt-only checks')
    for row in load(directory / 'registry-parallel-addendum.json')['rasters']:
        dest = tmp_path / row['path']; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / row['path'], dest)
    for name in ('novelty-surface.json', 'novelty-dots.json', 'novelty-parallel-surface.json', 'novelty-parallel-dots.json'):
        p = directory / name; r = load(p)
        r['template_sha256'] = hashlib.sha256(template.read_bytes()).hexdigest(); dump(p, r)
    monkeypatch.setattr(verifier, 'ROOT', tmp_path)
    return verifier, directory, template, tmp_path


def test_receipt_verification_is_explicitly_not_private_byte_reinspection(isolated):
    verifier, directory, template, _ = isolated
    r = verifier.verify(directory, template)
    assert r['research_verdict'] == 'negative' and not r['download_ok']
    assert not r['submission_approved'] and not r['slot_selected']
    assert r['recorded_local_validation']['status'] == 'passed'
    assert r['recorded_local_validation']['current_bytes_reopened'] is False
    assert r['observed_registry']['dots']['status'] == 'failed'


@pytest.mark.parametrize('field,value', [('download_ok', True), ('submission_approved', True),
                                        ('slot_selected', True), ('verdict', 'promote'),
                                        ('published_tiff', 'docs/downloads/forbidden.tif')])
def test_no_boolean_or_publication_override_for_a_duplicate(isolated, field, value):
    verifier, directory, template, _ = isolated
    p = directory / 'run-card.json'; r = load(p); r[field] = value; dump(p, r)
    with pytest.raises(ValueError, match='remain unpublished'):
        verifier.verify(directory, template, write=True)


def test_all_paired_intervals_are_recomputed_not_trusted_from_the_card(isolated):
    verifier, directory, template, _ = isolated
    p = directory / 'run-card.json'; r = load(p)
    r['holdout']['candidate_minus']['phase22']['ci95'] = [.01, .03]; dump(p, r)
    with pytest.raises(ValueError, match='numeric mismatch'):
        verifier.verify(directory, template)


def test_canary_alarm_cannot_be_hidden_by_an_alarm_false_flag(isolated):
    verifier, directory, template, _ = isolated
    p = directory / 'results.json'; r = load(p)
    r['feature_canaries'][0]['features'][0]['univariate_training_only_hgb_auc'] = .99; dump(p, r)
    with pytest.raises(ValueError, match='canary boolean'):
        verifier.verify(directory, template)


def test_elapsed_budget_is_bound_to_the_original_start_and_stop(isolated):
    verifier, directory, template, _ = isolated
    p = directory / 'run-card.json'; r = load(p); r['experimental_elapsed_seconds'] = 1.; dump(p, r)
    with pytest.raises(ValueError, match='elapsed'):
        verifier.verify(directory, template)


def test_changed_original_transform_and_guard_are_rejected(isolated):
    verifier, directory, template, root = isolated
    source = root / 'src/gemsdoe30/texture.py'; source.write_text(source.read_text() + '\n# altered parent\n')
    with pytest.raises(ValueError, match='transform/source'):
        verifier.verify(directory, template)


def test_repeated_reference_rows_cannot_stand_in_for_missing_identities(isolated):
    verifier, directory, template, _ = isolated
    p = directory / 'novelty-dots.json'; r = load(p)
    r['comparisons'][1] = deepcopy(r['comparisons'][0]); dump(p, r)
    with pytest.raises(ValueError, match='inventory'):
        verifier.verify(directory, template)


def test_duplicate_stop_requires_numeric_evidence_not_an_unverified_flag(isolated):
    verifier, directory, template, _ = isolated
    for name in ('novelty-dots.json', 'novelty-parallel-dots.json'):
        p = directory / name; r = load(p)
        r['errors'] = []
        for row in r['comparisons']:
            row['candidate_fraction_within_3px_of_reference'] = .2
            row['spearman_full_footprint'] = .1
            row['identical_inside_footprint'] = False
            row.pop('undefined', None)
        dump(p, r)
    p = directory / 'run-card.json'; c = load(p)
    c['registry']['dots']['max_fraction_within_3px'] = .2
    c['registry']['dots']['max_spearman'] = .1
    c['additional_novelty_evidence']['combined_observed_registry']['dots'].update(
        max_fraction_within_3px=.2, max_spearman=.1, status='passed')
    dump(p, c)
    with pytest.raises(ValueError, match='numeric duplicate'):
        verifier.verify(directory, template, write=True)


def test_source_scientific_result_reproduces_the_old_comparator_exactly():
    latest = load(REPORT / 'results.json')['summary']['arms']['core19']
    original = load(ROOT / 'docs/research/texture-displacement/results.json')['summary']['arms']['core19']
    assert latest == original
    summary = load(REPORT / 'results.json')['summary']
    assert all(row['ci95'][0] < 0 < row['ci95'][1] for row in summary['candidate_minus'].values())


def test_no_new_tiff_was_added_to_downloads_and_stopped_hash_is_not_public():
    card = load(REPORT / 'run-card.json')
    for path in (ROOT / 'docs/downloads').glob('*.tif'):
        assert hashlib.sha256(path.read_bytes()).hexdigest() != card['raster_sha256']
        assert path.stem != card['submission_name']
    assert card['published_tiff'] is None
    assert card['artifact_path'].startswith('outputs/')


def test_rerun_preflight_preserves_all_frozen_scientific_receipts():
    # The runner must refuse before its exception logger can overwrite the old
    # failure timestamp. This is a no-model preflight, not a second experiment.
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in REPORT.glob('*.json')}
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_texture_controls.py')],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 2 and 'frozen execution already exists' in result.stderr
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in REPORT.glob('*.json')}


def test_failed_write_does_not_modify_the_canonical_stopped_decision(isolated):
    verifier, directory, template, _ = isolated
    before = (directory / 'readiness.json').read_bytes()
    p = directory / 'results.json'; r = load(p)
    r['summary']['candidate_minus']['core19']['ci95'] = [.1, .2]; dump(p, r)
    with pytest.raises(ValueError):
        verifier.verify(directory, template, write=True)
    assert (directory / 'readiness.json').read_bytes() == before


def test_nan_canary_cannot_be_reported_as_a_clean_check(isolated):
    verifier, directory, template, _ = isolated
    p = directory / 'results.json'; r = load(p)
    r['feature_canaries'][0]['features'][0]['raw_auc'] = float('nan'); dump(p, r)
    with pytest.raises(ValueError, match='finite'):
        verifier.verify(directory, template, write=True)


def test_optional_private_byte_failure_happens_before_any_canonical_write(isolated):
    verifier, directory, template, _ = isolated
    before = (directory / 'readiness.json').read_bytes()
    with pytest.raises(OSError):
        verifier.verify(directory, template, write=True, inspect_quarantine=True)
    assert (directory / 'readiness.json').read_bytes() == before


def test_stopped_bytes_cannot_be_published_even_under_another_download_name(isolated):
    verifier, directory, template, root = isolated
    data = b'synthetic stopped bytes; no real raster is required for this publication-deny test'
    digest = hashlib.sha256(data).hexdigest()
    for name in ('results.json', 'run-card.json'):
        p = directory / name; r = load(p); r['raster_sha256'] = digest; dump(p, r)
    for name in ('novelty-dots.json', 'novelty-parallel-dots.json'):
        p = directory / name; r = load(p); r['candidate_sha256'] = digest; dump(p, r)
    p = directory / 'validation.json'; r = load(p); r['raster_sha256'] = digest; dump(p, r)
    p = directory / 'run-card.json'; r = load(p)
    r['recorded_validation_sha256'] = hashlib.sha256((directory / 'validation.json').read_bytes()).hexdigest(); dump(p, r)
    download = root / 'docs/downloads/renamed-duplicate.tif'
    download.parent.mkdir(parents=True, exist_ok=True); download.write_bytes(data)
    with pytest.raises(ValueError, match='published under a download name'):
        verifier.verify(directory, template, write=True)


def test_validator_summary_cannot_be_edited_independently_of_its_bound_receipt(isolated):
    verifier, directory, template, _ = isolated
    p = directory / 'run-card.json'; r = load(p); r['validator_output']['emitted_dots'] = 1; dump(p, r)
    with pytest.raises(ValueError, match='validator'):
        verifier.verify(directory, template)


def test_late_arrivals_are_checked_without_rewriting_the_original_snapshot(isolated):
    verifier, directory, template, _ = isolated
    original = (directory / 'registry.json').read_bytes()
    result = verifier.verify(directory, template)
    # 164 frozen + 2 S20 arrivals + 1 MSDB-1v2 + 1 PTA-1 = 168 total observed entries.
    assert result['observed_registry']['dots']['registry_entries_compared'] == 168
    assert (directory / 'registry.json').read_bytes() == original
    (directory / 'registry-parallel-addendum.json').unlink()
    with pytest.raises(ValueError, match='late-registry audit'):
        verifier.verify(directory, template)


@pytest.mark.parametrize('mutation', ['candidate', 'template', 'reference'])
def test_late_receipts_bind_saved_bytes_template_and_every_reference(isolated, mutation):
    verifier, directory, template, _ = isolated
    path = directory / 'novelty-parallel-dots.json'
    report = load(path)
    if mutation == 'candidate':
        report['candidate_sha256'] = '0' * 64
    elif mutation == 'template':
        report['template_sha256'] = '0' * 64
    else:
        report['comparisons'][0]['reference_sha256'] = '0' * 64
    dump(path, report)
    with pytest.raises(ValueError, match='post-stop novelty'):
        verifier.verify(directory, template)
