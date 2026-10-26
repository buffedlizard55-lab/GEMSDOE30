"""Exact, footprint-aware duplicate diagnostics; never a performance certificate.

Use before placement (continuous surfaces) and after placement (dots). A changed
filename, encoding, or hash is not scientific novelty. Undefined correlations
fail closed, including constant surfaces and empty supports.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import rankdata


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
        'correlation_duplicate': rho is not None and rho > 0.90,
        'dot_duplicate': overlap is not None and overlap > 0.70,
        'undefined': rho is None or (stage == 'dots' and overlap is None),
    }


def decision(comparisons, *, stage, registry_complete):
    """The stage must be explicit; incomplete inventories cannot certify novelty."""
    if stage not in ('surface', 'dots'):
        raise ValueError('stage must be surface or dots')
    rows = list(comparisons)
    duplicate = any(r['identical_inside_footprint'] or r['correlation_duplicate'] or
                    (stage == 'dots' and r['dot_duplicate']) for r in rows)
    undefined = any(r['spearman_full_footprint'] is None or
                    (stage == 'dots' and r['candidate_fraction_within_3px_of_reference'] is None)
                    for r in rows)
    if duplicate:
        return 'duplicate-stop'
    if not rows or not registry_complete or undefined:
        return 'blocked-incomplete-evidence'
    return 'novelty-check-passed-not-submission-approval'
