#!/usr/bin/env python3
"""Build a unique, machine-validated GeoTIFF submission — H1 blind thermal corridor.

Scientific hypothesis (H1, rank 1 in docs/research/blind-thermal-corridor/hypotheses.md):
  Concealed intrabasin faults that host blind Great Basin geothermal systems are
  under-represented in the USGS/INGENIOUS Quaternary catalogue, which favours
  well-constrained surface-rupturing traces.  A concealed fault cutting Quaternary
  cover and discharging geothermal fluid should co-locate with paleogeothermal
  sinter/tufa springs and shallow 2 m temperature anomalies, *without* requiring young
  Quaternary volcanism.  Dots are placed only in the 3–30 px (300 m–3 km) off-SGMC
  annulus — the hidden-splay band the DrivenData staff clarify may host new faults
  (<300 m from a mapped trace, thread 11536) — while the SGMC core (0–2 px) is excluded
  to avoid the unmasked-flank false-positive penalty.

  This lane differs from every shipped lane:
    * geothermal-corridor: volcanics(0.4)+paleo(0.3)+probes(0.3), SGMC-proximity boost,
      >2 px off structure everywhere. H1 removes volcanics, removes the SGMC boost, and
      restricts dots to the 3–30 px concealed-splay annulus.
    * G30-TAD / PTA-1: subsurface tilt-depth + radiometric K alteration + MT cover step.
    * G30-S19 / S20: lidar scarp + radiometrics on topographic scarps.
    * d28-poisson / h33: pure Poisson dot fields on the scarp catalogue.
  None uses paleo-springs × 2 m probes in the concealed-splay annulus with volcanics
  excluded as the primary driver.

Run: .venv/bin/python scripts/build_blind_thermal_corridor_submission.py
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
OUTPUT_DIR = Path("docs/downloads")

# External public layers (all verified on the competition grid, EPSG:32611,
# 100 m pixels, 3730 x 3292). Source/receipt: data/external/external_receipt.json
# (USGS SGMC state geologic maps NV/CA; DOE GDR INGENIOUS submission 1391).
LAYERS = {
    "paleo": Path("data/external/derived_gdr_paleo_100m_u8.tif"),
    "probes2m": Path("data/external/derived_gdr_2m_probes_100m_u8.tif"),
    "sgmc": Path("data/external/derived_sgmc_faults_100m_u8.tif"),
}

# Decay length in metres, matched to the 300 m DTI kernel support.
DECAY_M = 1000.0
# Equal weight to the two geothermal expressions; volcanics intentionally excluded.
W_PALEO, W_PROBES = 0.5, 0.5
# Only pixels with meaningful co-located thermal/fluid evidence become dot candidates.
BELIEF_THRESHOLD = 0.15
# Concealed-splay annulus: hidden faults may sit <300 m (3 px) from mapped traces but
# the 0–2 px flank is unmasked and pays the FP penalty, so dots live at 3–30 px.
ANNULUS_INNER_PX = 3.0
ANNULUS_OUTER_PX = 30.0
# Sparse emission budget comparable to the scored 0.24–0.28 family.
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

    paleo = read_layer(LAYERS["paleo"]) > 0
    probes = read_layer(LAYERS["probes2m"]) > 0
    sgmc = read_layer(LAYERS["sgmc"]) > 0

    with rasterio.open(TEMPLATE) as tmpl:
        template_data = tmpl.read(1)
        valid = np.isfinite(template_data)
        valid &= tmpl.dataset_mask() != 0

    # Distance-decay proximity to each geothermal signature.
    p = decay_surface(paleo, DECAY_M)
    t = decay_surface(probes, DECAY_M)

    # Equal-weight linear pool of thermal + fluid signatures; NO volcanics, NO SGMC
    # proximity boost (we do not reward being on mapped structure).
    belief = W_PALEO * p + W_PROBES * t
    belief = np.where(valid, belief, 0.0)
    span = float(belief.max() - belief.min())
    if span <= 0:
        print("BLOCKED: degenerate belief surface", file=sys.stderr)
        return 2
    belief = (belief - belief.min()) / span
    belief = np.clip(belief, 0.0, 1.0)

    # Off-catalogue concealed-splay annulus: > ANNULUS_INNER_PX and <= ANNULUS_OUTER_PX
    # from mapped SGMC structure; SGMC core (0-2 px) excluded pixel-exactly.
    distance_to_sgmc_px = distance_transform_edt(~sgmc)
    domain = (
        valid
        & (distance_to_sgmc_px > ANNULUS_INNER_PX)
        & (distance_to_sgmc_px <= ANNULUS_OUTER_PX)
        & (belief > BELIEF_THRESHOLD)
    )
    belief = np.where(domain, belief, 0.0)

    # Sparse binary emission: Poisson-disk thinned to the 300 m kernel scale (3 px),
    # capped at MAX_DOTS most confident dots.
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
    print(f"domain (concealed-splay annulus, belief>{BELIEF_THRESHOLD}) pixels: {n_valid:,}")
    print(f"dots emitted: {n_dots:,}")
    print(f"dot density: {n_dots / max(n_valid, 1) * 1e6:.2f} dots per million domain px")

    run_name = "GEMSDOE30-blind-thermal-corridor-h1-annulus"
    note = (
        f"Blind thermal corridor off-cat: paleo-springs x 2m probes, "
        f"SGMC 3-30px annulus, volcanics-excluded, 3px Poisson disk, {n_dots} dots"
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
