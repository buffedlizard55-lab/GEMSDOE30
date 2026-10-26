#!/usr/bin/env python3
"""Build a unique, machine-validated GeoTIFF submission from public external layers.

Scientific hypothesis (off-catalogue geothermal corridor):
  Concealed intrabasin faults that host Great Basin geothermal systems are
  under-represented in the USGS/INGENIOUS Quaternary catalogue, which favours
  well-constrained surface-rupturing traces.  A concealed fault cutting
  Quaternary volcanic cover should co-locate with:
    * Quaternary volcanic vents / flows (shallow heat source)            -> gdr_volcanics
    * paleogeothermal sinter / tufa spring deposits (fluid expression)   -> gdr_paleo
    * shallow 2 m temperature probe anomalies                            -> gdr_2m_probes
    * SGMC-mapped concealed / approximate structure (the fault itself)   -> sgmc_faults

  Layers are combined as a weighted linear pool of distance-decay surfaces,
  then masked OFF the SGMC catalogue core so the emission targets
  catalogue-missing structure (analogous to the 'offcat' family but driven by
  geothermal physics rather than topography or tilt/alteration).  Poisson-disk
  thinning emits sparse dots matched to the 300 m triangular DTI kernel.

  This lane differs from every shipped lane:
    * G30-TAD / PTA-1: subsurface tilt-depth + radiometric K alteration + MT cover step.
    * G30-S19 / S20: lidar scarp + radiometrics on topographic scarps.
    * d28-poisson / h33: pure Poisson dot fields on the scarp catalogue.
    * MSDB-1v2: piedmont full-stack scarp + regional geophysics.
  None uses Quaternary volcanic + paleogeothermal + shallow-thermal proximity
  as the primary driver gated off the SGMC catalogue.

Run: .venv/bin/python scripts/build_geothermal_corridor_submission.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from gemsdoe30.emission import poisson_disk_select_ordered
from gemsdoe30.submission import write_submission_file

TEMPLATE = Path("docs/downloads/gems30-PTA1-44090-20261025-9a3f7f9535a4.tif")
OUTPUT_DIR = Path("outputs")

# External public layers (all verified on the competition grid, EPSG:32611,
# 100 m pixels, 3730 x 3292).  Source/receipt: data/external/external_receipt.json
# (USGS SGMC state geologic maps; DOE GDR INGENIOUS submission 1391).
LAYERS = {
    "volcanics": Path("data/external/derived_gdr_volcanics_100m_u8.tif"),
    "paleo": Path("data/external/derived_gdr_paleo_100m_u8.tif"),
    "probes2m": Path("data/external/derived_gdr_2m_probes_100m_u8.tif"),
    "sgmc": Path("data/external/derived_sgmc_faults_100m_u8.tif"),
}

# Decay length in metres, matched to the 300 m DTI kernel support.
DECAY_M = 1000.0
# Weights for the linear (soft-union) pool of geothermal signatures: a pixel
# near any signature earns belief; near all three earns the most.
W_VOLCANICS, W_PALEO, W_PROBES = 0.4, 0.3, 0.3
# Only pixels with meaningful co-located geothermal evidence become dot
# candidates; the dot cap then keeps the most confident 40k.
BELIEF_THRESHOLD = 0.10
# Cap the emission at a sparse, metric-scale dot budget comparable to the
# scored 0.24-0.28 family (37k-44k dots).
MAX_DOTS = 40000


def read_layer(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
        nodata = ds.nodata
    if nodata is not None:
        arr = np.where(arr == nodata, 0.0, arr)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def decay_surface(binary: np.ndarray, decay_m: float, pixel_m: float = 100.0) -> np.ndarray:
    """exp(-distance_to_feature / decay_m); 1.0 on the feature, 0 far away."""
    distance = distance_transform_edt(~binary.astype(bool), sampling=(pixel_m, pixel_m))
    return np.exp(-distance / decay_m)


def main() -> int:
    for path in LAYERS.values():
        if not path.is_file():
            print(f"BLOCKED: required layer missing: {path}", file=sys.stderr)
            return 2
    if not TEMPLATE.is_file():
        print(f"BLOCKED: template missing: {TEMPLATE}", file=sys.stderr)
        return 2

    volcanics = read_layer(LAYERS["volcanics"]) > 0
    paleo = read_layer(LAYERS["paleo"]) > 0
    probes = read_layer(LAYERS["probes2m"]) > 0
    sgmc = read_layer(LAYERS["sgmc"]) > 0

    with rasterio.open(TEMPLATE) as tmpl:
        template_data = tmpl.read(1)
        valid = np.isfinite(template_data)
        nodata = tmpl.nodata
        if nodata is not None:
            valid &= ~np.isnan(template_data)
        valid &= tmpl.dataset_mask() != 0

    # Distance-decay proximity to each geothermal signature.
    v = decay_surface(volcanics, DECAY_M)
    p = decay_surface(paleo, DECAY_M)
    t = decay_surface(probes, DECAY_M)

    # Weighted linear pool of geothermal signatures, gently raised near (not
    # on) SGMC structure: step-over / splay strands of mapped systems are the
    # literature's blind-system locus. The boost uses the SGMC *proximity*
    # decay surface, so it survives the off-core mask below.
    sgmc_proximity = decay_surface(sgmc, DECAY_M)
    belief = W_VOLCANICS * v + W_PALEO * p + W_PROBES * t
    belief = belief * (0.75 + 0.25 * sgmc_proximity)
    belief = np.where(valid, belief, 0.0)
    span = float(belief.max() - belief.min())
    if span <= 0:
        print("BLOCKED: degenerate belief surface", file=sys.stderr)
        return 2
    belief = (belief - belief.min()) / span
    belief = np.clip(belief, 0.0, 1.0)

    # Off-catalogue gate + 2 px halo + belief floor: known-fault pixels are
    # masked pixel-exactly with zero buffer (DrivenData staff, thread 11516),
    # so dots in the 1-2 px unmasked flank of mapped structure pay FP mass
    # while a dot at 3 px still earns triangular-kernel credit across the
    # flank (the verified H33 b2 mechanism). SGMC is the local mapped-structure
    # proxy; the organizer catalogue (labels.tif) is not available here.
    distance_to_sgmc_px = distance_transform_edt(~sgmc)
    domain = valid & (distance_to_sgmc_px > 2.0) & (belief > BELIEF_THRESHOLD)
    belief = np.where(domain, belief, 0.0)

    # Sparse binary emission: Poisson-disk thinned to the 300 m kernel scale
    # (3 px), capped at MAX_DOTS most confident dots.
    rows, cols = poisson_disk_select_ordered(
        belief.astype(np.float32), radius_px=3.0,
        threshold=BELIEF_THRESHOLD, mask=domain, max_kept=MAX_DOTS,
    )
    dots = np.zeros(belief.shape, dtype=bool)
    if rows.size:
        dots[rows, cols] = True
    probabilities = dots.astype(np.float32)

    n_dots = int(dots.sum())
    n_valid = int(domain.sum())
    print(f"valid footprint pixels: {int(valid.sum()):,}")
    print(f"domain (off-catalogue, belief>{BELIEF_THRESHOLD}) pixels: {n_valid:,}")
    print(f"dots emitted: {n_dots:,}")
    print(f"dot density: {n_dots / max(n_valid, 1) * 1e6:.2f} dots per million domain px")

    run_name = "GEMSDOE30-geothermal-corridor-offcat-d3"
    # Portal note must be complete (never truncated mid-word) and <=140 chars.
    note = (
        f"Geothermal corridor off-cat: Q-volcanics x paleo-springs x 2m probes, "
        f"SGMC-gated, 3px Poisson disk, {n_dots} dots"
    )
    if len(note) > 140:
        raise ValueError(f"submission note exceeds 140 characters ({len(note)})")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"{run_name}-{timestamp}.tif"

    manifest = write_submission_file(
        probabilities,
        TEMPLATE,
        output_path,
        note=note,
        run_name=run_name,
        outside_value=float("nan"),
    )
    print(json.dumps(manifest, indent=2))
    print(f"\nGeoTIFF file: {output_path}")
    print(f"Published GEMS format compliant: {manifest['published_format_compliant']}")
    print(f"Note ({len(note)}/140): {note}")
    return 0 if manifest["published_format_compliant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
