#!/usr/bin/env python3
"""Holdout-DTI report for the CTD-1 concealed stepover candidate vs baselines.

Protocol (component-holdout-v3-blockstats-20261025 / buffered-quadrant whole
components): whole 8-connected catalogue components are split into stand-in
``hidden`` (new-fault proxy) and ``known`` (masked exactly as the organizer
masks USGS/INGENIOUS pixels, thread 11516).  Four spatial blocks are scored and
pooled; a paired geographic-block bootstrap (2000 replicates, seed 3071) gives
the 95% CI.  These are HOLDOUT-DTI proxy values on a catalogue split -- NOT
organizer scores and NOT leaderboard forecasts.

Arms (all 40,000 dots for a fair comparison):
  * ctd1      - candidate: concealed stepover belief (MT basement step x gravity
                x magnetic edge) AND (volcanics x paleo-springs), EDGE emission.
  * proximity - catalogue-echo baseline: exp(-d/1 km) around known traces.
  * random    - null control: uniform dots over the scored domain.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.emission import metric_optimal_emission, poisson_disk_select
from gemsdoe30.holdout import (fp_weight_field, masked_dti_by_blocks,
                               split_components, spatial_bootstrap)

RAW = Path("data/raw")
BLOCK_PX = 32  # ~371 geographic blocks (3.2 km tiles) for the block bootstrap
REPLICATES = 2000
SEED = 3071
N_DOTS = 40_000


def load_grids():
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
    return valid, catalogue


def proximity_field(known, valid):
    dist = distance_transform_edt(~known, sampling=(100.0, 100.0))
    return np.where(valid, np.exp(-dist / 1000.0), 0.0)


def emit(prediction, domain):
    """EDGE metric-optimal emission, capped at N_DOTS dots."""
    return metric_optimal_emission(prediction.astype(np.float32), domain,
                                   belief_cut=0.0, pool_limit=300_000,
                                   max_dots=N_DOTS)


def main() -> int:
    valid, catalogue = load_grids()
    hidden, known, n_components = split_components(catalogue, seed=31, stratify=32)
    scored = valid & ~known
    fp_weight = fp_weight_field(hidden, known)

    rng = np.random.default_rng(11)
    scored_flat = np.argwhere(scored)
    random_mask = np.zeros(scored.shape, dtype=bool)
    if scored_flat.size:
        pick = rng.choice(scored_flat.shape[0], size=min(N_DOTS, scored_flat.size),
                          replace=False)
        random_mask[tuple(scored_flat[pick].T)] = True

    candidate_path = sys.argv[1] if len(sys.argv) > 1 else \
        "docs/downloads/gems30-ctd1-concealed-stepper-20261027T172620Z-c39a9264.tif"
    candidate_name = Path(candidate_path).stem
    with rasterio.open(candidate_path) as ds:
        cand = ds.read(1).astype(np.float32)
    cand = np.where(valid & np.isfinite(cand), cand, 0.0)
    cand_dots = emit(cand, scored)

    prox = proximity_field(known, valid)
    prox_dots = emit(prox, scored)

    arms = {
        candidate_name: cand_dots.astype(np.float32),
        "proximity": prox_dots.astype(np.float32),
        "random": random_mask.astype(np.float32),
    }

    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "component-holdout-v3-blockstats-20261025; "
                    "buffered-quadrant-whole-components-v1-20261025",
        "candidate": candidate_name,
        "candidate_path": str(candidate_path),
        "frame": {
            "catalogue_pixels": int(catalogue.sum()),
            "components": int(n_components),
            "hidden_pixels": int(hidden.sum()),
            "known_pixels": int(known.sum()),
            "scored_pixels": int(scored.sum()),
            "block_px": BLOCK_PX,
        },
        "arms": {},
    }

    block_rows = {}
    for name, pred in arms.items():
        t0 = time.time()
        mdb = masked_dti_by_blocks(pred, hidden, known, valid,
                                   block_size_px=BLOCK_PX, fp_weight=fp_weight)
        pooled = mdb["pooled"]
        boot = spatial_bootstrap({name: mdb["spatial_blocks"]}, candidate=name,
                                 replicates=REPLICATES, seed=SEED)
        arm = boot["arms"][name]
        report["arms"][name] = {
            "dots": int((pred > 0).sum()),
            "pooled_dti": float(pooled["dti"]),
            "tp_weight": float(pooled["tp_weight"]),
            "fp_weight": float(pooled["fp_weight"]),
            "truth_pixels": float(pooled["truth_pixels"]),
            "ci95": arm["ci95"],
            "withheld_positives": arm["withheld_positives"],
            "seconds": round(time.time() - t0, 2),
        }
        block_rows[name] = mdb["spatial_blocks"]

    # Paired deltas vs each baseline.
    all_blocks = {name: block_rows[name] for name in arms}
    boot2 = spatial_bootstrap(all_blocks, candidate=candidate_name,
                              replicates=REPLICATES, seed=SEED)
    for baseline in ("proximity", "random"):
        report["arms"][f"{candidate_name}_minus_{baseline}"] = boot2["candidate_minus"][baseline]

    out = Path(f"docs/research/{candidate_name}-holdout-report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
