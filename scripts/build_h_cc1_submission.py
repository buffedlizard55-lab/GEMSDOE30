#!/usr/bin/env python3
"""Write the H-CC1 exp-3 dispersed raster through the shared writer (NaN outside, sidecar).

Recomputes the exact selection used by scripts/contact_coincidence_holdout.py (imported,
not re-implemented) and checks that the dot count matches the recorded experiment receipt.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage  # noqa: E402

import contact_coincidence_holdout as cc  # noqa: E402
from gemsdoe30.submission import write_submission_file  # noqa: E402

RAW = REPO / "data/raw"
OUT = REPO / "docs/downloads/gemsdoe30-h-cc1-dispersed3px-32058dots-nan.tif"
RECEIPT = REPO / "docs/research/2026-10-25/contact-coincidence-holdout.json"


def main() -> int:
    with rasterio.open(RAW / "sample_submission.tif") as t:
        valid = np.isfinite(t.read(1))
    with rasterio.open(RAW / "training_features.tif") as f:
        rtp = cc.read_layer(f, "rtp")
        grav = cc.read_layer(f, "iso_grav_anom")
    analysis = valid & np.isfinite(rtp) & np.isfinite(grav)
    eligible = ndimage.binary_erosion(analysis, iterations=cc.PRE["edge_erode_px"])
    z_mag = cc.gradient_magnitude_z(rtp, analysis, cc.PRE["hp_sigma_px"])
    z_grav = cc.gradient_magnitude_z(grav, analysis, cc.PRE["hp_sigma_px"])
    coincidence = np.sqrt(np.clip(z_mag, 0, None) * np.clip(z_grav, 0, None))
    coincidence = np.where(eligible, coincidence, 0.0)
    cand_prob, _ = cc.select_top(coincidence, eligible, cc.PRE["top_fraction"], cc.PRE["floor_p"])
    n_budget = int(np.count_nonzero(cand_prob))
    mask = cc.greedy_dispersed(coincidence, eligible, cc.PRE["exp3_pool_fraction"], n_budget,
                               cc.PRE["exp3_min_spacing_px"])
    receipt = json.loads(RECEIPT.read_text())
    expected = receipt["arms"]["H-CC1_dispersed_exp3"]["dots"]
    if int(mask.sum()) != expected:
        raise SystemExit(f"dot count {int(mask.sum())} != receipt {expected}; refusing to write")

    probs = np.where(valid, mask.astype(np.float32), np.nan).astype(np.float32)
    note = ("H-CC1 dispersed 3px contact-coincidence, 32058 dots; catalogue-proxy holdout-DTI 0.0539 "
            "(unscored, not slot-approved)")
    sidecar = write_submission_file(
        probs, RAW / "sample_submission.tif", OUT,
        note=note, run_name="gemsdoe30-h-cc1-dispersed3px-32058dots",
        metadata_path=OUT.with_suffix(".json"),
    )
    print(json.dumps({k: sidecar[k] for k in sorted(sidecar) if k in
                      ("sha256", "output", "published_format_compliant")}, indent=2, default=str))
    print("dots", int(mask.sum()), "wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
