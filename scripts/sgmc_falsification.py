#!/usr/bin/env python3
"""Falsification test for the SGMC off-catalogue fault layer (hypothesis H1).

Claim under test
----------------
The USGS State Geologic Map Compilation (SGMC) contains fault linework inside the
competition footprint that the public Quaternary-fault catalogue does not: 82,156 SGMC
fault pixels lie in the footprint and 61,668 of them are farther than 300 m from any
catalogue fault.  If those pixels mark *real structures*, they must be enriched in
evidence that was collected independently of the state geologic maps.

Design
------
``A`` = SGMC pixels farther than ``--off-catalogue-m`` from any catalogue fault.
``B`` = the same linework translated by a fixed offset (default 3 km), then filtered to
       valid, off-catalogue pixels and subsampled so that the distance-to-catalogue
       distribution matches ``A``.
``C`` = the same linework restricted to pixels *within* 100 m of the catalogue (a positive
       control: it is known-real faulting by construction).

A rigid translation preserves pixel count, line geometry, orientation spectrum, footprint
position and regional setting while destroying the geological association.  Matching the
distance-to-catalogue histogram removes the trivial confound that off-catalogue pixels are,
by construction, far from the catalogue.

For every independent evidence layer the script reports the class mean of the ranked
layer value (percentile within the valid footprint) and the Mann-Whitney AUC of A vs B.
An AUC near 0.5 means the SGMC off-catalogue linework carries no independent information;
consistently elevated AUCs across unrelated sensors mean it does.

Evidence layers used here are all collected independently of the SGMC:
  * 1 m airborne lidar scarp morphology (USGS 3DEP), 12 bands
  * seismic-event density (``deq_n100a15``) and historical intensity (``ieq_n100a15``)
  * airborne magnetics / gravity derivatives from the official 19-band stack
  * geodetic strain rate (Nevada Geodetic Laboratory)
  * GDR 1391 thermal springs and 2 m temperature probes (geothermal exploration)
  * GDR 1391 volcanic vents (a negative control: faults are not vents)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

BAND_INDEX = {
    "mag_anom": 0, "rtp": 1, "tmi_hg": 2, "geod_2ndinv": 3, "iso_grav_anom_slope": 4,
    "tc": 5, "geod_shearrate": 6, "geod_dilaterate": 7, "tmi_vg": 8, "deq_n100a15": 9,
    "iso_grav_anom_vg": 10, "det_elev": 11, "iso_grav_anom": 12, "tmi": 13,
    "depth_to_base_surf": 14, "ieq_n100a15": 15, "cond_surf": 16,
    "iso_grav_anom_hg": 17, "det_elev_slope": 18,
}
OFFICIAL_BANDS = ["tmi_hg", "iso_grav_anom_slope", "tmi_vg", "deq_n100a15", "ieq_n100a15",
                  "geod_shearrate", "geod_2ndinv", "cond_surf", "det_elev_slope",
                  "depth_to_base_surf"]
SCARP_BANDS = {0: "ex_max", 1: "ex_mean", 2: "step_max", 3: "lapneg_max", 4: "lappos_max",
               5: "downface_max", 6: "upface_max", 7: "cross_max", 8: "relief", 9: "coh100"}
EXT_BANDS = {0: "ThK", 1: "UK", 2: "UTh", 3: "TMI_up150"}


def _rank_percentile(values: np.ndarray, valid_values: np.ndarray) -> np.ndarray:
    """Percentile rank of each value within the valid-footprint distribution."""

    order = np.sort(valid_values)
    position = np.searchsorted(order, values, side="left")
    total = max(order.size - 1, 1)
    return position.astype(np.float64) / total


def _auc(positive: np.ndarray, negative: np.ndarray) -> float:
    """Mann-Whitney AUC via rank sums (ties handled by average ranks)."""

    combined = np.concatenate([positive, negative])
    order = np.argsort(combined, kind="mergesort")
    ranks = np.empty(combined.size, dtype=np.float64)
    ranks[order] = np.arange(1, combined.size + 1, dtype=np.float64)
    # average ranks over ties
    sorted_values = combined[order]
    start = 0
    for index in range(1, combined.size + 1):
        if index == combined.size or sorted_values[index] != sorted_values[start]:
            if index - start > 1:
                ranks[order[start:index]] = ranks[order[start:index]].mean()
            start = index
    n_pos = positive.size
    n_neg = negative.size
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    rank_sum = ranks[:n_pos].sum()
    return float((rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def _read_point_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read a point table with quoted-comma tolerant parsing; return (rows, cols)."""

    import csv

    with path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = {name.lower(): name for name in (reader.fieldnames or [])}
        row_key = fields.get("row") or fields.get("py")
        col_key = fields.get("col") or fields.get("px")
        if row_key is None or col_key is None:
            raise ValueError(f"{path.name}: no row/col pixel columns in {reader.fieldnames}")
        rows, cols = [], []
        for record in reader:
            try:
                rows.append(float(record[row_key]))
                cols.append(float(record[col_key]))
            except (TypeError, ValueError):
                continue
    return (np.asarray(rows, dtype=np.int64), np.asarray(cols, dtype=np.int64))


def _matched_subsample(target_distance: np.ndarray, candidate_distance: np.ndarray,
                       candidate_rows: np.ndarray, candidate_cols: np.ndarray,
                       bin_width_m: float, rng: np.random.Generator):
    """Subsample candidates so their distance-to-catalogue histogram matches the target."""

    edges = np.arange(0, target_distance.max() + 2 * bin_width_m, bin_width_m)
    target_counts, _ = np.histogram(target_distance, bins=edges)
    candidate_bin = np.clip(np.digitize(candidate_distance, edges) - 1, 0, target_counts.size - 1)
    target_bin = np.clip(np.digitize(target_distance, edges) - 1, 0, target_counts.size - 1)
    chosen: list[int] = []
    for index in range(target_counts.size):
        want = int(target_counts[index])
        if want == 0:
            continue
        pool = np.nonzero(candidate_bin == index)[0]
        if pool.size == 0:
            continue
        take = min(want, pool.size)
        chosen.append(rng.choice(pool, size=take, replace=False))
    if not chosen:
        empty = np.zeros(0, dtype=np.int64)
        return empty, empty
    index = np.concatenate(chosen)
    return candidate_rows[index], candidate_cols[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--external-dir", type=Path, default=ROOT / "data/external")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/research/sgmc-falsification.json")
    parser.add_argument("--off-catalogue-m", type=float, default=300.0)
    parser.add_argument("--offset-pixels", type=int, nargs=2, default=(0, 30),
                        help="row, col translation in 100 m pixels used to build the control")
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--max-class-pixels", type=int, default=60000)
    args = parser.parse_args()

    import rasterio
    from scipy.ndimage import distance_transform_edt

    started = time.time()
    with rasterio.open(args.template) as template:
        footprint = np.isfinite(template.read(1))
        grid = {
            "shape_hw": [template.height, template.width],
            "epsg": template.crs.to_epsg() if template.crs else None,
            "transform_gdal": [float(v) for v in template.transform.to_gdal()],
        }
    labels = np.load(args.data_dir / "labels.npy")
    features = np.load(args.data_dir / "features_raw.npy", mmap_mode="r")
    if features.shape[1:] != footprint.shape:
        raise ValueError("the prepared feature stack does not match the template grid")

    with rasterio.open(args.external_dir / "derived_sgmc_faults_100m_u8.tif") as dataset:
        sgmc = dataset.read(1) > 0
    catalogue = (labels == 1) & footprint
    distance_to_catalogue = distance_transform_edt(~catalogue, sampling=(100.0, 100.0))

    off_mask = catalogue | (distance_to_catalogue > args.off_catalogue_m)
    class_a_mask = sgmc & footprint & off_mask
    on_mask = sgmc & footprint & ~off_mask

    shifted = np.zeros_like(sgmc)
    row_shift, col_shift = args.offset_pixels
    source_rows = slice(max(0, -row_shift), sgmc.shape[0] - max(0, row_shift))
    dest_rows = slice(max(0, row_shift), sgmc.shape[0] - max(0, -row_shift))
    source_cols = slice(max(0, -col_shift), sgmc.shape[1] - max(0, col_shift))
    dest_cols = slice(max(0, col_shift), sgmc.shape[1] - max(0, -col_shift))
    shifted[dest_rows, dest_cols] = sgmc[source_rows, source_cols]

    rng = np.random.default_rng(args.seed)
    a_rows, a_cols = np.nonzero(class_a_mask)
    if a_rows.size > args.max_class_pixels:
        pick = rng.choice(a_rows.size, size=args.max_class_pixels, replace=False)
        a_rows, a_cols = a_rows[pick], a_cols[pick]
    c_rows, c_cols = np.nonzero(on_mask)

    control_pool = shifted & footprint & off_mask & ~class_a_mask
    pool_rows, pool_cols = np.nonzero(control_pool)
    b_rows, b_cols = _matched_subsample(
        distance_to_catalogue[a_rows, a_cols],
        distance_to_catalogue[pool_rows, pool_cols],
        pool_rows, pool_cols,
        bin_width_m=100.0, rng=rng,
    )

    # Second, stronger control: local case-control sampling.  For every SGMC
    # off-catalogue pixel draw a partner 1-2 km away in a random direction and keep
    # partners whose distance-to-catalogue and terrain-slope decile match the case.
    # Local partners share regional setting, so terrain/lithology confounds cancel.
    slope_band = np.asarray(features[BAND_INDEX["det_elev_slope"]], dtype=np.float64)
    slope_band = np.where(footprint & np.isfinite(slope_band), slope_band, np.nan)
    finite_slope = slope_band[footprint & np.isfinite(slope_band)]
    if finite_slope.size > 1000:
        slope_edges = np.unique(np.nanpercentile(finite_slope, np.arange(0, 101, 10)))
        slope_edges[-1] = np.inf
        slope_class = np.digitize(slope_band, slope_edges[1:-1])
    else:
        slope_class = np.zeros(footprint.shape, dtype=np.int64)
    distance_class = np.floor(distance_to_catalogue / 100.0).astype(np.int64)
    lookup: dict[tuple[int, int], np.ndarray] = {}
    pool_valid_rows, pool_valid_cols = np.nonzero(footprint & off_mask & ~class_a_mask)
    keys = (distance_class[pool_valid_rows, pool_valid_cols]
            * (slope_class.max() + 2) + slope_class[pool_valid_rows, pool_valid_cols])
    order = np.argsort(keys, kind="mergesort")
    sorted_keys = keys[order]
    boundaries = np.searchsorted(sorted_keys, np.arange(keys.min(), keys.max() + 2))
    for index, key in enumerate(range(int(keys.min()), int(keys.max()) + 1)):
        start, stop = boundaries[index], boundaries[index + 1]
        if stop > start:
            lookup[key] = order[start:stop]

    b2_rows: list[int] = []
    b2_cols: list[int] = []
    height, width = footprint.shape
    angle = rng.uniform(0.0, 2.0 * np.pi, size=a_rows.size)
    radius = rng.uniform(10.0, 20.0, size=a_rows.size)
    offsets_row = np.rint(radius * np.sin(angle)).astype(np.int64)
    offsets_col = np.rint(radius * np.cos(angle)).astype(np.int64)
    for index in range(a_rows.size):
        row = a_rows[index]
        col = a_cols[index]
        key = int(distance_class[row, col]) * (slope_class.max() + 2) + int(slope_class[row, col])
        pool = lookup.get(key)
        if pool is None:
            continue
        for _ in range(24):
            candidate_row = row + offsets_row[index]
            candidate_col = col + offsets_col[index]
            if not (0 <= candidate_row < height and 0 <= candidate_col < width):
                break
            if not footprint[candidate_row, candidate_col]:
                break
            if catalogue[candidate_row, candidate_col]:
                break
            b2_rows.append(int(candidate_row))
            b2_cols.append(int(candidate_col))
            break
    b2_rows_array = np.asarray(b2_rows, dtype=np.int64)
    b2_cols_array = np.asarray(b2_cols, dtype=np.int64)

    results: dict[str, object] = {
        "script": "scripts/sgmc_falsification.py",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": grid,
        "design": {
            "class_a": "SGMC fault pixels farther than the threshold from any catalogue fault",
            "class_b": "SGMC linework translated by (row, col) pixels, distance-to-catalogue matched",
            "class_c": "SGMC fault pixels within the threshold of a catalogue fault (positive control)",
            "class_d": "local partners 1-2 km away, matched on distance-to-catalogue and terrain-slope decile",
            "offset_pixels": list(args.offset_pixels),
            "matching_bin_m": 100.0,
            "seed": args.seed,
        },
        "class_sizes": {
            "a_off_catalogue": int(a_rows.size),
            "b_translated_control": int(b_rows.size),
            "c_on_catalogue": int(c_rows.size),
            "d_local_matched": int(b2_rows_array.size),
            "sgmc_pixels_in_footprint": int((sgmc & footprint).sum()),
        },
        "bands": {},
    }

    def evaluate(name: str, plane: np.ndarray):
        valid_plane = plane[footprint]
        finite = np.isfinite(valid_plane)
        values = {
            "a": plane[a_rows, a_cols], "b": plane[b_rows, b_cols], "c": plane[c_rows, c_cols],
            "d": plane[b2_rows_array, b2_cols_array],
        }
        valid_plane = valid_plane[finite]
        entry: dict[str, float] = {}
        for key in ("a", "b", "c", "d"):
            vector = values[key]
            vector = vector[np.isfinite(vector)]
            if vector.size == 0:
                entry[f"{key}_mean_percentile"] = float("nan")
                entry[f"{key}_n"] = 0
                continue
            entry[f"{key}_mean_percentile"] = float(_rank_percentile(vector, valid_plane).mean())
            entry[f"{key}_n"] = int(vector.size)
        a_vector = values["a"][np.isfinite(values["a"])]
        b_vector = values["b"][np.isfinite(values["b"])]
        d_vector = values["d"][np.isfinite(values["d"])]
        entry["auc_a_vs_b"] = _auc(a_vector, b_vector)
        entry["auc_a_vs_d"] = _auc(a_vector, d_vector)
        results["bands"][name] = entry

    for band_index, band_name in enumerate(OFFICIAL_BANDS):
        column = BAND_INDEX[band_name]
        plane = np.asarray(features[column], dtype=np.float64)
        plane = np.where(footprint, plane, np.nan)
        plane[~np.isfinite(plane)] = np.nan
        evaluate(f"official::{band_name}", plane)

    for path, band_map in (
        (args.external_dir / "lidar_scarp_features_u8.tif", SCARP_BANDS),
        (args.external_dir / "geodawn_extensions_u8.tif", EXT_BANDS),
    ):
        if not path.is_file():
            results.setdefault("skipped", []).append(str(path))
            continue
        with rasterio.open(path) as dataset:
            for band_index, band_name in band_map.items():
                plane = dataset.read(band_index + 1).astype(np.float64)
                plane[plane >= 255] = np.nan
                evaluate(f"{path.stem}::{band_name}", plane)

    for csv_name, label in (("gdr_wellspring_in_footprint.csv", "gdr_wellspring"),
                            ("gdr_volcanic_vents_in_footprint.csv", "gdr_volcanic_vents")):
        path = args.external_dir / csv_name
        if not path.is_file():
            results.setdefault("skipped", []).append(str(path))
            continue
        rows, cols = _read_point_csv(path)
        keep = ((rows >= 0) & (rows < footprint.shape[0])
                & (cols >= 0) & (cols < footprint.shape[1]))
        rows, cols = rows[keep], cols[keep]
        if rows.size == 0:
            results.setdefault("notes", []).append(f"{csv_name}: no points inside the grid")
            continue
        points = np.zeros(footprint.shape, dtype=bool)
        points[rows, cols] = True
        distance = distance_transform_edt(~points, sampling=(100.0, 100.0))
        evaluate(f"{label}::distance_to_point_m",
                 np.where(footprint, -distance, np.nan))

    a_distance = distance_to_catalogue[a_rows, a_cols]
    b_distance = distance_to_catalogue[b_rows, b_cols]
    results["distance_to_catalogue_m"] = {
        "a_median": float(np.median(a_distance)) if a_distance.size else float("nan"),
        "b_median": float(np.median(b_distance)) if b_distance.size else float("nan"),
        "a_mean": float(a_distance.mean()) if a_distance.size else float("nan"),
        "b_mean": float(b_distance.mean()) if b_distance.size else float("nan"),
    }
    results["elapsed_seconds"] = round(time.time() - started, 1)
    results["interpretation_key"] = (
        "auc_a_vs_b > 0.5 means the SGMC off-catalogue linework is associated with that "
        "independently measured property more strongly than its own translation control; "
        "mean_percentile is the class mean rank inside the valid footprint"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} in {results['elapsed_seconds']}s")
    for name, entry in sorted(results["bands"].items()):
        print(f"  {name:44s} AUCvsB={entry['auc_a_vs_b']:.3f} AUCvsD={entry['auc_a_vs_d']:.3f} "
              f"a={entry['a_mean_percentile']:.3f} b={entry['b_mean_percentile']:.3f} "
              f"d={entry['d_mean_percentile']:.3f} c={entry['c_mean_percentile']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
