#!/usr/bin/env python3
"""Reconstruct historical support identities for education; writes JSON, never TIFF."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from gemsdoe30.submission import valid_template_mask


def main():
    with rasterio.open('data/raw/sample_submission.tif') as ds:
        valid = valid_template_mask(ds, np)
        grid = ds.shape, ds.crs, ds.transform
    def read(path):
        with rasterio.open(path) as ds:
            if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != grid:
                raise ValueError(f'grid/band mismatch: {path}')
            return ds.read(1)
    cat = read('data/raw/labels.tif') == 1
    arrays = {n: read(f'data/raw/registry/{n}.tif') for n in (25, 28, 30, 31, 32)}
    expected = (arrays[28] > 0) & (distance_transform_edt(~cat) > 2) & valid
    actual = (arrays[32] > 0) & valid
    result = {
        'kind': 'historical recipe reconstruction, not a new submission',
        'h33_exactly_matches_h28_pruned_with_catalogue_distance_gt_2px': bool(np.array_equal(expected, actual)),
        'mismatching_pixels': int(np.count_nonzero(expected != actual)),
        'h25_h30_identical_in_footprint': bool(np.array_equal(arrays[25][valid], arrays[30][valid])),
        'h28_h31_identical_in_footprint': bool(np.array_equal(arrays[28][valid], arrays[31][valid])),
        'base_dots': int(np.count_nonzero((arrays[28] > 0) & valid)),
        'h33_dots': int(actual.sum()),
    }
    path = Path('docs/research/2026-10-25/recipe-reconstruction.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(path)


if __name__ == '__main__':
    main()
