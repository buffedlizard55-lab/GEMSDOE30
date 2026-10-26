#!/usr/bin/env python3
"""Compare a raster to every pinned entry in a registry; exit nonzero unless clear.

Registry schema: {"complete": false, "rasters": [{"path": ..., "sha256": ...}]}.
Paths are relative to the repository working directory. 'complete' is an explicit
inventory attestation, not something inferred from a successful partial download.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
import rasterio
from gemsdoe30.novelty import compare, decision, rank_cache
from gemsdoe30.submission import valid_template_mask


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit(candidate, template, registry, stage):
    manifest = json.loads(Path(registry).read_text())
    with rasterio.open(template) as ds:
        mask = valid_template_mask(ds, np)
        grid = (ds.shape, ds.crs, ds.transform)
    def read(path):
        with rasterio.open(path) as ds:
            if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != grid:
                raise ValueError(f'grid/band mismatch: {path}')
            return ds.read(1)
    a = read(candidate)
    comparisons, errors = [], []
    seen = set()
    cached = rank_cache(a, mask)
    # Encoding variants often share identical in-footprint values. Reuse exact
    # results, but retain a comparison row for EVERY hash-verified registry entry.
    by_values = {}
    for row in manifest['rasters']:
        try:
            path = row['path']
            if path in seen:
                raise ValueError(f'duplicate registry entry: {path}')
            seen.add(path)
            if digest(path) != row['sha256']:
                raise ValueError(f'hash mismatch: {path}')
            reference = read(path)
            value_hash = hashlib.sha256(np.ascontiguousarray(reference[mask], dtype=np.float64).tobytes()).hexdigest()
            if value_hash not in by_values:
                by_values[value_hash] = compare(a, reference, mask, stage=stage, cached_ranks=cached)
            comparisons.append({'reference': path, 'site': row.get('site'),
                                'reference_sha256': row['sha256'],
                                'reference_values_sha256': value_hash,
                                **by_values[value_hash]})
        except (ValueError, OSError, KeyError) as exc:
            errors.append(f"{row.get('path', '<missing path>')}: {exc}")
    malformed_audited = []
    for row in manifest.get('exclusions', []):
        if not row.get('aligned') or row.get('footprint_complete', True) or 'path' not in row:
            continue
        try:
            path = row['path']
            if digest(path) != row['sha256']:
                raise ValueError(f'hash mismatch in malformed exclusion: {path}')
            reference = read(path)
            in_fp = reference[mask]
            fin_in_fp = np.isfinite(in_fp)
            invalid_cells = int((~fin_in_fp).sum())
            out_of_range = int((fin_in_fp & ((in_fp < 0.0) | (in_fp > 1.0))).sum())
            finite_mask = mask & np.isfinite(reference) & (reference >= 0.0) & (reference <= 1.0)
            subset_stats = (
                compare(a, np.where(finite_mask, reference, 0.0), finite_mask, stage=stage)
                if finite_mask.any() else {'spearman': 0.0, 'duplicate': False}
            )
            if subset_stats.get('duplicate'):
                errors.append(f"duplicate against finite subset of malformed exclusion: {path}")
            malformed_audited.append({
                'reference': path,
                'site': row.get('site'),
                'reference_sha256': row['sha256'],
                'invalid_in_footprint_cells': invalid_cells,
                'out_of_range_in_footprint_cells': out_of_range,
                'finite_in_footprint_cells': int(finite_mask.sum()),
                'excluded_reason': row.get('excluded_reason'),
                'finite_subset_comparison': subset_stats,
            })
        except (ValueError, OSError, KeyError) as exc:
            errors.append(f"{row.get('path', '<missing exclusion path>')}: {exc}")
    result = decision(comparisons, stage=stage,
                      registry_complete=manifest.get('complete') is True and not errors)
    if errors and result == 'novelty-check-passed-not-submission-approval':
        result = 'blocked-incomplete-registry'
    return {'schema_version': 1, 'stage': stage, 'candidate': str(candidate),
            'candidate_sha256': digest(candidate), 'template_sha256': digest(template),
            'registry_sha256': digest(registry), 'registry_complete': manifest.get('complete') is True,
            'comparisons': comparisons, 'malformed_exclusions_audited': malformed_audited,
            'errors': errors, 'decision': result,
            'submission_approved': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate', type=Path)
    p.add_argument('--template', type=Path, default=Path('data/raw/sample_submission.tif'))
    p.add_argument('--registry', type=Path, required=True)
    p.add_argument('--stage', choices=['surface', 'dots'], required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        result = audit(args.candidate, args.template, args.registry, args.stage)
    except (ValueError, OSError, KeyError) as exc:
        result = {'decision': 'blocked-invalid-input', 'errors': [str(exc)], 'submission_approved': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(result['decision'])
    return 0 if result['decision'] == 'novelty-check-passed-not-submission-approval' else 2


if __name__ == '__main__':
    raise SystemExit(main())
