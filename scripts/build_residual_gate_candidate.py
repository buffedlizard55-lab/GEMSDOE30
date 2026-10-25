#!/usr/bin/env python3
"""Build the review-hypothesis-3 residual-ridge-gate GeoTIFF on the real competition grid.

Same pre-registered recipe as scripts/residual_gate_holdout.py (arm A, review hypothesis 3), with the FULL
training catalogue as the visible set (the real competition setting). Writes a
published-format single-band float32 GeoTIFF (NaN outside the template footprint),
validates it, runs the registry duplicate check, and writes a run-card sidecar.

The output is a downloadable, format-valid research artifact (review hypothesis 3). Its holdout verdict is
NEGATIVE (see docs/research/2026-10-25/residual-gate-verdict.md); it is not approved for a
weekly submission slot by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gemsdoe30.emission import poisson_disk_select_ordered  # noqa: E402
from gemsdoe30.fields import distance_to_mask  # noqa: E402
from gemsdoe30.residual_gate import fit_residual, gated_residual_ridge  # noqa: E402
from gemsdoe30.submission import (  # noqa: E402
    validate_submission_file,
    valid_template_mask,
    write_submission_file,
)

RADIUS_PX = 4
GATE_M = 3000.0
REGRESSORS = ("iso_grav_anom", "det_elev", "depth_to_base_surf")
TARGET = "rtp"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=ROOT / "data/processed/features_raw.npy")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/processed/manifest.json")
    parser.add_argument("--labels", type=Path, default=ROOT / "data/raw/labels.tif")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--downloads", type=Path, default=ROOT / "docs/downloads")
    parser.add_argument("--receipts", type=Path, default=ROOT / "docs/research/2026-10-25")
    parser.add_argument("--registry", type=Path, default=ROOT / "docs/research/priority-site-pins.json")
    args = parser.parse_args()

    import rasterio

    names = {n.split(" - ")[0]: i for i, n in
             enumerate(json.loads(args.manifest.read_text())["feature_band_names"])}
    feats = np.load(args.features, mmap_mode="r")
    with rasterio.open(args.template) as ds:
        footprint = valid_template_mask(ds, np)
    with rasterio.open(args.labels) as ds:
        labels = ds.read(1)
    catalogue = (labels == 1) & footprint
    scored = footprint & ~catalogue

    residual, fit_info = fit_residual(
        np.asarray(feats[names[TARGET]], dtype=np.float64),
        [np.asarray(feats[names[r]], dtype=np.float64) for r in REGRESSORS],
        footprint,
    )
    belief = gated_residual_ridge(residual, footprint, distance_to_mask(catalogue), gate_m=GATE_M)
    belief[~scored] = 0.0
    rows, cols = poisson_disk_select_ordered(belief, RADIUS_PX, threshold=0.0,
                                             mask=scored & (belief > 0))
    prediction = np.zeros(belief.shape, dtype=np.float32)
    prediction[rows, cols] = 1.0
    dots = int(prediction.sum())
    if dots == 0:
        raise SystemExit("no dots emitted; refusing to write an empty submission")

    digest = hashlib.sha256(
        f"h-a-residual-ridge-gate:{RADIUS_PX}:{GATE_M}:{dots}".encode()
    ).hexdigest()[:8]
    stem = f"gemsdoe30-h3a-residual-ridge-gate-p400-{digest}"
    output = args.downloads / f"{stem}-nan.tif"
    note = "GEMSDOE30 review-hyp3 residual-ridge gate, 3km catalogue corridor, 400m Poisson"
    write_submission_file(prediction, args.template, output, note=note,
                          run_name="residual-gate-session-2026-10-25",
                          metadata_path=args.downloads / f"{stem}-nan.json")
    report = validate_submission_file(output, args.template)
    if not report.passed:
        print(report.to_dict())
        return 1

    novelty_path = args.receipts / "residual-gate-novelty-dots.json"
    novelty = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_novelty.py"), str(output), "--template", str(args.template),
         "--registry", str(args.registry), "--stage", "dots", "--output", str(novelty_path)],
        capture_output=True, text=True, cwd=ROOT,
    )
    novelty_result = json.loads(novelty_path.read_text())

    sidecar_path = args.downloads / f"{stem}-nan.json"
    sidecar = json.loads(sidecar_path.read_text()) if sidecar_path.exists() else {}
    sidecar.update({
        "run_card": {
            "schema_version": 1,
            "hypothesis": "Review hypothesis 3 (docs/research/2026-10-25/review.md): magnetically quiet, gravity-consistent residual ridges of rtp after linear iso-gravity/elevation/basement removal, gated 3 km from mapped traces.",
            "mechanism": "Gravity-consistent magnetically quiet corridors as fluid-altered or fractured zones.",
            "non_fault_mimic": "Nonmagnetic sediment fill",
            "holdout_dti": "see docs/research/2026-10-25/residual-gate-holdout-buffer0.json (HOLDOUT-DTI, component-holdout-v2-footprint-20261025)",
            "verdict": "negative",
            "organizer_score": None,
            "label": "NOT ORGANIZER-CONFIRMED",
        },
        "dots": dots,
        "residual_fit": fit_info,
        "raster_sha256": sha256(output),
        "validator": report.to_dict(),
        "novelty_dots_decision": novelty_result["decision"],
        "novelty_returncode": novelty.returncode,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "submission_name": stem,
        "submission_note": note,
        "note_length": len(note),
    })
    sidecar_path.write_text(json.dumps(sidecar, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "dots": dots, "sha256": sidecar["raster_sha256"],
                      "validator_passed": report.passed, "novelty": novelty_result["decision"],
                      "note_length": len(note)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
