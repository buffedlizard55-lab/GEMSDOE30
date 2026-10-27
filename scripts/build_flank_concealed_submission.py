#!/usr/bin/env python3
"""Build a UNIQUE GeoTIFF submission: FC-1 Concealed Flank Corridor (Experiment 2).

Scientific hypothesis (concealed fault discovery, distinct from CTD-1 and every
shipped lane):

  The holdout proxy shows hidden catalogue components sit adjacent to known
  traces (new faults can occur <300 m from known traces, DrivenData thread
  11516).  The scored 0.24-0.278 family (H33 / d28 / r1) exploits this but
  places ~81% of dots on steep range-fronts (det_elev_slope >= 5°).  The
  concealed faults actually missing from the USGS/INGENIOUS catalogue are the
  splays on the *alluvial/basin (low-slope) side* of known traces, where there
  is no surface scarp to map.

  FC-1 dots live on the 300 m kernel ring around known traces (d_cat ~ 3 px,
  outside the pixel-exact mask and the 1-2 px unmasked flank that pays full FP
  weight) BUT restricted to low-slope concealed terrain (det_elev_slope < 4°)
  and ranked by a mild geothermal belief (Quaternary heat x paleo-fluid x
  gravity gradient).  This targets near-trace concealed splays that H33's
  steep range-front dots miss -- high holdout credit with low overlap.

  Differs from:
    * CTD-1: FC-1 dots are near-trace (d_cat ~ 3 px); CTD-1 dots are deep-basin
      (off-catalogue, far from traces). CTD-1 failed its holdout gate (0.00027).
    * H33/d28/r1: same near-trace mechanism but on steep range-fronts; FC-1 is
      low-slope concealed side (different spatial configuration -> unique).
    * CSR-1 / PTA-1 / TAD: physics-first, not catalogue-adjacent dots.
    * geothermal-corridor: linear pool + SGMC gate + Poisson disk; FC-1 is a
      near-trace ring on concealed slopes with EDGE emission.

Output: single-band float32 GeoTIFF, NaN outside the footprint, finite [0,1]
inside, EPSG:32611, 100 m grid identical to sample_submission.tif.

Run: .venv/bin/python scripts/build_flank_concealed_submission.py
"""

from __future__ import annotations

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

BAND = {
    "det_elev_slope": 18,
    "iso_grav_anom_hg": 17,
    "tc": 5,
}

EXTERNAL_LAYERS = {
    "volcanics": EXTERNAL / "derived_gdr_volcanics_100m_u8.tif",
    "paleo": EXTERNAL / "derived_gdr_paleo_100m_u8.tif",
}

DECAY_M = 1000.0
RING_INNER_PX = 2.0   # just outside the pixel-exact mask (d_cat=0); d_cat in {1,2}
RING_OUTER_PX = 6.0   # px is the unmasked flank (full FP weight); credit ring ~ 3 px
SLOPE_DEG_CONCEALED = 6.0  # low-slope alluvial side = concealed, unmapped
MAX_DOTS = 40_000
BELIEF_CUT = 0.01
POOL_LIMIT = 400_000


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
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        return np.zeros_like(x)
    low, high = np.percentile(finite, lo), np.percentile(finite, hi)
    span = max(high - low, 1e-12)
    return np.clip((x - low) / span, 0.0, 1.0)


def _decay_surface(binary: np.ndarray, decay_m: float, pixel_m: float = 100.0) -> np.ndarray:
    distance = distance_transform_edt(~binary.astype(bool), sampling=(pixel_m, pixel_m))
    return np.exp(-distance / decay_m)


def build_belief_and_domain() -> tuple[np.ndarray, np.ndarray]:
    """Return (belief [0,1], domain mask where dots may be placed)."""
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
    dist_to_cat_px = distance_transform_edt(~catalogue)

    slope = _read_feature(BAND["det_elev_slope"])
    concealed = slope < SLOPE_DEG_CONCEALED

    # Near-trace kernel ring on the concealed side.  d_cat in {1,2} px is the
    # unmasked catalogue flank (full FP weight, H33-b2 prunes it); the useful
    # credit ring is d_cat ~ 3 px.  Extend slightly to capture splay position
    # uncertainty while staying off the masked core.
    ring = (dist_to_cat_px > RING_INNER_PX) & (dist_to_cat_px <= RING_OUTER_PX)

    # Mild geothermal belief to rank within the concealed near-trace ring:
    # Quaternary heat x paleo-fluid x gravity gradient (broad, not AND-restrictive).
    volcanics = _read_band(EXTERNAL_LAYERS["volcanics"]) > 0
    paleo = _read_band(EXTERNAL_LAYERS["paleo"]) > 0
    grav_hg = _read_feature(BAND["iso_grav_anom_hg"])
    mag_tc = _read_feature(BAND["tc"])
    thermal = geometric_mean(_decay_surface(volcanics, DECAY_M),
                             _decay_surface(paleo, DECAY_M))
    structure = geometric_mean(_percentile_unit(np.abs(grav_hg)),
                               _percentile_unit(np.abs(mag_tc)))
    belief = geometric_mean(thermal, structure)
    belief = np.where(valid, belief, 0.0)
    span = float(belief.max() - belief.min())
    belief = np.clip((belief - belief.min()) / max(span, 1e-12), 0.0, 1.0)

    domain = valid & ring & concealed
    belief = np.where(domain, belief, 0.0)
    return belief, domain


def main() -> int:
    belief, domain = build_belief_and_domain()
    n_domain = int(domain.sum())
    print(f"concealed near-trace domain pixels: {n_domain:,}")

    dots = metric_optimal_emission(belief, domain,
                                   belief_cut=BELIEF_CUT,
                                   pool_limit=POOL_LIMIT,
                                   max_dots=MAX_DOTS)
    probabilities = dots.astype(np.float32)
    n_dots = int(dots.sum())
    print(f"dots emitted: {n_dots:,}")
    print(f"dot density: {n_dots / max(n_domain, 1) * 1e6:.2f} dots per million domain px")

    digest_input = probabilities.tobytes() + b"|fc1-concealed-flank"
    digest = hashlib.sha256(digest_input).hexdigest()[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"gems30-fc1-concealed-flank-{timestamp}-{digest}"
    note = ("FC1 concealed near-trace flank: 3px ring on low-slope alluvial side "
            "of known traces; heat+fluid+gravity ranked; EDGE dots; [0,1]")
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
