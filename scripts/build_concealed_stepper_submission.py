#!/usr/bin/env python3
"""Build a UNIQUE GeoTIFF submission: CTD-1 Concealed Piedmont Stepover Corridor.

Scientific hypothesis (concealed fault discovery, NOT a copy of any shipped lane):

  Great Basin geothermal systems localize at concealed intrabasin fault
  stepovers / relay ramps buried under Quaternary alluvium -- precisely the
  structures the USGS/INGENIOUS catalogue (labels.tif) under-represents, because
  that catalogue favours well-constrained surface-rupturing range-front traces.
  A concealed fault offsetting the basin base leaves a co-located physical
  signature that is NOT topography:

    * MT depth_to_base_surf step       -> basement is offset across the fault
    * isostatic gravity gradient       -> density contrast across the fault
    * magnetic total-curvature edge    -> lithologic offset at the fault trace
    * Quaternary volcanics proximity   -> shallow heat source
    * paleogeothermal spring proximity -> fossil hydrothermal fluid expression

  The score surface is an AND-fusion (geometric mean) of a structural term
  (basement step x gravity gradient x magnetic edge) and a thermal/fluid term
  (volcanics x paleo-springs): a cell scores highly only when BOTH structure and
  heat/fluid support it.  This is deliberately different from:

    * H33 / d28 family: pure denominator pruning near catalogue dots (topographic
      range-front focus; no concealed-basin signal).
    * CSR-1: cover-corrected 3D gravity + Radon stepover expert (Walker Lane).
    * PTA-1 / TAD: subsurface magnetic tilt-depth + radiometric alteration.
    * MSDB-1v2: full-stack scarp + regional geophysics on range fronts.
    * geothermal-corridor lane: linear soft-union volcanics/paleo/probes gated
      off SGMC with Poisson-disk emission (linear pool, not AND-fusion; no MT
      basement step; no magnetic edge).

  Known catalogue pixels are masked pixel-exactly (zero buffer, per DrivenData
  staff thread 11516) and dots are kept off the 1-2 px unmasked catalogue flank
  (the H33-b2 mechanism) so the emission targets catalogue-missing structure.

  Output: single-band float32 GeoTIFF, NaN outside the template footprint,
  finite [0, 1] inside, EPSG:32611, 100 m grid identical to sample_submission.tif.

Run: .venv/bin/python scripts/build_concealed_stepper_submission.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.emission import metric_optimal_emission
from gemsdoe30.fields import geometric_mean
from gemsdoe30.submission import write_submission_file

PROCESSED = Path("data/processed")
RAW = Path("data/raw")
EXTERNAL = Path("data/external")
OUTPUT_DIR = Path("docs/downloads")

# Band layout from scripts/prepare_data.py (features_raw.npy, channels first):
BAND = {
    "mag_anom": 0,
    "rtp": 1,
    "tmi_hg": 2,
    "geod_2ndinv": 3,
    "iso_grav_anom_slope": 4,
    "tc": 5,
    "geod_shearrate": 6,
    "geod_dilaterate": 7,
    "tmi_vg": 8,
    "deq_n100a15": 9,
    "iso_grav_anom_vg": 10,
    "det_elev": 11,
    "iso_grav_anom": 12,
    "tmi": 13,
    "depth_to_base_surf": 14,
    "ieq_n100a15": 15,
    "cond_surf": 16,
    "iso_grav_anom_hg": 17,
    "det_elev_slope": 18,
}

# External public layers (verified on the competition grid; receipt:
# data/external/external_receipt.json).  USGS SGMC state geologic maps; DOE GDR
# INGENIOUS submission 1391 (CC BY 4.0, DOI 10.15121/1881483).
EXTERNAL_LAYERS = {
    "sgmc": EXTERNAL / "derived_sgmc_faults_100m_u8.tif",
    "volcanics": EXTERNAL / "derived_gdr_volcanics_100m_u8.tif",
    "paleo": EXTERNAL / "derived_gdr_paleo_100m_u8.tif",
}

DECAY_M = 1000.0  # proximity decay length, matched to the 300 m DTI kernel support
MAX_DOTS = 40000  # sparse metric-scale dot budget, comparable to the scored family
BELIEF_CUT = 0.05  # below this belief a cell cannot emit a dot
POOL_LIMIT = 300_000  # cap the candidate pool for speed (highest belief wins)


def _read_band(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
        nodata = ds.nodata
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def _read_feature(channel: int) -> np.ndarray:
    arr = np.load(PROCESSED / "features_raw.npy", mmap_mode="r")[channel]
    return np.nan_to_num(np.asarray(arr, dtype=np.float64), nan=0.0,
                         posinf=0.0, neginf=0.0)


def _percentile_unit(x: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> np.ndarray:
    """Robustly rescale to [0, 1] using percentile clipping (ignores flat/dead bands)."""
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        return np.zeros_like(x)
    low, high = np.percentile(finite, lo), np.percentile(finite, hi)
    span = max(high - low, 1e-12)
    return np.clip((x - low) / span, 0.0, 1.0)


def _gradient_magnitude(x: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(x)
    return np.hypot(gy, gx)


def _decay_surface(binary: np.ndarray, decay_m: float, pixel_m: float = 100.0) -> np.ndarray:
    distance = distance_transform_edt(~binary.astype(bool), sampling=(pixel_m, pixel_m))
    return np.exp(-distance / decay_m)


def build_belief() -> tuple[np.ndarray, np.ndarray]:
    """Return (belief [0,1] on the valid footprint, valid footprint mask)."""
    with rasterio.open(RAW / "sample_submission.tif") as tmpl:
        template = tmpl.read(1)
        valid = np.isfinite(template)
        nodata = tmpl.nodata
        if nodata is not None:
            valid &= ~np.isnan(template)
        valid &= tmpl.dataset_mask() != 0

    with rasterio.open(RAW / "labels.tif") as ds:
        labels = ds.read(1)
    catalogue = labels == 1

    # ---- structural term: concealed-fault basement/structure offset ---------
    basement = _read_feature(BAND["depth_to_base_surf"])
    grav_hg = _read_feature(BAND["iso_grav_anom_hg"])
    grav_vg = _read_feature(BAND["iso_grav_anom_vg"])
    mag_tc = _read_feature(BAND["tc"])

    basin_step = _percentile_unit(_gradient_magnitude(basement))
    grav_grad = _percentile_unit(np.hypot(_gradient_magnitude(grav_hg),
                                          _gradient_magnitude(grav_vg)))
    mag_edge = _percentile_unit(np.abs(mag_tc))
    structural = geometric_mean(geometric_mean(basin_step, grav_grad), mag_edge)

    # ---- thermal / fluid term: heat + fossil fluid expression ---------------
    volcanics = _read_band(EXTERNAL_LAYERS["volcanics"]) > 0
    paleo = _read_band(EXTERNAL_LAYERS["paleo"]) > 0
    thermal = geometric_mean(_decay_surface(volcanics, DECAY_M),
                             _decay_surface(paleo, DECAY_M))

    # AND-fusion: structure AND heat/fluid must both support a cell.
    belief = geometric_mean(structural, thermal)
    belief = np.where(valid, belief, 0.0)
    span = float(belief.max() - belief.min())
    if span <= 0:
        raise RuntimeError("degenerate belief surface")
    belief = np.clip((belief - belief.min()) / span, 0.0, 1.0)
    return belief, valid


def main() -> int:
    belief, valid = build_belief()

    with rasterio.open(RAW / "labels.tif") as ds:
        catalogue = ds.read(1) == 1
    dist_to_cat_px = distance_transform_edt(~catalogue)

    # Off-catalogue gate + 1-2 px halo suppression (H33-b2 mechanism): dots at
    # d_cat in {1, 2} px pay full FP weight on unmasked catalogue flanks while
    # dots at 3 px still earn triangular-kernel credit across the flank.
    domain = valid & (dist_to_cat_px > 2.0) & (belief > BELIEF_CUT)
    belief = np.where(domain, belief, 0.0)

    dots = metric_optimal_emission(belief, domain,
                                   belief_cut=BELIEF_CUT,
                                   pool_limit=POOL_LIMIT,
                                   max_dots=MAX_DOTS)
    probabilities = dots.astype(np.float32)

    n_dots = int(dots.sum())
    n_domain = int(domain.sum())
    print(f"valid footprint pixels: {int(valid.sum()):,}")
    print(f"domain (off-catalogue, belief>{BELIEF_CUT}) pixels: {n_domain:,}")
    print(f"dots emitted: {n_dots:,}")
    print(f"dot density: {n_dots / max(n_domain, 1) * 1e6:.2f} dots per million domain px")

    # ---- unique run identity -----------------------------------------------
    digest_input = probabilities.tobytes() + b"|ctd1-concealed-stepper"
    digest = hashlib.sha256(digest_input).hexdigest()[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"gems30-ctd1-concealed-stepper-{timestamp}-{digest}"
    note = ("CTD1 concealed piedmont stepover: basement step+gravity+mag edge AND "
            "volcanics+paleo springs; off-catalogue; EDGE dots; all-finite [0,1]")
    if len(note) > 140:
        raise ValueError(f"submission note exceeds 140 characters ({len(note)})")

    output_path = OUTPUT_DIR / f"{run_name}.tif"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = write_submission_file(
        probabilities,
        RAW / "sample_submission.tif",
        output_path,
        note=note,
        run_name=run_name,
        outside_value=float("nan"),
    )
    print(json.dumps(manifest, indent=2))
    print(f"\nGeoTIFF file: {output_path}")
    print(f"Published GEMS format compliant: {manifest['published_format_compliant']}")
    print(f"Note ({len(note)}/140): {note}")
    print(f"Run name: {run_name}")
    return 0 if manifest["published_format_compliant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
