"""Exact, footprint-aware duplicate diagnostics; never a performance certificate.

Use before placement (continuous surfaces) and after placement (dots). A changed
filename, encoding, or hash is not scientific novelty. Undefined correlations
fail closed, including constant surfaces and empty supports.
"""
from __future__ import annotations

from fractions import Fraction
import math
from numbers import Real

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import rankdata


def dot_budget_bound(reference, footprint, budget, *, radius_px=3.0, threshold=0.70):
    """Prove a directional overlap STOP before a candidate is produced.

    If only ``U`` footprint cells are farther than ``radius_px`` from a
    reference dot, any ``budget`` distinct candidate dots must have at least
    ``max(0, budget - U)`` dots inside that reference's neighbourhood. This is
    a necessary bound, not a novelty test: no proof of a STOP is *not* a pass.
    The reference support is defined by its positive in-footprint values, the
    same definition used by :func:`compare`. No candidates are constructed.
    """
    ref = np.asarray(reference)
    mask = np.asarray(footprint, dtype=bool)
    if ref.ndim != 2 or ref.shape != mask.shape or not mask.any():
        raise ValueError('reference and nonempty footprint must be same-shaped 2D arrays')
    inside = ref[mask]
    if not np.isfinite(inside).all() or np.any((inside < 0) | (inside > 1)):
        raise ValueError('reference must be finite and in [0, 1] throughout the footprint')
    if isinstance(budget, bool) or not isinstance(budget, (int, np.integer)):
        raise ValueError('budget must be an integer number of distinct dots')
    n = int(mask.sum())
    if budget < 1 or budget > n:
        raise ValueError('budget must be between one and the footprint pixel count')
    if (isinstance(radius_px, (bool, np.bool_)) or not isinstance(radius_px, Real)
            or not math.isfinite(radius_px) or radius_px < 0
            or isinstance(threshold, (bool, np.bool_)) or not isinstance(threshold, Real)
            or not math.isfinite(threshold) or not 0 <= threshold < 1):
        raise ValueError('radius must be finite and nonnegative; threshold must be in [0, 1)')
    dots = mask & (ref > 0)
    if not dots.any():
        raise ValueError('reference has no in-footprint positive support')
    # EDT uses exact Euclidean pixel geometry; no edge wrapping or approximated
    # square dilation. Restrict support AND the count to the template footprint.
    distance = distance_transform_edt(~dots)
    covered = int(np.count_nonzero(mask & (distance <= radius_px)))
    uncovered = n - covered
    minimum = max(0, int(budget) - uncovered)
    # Compare integers rather than rounded floating-point percentages. At
    # exactly 70% the requested strictly-greater-than rule does not stop.
    limit = Fraction(str(threshold))
    stop = minimum * limit.denominator > int(budget) * limit.numerator
    first = (uncovered * limit.denominator // (limit.denominator - limit.numerator)) + 1
    return {
        'reference_dots': int(dots.sum()),
        'footprint_pixels': n,
        'covered_within_radius_pixels': covered,
        'uncovered_pixels': uncovered,
        'radius_px': float(radius_px),
        'threshold': float(threshold),
        'candidate_dot_budget': int(budget),
        'minimum_overlapping_dots': minimum,
        'minimum_fraction_within_radius': minimum / int(budget),
        'first_provably_stopped_budget': first if first <= n else None,
        'decision': 'duplicate-stop' if stop else 'not-proven',
        'scope': 'one-reference lower bound; not a complete novelty or submission approval',
    }


def rank_cache(candidate, footprint):
    """Reuse the exact full-footprint candidate ranks across a large registry."""
    values = np.asarray(candidate)[np.asarray(footprint, dtype=bool)]
    if not values.size or not np.isfinite(values).all():
        raise ValueError('finite, nonempty candidate footprint required')
    ranks = rankdata(values).astype(np.float64)
    ranks -= ranks.mean()
    return ranks, float(np.sqrt(np.dot(ranks, ranks)))


def compare(candidate, reference, footprint, *, stage='dots', cached_ranks=None):
    """Full-footprint Spearman and directional dot overlap (Euclidean <=3 px).

    Positive values define dots; this definition is meaningful for sparse
    emission rasters, not arbitrary dense probability surfaces. Surface-stage
    decisions use correlation only. Arrays must already share a verified grid.
    """
    if stage not in ('surface', 'dots'):
        raise ValueError('stage must be surface or dots')
    a, b = np.asarray(candidate), np.asarray(reference)
    mask = np.asarray(footprint, dtype=bool)
    if a.ndim != 2 or a.shape != b.shape or a.shape != mask.shape or not mask.any():
        raise ValueError('nonempty, same-shaped 2D arrays and footprint required')
    if not (np.isfinite(a[mask]).all() and np.isfinite(b[mask]).all()):
        raise ValueError('non-finite values inside footprint')
    av, bv = a[mask], b[mask]
    constant = np.ptp(av) == 0 or np.ptp(bv) == 0
    rho = None
    if not constant:
        ar, an = rank_cache(a, mask) if cached_ranks is None else cached_ranks
        # Most registered outputs are binary dots. Their average-tie ranks
        # have a closed form, avoiding hundreds of expensive full-grid sorts.
        # This is algebraically the same full-footprint Spearman statistic;
        # arbitrary-valued rasters still use the general rankdata path.
        binary = np.all((bv == 0) | (bv == 1))
        if binary:
            positives = bv == 1
            n1 = int(np.count_nonzero(positives))
            n0 = len(bv) - n1
            if an > 0 and n0 and n1:
                numer = float(np.sum(ar, where=positives, dtype=np.float64)) * np.sqrt(float(len(bv)))
                denom = an * np.sqrt(float(n0) * float(n1))
                rho = float(np.clip(numer / denom, -1.0, 1.0))
        else:
            br = rankdata(bv).astype(np.float64)
            br -= br.mean()
            bn = float(np.sqrt(np.dot(br, br)))
            if an > 0 and bn > 0:
                rho = float(np.clip(np.dot(ar, br) / (an * bn), -1.0, 1.0))
    overlap = None
    candidate_count, reference_count = int(np.count_nonzero(av > 0)), int(np.count_nonzero(bv > 0))
    # Positive support of a dense continuous surface is NOT a set of placed dots.
    # Avoid a misleading overlap statistic (and millions of unnecessary KD queries).
    if stage == 'dots' and candidate_count and reference_count:
        ac = np.argwhere(mask & (a > 0))
        bc = np.argwhere(mask & (b > 0))
        distances = cKDTree(bc).query(ac, k=1)[0]
        overlap = float(np.mean(distances <= 3.0))
    return {
        'stage': stage,
        'spearman_full_footprint': rho,
        'candidate_dots': candidate_count if stage == 'dots' else None,
        'candidate_positive_support': candidate_count,
        'reference_dots': reference_count,
        'candidate_fraction_within_3px_of_reference': overlap,
        'identical_inside_footprint': bool(np.array_equal(av, bv)),
        # Treat a strongly inverted rank as suspicious too. This conservative
        # absolute-rho rule is at least as strict as the owner's >0.90 stop.
        'correlation_duplicate': rho is not None and abs(rho) > 0.90,
        'dot_duplicate': overlap is not None and overlap > 0.70,
        'undefined': rho is None or (stage == 'dots' and overlap is None),
    }


def decision(comparisons, *, stage, registry_complete):
    """The stage must be explicit; incomplete inventories cannot certify novelty."""
    if stage not in ('surface', 'dots'):
        raise ValueError('stage must be surface or dots')
    rows = list(comparisons)
    # Derive the stop from the numeric measurements as well as the recorded
    # flags: a stale or tampered flag must not turn a duplicate into a pass.
    def finite_number(value):
        return isinstance(value, (int, float, np.number)) and not isinstance(value, (bool, np.bool_)) and math.isfinite(value)

    duplicate = any(
        r.get('identical_inside_footprint') or r.get('correlation_duplicate')
        or (finite_number(r.get('spearman_full_footprint')) and abs(r['spearman_full_footprint']) > 0.90)
        or (stage == 'dots' and (r.get('dot_duplicate')
            or (finite_number(r.get('candidate_fraction_within_3px_of_reference'))
                and r['candidate_fraction_within_3px_of_reference'] > 0.70)))
        for r in rows
    )
    undefined = any(
        not finite_number(r.get('spearman_full_footprint'))
        or not -1 <= r['spearman_full_footprint'] <= 1
        or (stage == 'dots' and (not finite_number(r.get('candidate_fraction_within_3px_of_reference'))
            or not 0 <= r['candidate_fraction_within_3px_of_reference'] <= 1))
        for r in rows
    )
    if duplicate:
        return 'duplicate-stop'
    if not rows or not registry_complete or undefined:
        return 'blocked-incomplete-evidence'
    return 'novelty-check-passed-not-submission-approval'
