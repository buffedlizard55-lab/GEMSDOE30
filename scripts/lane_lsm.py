#!/usr/bin/env python3
"""Lane G30-LSM: LiDAR scarp morphology fused with geophysics, no catalogue-proximity input.

Preregistration: docs/research/2026-10-25-lsm/preregistration.md (SHA-256 recorded at start).
Stages (run in order):
  build  - label-free layers -> data/processed/lsm/extra.npy (+ receipt)
  e1     - v3 spatially blocked holdout: core19 / geo25 / lsm42, canaries, paired bootstrap (GATE)
  e2     - full-catalogue models; independent SGMC-new frame; owner-scored frame validity
  final  - production TIFFs (zeros-outside primary, NaN-outside alternate), novelty, validation, run card
Shared tools only: gemsdoe30.holdout / emission / submission / novelty and the shared
sampler/predictor in scripts/feature_value_holdout.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from gemsdoe30.emission import poisson_disk_select_ordered  # noqa: E402
from gemsdoe30.holdout import (EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION,  # noqa: E402
                              masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds)
from gemsdoe30.lidar_morphology import (GEO_LAYERS, LIDAR_LAYERS, TRANSFORM_VERSION,  # noqa: E402
                                       StackedFeatures, geo_layers, lidar_layers)
from scripts.feature_value_holdout import fit_standardiser, predict_grid, sample_training_pixels  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-25-lsm"
CACHE = ROOT / "data/processed/lsm"
SEED = 3070
GATE_BUDGET = 44090        # TDX-1-exact primary emission budget (v3 comparability)
PROD_BUDGET = 38000        # leaderboard-informed operating point (H33 = 37,654)
RADIUS = 3.0
EXCLUDE_PX = 2             # barren <=2 px band (leaderboard differentials)
CORE19_RECORDED = {"value": 0.13982105545350187, "ci95": [0.12417828328479568, 0.15590455150138017],
                   "source": "docs/research/texture-displacement/run-card.json (TDX-1, same folds/budget)"}
SGMC = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"


def sha(path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(name, data) -> None:
    path = REPORT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, allow_nan=False, default=float) + "\n")


def band_names() -> list[str]:
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    return [n.split(" - ")[0] for n in manifest["feature_band_names"]]


def load_base():
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT / "data/processed/labels.npy") > 0.5
    valid = np.load(ROOT / "data/processed/valid.npy")
    labels &= valid
    return base, labels, valid


def arms(base):
    extra = np.load(CACHE / "extra.npy", mmap_mode="r")
    names19 = band_names()
    geo = StackedFeatures(base, extra[: len(GEO_LAYERS)], names=names19 + list(GEO_LAYERS))
    lsm = StackedFeatures(base, extra, names=names19 + list(GEO_LAYERS) + list(LIDAR_LAYERS))
    core = StackedFeatures(base, names=names19)
    return {"core19": core, "geo25": geo, "lsm42": lsm}


def fit_model(x, y, *, seed, iterations=120, leaves=31):
    median, scale = fit_standardiser(x)
    x = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(max_iter=iterations, learning_rate=0.1, max_leaf_nodes=leaves,
                                           early_stopping=False, random_state=seed)
    with threadpool_limits(limits=2):
        model.fit((x - median) / scale, y)
    return model, median, scale


def select(surface, mask, count):
    rows, cols = poisson_disk_select_ordered(surface, RADIUS, mask=mask, max_kept=count)
    if len(rows) != count:
        raise ValueError(f"capacity gate: pool supplies {len(rows)} of {count} dots")
    dots = np.zeros(surface.shape, dtype=np.float32)
    dots[rows, cols] = 1.0
    return dots


# ----------------------------------------------------------------------------- build
def stage_build():
    base, labels, valid = load_base()
    CACHE.mkdir(parents=True, exist_ok=True)
    names = list(GEO_LAYERS) + list(LIDAR_LAYERS)
    out = np.lib.format.open_memmap(CACHE / "extra.npy", mode="w+", dtype=np.float32,
                                    shape=(len(names),) + valid.shape)
    i = 0
    for name, layer in geo_layers(base, valid):
        assert name == names[i], (name, names[i])
        out[i] = layer
        i += 1
        print("built", name, flush=True)
    lidar_path = ROOT / "data/raw/external/lidar_scarp_features_u8.tif"
    with rasterio.open(lidar_path) as ds, rasterio.open(TEMPLATE) as tpl:
        if (ds.shape, ds.crs, ds.transform) != (tpl.shape, tpl.crs, tpl.transform) or ds.count != 12:
            raise ValueError("LiDAR stack grid mismatch")
        stack = ds.read()
    for name, layer in lidar_layers(stack, valid):
        assert name == names[i], (name, names[i])
        out[i] = layer
        i += 1
        print("built", name, flush=True)
    del stack
    out.flush()
    receipt = {"transform_version": TRANSFORM_VERSION, "layers": names,
               "module_sha256": sha(ROOT / "src/gemsdoe30/lidar_morphology.py"),
               "lidar_stack_sha256": sha(lidar_path), "extra_npy_sha256": sha(CACHE / "extra.npy"),
               "uses_catalogue_geometry": False, "uses_registry_values": False,
               "uses_template_values_as_features": False,
               "lidar_coverage_fraction_of_footprint": float((np.asarray(out[len(GEO_LAYERS)]) > 0)[valid].mean())}
    dump("feature-receipt.json", receipt)
    print(json.dumps(receipt, indent=1))


# ----------------------------------------------------------------------------- canaries
def canaries(stack, names, x, y, fold, seed):
    domain = fold["score_valid"] & ~fold["visible"]
    rng = np.random.default_rng(seed + 10000)
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(domain & ~fold["hidden"])
    negatives = rng.choice(negatives, min(60000, negatives.size), replace=False)
    test = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])
    rr, cc = np.unravel_index(test, domain.shape)
    values_all = stack[:, rr, cc].T.astype(np.float32)
    rows = []
    for j, name in enumerate(names):
        model, median, scale = fit_model(x[:, j:j + 1], y, seed=seed + j, iterations=32, leaves=7)
        filled = np.where(np.isfinite(values_all[:, j]), values_all[:, j], median[0])
        raw = float(roc_auc_score(target, filled)) if np.ptp(filled) > 0 else 0.5
        with threadpool_limits(limits=2):
            prob = model.predict_proba(((filled - median[0]) / scale[0])[:, None])[:, 1]
        uni = float(roc_auc_score(target, prob)) if np.ptp(prob) > 0 else 0.5
        rows.append({"feature": name, "label": "LEAKAGE-CANARY AUC (not DTI)", "raw_auc": raw,
                     "raw_auc_either_direction": max(raw, 1 - raw),
                     "univariate_training_only_hgb_auc": uni,
                     "alarm_above_0_90": bool(max(raw, 1 - raw) > 0.90 or max(uni, 1 - uni) > 0.90),
                     "heldout_positives": int(positives.size), "sampled_negatives": int(negatives.size)})
    return rows


# ----------------------------------------------------------------------------- E1
def stage_e1(max_seconds: float):
    from scipy.ndimage import distance_transform_edt
    t0 = time.monotonic()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dump("started-e1.json", {"started_utc": started, "preregistration_sha256": sha(REPORT / "preregistration.md"),
                             "script_sha256": sha(__file__), "experiment": 1,
                             "arms": ["core19", "geo25", "lsm42"]})
    base, labels, valid = load_base()
    stacks = arms(base)
    names = stacks["lsm42"].names
    blocks = {e: {a: [] for a in stacks} for e in ("primary", "production")}
    folds, canary_rows = [], []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)
    for fold in spatial_segment_folds(labels, valid, buffer_px=17):
        f = fold["fold"]
        hidden_total += fold["hidden"]
        active = fold["score_valid"] & ~fold["visible"]
        far = distance_transform_edt(~fold["visible"]) > EXCLUDE_PX
        n_primary = int(round(GATE_BUDGET * active.sum() / valid.sum()))
        n_prod = int(round(PROD_BUDGET * active.sum() / valid.sum()))
        x_all, y = sample_training_pixels(stacks["lsm42"], fold["visible"], fold["train_mask"],
                                          negatives_per_positive=6, seed=SEED + f)
        print(f"fold {f}: {len(y)} training samples; canaries", flush=True)
        canary_rows.append({"fold": f, "features": canaries(stacks["lsm42"], names, x_all, y, fold, SEED + f)})
        dump("canaries-partial.json", {"folds": canary_rows})
        row = {**{k: v for k, v in fold["metadata"].items() if k != "hidden_component_ids"},
               "dot_budget_primary": n_primary, "dot_budget_production": n_prod, "arms": {}}
        for arm, stack in stacks.items():
            k = stack.shape[0]
            model, median, scale = fit_model(x_all[:, :k], y, seed=SEED + f)
            with threadpool_limits(limits=2):
                pred = predict_grid(model, stack, median, scale, active)
            res = {}
            for emission, mask, count in (("primary", active, n_primary), ("production", active & far, n_prod)):
                dots = select(pred, mask, count)
                score = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"], fold["score_valid"],
                                             block_size_px=128)
                blocks[emission][arm].extend(score["spatial_blocks"])
                res[emission] = {kk: vv for kk, vv in score["pooled"].items()}
            row["arms"][arm] = res
            print(f"fold {f} {arm}: primary {res['primary']['dti']:.4f} production {res['production']['dti']:.4f} "
                  f"(fold-local HOLDOUT-DTI, {time.monotonic() - t0:.0f}s)", flush=True)
            del model, pred
            if time.monotonic() - t0 > max_seconds:
                raise TimeoutError("experiment time cap reached; stop without retuning")
        folds.append(row)
        del x_all, y
    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("each withheld positive must be counted exactly once")
    summary = {e: spatial_bootstrap(blocks[e], candidate="lsm42", replicates=2000, seed=3071) for e in blocks}
    dump("bootstrap-blocks-e1.json", {"label": "per-128px-block sufficient statistics (tp, fp, truth) for E1",
                                      "blocks": blocks})
    first = REPORT / "results-e1.first-execution.json"
    if first.exists():
        # Deterministic re-execution: every pooled value and CI must match the first execution.
        previous = json.loads(first.read_text())["summary"]
        for e in summary:
            for arm, v in summary[e]["arms"].items():
                old_v = previous[e]["arms"][arm]
                if abs(v["value"] - old_v["value"]) > 1e-12 or any(abs(a - b) > 1e-12 for a, b in zip(v["ci95"], old_v["ci95"])):
                    raise AssertionError(f"re-execution differs from first execution: {e}/{arm}")
        print("re-execution reproduces first execution exactly", flush=True)
    alarms = [dict(fold=c["fold"], **r) for c in canary_rows for r in c["features"] if r["alarm_above_0_90"]]
    p, q = summary["primary"], summary["production"]
    gate = {
        "primary_beats_core19_ci": bool(p["candidate_minus"]["core19"]["value"] > 0
                                        and p["candidate_minus"]["core19"]["ci95"][0] > 0),
        "production_point_ge_core19": bool(q["candidate_minus"]["core19"]["value"] >= 0),
        "no_canary_alarm": not alarms,
        "core19_reproduces_recorded": bool(abs(p["arms"]["core19"]["value"] - CORE19_RECORDED["value"]) < 1e-6),
    }
    gate["passed"] = bool(gate["primary_beats_core19_ci"] and gate["production_point_ge_core19"] and gate["no_canary_alarm"])
    result = {"schema_version": 1, "experiment": 1, "label": "HOLDOUT-DTI (catalogue-recovery proxy; NOT organizer score)",
              "evaluator_version": EVALUATOR_VERSION, "protocol_version": SEGMENT_PROTOCOL_VERSION,
              "preregistration_sha256": sha(REPORT / "preregistration.md"), "script_sha256": sha(__file__),
              "feature_receipt": json.loads((REPORT / "feature-receipt.json").read_text()),
              "core19_recorded_tdx1": CORE19_RECORDED, "summary": summary, "folds": folds,
              "feature_canaries": canary_rows, "canary_alarms": alarms, "gate": gate,
              "elapsed_seconds": round(time.monotonic() - t0, 1)}
    dump("results-e1.json", result)
    for e in summary:
        print(e, json.dumps({a: (round(v["value"], 5), [round(c, 5) for c in v["ci95"]]) for a, v in summary[e]["arms"].items()}),
              json.dumps({a: (round(v["value"], 5), [round(c, 5) for c in v["ci95"]]) for a, v in summary[e]["candidate_minus"].items()}))
    print("GATE", json.dumps(gate))


# ----------------------------------------------------------------------------- E2 (+ production surface)
def stage_e2():
    from scipy.ndimage import distance_transform_edt
    from gemsdoe30.holdout import fp_weight_field
    t0 = time.monotonic()
    dump("started-e2.json", {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "preregistration_sha256": sha(REPORT / "preregistration.md"),
                             "script_sha256": sha(__file__), "experiment": 2})
    base, labels, valid = load_base()
    stacks = arms(base)
    dist = distance_transform_edt(~labels)
    prod_mask = valid & ~labels & (dist > EXCLUDE_PX)
    with rasterio.open(SGMC) as ds:
        sgmc = (ds.read(1) > 0) & valid & (dist > 3)
    scored = valid & ~labels
    fpw = fp_weight_field(sgmc & scored, ~scored)
    x_all, y = sample_training_pixels(stacks["lsm42"], labels, valid, negatives_per_positive=6, seed=SEED)
    CACHE.mkdir(parents=True, exist_ok=True)
    frame_rows, block_rows = {}, {}
    for arm in ("core19", "lsm42"):
        stack = stacks[arm]
        model, median, scale = fit_model(x_all[:, :stack.shape[0]], y, seed=SEED)
        with threadpool_limits(limits=2):
            surface = predict_grid(model, stack, median, scale, valid)
        np.save(CACHE / f"surface_{arm}.npy", surface)
        dots = select(surface, prod_mask, PROD_BUDGET)
        np.save(CACHE / f"dots_{arm}.npy", dots.astype(np.uint8))
        s = masked_dti_by_blocks(dots, sgmc, labels, valid, fp_weight=fpw, block_size_px=128)
        frame_rows[arm] = s["pooled"]
        block_rows[arm] = s["spatial_blocks"]
        print(arm, "SGMC-new frame", round(s["pooled"]["dti"], 5), f"{time.monotonic() - t0:.0f}s", flush=True)
        del model, surface
    # Frame validity: owner-scored isolated-dot rasters through the identical frame.
    cal = json.loads((REPORT / "leaderboard-calibration.json").read_text())
    from scripts.leaderboard_calibration import resolve, read
    owner = []
    for name, info in cal["rasters"].items():
        a = read(resolve(info["path"]))
        s = masked_dti_by_blocks(np.where(valid, a, 0).astype(np.float32), sgmc, labels, valid, fp_weight=fpw,
                                 block_size_px=128)
        owner.append({"raster": name, "owner_reported_score": info["owner_reported_score"],
                      "frame_dti": s["pooled"]["dti"], "dots": info["dots_in_scored_domain"]})
        block_rows[name] = s["spatial_blocks"]
    from scipy.stats import spearmanr
    rho = spearmanr([o["owner_reported_score"] for o in owner], [o["frame_dti"] for o in owner])
    boot = spatial_bootstrap({k: block_rows[k] for k in ("lsm42", "core19", "GEMSDOE32 H33-B2", "GEMSDOE25/30 d2.8")},
                             candidate="lsm42", replicates=2000, seed=3072)
    result = {"schema_version": 1, "experiment": 2,
              "label": "HOLDOUT-DTI on independent SGMC-new frame (proxy; NOT organizer score)",
              "frame": {"truth": "SGMC fault pixels > 3 px from catalogue", "truth_pixels": int(sgmc.sum()),
                        "mask": "catalogue pixels (pixel-exact)", "emission": f"{PROD_BUDGET} dots, r={RADIUS}, dist>{EXCLUDE_PX}px"},
              "arms": frame_rows, "bootstrap_vs_references": boot,
              "owner_scored_frame_validity": {"rows": owner, "spearman": float(rho.statistic), "p_value": float(rho.pvalue),
                                              "n": len(owner), "note": "owner scores UNVERIFIED; small, highly correlated set"},
              "confirmation_lsm42_ge_core19": bool(frame_rows["lsm42"]["dti"] >= frame_rows["core19"]["dti"]),
              "elapsed_seconds": round(time.monotonic() - t0, 1)}
    dump("results-e2.json", result)
    print(json.dumps({k: v for k, v in result.items() if k in ("arms", "confirmation_lsm42_ge_core19")}, indent=1, default=float))
    print("frame validity spearman", rho)
    print(json.dumps(boot["arms"], indent=1, default=float))


# ----------------------------------------------------------------------------- E3 (crest-line emission)
def stage_e3():
    """Frozen amendment preregistration-e3.md: same lsm42 predictions, plain vs crest-line placement."""
    from scipy.ndimage import distance_transform_edt
    from gemsdoe30.emission import crest_mask
    from gemsdoe30.holdout import fp_weight_field
    t0 = time.monotonic()
    dump("started-e3.json", {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "preregistration_sha256": sha(REPORT / "preregistration.md"),
                             "amendment_sha256": sha(REPORT / "preregistration-e3.md"),
                             "script_sha256": sha(__file__), "experiment": 3})
    e1 = json.loads((REPORT / "results-e1.json").read_text())
    base, labels, valid = load_base()
    stack = arms(base)["lsm42"]
    blocks = {e: {"lsm42": [], "lsm42_ridge": []} for e in ("primary", "production")}
    folds = []
    for fold in spatial_segment_folds(labels, valid, buffer_px=17):
        f = fold["fold"]
        active = fold["score_valid"] & ~fold["visible"]
        far = distance_transform_edt(~fold["visible"]) > EXCLUDE_PX
        n_primary = int(round(GATE_BUDGET * active.sum() / valid.sum()))
        n_prod = int(round(PROD_BUDGET * active.sum() / valid.sum()))
        x_all, y = sample_training_pixels(stack, fold["visible"], fold["train_mask"],
                                          negatives_per_positive=6, seed=SEED + f)
        model, median, scale = fit_model(x_all, y, seed=SEED + f)
        with threadpool_limits(limits=2):
            pred = predict_grid(model, stack, median, scale, active)
        crest = crest_mask(pred, active)
        row = {"fold": f, "crest_pixels": int(crest.sum()), "active_pixels": int(active.sum()), "arms": {}}
        for arm, extra in (("lsm42", None), ("lsm42_ridge", crest)):
            res = {}
            for emission, mask, count in (("primary", active, n_primary), ("production", active & far, n_prod)):
                m = mask if extra is None else (mask & extra)
                dots = select(pred, m, count)
                score = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
                blocks[emission][arm].extend(score["spatial_blocks"])
                res[emission] = score["pooled"]
            row["arms"][arm] = res
        e1_dti = e1["folds"][f]["arms"]["lsm42"]["primary"]["dti"]
        row["reproduces_e1_lsm42"] = bool(abs(row["arms"]["lsm42"]["primary"]["dti"] - e1_dti) < 1e-9)
        folds.append(row)
        print(f"fold {f}: plain {row['arms']['lsm42']['primary']['dti']:.4f} ridge {row['arms']['lsm42_ridge']['primary']['dti']:.4f} "
              f"crest px {row['crest_pixels']} reproduces E1 {row['reproduces_e1_lsm42']} ({time.monotonic() - t0:.0f}s)", flush=True)
        del model, pred, x_all, y
    summary = {e: spatial_bootstrap(blocks[e], candidate="lsm42_ridge", replicates=2000, seed=3071) for e in blocks}
    p, q = summary["primary"], summary["production"]
    gate = {"primary_beats_lsm42_ci": bool(p["candidate_minus"]["lsm42"]["value"] > 0 and p["candidate_minus"]["lsm42"]["ci95"][0] > 0),
            "production_point_ge_lsm42": bool(q["candidate_minus"]["lsm42"]["value"] >= 0),
            "plain_reproduces_e1": all(r["reproduces_e1_lsm42"] for r in folds)}
    gate["passed"] = bool(gate["primary_beats_lsm42_ci"] and gate["production_point_ge_lsm42"])
    # E3b: SGMC-new frame, production surface (reported, not gated).
    dist = distance_transform_edt(~labels)
    surface = np.load(CACHE / "surface_lsm42.npy")
    crest_full = crest_mask(surface, valid)
    ridge_dots = select(surface, valid & ~labels & (dist > EXCLUDE_PX) & crest_full, PROD_BUDGET)
    np.save(CACHE / "dots_lsm42_ridge.npy", ridge_dots.astype(np.uint8))
    with rasterio.open(SGMC) as ds:
        sgmc = (ds.read(1) > 0) & valid & (dist > 3)
    scored = valid & ~labels
    fpw = fp_weight_field(sgmc & scored, ~scored)
    from scripts.leaderboard_calibration import read, resolve
    refs = {"lsm42_ridge": ridge_dots, "lsm42": np.load(CACHE / "dots_lsm42.npy").astype(np.float32),
            "GEMSDOE32 H33-B2": np.where(valid, read(resolve("gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")), 0),
            "GEMSDOE25/30 d2.8": np.where(valid, read(resolve("data/raw/scored/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif")), 0)}
    frame_blocks = {k: masked_dti_by_blocks(v.astype(np.float32), sgmc, labels, valid, fp_weight=fpw, block_size_px=128)["spatial_blocks"]
                    for k, v in refs.items()}
    sgmc_boot = spatial_bootstrap(frame_blocks, candidate="lsm42_ridge", replicates=2000, seed=3072)
    result = {"schema_version": 1, "experiment": 3, "label": "HOLDOUT-DTI (catalogue-recovery proxy; NOT organizer score)",
              "evaluator_version": EVALUATOR_VERSION, "protocol_version": SEGMENT_PROTOCOL_VERSION,
              "preregistration_sha256": sha(REPORT / "preregistration.md"), "amendment_sha256": sha(REPORT / "preregistration-e3.md"),
              "script_sha256": sha(__file__), "summary": summary, "folds": folds, "gate": gate,
              "production_crest_pixels": int((crest_full & valid & ~labels & (dist > EXCLUDE_PX)).sum()),
              "sgmc_frame_reported_not_gated": sgmc_boot, "elapsed_seconds": round(time.monotonic() - t0, 1)}
    dump("results-e3.json", result)
    for e in summary:
        print(e, json.dumps({a: (round(v["value"], 5), [round(c, 5) for c in v["ci95"]]) for a, v in summary[e]["arms"].items()}),
              json.dumps({a: (round(v["value"], 5), [round(c, 5) for c in v["ci95"]]) for a, v in summary[e]["candidate_minus"].items()}))
    print("SGMC", json.dumps({a: round(v["value"], 5) for a, v in sgmc_boot["arms"].items()}),
          json.dumps({a: (round(v["value"], 5), [round(c, 5) for c in v["ci95"]]) for a, v in sgmc_boot["candidate_minus"].items()}))
    print("GATE-E3", json.dumps(gate))


# ----------------------------------------------------------------------------- final
def reference_paths():
    refs = []
    reg = json.loads((ROOT / "docs/research/texture-displacement/registry.json").read_text())
    refs += [("registry:" + r["site"], ROOT / r["path"]) for r in reg["rasters"]]
    add = ROOT / "docs/research/texture-displacement/registry-parallel-addendum.json"
    if add.exists():
        for r in json.loads(add.read_text()).get("rasters", []):
            if "path" in r and (ROOT / r["path"]).exists():
                refs.append(("addendum:" + str(r.get("site")), ROOT / r["path"]))
    refs += [("owner-scored", p) for p in sorted((ROOT / "data/raw/scored").glob("*.tif"))]
    refs += [("repo-download", p) for p in sorted((ROOT / "docs/downloads").glob("*.tif")) if "LSM42" not in p.name]
    seen, out = set(), []
    for tag, p in refs:
        if p.exists() and p.resolve() not in seen:
            seen.add(p.resolve())
            out.append((tag, p))
    return out


def novelty(candidate, valid, stage):
    from gemsdoe30.novelty import compare, decision, rank_cache
    cached = rank_cache(candidate, valid)
    rows, by_hash, errors = [], {}, []
    with rasterio.open(TEMPLATE) as tpl:
        grid = (tpl.shape, tpl.crs, tpl.transform)
    for tag, path in reference_paths():
        try:
            with rasterio.open(path) as ds:
                if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != grid:
                    raise ValueError(f"grid mismatch {path}")
                ref = ds.read(1).astype(np.float32)
            ref = np.where(np.isfinite(ref), ref, 0.0)
            h = hashlib.sha256(np.ascontiguousarray(ref[valid]).tobytes()).hexdigest()
            if h not in by_hash:
                by_hash[h] = compare(candidate, ref, valid, stage=stage, cached_ranks=cached)
            rows.append({"reference": str(path.relative_to(ROOT)), "source": tag, "values_sha256": h, **by_hash[h]})
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
    dec = decision(rows, stage=stage, registry_complete=not errors)
    max_rho = max((r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None), default=None)
    max_ov = max((r["candidate_fraction_within_3px_of_reference"] or 0.0 for r in rows), default=None)
    return {"stage": stage, "decision": dec, "references_compared": len(rows), "unique_value_rasters": len(by_hash),
            "errors": errors, "max_spearman": max_rho, "max_fraction_within_3px": max_ov if stage == "dots" else None,
            "thresholds": {"spearman": 0.90, "fraction_within_3px": 0.70},
            "scope": "observed inventory: 105 hash-pinned priority-site rasters + addendum + 11 owner-scored + repo downloads",
            "rows": rows}


def production_surface(base, labels, valid):
    """Deterministically refit the full-catalogue lsm42 model (seed 3070) and rebuild its surface.

    IR-30-084: the first 4 KiB page of both saved E2 surface files was found zeroed (373
    row-0 pixels) although the E2 dots had been selected from the correct in-memory values.
    The production surface is therefore never trusted from disk: it is recomputed, must
    round-trip through disk bit-exactly, and must reproduce the E2-evaluated dots exactly.
    """
    from scipy.ndimage import distance_transform_edt
    stack = arms(base)["lsm42"]
    x_all, y = sample_training_pixels(stack, labels, valid, negatives_per_positive=6, seed=SEED)
    model, median, scale = fit_model(x_all, y, seed=SEED)
    with threadpool_limits(limits=2):
        surface = predict_grid(model, stack, median, scale, valid)
    path = CACHE / "surface_lsm42_final.npy"
    np.save(path, surface)
    if not np.array_equal(np.load(path), surface):
        raise AssertionError("production surface failed its disk round-trip")
    dist = distance_transform_edt(~labels)
    dots = select(surface, valid & ~labels & (dist > EXCLUDE_PX), PROD_BUDGET)
    if not np.array_equal(dots.astype(np.uint8), np.load(CACHE / "dots_lsm42.npy")):
        raise AssertionError("recomputed production dots differ from the E2-evaluated dots")
    dump("production-surface-receipt.json", {
        "label": "deterministic recomputation of the E2 production surface (IR-30-084)",
        "surface_sha256": hashlib.sha256(np.ascontiguousarray(surface).tobytes()).hexdigest(),
        "reproduces_e2_dots_exactly": True, "seed": SEED,
        "row0_zero_pixels_inside_footprint": int(((surface[0] == 0) & valid[0]).sum())})
    return surface


def duplicate_stop_card(stem, identity, e1, e2, e3, surf_nov, dot_nov, dots, labels, valid):
    """Protocol: >70 % of dots within 3 px of a registry raster => log duplicate and stop."""
    from scipy.ndimage import distance_transform_edt
    dist = distance_transform_edt(~labels)
    bins = [0, 1.5, 2.5, 5.5, 10.5, 15.5, 30.5, 50.5, 1e9]
    hist = np.histogram(dist[dots > 0], bins=bins)[0]
    offenders = sorted((r for r in dot_nov["rows"] if (r["candidate_fraction_within_3px_of_reference"] or 0) > 0.70),
                       key=lambda r: -r["candidate_fraction_within_3px_of_reference"])
    seen, flagged = set(), []
    for r in offenders:
        if r["values_sha256"] in seen:
            continue
        seen.add(r["values_sha256"])
        flagged.append({"reference": r["reference"], "source": r["source"], "reference_dots": r["reference_dots"],
                        "fraction_within_3px": r["candidate_fraction_within_3px_of_reference"],
                        "spearman": r["spearman_full_footprint"],
                        "dense_reference_non_discriminating": r["reference_dots"] > 150000})
    p = e1["summary"]["primary"]
    card = {
        "schema_version": 3, "run_id": stem, "lane": "G30-LSM (self-assigned; no lane paragraph supplied, IR-30-078)",
        "hypothesis": "H-LSM-1: 1 m-LiDAR scarp morphology fused with GeoDAWN geophysics finds unmapped faults better than geophysics alone, without any catalogue-proximity input.",
        "mechanism": "HGB on 19 raw bands + 6 geophysical edge transforms + 17 decoded 3DEP-LiDAR scarp descriptors; Poisson r=300 m dots, >200 m off catalogue.",
        "non_fault_mimic": "Lake Lahontan paleo-shorelines; fluvial terrace risers/channel banks; roads, canals, mines",
        "verdict": "duplicate-stop", "ok_to_submit": False,
        "stop_reason": ("Dot-stage duplicate under the owner protocol: >70 % of the 38,000 final dots fall within 3 px of "
                        f"{len([f for f in flagged if not f['dense_reference_non_discriminating']])} sparse registry rasters "
                        "(chance level 14-18 %). The habitat model learned that catalogue-like pixels sit next to mapped "
                        "faults, so its dots concentrate where proximity-based lanes already placed theirs."),
        "duplicate_references": flagged,
        "dots_by_catalogue_distance_px": dict(zip(["1", "2", "3-5", "6-10", "11-15", "16-30", "31-50", ">50"], hist.tolist())),
        "candidate_values_sha256": identity, "tiff_published": False,
        "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EVALUATOR_VERSION, "protocol_version": SEGMENT_PROTOCOL_VERSION,
                    "withheld_positives": p["arms"]["lsm42"]["withheld_positives"],
                    "lsm42": p["arms"]["lsm42"], "core19": p["arms"]["core19"], "geo25": p["arms"]["geo25"],
                    "lsm42_minus": p["candidate_minus"], "production_emission": e1["summary"]["production"],
                    "gate": e1["gate"],
                    "scope": "spatially blocked whole-segment catalogue-recovery proxy; NOT organizer performance"},
        "independent_frame": {"label": "HOLDOUT-DTI (SGMC-new frame)", "arms": e2["arms"],
                              "owner_scored_frame_spearman": e2["owner_scored_frame_validity"]["spearman"],
                              "bootstrap": e2["bootstrap_vs_references"]["arms"],
                              "lsm42_minus": e2["bootstrap_vs_references"]["candidate_minus"]},
        "e3_crest_line_emission": {"verdict": "negative (gate failed; plain emission kept per amendment)", "gate": e3["gate"],
                                   "v3_primary_ridge_minus_plain": e3["summary"]["primary"]["candidate_minus"]["lsm42"],
                                   "v3_production_ridge_minus_plain": e3["summary"]["production"]["candidate_minus"]["lsm42"],
                                   "sgmc_frame_reported_not_gated": e3["sgmc_frame_reported_not_gated"]["candidate_minus"]},
        "feature_canaries": {"alarms": len(e1["canary_alarms"]), "features_per_fold": len(e1["feature_canaries"][0]["features"]),
                             "max_auc": max(max(r["raw_auc_either_direction"], r["univariate_training_only_hgb_auc"])
                                            for c in e1["feature_canaries"] for r in c["features"])},
        "novelty": {"surface": {k: surf_nov[k] for k in ("decision", "max_spearman", "references_compared", "scope")},
                    "dots": {k: dot_nov[k] for k in ("decision", "max_spearman", "max_fraction_within_3px", "references_compared", "scope")}},
        "validator": "not run: protocol stops at a dot-stage duplicate before any TIFF is written",
        "submission_name": None, "submission_note": None,
        "experiments_run": 3, "experiment_cap": 3, "time_cap_hours": 2,
        "executions": {"E1": "2 (second = deterministic re-execution to persist block statistics; identical)", "E2": 1, "E3": 1},
        "experiment_seconds": round(json.loads((REPORT / "results-e1.first-execution.json").read_text())["elapsed_seconds"]
                                    + e2["elapsed_seconds"] + e3["elapsed_seconds"], 1),
        "slot_selection": "not performed", "organizer_score": None,
        "lesson": ("Run the dot-stage novelty check on full-catalogue production dots BEFORE spending experiments; "
                   "a catalogue-trained habitat model needs an explicit far-field allocation to be unique."),
    }
    dump("run-card.json", card)
    print(json.dumps({k: card[k] for k in ("run_id", "verdict", "stop_reason")}, indent=1))


def stage_final():
    from scipy.ndimage import distance_transform_edt
    from gemsdoe30.submission import validate_submission_file, write_submission_file
    e1 = json.loads((REPORT / "results-e1.json").read_text())
    e2 = json.loads((REPORT / "results-e2.json").read_text())
    e3 = json.loads((REPORT / "results-e3.json").read_text())
    if e3["gate"]["passed"]:
        raise SystemExit("E3 passed: the crest-line emission must be wired in before building the artifact")
    base, labels, valid = load_base()
    surface = production_surface(base, labels, valid)
    surf_nov = novelty(np.where(valid, surface, 0).astype(np.float32), valid, "surface")
    dump("novelty-surface.json", surf_nov)
    print("surface novelty", surf_nov["decision"], surf_nov["max_spearman"], flush=True)
    if surf_nov["decision"] == "duplicate-stop":
        raise SystemExit("duplicate-stop at surface stage; no placement")
    dist = distance_transform_edt(~labels)
    dots = select(surface, valid & ~labels & (dist > EXCLUDE_PX), PROD_BUDGET)
    if not np.array_equal(dots.astype(np.uint8), np.load(CACHE / "dots_lsm42.npy")):
        raise AssertionError("final dots differ from the E2-evaluated dots")
    dot_nov = novelty(dots, valid, "dots")
    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    dot_nov["candidate_values_sha256"] = identity
    dump("novelty-dots.json", dot_nov)
    print("dot novelty", dot_nov["decision"], dot_nov["max_spearman"], dot_nov["max_fraction_within_3px"], flush=True)
    stem = f"gems30-LSM42-{PROD_BUDGET}-20261025-{identity[:12]}"
    if dot_nov["decision"] == "duplicate-stop":
        duplicate_stop_card(stem, identity, e1, e2, e3, surf_nov, dot_nov, dots, labels, valid)
        raise SystemExit("duplicate-stop at dot stage: logged; no TIFF published; no further experiment")
    promote = bool(e1["gate"]["passed"] and e2["confirmation_lsm42_ge_core19"]
                   and surf_nov["decision"].startswith("novelty-check-passed")
                   and dot_nov["decision"].startswith("novelty-check-passed"))
    note = ("LSM42: 1m-LiDAR scarp morphology+GeoDAWN geophysics HGB, no proximity input; "
            f"{PROD_BUDGET} r300m dots >200m off catalogue")
    if len(note) > 140:
        raise ValueError("note exceeds 140 characters")
    out_zero = ROOT / f"docs/downloads/{stem}-zeros.tif"
    out_nan = ROOT / f"docs/downloads/{stem}-nan.tif"
    m0 = write_submission_file(dots, TEMPLATE, out_zero, note=note, run_name=stem + "-zeros", outside_value=0.0)
    mn = write_submission_file(dots, TEMPLATE, out_nan, note=note, run_name=stem + "-nan", outside_value=float("nan"))
    checks = {}
    for tag, path in (("zeros", out_zero), ("nan", out_nan)):
        rep = validate_submission_file(path, TEMPLATE).to_dict()
        with rasterio.open(path) as ds, rasterio.open(TEMPLATE) as tpl:
            a = ds.read(1)
            checks[tag] = {"shared_validator_passed": rep["passed"], "shared_validator": rep,
                           "no_nan_inside_footprint": bool(np.isfinite(a[valid]).all()),
                           "inside_values_in_0_1": bool(((a[valid] >= 0) & (a[valid] <= 1)).all()),
                           "whole_array_finite": bool(np.isfinite(a).all()),
                           "whole_array_in_0_1": bool(np.isfinite(a).all() and ((a >= 0) & (a <= 1)).all()),
                           "unique_values_inside": sorted(np.unique(a[valid]).tolist()),
                           "crs_match": ds.crs == tpl.crs, "shape_match": ds.shape == tpl.shape,
                           "transform_match": ds.transform == tpl.transform,
                           "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
                           "dots": int((a[valid] > 0).sum()),
                           "dots_on_catalogue": int((a[labels] > 0).sum()),
                           "dots_within_2px_of_catalogue": int(((a > 0) & valid & (dist <= 2)).sum()),
                           "sha256": sha(path), "bytes": path.stat().st_size}
    if not (checks["zeros"]["shared_validator_passed"] and checks["zeros"]["whole_array_in_0_1"]
            and checks["nan"]["shared_validator_passed"] and checks["zeros"]["dots_on_catalogue"] == 0):
        raise AssertionError("format gate failed")
    dump("validation.json", checks)
    p = e1["summary"]["primary"]
    card = {
        "schema_version": 3, "run_id": stem, "lane": "G30-LSM (self-assigned; no lane paragraph supplied, IR-30-078)",
        "hypothesis": "H-LSM-1: 1 m-LiDAR scarp morphology fused with GeoDAWN geophysics finds unmapped faults better than geophysics alone, without any catalogue-proximity input.",
        "mechanism": "HGB on 19 raw bands + 6 geophysical edge transforms + 17 decoded 3DEP-LiDAR scarp descriptors (step, crest-toe dipole, facing step, scarp/channel ratio, strike persistence); Poisson r=300 m dots, >200 m off catalogue.",
        "non_fault_mimic": "Lake Lahontan paleo-shorelines; fluvial terrace risers/channel banks; roads, canals, mines",
        "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EVALUATOR_VERSION, "protocol_version": SEGMENT_PROTOCOL_VERSION,
                    "withheld_positives": p["arms"]["lsm42"]["withheld_positives"],
                    "lsm42": p["arms"]["lsm42"], "core19": p["arms"]["core19"], "geo25": p["arms"]["geo25"],
                    "lsm42_minus": p["candidate_minus"], "production_emission": e1["summary"]["production"],
                    "scope": "spatially blocked whole-segment catalogue-recovery proxy; NOT organizer performance"},
        "independent_frame": {"label": "HOLDOUT-DTI (SGMC-new frame)", "arms": e2["arms"],
                              "owner_scored_frame_spearman": e2["owner_scored_frame_validity"]["spearman"],
                              "bootstrap": e2["bootstrap_vs_references"]["arms"]},
        "feature_canaries": {"alarms": len(e1["canary_alarms"]), "features_per_fold": len(e1["feature_canaries"][0]["features"]),
                             "max_auc": max(max(r["raw_auc_either_direction"], r["univariate_training_only_hgb_auc"])
                                            for c in e1["feature_canaries"] for r in c["features"])},
        "novelty": {"surface": {k: surf_nov[k] for k in ("decision", "max_spearman", "references_compared", "scope")},
                    "dots": {k: dot_nov[k] for k in ("decision", "max_spearman", "max_fraction_within_3px", "references_compared", "scope")}},
        "files": {"primary_zeros_outside": {"path": str(out_zero.relative_to(ROOT)), "sha256": checks["zeros"]["sha256"]},
                  "alternate_nan_outside": {"path": str(out_nan.relative_to(ROOT)), "sha256": checks["nan"]["sha256"]}},
        "validator": {"zeros": {k: v for k, v in checks["zeros"].items() if k != "shared_validator"},
                      "nan": {k: v for k, v in checks["nan"].items() if k != "shared_validator"}},
        "submission_name": stem, "submission_note": note, "note_chars": len(note),
        "e3_crest_line_emission": {"verdict": "negative (gate failed; plain emission kept per amendment)",
                                   "gate": e3["gate"],
                                   "v3_primary_ridge_minus_plain": e3["summary"]["primary"]["candidate_minus"]["lsm42"],
                                   "v3_production_ridge_minus_plain": e3["summary"]["production"]["candidate_minus"]["lsm42"],
                                   "sgmc_frame_reported_not_gated": e3["sgmc_frame_reported_not_gated"]["candidate_minus"]},
        "experiments_run": 3, "experiment_cap": 3, "time_cap_hours": 2,
        "executions": {"E1": "2 (second = deterministic re-execution to persist block statistics; identical)",
                       "E2": 1, "E3": 1},
        "experiment_seconds": round(json.loads((REPORT / "results-e1.first-execution.json").read_text())["elapsed_seconds"]
                                    + e2["elapsed_seconds"] + e3["elapsed_seconds"], 1),
        "leaderboard_expectation": ("PROJECTION, not a score: no offline frame is a validated leaderboard proxy "
                                    "(frame-validity.json). On the only equal-budget comparison with H33 (independent "
                                    "SGMC-new frame) LSM42 trails H33; P(beating owner-reported 0.2778) is judged low-to-moderate."),
        "verdict": "promote" if promote else "negative",
        "ok_to_submit": promote,
        "slot_selection": "not performed (separate selector step within the weekly cap)",
        "organizer_score": None,
    }
    dump("run-card.json", card)
    print(json.dumps({k: card[k] for k in ("run_id", "verdict", "submission_note")}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["build", "e1", "e2", "e3", "final"])
    ap.add_argument("--max-seconds", type=float, default=5400)
    a = ap.parse_args()
    {"build": stage_build, "e1": lambda: stage_e1(a.max_seconds), "e2": stage_e2, "e3": stage_e3,
     "final": stage_final}[a.stage]()


if __name__ == "__main__":
    main()
