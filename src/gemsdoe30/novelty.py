"""Exact, footprint-aware duplicate diagnostics; never a performance certificate.

Use before placement (continuous surfaces) and after placement (dots). A changed
filename, encoding, or hash is not scientific novelty. Undefined correlations
fail closed, including constant surfaces and empty supports.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import spearmanr


def compare(candidate, reference, footprint):
    """Full-footprint Spearman and directional dot overlap (Euclidean <=3 px).

    Positive values define dots; this definition is meaningful for sparse
    emission rasters, not arbitrary dense probability surfaces. Surface-stage
    decisions use correlation only. Arrays must already share a verified grid.
    """
    a, b = np.asarray(candidate), np.asarray(reference)
    mask = np.asarray(footprint, dtype=bool)
    if a.ndim != 2 or a.shape != b.shape or a.shape != mask.shape or not mask.any():
        raise ValueError('nonempty, same-shaped 2D arrays and footprint required')
    if not (np.isfinite(a[mask]).all() and np.isfinite(b[mask]).all()):
        raise ValueError('non-finite values inside footprint')
    av, bv = a[mask], b[mask]
    constant = np.ptp(av) == 0 or np.ptp(bv) == 0
    rho = None if constant else float(spearmanr(av, bv).statistic)
    ac = np.argwhere(mask & (a > 0))
    bc = np.argwhere(mask & (b > 0))
    overlap = None
    if len(ac) and len(bc):
        distances = cKDTree(bc).query(ac, k=1)[0]
        overlap = float(np.mean(distances <= 3.0))
    return {
        'spearman_full_footprint': rho,
        'candidate_dots': len(ac), 'reference_dots': len(bc),
        'candidate_fraction_within_3px_of_reference': overlap,
        'identical_inside_footprint': bool(np.array_equal(av, bv)),
        'correlation_duplicate': rho is not None and rho > 0.90,
        'dot_duplicate': overlap is not None and overlap > 0.70,
        'undefined': rho is None or overlap is None,
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
