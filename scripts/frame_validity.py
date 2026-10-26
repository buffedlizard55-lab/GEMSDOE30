#!/usr/bin/env python3
"""Cross-family validity of the SGMC-new frame against OWNER-REPORTED (unverified) scores.

Scores every locally available owner-scored raster (all belief families, dense and dotted)
through the identical SGMC-new frame used by lane G30-LSM E2 and reports Spearman/Kendall
correlations. Diagnostic only: owner scores are unverified and the set is small.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.leaderboard_calibration import read, resolve, DOTTED  # noqa: E402

SCORED = [("GEMSDOE19 h19-5 (continuous)", 0.1922, "data/raw/scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"),
          ("GEMSDOE19 h19-4 (continuous)", 0.1894, "data/raw/scored/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan.tif"),
          ("GEMSDOE16 h16-1 ridges", 0.1855, "data/raw/scored/gems16-h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan.tif"),
          ("GEMSDOE10 h28 dotted-ridge", 0.1839, "data/raw/scored/gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif"),
          ("GEMSDOE8 Hedge-v2", 0.1563, "data/raw/scored/8GEMSDOE_Hedge-v2_submission.tif"),
          ("GEMSDOE ens12", 0.1563, "data/raw/scored/gemsdoe-ens12-adopted-7f00890a.tif"),
          ("GEMSDOE10 h25 ctx-ridge", 0.1280, "data/raw/scored/gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif"),
          ("GEMSDOE13 lattice-s5", 0.0904, "data/raw/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"),
          ("GEMSDOE9 PLACEHOLDER", 0.0107, "data/raw/scored/gemsdoe9-PLACEHOLDER-2314b599.tif")]


def main():
    import rasterio
    from scipy.ndimage import distance_transform_edt
    from scipy.stats import kendalltau, spearmanr
    from gemsdoe30.holdout import fp_weight_field, masked_dti_by_blocks
    labels = np.load(ROOT / "data/processed/labels.npy") > 0.5
    valid = np.load(ROOT / "data/processed/valid.npy")
    labels &= valid
    dist = distance_transform_edt(~labels)
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & valid & (dist > 3)
    scored = valid & ~labels
    fpw = fp_weight_field(sgmc & scored, ~scored)
    rows = []
    for name, score, path in SCORED + [(n, s, p) for n, s, p in DOTTED if "solo-d28" not in n]:
        a = read(resolve(path))
        a = np.where(valid, np.clip(a, 0, 1), 0).astype(np.float32)
        r = masked_dti_by_blocks(a, sgmc, labels, valid, fp_weight=fpw)["pooled"]
        rows.append({"raster": name, "owner_reported_score": score, "frame_dti": r["dti"],
                     "tp_weight": r["tp_weight"], "fp_weight": r["fp_weight"],
                     "positive_mass": float(a[scored].sum())})
        print(f"{name:34s} owner={score:.4f} frame={r['dti']:.5f} mass={rows[-1]['positive_mass']:.0f}", flush=True)
    own = [r["owner_reported_score"] for r in rows]
    frm = [r["frame_dti"] for r in rows]
    out = {"label": "DIAGNOSTIC; owner scores UNVERIFIED; frame = SGMC fault px >3 px from catalogue, catalogue masked",
           "n": len(rows), "spearman": float(spearmanr(own, frm).statistic), "kendall": float(kendalltau(own, frm).statistic),
           "spearman_non_d_family": float(spearmanr(own[:len(SCORED)], frm[:len(SCORED)]).statistic), "rows": rows}
    (ROOT / "docs/research/2026-10-25-lsm/frame-validity.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
