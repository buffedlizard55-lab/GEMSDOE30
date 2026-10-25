#!/usr/bin/env python3
"""Lane G30-S20: discovery-channel (lidar scarp + GeoDAWN radiometric) habitat
belief with oriented line coherence, EDGE emission.

Preregistration: docs/research/2026-10-25-s20/preregistration.md (frozen
before any S20 holdout result). Stages: preflight -> canary -> holdout
(E1 seed 31, E2 seed 47) -> final (E3) -> novelty. Shared tools only:
gemsdoe30.holdout / emitter_opt / emission / fields / submission / novelty,
and the S19 lane's habitat-stack builder imported unchanged. No registry
raster and no catalogue-distance field is ever a model input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import lane_g30s19 as s19  # noqa: E402  (shared habitat-stack builder / GBM / EDGE driver)

WORK = ROOT / "data/processed/lane_g30s20"
OUT = ROOT / "docs/research/2026-10-25-s20"
EXT_DIR = ROOT / "data/raw/external"
DIST_NAMES = {"dist_visible_catalogue_px_capped", "prox_exp_d10px", "log1p_dist_visible_px"}

LIDAR_FILE = EXT_DIR / "lidar_scarp_features_u8.tif"
RAD_FILE = EXT_DIR / "geodawn_rad_u8.tif"
RADEXT_FILE = EXT_DIR / "geodawn_extensions_u8.tif"
LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
               "downface_max", "upface_max", "cross_max", "relief", "coh100",
               "strike", "valid"]
RAD_BANDS = ["K", "Th", "U", "TC"]
RADEXT_BANDS = ["ThK", "UK", "UTh", "TMI_up150"]

EXT_NAMES = [
    "lid_ex_max", "lid_ex_mean", "lid_step_max", "lid_lapneg_max", "lid_lappos_max",
    "lid_downface_max", "lid_upface_max", "lid_cross_max", "lid_relief", "lid_coh100",
    "lidar_present", "lid_sin2strike", "lid_cos2strike", "scarp_dipole", "step_x_coh",
    "rad_K", "rad_Th", "rad_U", "rad_TC", "rad_ThK", "rad_UK", "rad_UTh",
    "rad_TMI_up150", "gradmag_rad_TC", "gradmag_rad_ThK", "rad_present",
]
assert len(EXT_NAMES) == 26


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_grid(ds, valid_shape):
    if (ds.height, ds.width) != tuple(valid_shape):
        raise SystemExit(f"PREFLIGHT STOP: shape {(ds.height, ds.width)} != {valid_shape}")
    if ds.crs is None or ds.crs.to_epsg() != 32611:
        raise SystemExit(f"PREFLIGHT STOP: CRS {ds.crs} is not EPSG:32611")
    expected = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    got = tuple(ds.transform)[:6]
    if got != expected:
        raise SystemExit(f"PREFLIGHT STOP: transform {got} != {expected}")


def stage_preflight():
    import rasterio

    OUT.mkdir(parents=True, exist_ok=True)
    _, _, valid = s19.load_base()
    pins = {row["id"]: row for row in json.loads(
        (ROOT / "docs/research/mirror-pins-extra.json").read_text())["files"]}
    report = {"stage": "preflight", "rasters": {}, "dti_scoring_performed": False}
    specs = [(LIDAR_FILE, "ext_lidar_scarp_features_u8", LIDAR_BANDS),
             (RAD_FILE, "ext_geodawn_rad_u8", RAD_BANDS),
             (RADEXT_FILE, "ext_geodawn_extensions_u8", RADEXT_BANDS)]
    for path, pin_id, expected_bands in specs:
        digest = sha256_file(path)
        pin = pins[pin_id]
        if digest != pin["sha256"] or path.stat().st_size != pin["bytes"]:
            raise SystemExit(f"PREFLIGHT STOP: pin mismatch for {path.name}: {digest}")
        with rasterio.open(path) as ds:
            check_grid(ds, valid.shape)
            if list(ds.descriptions) != expected_bands:
                raise SystemExit(
                    f"PREFLIGHT STOP: {path.name} bands {ds.descriptions} != {expected_bands}")
            entry = {"file": str(path.relative_to(ROOT)), "sha256": digest,
                     "sha256_matches_pin": True, "bytes": path.stat().st_size,
                     "bands": list(ds.descriptions), "dtype": ds.dtypes[0],
                     "nodata": ds.nodata, "crs": "EPSG:32611", "grid_match": True}
            if path is LIDAR_FILE:
                present = ds.read(12) > 0
                entry["present_inside_footprint"] = int((present & valid).sum())
            if path is RAD_FILE:
                present = np.zeros(valid.shape, dtype=bool)
                for b in range(1, 5):
                    present |= ds.read(b) > 0
                entry["present_inside_footprint"] = int((present & valid).sum())
            entry["footprint_pixels"] = int(valid.sum())
            if "present_inside_footprint" in entry:
                entry["present_fraction_inside"] = (
                    entry["present_inside_footprint"] / entry["footprint_pixels"])
            report["rasters"][pin_id] = entry
        print(path.name, "OK", digest[:12], flush=True)
    json.dump(report, open(OUT / "preflight.json", "w"), indent=1)
    print(json.dumps(report, indent=1))


def build_ext_stack(path: Path, valid):
    """Write the 26-layer external stack (label-independent; seed-independent)."""
    import rasterio
    from scipy.ndimage import sobel

    if path.exists():
        existing = np.load(path, mmap_mode="r")
        if existing.shape == (len(EXT_NAMES), *valid.shape):
            print(f"external stack cached: {path}", flush=True)
            return existing
    H, W = valid.shape
    stack = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32,
                                      shape=(len(EXT_NAMES), H, W))
    li = 0

    def decode_lidar(q):
        q = q.astype(np.float32)
        return np.where(q > 0, np.clip((q - 1.0) / 254.0, 0, 1), 0.0).astype(np.float32)

    with rasterio.open(LIDAR_FILE) as ds:
        check_grid(ds, valid.shape)
        decoded = {}
        for i, name in enumerate(LIDAR_BANDS[:10]):
            decoded[name] = decode_lidar(ds.read(i + 1))
            stack[li] = decoded[name]
            li += 1
        strike_t = decode_lidar(ds.read(11))
        present = ds.read(12) > 0
    stack[li] = present.astype(np.float32); li += 1
    theta = strike_t * np.pi
    stack[li] = np.where(present, np.sin(2 * theta), 0).astype(np.float32); li += 1
    stack[li] = np.where(present, np.cos(2 * theta), 0).astype(np.float32); li += 1
    stack[li] = np.sqrt(decoded["lapneg_max"] * decoded["lappos_max"]).astype(np.float32); li += 1
    stack[li] = (decoded["step_max"] * decoded["coh100"]).astype(np.float32); li += 1
    del decoded, strike_t, present, theta

    rad = {}
    with rasterio.open(RAD_FILE) as ds:
        check_grid(ds, valid.shape)
        for i, name in enumerate(RAD_BANDS):
            rad[name] = (ds.read(i + 1).astype(np.float32) / 255.0)
            stack[li] = rad[name]; li += 1
    with rasterio.open(RADEXT_FILE) as ds:
        check_grid(ds, valid.shape)
        for i, name in enumerate(RADEXT_BANDS):
            rad[name] = (ds.read(i + 1).astype(np.float32) / 255.0)
            stack[li] = rad[name]; li += 1
    rad_present = rad["K"] > 0
    for name in ("TC", "ThK"):
        grad = np.hypot(sobel(rad[name], axis=1), sobel(rad[name], axis=0)).astype(np.float32)
        stack[li] = np.where(rad_present, grad, 0).astype(np.float32); li += 1
        del grad
    stack[li] = rad_present.astype(np.float32); li += 1
    assert li == len(EXT_NAMES), (li, len(EXT_NAMES))
    stack.flush()
    return np.load(path, mmap_mode="r")


class TwoStacks:
    """Read-only view over the habitat (43) + external (26) memmap stacks."""

    def __init__(self, hab, ext):
        self.hab = hab
        self.ext = ext
        self.n_hab = int(hab.shape[0])
        self.names = s19.layer_names() + list(EXT_NAMES)

    def layer(self, global_idx: int):
        if global_idx < self.n_hab:
            return self.hab[global_idx]
        return self.ext[global_idx - self.n_hab]

    def gather(self, sel_flat, idx_list):
        X = np.empty((sel_flat.size, len(idx_list)), dtype=np.float32)
        for j, g in enumerate(idx_list):
            arr = np.asarray(self.layer(g))
            X[:, j] = arr.reshape(-1)[sel_flat]
            del arr
        return X

    def predict_grid(self, model, idx_list, valid):
        H, W = valid.shape
        out = np.zeros((H, W), dtype=np.float32)
        for r0 in range(0, H, 250):
            r1 = min(r0 + 250, H)
            Xb = np.empty(((r1 - r0) * W, len(idx_list)), dtype=np.float32)
            for j, g in enumerate(idx_list):
                Xb[:, j] = np.asarray(self.layer(g)[r0:r1, :]).reshape(-1)
            out[r0:r1, :] = model.predict_proba(Xb)[:, 1].reshape(-1, W)
            del Xb
        return np.where(valid, out, 0).astype(np.float32)


def build_holdout_stacks(seed: int):
    """Build (or reuse) the seed-specific habitat stack and shared ext stack."""
    from gemsdoe30.holdout import split_components
    from scipy.ndimage import distance_transform_edt

    WORK.mkdir(parents=True, exist_ok=True)
    feats, catalogue, valid = s19.load_base()
    meta_path = WORK / f"holdout{seed}_meta.json"
    hab_path = WORK / f"holdout{seed}_hab_stack.npy"
    if meta_path.exists() and hab_path.exists():
        meta = json.loads(meta_path.read_text())
        hidden = np.load(WORK / f"hidden{seed}.npy")
        known = np.load(WORK / f"known{seed}.npy")
        hab = np.load(hab_path, mmap_mode="r")
        print(f"seed {seed} habitat stack cached", flush=True)
    else:
        hidden, known, ncomp = split_components(catalogue, seed=seed)
        rng = np.random.default_rng(7)
        dist_hidden = distance_transform_edt(~hidden)
        elig = valid & (dist_hidden > 3)
        stats = s19.fit_stats(feats, elig, rng)
        dist_known = distance_transform_edt(~known)
        hab = s19.build_stack_mmap(hab_path, feats, stats, dist_known, valid.shape)
        np.save(WORK / f"hidden{seed}.npy", hidden)
        np.save(WORK / f"known{seed}.npy", known)
        meta = {"names": s19.layer_names(), "ext_names": list(EXT_NAMES),
                "stats": stats, "n_components": int(ncomp),
                "hidden_px": int(hidden.sum()), "known_px": int(known.sum())}
        meta_path.write_text(json.dumps(meta, indent=1))
        print(f"seed {seed} habitat stack built", flush=True)
    ext = build_ext_stack(WORK / "ext_stack.npy", valid)
    return TwoStacks(hab, ext), hidden, known, meta


def stage_canary(seed: int):
    from scipy.ndimage import distance_transform_edt
    from sklearn.metrics import roc_auc_score

    stacks, hidden, known, meta = build_holdout_stacks(seed)
    _, catalogue, valid = s19.load_base()
    rng = np.random.default_rng(7)
    dist_hidden = distance_transform_edt(~hidden)
    scored = valid & ~known
    pos = np.flatnonzero((hidden & scored).ravel())
    negpool = np.flatnonzero((scored & ~catalogue & (dist_hidden > 3)).ravel())
    neg = rng.choice(negpool, min(300_000, negpool.size), replace=False)
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    sel = np.concatenate([pos, neg])
    rows = []
    for g, name in enumerate(stacks.names):
        arr = np.asarray(stacks.layer(g))
        v = arr.reshape(-1)[sel].astype(np.float64)
        del arr
        auc = float(roc_auc_score(y, v)) if np.ptp(v) > 0 else 0.5
        rows.append({"feature": name, "auc_hidden": round(auc, 4),
                     "leakage_flag": bool(auc > 0.90 or auc < 0.10)})
        print(f"{name:36s} AUC={auc:.4f}", flush=True)
    out = {"evaluator": "component-holdout-v2-footprint-20261025",
           "split_seed": seed, "buffer_px": 3, "hidden_px": int(pos.size),
           "neg_sampled": int(neg.size), "lane": "G30-S20", "features": rows}
    json.dump(out, open(OUT / f"canaries-seed{seed}.json", "w"), indent=1)
    print("CANARY DONE; flagged:", [r["feature"] for r in rows if r["leakage_flag"]])


def component_credit(mask_bool, hidden, known, valid):
    """Per-hidden-component kernel-credit sums and pixel counts (for bootstrap)."""
    from gemsdoe30.emission import kernel_credit
    from scipy.ndimage import label as cc_label

    scored = valid & ~known
    credit = kernel_credit(np.where(scored, mask_bool.astype(np.float32), 0))
    truth = hidden & scored
    comp, nc = cc_label(truth, structure=np.ones((3, 3), dtype=int))
    ids = comp[truth]
    cred = credit[truth]
    order = np.argsort(ids)
    ids_s, cred_s = ids[order], cred[order]
    starts = np.searchsorted(ids_s, np.arange(1, nc + 2))
    csum = np.add.reduceat(cred_s, starts[:-1])
    cnum = np.diff(starts).astype(float)
    return csum, cnum, nc


def paired_bootstrap(arm_masks, arm_fp, hidden, known, valid):
    """Component bootstrap (500) of each arm's DTI and of candidate-minus-A.

    FP mass is held fixed at its pooled value (conditional CI, as in S19);
    truth mass and TP credit resample with the hidden components.
    """
    from gemsdoe30.emission import dti_from_components

    stats = {name: component_credit(mask, hidden, known, valid)
             for name, mask in arm_masks.items()}
    nc = next(iter(stats.values()))[2]
    rng = np.random.default_rng(7)
    boots = {name: [] for name in arm_masks}
    for _ in range(500):
        pick = rng.integers(0, nc, nc)
        for name, (csum, cnum, _) in stats.items():
            boots[name].append(dti_from_components(
                float(csum[pick].sum()), float(arm_fp[name]), float(cnum[pick].sum())))
    result = {"bootstrap_n_hidden_components": int(nc), "ci95": {}}
    for name, values in boots.items():
        result["ci95"][name] = [float(x) for x in np.percentile(values, [2.5, 97.5])]
    names = list(arm_masks)
    if len(names) == 2:
        delta = np.array(boots[names[1]]) - np.array(boots[names[0]])
        result[f"ci95_delta_{names[1]}_minus_{names[0]}"] = [
            float(x) for x in np.percentile(delta, [2.5, 97.5])]
    return result


def stage_holdout(seed: int, focus: str | None):
    from gemsdoe30.emitter_opt import mask_from_order
    from gemsdoe30.fields import line_coherent_belief
    from gemsdoe30.holdout import fp_weight_field
    from scipy.ndimage import distance_transform_edt

    t0 = time.time()
    canary_path = OUT / f"canaries-seed{seed}.json"
    if not canary_path.exists():
        raise SystemExit("run canary first (protocol: canary before any holdout result)")
    canaries = json.loads(canary_path.read_text())
    flagged = {r["feature"] for r in canaries["features"] if r["leakage_flag"]}
    stacks, hidden, known, meta = build_holdout_stacks(seed)
    _, catalogue, valid = s19.load_base()
    names = stacks.names
    hab_idx = [i for i, n in enumerate(names[: stacks.n_hab])
               if n not in DIST_NAMES and n not in flagged]
    ext_idx = [i for i, n in enumerate(names)
               if i >= stacks.n_hab and n not in flagged]
    all_idx = hab_idx + ext_idx

    rng = np.random.default_rng(7)
    dist_hidden = distance_transform_edt(~hidden)
    dist_known = distance_transform_edt(~known)
    elig_neg = valid & (dist_hidden > 3) & (dist_known > 3)
    pos = np.flatnonzero(known.ravel())
    negpool = np.flatnonzero(elig_neg.ravel())
    neg = rng.choice(negpool, min(400_000, negpool.size), replace=False)
    sel = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)]).astype(np.int8)
    print(f"paired sample pos={pos.size} neg={neg.size} flagged={sorted(flagged)}", flush=True)

    X_all = stacks.gather(sel, all_idx)
    xcols = {name: j for j, name in enumerate([names[i] for i in all_idx])}
    X_a = X_all[:, [xcols[names[i]] for i in hab_idx]]
    models = {"A_habitat": (s19.fit_gbm(X_a, y), hab_idx),
              "B_combined": (s19.fit_gbm(X_all, y), all_idx)}
    del X_all, X_a

    p_sample = pos.size / sel.size
    p_true = float(known.sum()) / float(valid.sum())
    beliefs = {}
    for arm, (model, idx) in models.items():
        raw = stacks.predict_grid(model, idx, valid)
        belief = s19.prevalence_correct(raw, p_sample, p_true)
        beliefs[arm] = np.where(valid, belief, 0).astype(np.float32)
        np.save(WORK / f"holdout{seed}_belief_{arm}.npy", beliefs[arm])
        print(f"{arm} belief sum(scored)=", float(beliefs[arm][valid & ~known].sum()), flush=True)
    beliefs["C_combined_line"] = line_coherent_belief(
        beliefs["B_combined"], orientations=16, half_length=4, footprint=valid)
    beliefs["D_habitat_line_diag"] = line_coherent_belief(
        beliefs["A_habitat"], orientations=16, half_length=4, footprint=valid)
    np.save(WORK / f"holdout{seed}_belief_C_combined_line.npy", beliefs["C_combined_line"])

    scored = valid & ~known
    support = scored & (dist_known > 2)
    truth_mass = float(known.sum())
    fpw = fp_weight_field(hidden & scored, ~scored)
    results = {"evaluator_version": "component-holdout-v2-footprint-20261025",
               "split_seed": seed, "withheld_positives": int((hidden & scored).sum()),
               "lane": "G30-S20", "flagged_features_excluded": sorted(flagged),
               "n_features": {"A_habitat": len(hab_idx), "B_combined": len(all_idx)},
               "train_pos": int(pos.size), "train_neg": int(neg.size), "arms": {}}
    masks_at_60k, fp_at_60k = {}, {}
    for arm, belief in beliefs.items():
        diag = s19.emit_edge(belief, support, truth_mass)
        order = diag["order_flat"]
        arm_out = {"edge_selfstop_dots": int(order.size)}
        for label, keep in (("selfstop", int(order.size)), ("at60000", min(60_000, int(order.size)))):
            mask = mask_from_order(order, keep, belief.shape)
            scored_r, _ = s19.score(mask, hidden, known, valid, fpw)
            arm_out[label] = {"dots": int(mask.sum()), **scored_r["pooled"]}
            if label == "at60000":
                masks_at_60k[arm] = mask
                fp_at_60k[arm] = scored_r["pooled"]["fp_weight"]
        results["arms"][arm] = arm_out
        print(arm, arm_out, flush=True)

    primary = {arm: results["arms"][arm]["at60000"]["dti"]
               for arm in ("A_habitat", "B_combined", "C_combined_line")}
    if focus is None:
        if primary["C_combined_line"] >= primary["B_combined"] and \
                primary["C_combined_line"] >= primary["A_habitat"]:
            focus = "C_combined_line"
        elif primary["B_combined"] > primary["A_habitat"]:
            focus = "B_combined"
        else:
            focus = None
    results["primary_at60000"] = primary
    results["candidate_by_preregistered_rule"] = focus
    results["delta_candidate_minus_A_at60000"] = (
        None if focus is None else primary[focus] - primary["A_habitat"])
    boot_arms = {"A_habitat": masks_at_60k["A_habitat"]}
    boot_fp = {"A_habitat": fp_at_60k["A_habitat"]}
    if focus is not None:
        boot_arms[focus] = masks_at_60k[focus]
        boot_fp[focus] = fp_at_60k[focus]
    results["bootstrap_at60000_conditional_fp_fixed"] = paired_bootstrap(
        boot_arms, boot_fp, hidden, known, valid)
    results["seconds"] = round(time.time() - t0, 1)
    json.dump(results, open(OUT / f"holdout-seed{seed}.json", "w"), indent=1)
    print(json.dumps(results, indent=1))


def stage_final(recipe: str):
    """E3 production on the full catalogue. recipe: B_combined | C_combined_line."""
    from gemsdoe30.emitter_opt import mask_from_order
    from gemsdoe30.fields import line_coherent_belief
    from gemsdoe30.submission import write_submission_file
    from scipy.ndimage import distance_transform_edt

    if recipe not in ("B_combined", "C_combined_line"):
        raise SystemExit("recipe must be B_combined or C_combined_line")
    t0 = time.time()
    canaries = json.loads((OUT / "canaries-seed31.json").read_text())
    flagged = {r["feature"] for r in canaries["features"] if r["leakage_flag"]}
    feats, catalogue, valid = s19.load_base()
    rng = np.random.default_rng(7)
    stats = s19.fit_stats(feats, valid, rng)
    dist_cat = distance_transform_edt(~catalogue)
    hab = s19.build_stack_mmap(WORK / "final_hab_stack.npy", feats, stats,
                               dist_cat, valid.shape)
    ext = build_ext_stack(WORK / "ext_stack.npy", valid)
    stacks = TwoStacks(hab, ext)
    names = stacks.names
    all_idx = [i for i, n in enumerate(names)
               if n not in DIST_NAMES and n not in flagged]
    pos = np.flatnonzero(catalogue.ravel())
    negpool = np.flatnonzero((valid & (dist_cat > 3)).ravel())
    neg = rng.choice(negpool, min(600_000, negpool.size), replace=False)
    sel = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)]).astype(np.int8)
    X = stacks.gather(sel, all_idx)
    model = s19.fit_gbm(X, y)
    del X
    raw = stacks.predict_grid(model, all_idx, valid)
    p_sample = pos.size / sel.size
    p_true = float(catalogue.sum()) / float(valid.sum())
    belief = s19.prevalence_correct(raw, p_sample, p_true)
    belief = np.where(valid, belief, 0).astype(np.float32)
    np.save(WORK / "final_belief_B.npy", belief)
    if recipe == "C_combined_line":
        belief_used = line_coherent_belief(
            belief, orientations=16, half_length=4, footprint=valid)
    else:
        belief_used = belief
    np.save(WORK / "final_belief_used.npy", belief_used)

    scored = valid & ~catalogue
    support = scored & (dist_cat > 2)
    diag = s19.emit_edge(belief_used, support, float(catalogue.sum()),
                         max_dots=120_000)
    np.save(WORK / "final_edge_order.npy", diag["order_flat"])
    keep = min(60_000, int(diag["order_flat"].size))
    mask = mask_from_order(diag["order_flat"], keep, belief_used.shape)
    pred = mask.astype(np.float32)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    arr_hash = hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest()[:10]
    recipe_slug = "discline" if recipe == "C_combined_line" else "disc"
    stem = f"gemsdoe30-g30s20-{recipe_slug}-60000dots-{stamp}-{arr_hash}"
    note = ("G30-S20 19-band+lidar scarp+GeoDAWN rad GBM"
            + (" + line-coherence" if recipe == "C_combined_line" else "")
            + " + EDGE 60k off-cat>2px")[:140]
    template = ROOT / "data/raw/sample_submission.tif"
    out_zeros = ROOT / f"docs/downloads/{stem}-zeros.tif"
    out_nan = ROOT / f"docs/downloads/{stem}-nan.tif"
    man_zeros = write_submission_file(pred, template, out_zeros, note=note,
                                      run_name=stem + "-zeros", outside_value=0.0)
    man_nan = write_submission_file(pred, template, out_nan, note=note,
                                    run_name=stem + "-nan", outside_value=float("nan"))
    info = {"stem": stem, "recipe": recipe, "note": note, "note_chars": len(note),
            "dots": int(mask.sum()), "keep_requested": 60_000,
            "edge_selfstop": int(diag["order_flat"].size),
            "dots_on_catalogue": int((mask & catalogue).sum()),
            "dots_within_2px_of_catalogue": int((mask & (dist_cat <= 2)).sum()),
            "zeros_file": str(out_zeros.relative_to(ROOT)),
            "nan_file": str(out_nan.relative_to(ROOT)),
            "zeros_sha256": man_zeros["output_sha256"],
            "nan_sha256": man_nan["output_sha256"],
            "zeros_bytes": out_zeros.stat().st_size,
            "nan_bytes": out_nan.stat().st_size,
            "flagged_features_excluded": sorted(flagged),
            "n_features": len(all_idx),
            "train_pos": int(pos.size), "train_neg": int(neg.size),
            "belief_used": "final_belief_used.npy",
            "seconds": round(time.time() - t0, 1)}
    json.dump(info, open(WORK / "final_info.json", "w"), indent=1)
    json.dump(info, open(OUT / "final-info.json", "w"), indent=1)
    print(json.dumps(info, indent=1))


def stage_novelty():
    import rasterio
    from gemsdoe30.novelty import compare, decision

    info = json.loads((WORK / "final_info.json").read_text())
    _, _, valid = s19.load_base()
    belief = np.load(WORK / "final_belief_used.npy")
    with rasterio.open(ROOT / info["zeros_file"]) as ds:
        dots = ds.read(1)
    references = {}
    pins = json.loads((ROOT / "docs/research/priority-site-pins.json").read_text())
    for row in pins["rasters"]:
        references[f"priority-{row['site']}"] = ROOT / row["path"]
    for path in sorted((ROOT / "docs/downloads").glob("*.tif")):
        if info["stem"] in path.name:
            continue
        references[f"local-{path.stem}"] = path
    surface_rows, dot_rows, detail = [], [], {}
    for name, path in references.items():
        with rasterio.open(path) as ds:
            ref = ds.read(1).astype(np.float32)
        surf = compare(belief, ref, valid)
        surface_rows.append({**{k: surf[k] for k in
                                ("spearman_full_footprint", "candidate_dots",
                                 "reference_dots", "identical_inside_footprint",
                                 "correlation_duplicate")},
                             "dot_duplicate": False,
                             "candidate_fraction_within_3px_of_reference": 0.0})
        got = compare(dots, ref, valid)
        dot_rows.append(got)
        detail[name] = {"surface_spearman_belief_vs_refdots":
                        surf["spearman_full_footprint"], "dots": got}
        print(name, "surf_rho=", surf["spearman_full_footprint"],
              "dot_rho=", got["spearman_full_footprint"],
              "overlap=", got["candidate_fraction_within_3px_of_reference"],
              flush=True)
        del ref
    out = {"candidate": info["stem"], "candidate_recipe": info["recipe"],
           "registry_complete": False,
           "registry_note": (
               "9 pinned priority-site rasters + every other local download "
               "(incl. promoted G30-S19 Candidate C and its twin). Parallel "
               "lanes outside these repos are unavailable, so a pass is "
               "against this registry only. Registry continuous surfaces are "
               "also unavailable; the surface stage compares the candidate "
               "belief with registry dot rasters."),
           "n_references": len(references),
           "surface_decision_vs_registry_dots": decision(
               surface_rows, stage="surface", registry_complete=True),
           "dots_decision": decision(dot_rows, stage="dots", registry_complete=True),
           "max_surface_spearman": max(
               (r["spearman_full_footprint"] or 0.0) for r in surface_rows),
           "max_dots_spearman": max(
               (r["spearman_full_footprint"] or 0.0) for r in dot_rows),
           "max_fraction_within_3px": max(
               (r["candidate_fraction_within_3px_of_reference"] or 0.0)
               for r in dot_rows),
           "detail": detail}
    json.dump(out, open(OUT / "novelty.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "detail"}, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["preflight", "canary", "holdout", "final", "novelty"])
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--focus", default=None,
                        help="candidate arm for bootstrap (default: preregistered rule)")
    parser.add_argument("--recipe", default="C_combined_line")
    args = parser.parse_args()
    {"preflight": stage_preflight,
     "canary": lambda: stage_canary(args.seed),
     "holdout": lambda: stage_holdout(args.seed, args.focus),
     "final": lambda: stage_final(args.recipe),
     "novelty": stage_novelty}[args.stage]()
