"""Fail-closed tests for the one-witness budget proof and current negative card."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

from gemsdoe30.novelty import dot_budget_bound
from gemsdoe30.submission import valid_template_mask
from scripts import verify_registry_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE, LATTICE = preflight.TEMPLATE, preflight.LATTICE
requires_mirrors = pytest.mark.skipif(not TEMPLATE.is_file() or not LATTICE.is_file(),
                                      reason="pinned template and registry witness required")


@requires_mirrors
def test_actual_lattice_bound_and_strict_threshold():
    with rasterio.open(TEMPLATE) as tpl, rasterio.open(LATTICE) as ref:
        assert (tpl.shape, tpl.crs, tpl.transform) == (ref.shape, ref.crs, ref.transform)
        mask, values = valid_template_mask(tpl, np), ref.read(1)
    b = dot_budget_bound(values, mask, 44090)
    assert b['footprint_pixels'] == 5_167_373
    assert b['reference_dots'] == 206_895
    assert b['covered_within_radius_pixels'] == 5_160_724
    assert b['uncovered_pixels'] == 6_649
    assert b['minimum_overlapping_dots'] == 37_441
    assert b['decision'] == 'duplicate-stop'
    assert b['first_provably_stopped_budget'] == 22_164
    assert dot_budget_bound(values, mask, 22_163)['decision'] == 'not-proven'
    assert dot_budget_bound(values, mask, 22_164)['decision'] == 'duplicate-stop'


def test_preflight_rejects_invalid_shape_budget_range_and_parameters():
    ref, mask = np.ones((5, 5)), np.ones((5, 5), dtype=bool)
    for bad in (0, -1, 26, 1.5, True):
        with pytest.raises(ValueError): dot_budget_bound(ref, mask, bad)
    for bad in (-0.1, 1.0, float('nan'), 'bad', True):
        with pytest.raises(ValueError): dot_budget_bound(ref, mask, 2, threshold=bad)
    for bad in (-1, float('inf'), 'bad', True):
        with pytest.raises(ValueError): dot_budget_bound(ref, mask, 2, radius_px=bad)
    with pytest.raises(ValueError): dot_budget_bound(ref, mask[:2], 1)
    with pytest.raises(ValueError): dot_budget_bound(ref, np.zeros_like(mask), 1)
    bad_ref = ref.copy(); bad_ref[0, 0] = 1.1
    with pytest.raises(ValueError): dot_budget_bound(bad_ref, mask, 1)


@requires_mirrors
def test_recomputes_exact_historical_candidate_and_refuses_promotion():
    result = preflight.verify()
    old = result['measurement']['previous_candidate']
    assert result['research_verdict'] == 'negative' and not result['ok_to_submit']
    assert old['matching_dots'] == 44_084
    assert old['comparison']['candidate_dots'] == 44_090
    assert old['comparison']['dot_duplicate']
    assert not old['published_format_validator_passed']
    assert old['published_failed_checks'] == ['null_outside_template_footprint']
    assert old['whole_array_finite_range_diagnostic_passed']
    p = subprocess.run([sys.executable, 'scripts/verify_registry_preflight.py', '--require-promote'],
                       cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 2 and 'VERIFIED NEGATIVE' in p.stdout


@requires_mirrors
def test_tampered_witness_or_saved_measurement_cannot_be_verified(tmp_path, monkeypatch):
    broken = tmp_path / 'reference.tif'
    broken.write_bytes(LATTICE.read_bytes() + b'tampered')
    with pytest.raises(ValueError, match='lattice SHA-256 or size mismatch'):
        preflight.inspect(lattice=broken)
    card = json.loads(preflight.CARD.read_text())
    card['registry']['measurement']['bound']['uncovered_pixels'] -= 1
    bad_card = tmp_path / 'card.json'; bad_card.write_text(json.dumps(card))
    monkeypatch.setattr(preflight, 'CARD', bad_card)
    with pytest.raises(ValueError, match='saved preflight measurement'):
        preflight.verify()


def test_float_tolerance_does_not_launder_integer_counts_or_fields():
    original = {'count': 44084, 'fraction': .9998639147198911, 'pass': False}
    rounded = copy.deepcopy(original); rounded['fraction'] += 1e-14
    assert preflight.same_measurement(rounded, original)
    rounded['count'] += 1
    assert not preflight.same_measurement(rounded, original)
    assert not preflight.same_measurement({'count': 44084}, original)
    bad_type = copy.deepcopy(original); bad_type['pass'] = 0
    assert not preflight.same_measurement(bad_type, original)


def test_nine_historical_selections_are_above_proven_budget_floor():
    f = json.loads((ROOT / 'docs/research/2026-10-26-csr/fleet-audit.json').read_text())
    c = json.loads(preflight.CARD.read_text())
    threshold = c['registry']['measurement']['bound']['first_provably_stopped_budget']
    assert len(f['rows']) == 9 and all(row['dots'] >= threshold for row in f['rows'])
    assert all(row['organizer_confirmed'] is None and row['leaderboard_estimate'] is None for row in f['rows'])
    assert c['raster_sha256'] is c['validator_output'] is c['submission_name'] is c['note'] is None
    assert c['new_holdout']['value'] is None and c['experiments_run'] == 0


def test_independent_integer_disk_clips_edges_without_wrap():
    reference = np.zeros((5, 8)); reference[0, 0] = 1
    footprint = np.ones_like(reference, dtype=bool)
    assert preflight.independent_three_pixel_coverage(reference, footprint) == 11
    footprint[1, 1] = False
    assert preflight.independent_three_pixel_coverage(reference, footprint) == 10
    assert preflight.independent_three_pixel_coverage(np.ones((1, 1)), np.ones((1, 1), bool)) == 1
    # Outside-footprint positives cannot create reference neighbourhoods.
    footprint[0, 0] = False
    assert preflight.independent_three_pixel_coverage(reference, footprint) == 0
