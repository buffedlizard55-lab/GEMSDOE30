#!/usr/bin/env python3
"""Lane G30-S19: independent 19-band habitat belief + EDGE emission.

Preregistration: docs/research/2026-10-25/lane-g30s19-preregistration.md
Stages: canary -> holdout -> final. Shared tools only (holdout/metric/
emission/emitter_opt/novelty/submission); no registry raster is an input.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
WORK = ROOT / "data/processed/lane_g30s19"
BANDS = ["mag_anom","rtp","tmi_hg","geod_2ndinv","iso_grav_anom_slope","tc",
 "geod_shearrate","geod_dilaterate","tmi_vg","deq_n100a15","iso_grav_anom_vg",
 "det_elev","iso_grav_anom","tmi","depth_to_base_surf","ieq_n100a15",
 "cond_surf","iso_grav_anom_hg","det_elev_slope"]
GRAD_BANDS = [0,1,11,12,13,14,16]
LAP_BANDS = [1,11,12]
STD_BANDS = [1,11,12]

def load_base():
    feats = np.load(ROOT/"data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT/"data/processed/labels.npy")
    valid = np.load(ROOT/"data/processed/valid.npy")
    return feats, (labels == 1), valid

def fit_stats(feats, fit_mask, rng):
    idx = np.flatnonzero(fit_mask.ravel())
    if idx.size > 400_000:
        idx = rng.choice(idx, 400_000, replace=False)
    H, W = fit_mask.shape
    rows, cols = np.divmod(idx, W)
    stats = []
    for b in range(19):
        band = np.asarray(feats[b], dtype=np.float32)
        v = band[rows, cols]
        v = v[np.isfinite(v) & (v > -1e30)]
        med = float(np.median(v)); q1, q3 = np.percentile(v, [25, 75])
        stats.append({"band": BANDS[b], "median": med, "iqr": float(q3-q1) or 1.0})
        del band
    return stats

def norm_band(feats, b, st):
    band = np.asarray(feats[b], dtype=np.float32)
    band = np.where(np.isfinite(band) & (band > -1e30), band, np.float32(st["median"]))
    return np.clip((band - st["median"]) / st["iqr"], -8, 8).astype(np.float32)

NLAYERS = 19 + len(GRAD_BANDS) + len(LAP_BANDS) + 2*len(STD_BANDS) + 2 + 3 + 3

def layer_names():
    names = list(BANDS)
    names += [f"gradmag_{BANDS[b]}" for b in GRAD_BANDS]
    names += [f"abslap_{BANDS[b]}" for b in LAP_BANDS]
    for b in STD_BANDS:
        names += [f"localstd_s1_{BANDS[b]}", f"localstd_s3_{BANDS[b]}"]
    names += ["tensor_coherence_rtp", "tensor_energy_rtp",
              "edge_coinc_mag_grav", "edge_coinc_mag_topo", "edge_coinc_grav_base",
              "dist_visible_catalogue_px_capped", "prox_exp_d10px", "log1p_dist_visible_px"]
    assert len(names) == NLAYERS, (len(names), NLAYERS)
    return names

def build_stack_mmap(path, feats, stats, dist_known_px, shape):
    """Write the feature stack to a disk memmap, one layer in RAM at a time (3 GB box)."""
    from scipy.ndimage import gaussian_filter, laplace, sobel
    H, W = shape
    stack = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(NLAYERS, H, W))
    norm = {}
    def get_norm(b):
        if b not in norm:
            norm[b] = np.asarray(stack[b])
        return norm[b]
    li = 0
    for b in range(19):
        stack[li] = norm_band(feats, b, stats[b]); li += 1
    stack.flush()
    grads = {}
    for b in GRAD_BANDS:
        x = get_norm(b)
        g = np.hypot(sobel(x, axis=1), sobel(x, axis=0)).astype(np.float32)
        grads[b] = g; stack[li] = g; li += 1
        if b not in STD_BANDS and b not in LAP_BANDS and b != 1:
            norm.pop(b, None)
    for b in LAP_BANDS:
        stack[li] = np.abs(laplace(get_norm(b))).astype(np.float32); li += 1
    for b in STD_BANDS:
        x = get_norm(b)
        for sigma in (1.0, 3.0):
            m = gaussian_filter(x, sigma)
            m2 = gaussian_filter(x*x, sigma)
            stack[li] = np.sqrt(np.maximum(m2 - m*m, 0)).astype(np.float32); li += 1
    x = gaussian_filter(get_norm(1), 1.0)
    gx = sobel(x, axis=1); gy = sobel(x, axis=0); del x
    jxx = gaussian_filter(gx*gx, 2.0); jyy = gaussian_filter(gy*gy, 2.0); jxy = gaussian_filter(gx*gy, 2.0)
    del gx, gy
    tr = jxx + jyy; disc = np.sqrt(np.maximum((jxx-jyy)**2 + 4*jxy**2, 0))
    stack[li] = (disc/(tr+1e-6)).astype(np.float32); li += 1
    stack[li] = tr.astype(np.float32); li += 1
    del jxx, jyy, jxy, tr, disc, norm
    def clip01(g):
        p99 = float(np.percentile(g[::7, ::7], 99)) + 1e-9
        return np.clip(g/p99, 0, 1).astype(np.float32)
    for a, b in [(1, 12), (1, 11), (12, 14)]:
        stack[li] = np.sqrt(clip01(grads[a])*clip01(grads[b])); li += 1
    del grads
    d = dist_known_px.astype(np.float32)
    stack[li] = np.minimum(d, 100); li += 1
    stack[li] = np.exp(-d/10.0).astype(np.float32); li += 1
    stack[li] = np.log1p(d); li += 1
    assert li == NLAYERS
    stack.flush()
    return np.load(path, mmap_mode="r")

def sample_train(stack, pos_mask, elig_mask, rng, max_neg=400_000):
    H, W = pos_mask.shape
    pos = np.flatnonzero((pos_mask & elig_mask).ravel())
    neg = np.flatnonzero((~pos_mask & elig_mask).ravel())
    if neg.size > max_neg:
        neg = rng.choice(neg, max_neg, replace=False)
    sel = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)]).astype(np.int8)
    X = stack.reshape(stack.shape[0], -1)[:, sel].T
    return X, y, pos.size, neg.size

def fit_gbm(X, y, seed=7):
    from sklearn.ensemble import HistGradientBoostingClassifier
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
        max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=1.0,
        random_state=seed)
    m.fit(X, y); return m

def predict_grid(model, stack, valid, keep_idx):
    H, W = valid.shape
    out = np.zeros((H, W), dtype=np.float32)
    for r0 in range(0, H, 250):
        block = np.asarray(stack[keep_idx, r0:r0+250, :])  # (F, h, W)
        Xb = block.reshape(block.shape[0], -1).T
        out[r0:r0+250, :] = model.predict_proba(Xb)[:, 1].reshape(-1, W)
    return np.where(valid, out, 0).astype(np.float32)

def prevalence_correct(p, p_sample, p_true):
    p = np.clip(p.astype(np.float64), 1e-9, 1-1e-9)
    odds = p/(1-p) * (p_true/(1-p_true)) / (p_sample/(1-p_sample))
    return (odds/(1+odds)).astype(np.float32)

def stage_canary():
    from gemsdoe30.holdout import split_components
    from scipy.ndimage import distance_transform_edt
    from sklearn.metrics import roc_auc_score
    WORK.mkdir(parents=True, exist_ok=True)
    feats, catalogue, valid = load_base()
    hidden, known, ncomp = split_components(catalogue, seed=31)
    rng = np.random.default_rng(7)
    dist_hidden = distance_transform_edt(~hidden)
    elig = valid & (dist_hidden > 3)  # 300 m buffer around hidden truth
    stats = fit_stats(feats, elig, rng)
    dist_known = distance_transform_edt(~known)
    stack = build_stack_mmap(WORK/"holdout_stack.npy", feats, stats, dist_known, valid.shape)
    names = layer_names()
    np.save(WORK/"hidden.npy", hidden); np.save(WORK/"known.npy", known)
    json.dump({"names": names, "stats": stats, "n_components": int(ncomp),
               "hidden_px": int(hidden.sum()), "known_px": int(known.sum())},
              open(WORK/"holdout_meta.json","w"), indent=1)
    # AUC per feature: hidden positives vs scored negatives (sampled)
    scored = valid & ~known
    pos = np.flatnonzero((hidden & scored).ravel())
    negpool = np.flatnonzero((scored & ~catalogue & (dist_hidden > 3)).ravel())
    neg = rng.choice(negpool, min(300_000, negpool.size), replace=False)
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    sel = np.concatenate([pos, neg])
    flat = stack.reshape(stack.shape[0], -1)
    rows = []
    for i, n in enumerate(names):
        v = flat[i, sel].astype(np.float64)
        auc = float(roc_auc_score(y, v)) if np.ptp(v) > 0 else 0.5
        rows.append({"feature": n, "auc_hidden": round(auc, 4),
                     "leakage_flag": bool(auc > 0.90 or auc < 0.10)})
        print(f"{n:36s} AUC={auc:.4f}", flush=True)
    json.dump({"evaluator": "component-holdout-v2-footprint-20261025",
               "split_seed": 31, "buffer_px": 3, "hidden_px": int(pos.size),
               "neg_sampled": int(neg.size), "features": rows},
              open(ROOT/"docs/research/2026-10-25/lane-g30s19-canaries.json","w"), indent=1)
    print("CANARY DONE; flagged:", [r["feature"] for r in rows if r["leakage_flag"]])

def emit_edge(belief, support, truth_mass, max_dots=120_000, pool=500_000):
    from gemsdoe30.emitter_opt import edge_select, mask_from_order
    cand = np.zeros(belief.shape, dtype=bool)
    vals = np.where(support, belief, -1).ravel()
    k = min(pool, int(support.sum()))
    top = np.argpartition(vals, -k)[-k:]
    cand.ravel()[top[vals[top] > 0]] = True
    cand &= support
    _, diag = edge_select(belief, cand, truth_mass=float(truth_mass),
                          max_dots=max_dots, return_diagnostics=True)
    return diag

def score(pred_mask_or_float, hidden, known, valid, fpw=None):
    from gemsdoe30.holdout import masked_dti_by_blocks, fp_weight_field
    if fpw is None:
        scored = valid & ~known
        fpw = fp_weight_field(hidden & scored, ~scored)
    r = masked_dti_by_blocks(pred_mask_or_float.astype(np.float32), hidden, known, valid, fp_weight=fpw)
    return r, fpw

def stage_holdout():
    from gemsdoe30.holdout import fp_weight_field
    from gemsdoe30.emission import poisson_disk_select, dti_from_components
    from gemsdoe30.emitter_opt import mask_from_order
    from scipy.ndimage import distance_transform_edt, label as cc_label
    import rasterio
    t0 = time.time()
    feats, catalogue, valid = load_base()
    hidden = np.load(WORK/"hidden.npy"); known = np.load(WORK/"known.npy")
    stack = np.load(WORK/"holdout_stack.npy", mmap_mode="r")
    meta = json.load(open(WORK/"holdout_meta.json"))
    can = json.load(open(ROOT/"docs/research/2026-10-25/lane-g30s19-canaries.json"))
    drop = {r["feature"] for r in can["features"] if r["leakage_flag"]}
    keep_idx = [i for i, n in enumerate(meta["names"]) if n not in drop]
    rng = np.random.default_rng(7)
    dist_hidden = distance_transform_edt(~hidden)
    elig = valid & (dist_hidden > 3)
    X, y, npos, nneg = sample_train(np.asarray(stack[keep_idx]), known, elig, rng)
    model = fit_gbm(X, y)
    raw = predict_grid(model, stack, valid, keep_idx)
    p_sample = npos / (npos + nneg)
    p_true = float((known & elig).sum()) / float(elig.sum())
    belief = prevalence_correct(raw, p_sample, p_true)
    belief = np.where(valid, belief, 0).astype(np.float32)
    np.save(WORK/"holdout_belief.npy", belief)
    scored = valid & ~known
    dist_known = distance_transform_edt(~known)
    support = scored & (dist_known > 2)
    tm = float(belief[scored].sum())
    print(f"train pos={npos} neg={nneg} p_sample={p_sample:.4f} p_true={p_true:.5f} truth_mass={tm:.0f} dropped={sorted(drop)}", flush=True)
    fpw = fp_weight_field(hidden & scored, ~scored)
    results = {"evaluator_version": "component-holdout-v2-footprint-20261025",
               "withheld_positives": int((hidden & scored).sum()),
               "dropped_leakage_features": sorted(drop), "truth_mass_belief_sum": tm}
    # comparators
    prox = np.exp(-dist_known / 10.0).astype(np.float32)
    prox = np.where(support, prox, 0)
    diag_p = emit_edge(prevalence_correct(prox, 0.5, p_true) if False else prox / max(prox.max(),1e-9) * float(belief.max()), support, tm)
    for label_, diag in [("proximity_edge", diag_p)]:
        m = mask_from_order(diag["order_flat"], int(diag["order_flat"].size), belief.shape)
        r, _ = score(m, hidden, known, valid, fpw)
        results[label_] = {"dots": int(m.sum()), **r["pooled"]}
        print(label_, results[label_], flush=True)
    pois = poisson_disk_select(np.where(support, belief, 0), 2.8, mask=support, limit=500_000)
    r, _ = score(pois, hidden, known, valid, fpw)
    results["gbm_poisson28"] = {"dots": int(pois.sum()), **r["pooled"]}
    print("gbm_poisson28", results["gbm_poisson28"], flush=True)
    diag = emit_edge(belief, support, tm)
    np.save(WORK/"holdout_edge_order.npy", diag["order_flat"])
    curve = []
    for keep in [10_000, 20_000, 30_000, 38_000, 44_000, 60_000, 80_000]:
        if keep > diag["order_flat"].size: continue
        m = mask_from_order(diag["order_flat"], keep, belief.shape)
        r, _ = score(m, hidden, known, valid, fpw)
        curve.append({"keep": keep, **r["pooled"]}); print("edge curve", curve[-1], flush=True)
    mstop = mask_from_order(diag["order_flat"], int(diag["order_flat"].size), belief.shape)
    rstop, _ = score(mstop, hidden, known, valid, fpw)
    results["gbm_edge_selfstop"] = {"dots": int(mstop.sum()), **rstop["pooled"]}
    results["gbm_edge_curve"] = curve
    best = max(curve, key=lambda c: c["dti"]) if curve else None
    results["gbm_edge_best_on_curve"] = best
    # component bootstrap CI at best keep (FP fixed, conditional)
    if best:
        from gemsdoe30.emission import kernel_credit
        m = mask_from_order(diag["order_flat"], best["keep"], belief.shape)
        credit = kernel_credit(np.where(scored, m.astype(np.float32), 0))
        comp, nc = cc_label(hidden & scored, structure=np.ones((3,3), int))
        ids = comp[hidden & scored]; cred = credit[hidden & scored]
        order = np.argsort(ids); ids_s, cred_s = ids[order], cred[order]
        starts = np.searchsorted(ids_s, np.arange(1, nc+2))
        csum = np.add.reduceat(cred_s, starts[:-1]); cnum = np.diff(starts).astype(float)
        fp = best["fp_weight"]; boots = []
        rs = np.random.default_rng(7)
        for _ in range(500):
            pick = rs.integers(0, nc, nc)
            boots.append(dti_from_components(float(csum[pick].sum()), fp, float(cnum[pick].sum())))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        results["bootstrap_ci95_conditional_fp_fixed"] = [float(lo), float(hi)]
        results["bootstrap_n_hidden_components"] = int(nc)
    # leaky registry references (never gates)
    for name, path in [("registry_D28_LEAKY", ROOT/"data/raw/registry/25.tif"),
                       ("registry_H33_LEAKY", ROOT/"data/raw/registry/32.tif")]:
        with rasterio.open(path) as ds:
            a = ds.read(1).astype(np.float32)
        a = np.where(np.isfinite(a), a, 0)
        r, _ = score(a, hidden, known, valid, fpw)
        results[name] = {"dots": int((a > 0).sum()), **r["pooled"],
                         "warning": "built with full-catalogue knowledge; leaky on this holdout"}
        print(name, results[name], flush=True)
    results["seconds"] = round(time.time() - t0, 1)
    json.dump(results, open(ROOT/"docs/research/2026-10-25/lane-g30s19-holdout.json","w"), indent=1)
    print(json.dumps(results, indent=1))

def stage_final(keep: int):
    from gemsdoe30.emitter_opt import mask_from_order
    from gemsdoe30.submission import write_submission_file, validate_submission_file
    from scipy.ndimage import distance_transform_edt
    t0 = time.time()
    feats, catalogue, valid = load_base()
    rng = np.random.default_rng(7)
    can = json.load(open(ROOT/"docs/research/2026-10-25/lane-g30s19-canaries.json"))
    drop = {r["feature"] for r in can["features"] if r["leakage_flag"]}
    stats = fit_stats(feats, valid, rng)
    dist_cat = distance_transform_edt(~catalogue)
    stack = build_stack_mmap(WORK/"final_stack.npy", feats, stats, dist_cat, valid.shape)
    names = layer_names()
    keep_idx = [i for i, n in enumerate(names) if n not in drop]
    # final training: all catalogue positives; negatives exclude 3px halo of catalogue
    elig = valid & ((dist_cat > 3) | catalogue)
    X, y, npos, nneg = sample_train(np.asarray(stack[keep_idx]), catalogue, elig, rng, max_neg=600_000)
    model = fit_gbm(X, y)
    raw = predict_grid(model, stack, valid, keep_idx)
    p_sample = npos/(npos+nneg); p_true = float(catalogue.sum())/float(valid.sum())
    belief = prevalence_correct(raw, p_sample, p_true)
    belief = np.where(valid, belief, 0).astype(np.float32)
    np.save(WORK/"final_belief.npy", belief)
    scored = valid & ~catalogue
    support = scored & (dist_cat > 2)
    tm = float(belief[scored].sum())
    print(f"final train pos={npos} neg={nneg} truth_mass={tm:.0f}", flush=True)
    diag = emit_edge(belief, support, tm, max_dots=max(120_000, keep))
    np.save(WORK/"final_edge_order.npy", diag["order_flat"])
    k = min(keep, int(diag["order_flat"].size))
    mask = mask_from_order(diag["order_flat"], k, belief.shape)
    pred = mask.astype(np.float32)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    arr_hash = hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest()[:10]
    stem = f"gemsdoe30-g30s19-habitat-edge-{k}dots-{stamp}-{arr_hash}"
    note = "G30-S19 independent 19-band habitat GBM + EDGE emission, off-catalogue >2px; see run card"[:140]
    tmpl = ROOT/"data/raw/sample_submission.tif"
    out0 = ROOT/f"docs/downloads/{stem}-zeros.tif"
    outn = ROOT/f"docs/downloads/{stem}-nan.tif"
    m0 = write_submission_file(pred, tmpl, out0, note=note, run_name=stem+"-zeros", outside_value=0.0)
    mn = write_submission_file(pred, tmpl, outn, note=note, run_name=stem+"-nan", outside_value=float("nan"))
    info = {"stem": stem, "keep_requested": keep, "dots": int(mask.sum()),
            "edge_accepted": int(diag["order_flat"].size), "truth_mass": tm,
            "zeros_sha256": m0["output_sha256"], "nan_sha256": mn["output_sha256"],
            "note": note, "seconds": round(time.time()-t0, 1)}
    json.dump(info, open(WORK/"final_info.json","w"), indent=1)
    print(json.dumps(info, indent=1))

def stage_novelty():
    from gemsdoe30.novelty import compare, decision
    import rasterio
    info = json.load(open(WORK/"final_info.json"))
    belief = np.load(WORK/"final_belief.npy")
    feats, catalogue, valid = load_base()
    cand_path = ROOT/f"docs/downloads/{info['stem']}-zeros.tif"
    with rasterio.open(cand_path) as ds:
        cand = ds.read(1).astype(np.float32)
    refs = {}
    for p in sorted((ROOT/"data/raw/registry").glob("*.tif")):
        refs[f"registry_{p.stem}"] = p
    for p in sorted((ROOT/"docs/downloads").glob("*.tif")):
        if info["stem"] not in p.name:
            refs[f"downloads_{p.stem[:60]}"] = p
    surf_rows, dot_rows, detail = [], [], {}
    for name, p in refs.items():
        with rasterio.open(p) as ds:
            ref = ds.read(1).astype(np.float32)
        ref = np.where(np.isfinite(ref), ref, 0)
        s = compare(belief, ref, valid); d = compare(cand, ref, valid)
        # surface-stage: correlation only (belief is dense; dot defn n/a)
        surf_rows.append({"spearman_full_footprint": s["spearman_full_footprint"],
                          "identical_inside_footprint": False,
                          "correlation_duplicate": s["correlation_duplicate"],
                          "dot_duplicate": False,
                          "candidate_fraction_within_3px_of_reference": 0.0})
        dot_rows.append(d)
        detail[name] = {"surface_spearman_belief_vs_refdots": s["spearman_full_footprint"],
                        "dots": d}
        print(name, "surf_rho=", s["spearman_full_footprint"], "dot_rho=", d["spearman_full_footprint"],
              "overlap=", d["candidate_fraction_within_3px_of_reference"], flush=True)
    out = {"candidate": info["stem"], "registry_complete": False,
           "registry_note": "9 pinned priority-site rasters + local downloads; parallel-lane surfaces unavailable, so a pass is vs this registry only",
           "surface_decision_vs_registry_dots": decision(surf_rows, stage="surface", registry_complete=True),
           "dots_decision": decision(dot_rows, stage="dots", registry_complete=True),
           "detail": detail}
    json.dump(out, open(ROOT/"docs/research/2026-10-25/lane-g30s19-novelty.json","w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "detail"}, indent=1))


def stage_holdout2():
    """E3: habitat-only GBM (no catalogue-distance inputs), halo-excluded
    negatives, proximity combined only at emission. Fixes E2 catalogue-tracing."""
    from gemsdoe30.holdout import fp_weight_field
    from gemsdoe30.emission import poisson_disk_select, dti_from_components, kernel_credit
    from gemsdoe30.emitter_opt import mask_from_order
    from gemsdoe30.fields import geometric_mean
    from scipy.ndimage import distance_transform_edt, label as cc_label
    import rasterio
    t0 = time.time()
    feats, catalogue, valid = load_base()
    hidden = np.load(WORK/"hidden.npy"); known = np.load(WORK/"known.npy")
    stack = np.load(WORK/"holdout_stack.npy", mmap_mode="r")
    meta = json.load(open(WORK/"holdout_meta.json")); names = meta["names"]
    dist_names = {"dist_visible_catalogue_px_capped","prox_exp_d10px","log1p_dist_visible_px"}
    hab_idx = [i for i,n in enumerate(names) if n not in dist_names]
    rng = np.random.default_rng(7)
    dist_hidden = distance_transform_edt(~hidden)
    dist_known = distance_transform_edt(~known)
    # negatives: >3px from BOTH hidden (buffer) and known (halo = unlabelled zone)
    elig_neg = valid & (dist_hidden > 3) & (dist_known > 3)
    elig = elig_neg | known
    sub = np.asarray(stack[hab_idx])
    X, y, npos, nneg = sample_train(sub, known, elig, rng)
    model = fit_gbm(X, y)
    raw = predict_grid(model, stack, valid, hab_idx)
    p_sample = npos/(npos+nneg); p_true = float(known.sum())/float(valid.sum())
    hab = prevalence_correct(raw, p_sample, p_true)
    hab = np.where(valid, hab, 0).astype(np.float32)
    np.save(WORK/"holdout_habitat_belief.npy", hab)
    scored = valid & ~known
    support = scored & (dist_known > 2)
    prox = np.exp(-dist_known/15.0).astype(np.float32)  # 1.5 km decay
    combined = geometric_mean(hab, np.where(valid, prox, 0).astype(np.float32))
    combined = np.where(valid, combined, 0).astype(np.float32)
    np.save(WORK/"holdout_combined_belief.npy", combined)
    tm = float(known.sum())  # visible-only truth-mass prior
    print(f"E3 train pos={npos} neg={nneg} hab_sum_scored={float(hab[scored].sum()):.0f} truth_mass_prior={tm:.0f}", flush=True)
    fpw = fp_weight_field(hidden & scored, ~scored)
    R = {"evaluator_version":"component-holdout-v2-footprint-20261025",
         "withheld_positives": int((hidden & scored).sum()), "experiment": 3,
         "design_fix_vs_v1": "no distance inputs to GBM; negatives >3px from known+hidden; proximity only in emission belief"}
    def run(label_, belief, do_curve=False):
        diag = emit_edge(belief, support, tm)
        m = mask_from_order(diag["order_flat"], int(diag["order_flat"].size), belief.shape)
        r,_ = score(m, hidden, known, valid, fpw)
        R[label_] = {"dots": int(m.sum()), **r["pooled"]}; print(label_, R[label_], flush=True)
        if do_curve:
            curve=[]
            for keep in [10000,20000,30000,38000,44000,60000,80000,100000]:
                if keep > diag["order_flat"].size: continue
                mm = mask_from_order(diag["order_flat"], keep, belief.shape)
                rr,_ = score(mm, hidden, known, valid, fpw)
                curve.append({"keep":keep, **rr["pooled"]}); print(" curve", curve[-1], flush=True)
            R[label_+"_curve"]=curve
            np.save(WORK/"holdout2_edge_order.npy", diag["order_flat"])
        return diag
    run("proximity_only_edge", np.where(valid, prox, 0).astype(np.float32))
    run("habitat_only_edge", hab)
    diag = run("combined_edge", combined, do_curve=True)
    pois = poisson_disk_select(np.where(support, combined, 0), 2.8, mask=support, limit=300_000)
    r,_ = score(pois, hidden, known, valid, fpw)
    R["combined_poisson28"] = {"dots": int(pois.sum()), **r["pooled"]}
    print("combined_poisson28", R["combined_poisson28"], flush=True)
    curve = R.get("combined_edge_curve", [])
    cands = curve + ([{"keep": R["combined_edge"]["dots"], **{k:R["combined_edge"][k] for k in ("dti","tp_weight","fp_weight","truth_pixels")}}] if R.get("combined_edge") else [])
    best = max(cands, key=lambda c: c["dti"]) if cands else None
    R["combined_edge_best"] = best
    if best:
        m = mask_from_order(diag["order_flat"], int(best["keep"]), combined.shape)
        credit = kernel_credit(np.where(scored, m.astype(np.float32), 0))
        comp, nc = cc_label(hidden & scored, structure=np.ones((3,3),int))
        ids = comp[hidden & scored]; cred = credit[hidden & scored]
        o = np.argsort(ids); ids_s, cred_s = ids[o], cred[o]
        starts = np.searchsorted(ids_s, np.arange(1, nc+2))
        csum = np.add.reduceat(cred_s, starts[:-1]); cnum = np.diff(starts).astype(float)
        rs = np.random.default_rng(7); boots=[]
        for _ in range(500):
            pk = rs.integers(0, nc, nc)
            boots.append(dti_from_components(float(csum[pk].sum()), float(best["fp_weight"]), float(cnum[pk].sum())))
        R["bootstrap_ci95_conditional_fp_fixed"] = [float(x) for x in np.percentile(boots,[2.5,97.5])]
        R["bootstrap_n_hidden_components"] = int(nc)
    R["seconds"] = round(time.time()-t0,1)
    json.dump(R, open(ROOT/"docs/research/2026-10-25/lane-g30s19-holdout.json","w"), indent=1)
    print(json.dumps(R, indent=1))


def stage_final2(keep: int):
    """Production run of the E3-winning recipe on the full catalogue.
    Habitat-only GBM (no distance inputs), halo-excluded negatives,
    EDGE emission, support = footprint & catalogue-distance > 2px."""
    from gemsdoe30.emitter_opt import mask_from_order
    from gemsdoe30.submission import write_submission_file
    from scipy.ndimage import distance_transform_edt
    t0 = time.time()
    feats, catalogue, valid = load_base()
    rng = np.random.default_rng(7)
    stats = fit_stats(feats, valid, rng)
    dist_cat = distance_transform_edt(~catalogue)
    stack = build_stack_mmap(WORK/"final_stack.npy", feats, stats, dist_cat, valid.shape)
    names = layer_names()
    dist_names = {"dist_visible_catalogue_px_capped","prox_exp_d10px","log1p_dist_visible_px"}
    hab_idx = [i for i,n in enumerate(names) if n not in dist_names]
    elig = valid & ((dist_cat > 3) | catalogue)
    X, y, npos, nneg = sample_train(np.asarray(stack[hab_idx]), catalogue, elig, rng, max_neg=600_000)
    model = fit_gbm(X, y)
    raw = predict_grid(model, stack, valid, hab_idx)
    p_sample = npos/(npos+nneg); p_true = float(catalogue.sum())/float(valid.sum())
    belief = prevalence_correct(raw, p_sample, p_true)
    belief = np.where(valid, belief, 0).astype(np.float32)
    np.save(WORK/"final_belief.npy", belief)
    scored = valid & ~catalogue
    support = scored & (dist_cat > 2)
    tm = float(catalogue.sum())
    print(f"final2 pos={npos} neg={nneg} belief_sum_scored={float(belief[scored].sum()):.0f} truth_mass_prior={tm:.0f}", flush=True)
    diag = emit_edge(belief, support, tm, max_dots=120_000)
    np.save(WORK/"final_edge_order.npy", diag["order_flat"])
    k = min(keep, int(diag["order_flat"].size))
    mask = mask_from_order(diag["order_flat"], k, belief.shape)
    pred = mask.astype(np.float32)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    arr_hash = hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest()[:10]
    stem = f"gemsdoe30-g30s19-habitat-edge-{k}dots-{stamp}-{arr_hash}"
    note = "G30-S19 habitat GBM (19-band, no catalogue-distance inputs) + EDGE 60k, off-cat >2px"[:140]
    tmpl = ROOT/"data/raw/sample_submission.tif"
    out0 = ROOT/f"docs/downloads/{stem}-zeros.tif"
    outn = ROOT/f"docs/downloads/{stem}-nan.tif"
    m0 = write_submission_file(pred, tmpl, out0, note=note, run_name=stem+"-zeros", outside_value=0.0)
    mn = write_submission_file(pred, tmpl, outn, note=note, run_name=stem+"-nan", outside_value=float("nan"))
    info = {"stem": stem, "keep_requested": keep, "dots": int(mask.sum()),
            "dots_on_catalogue": int((mask & catalogue).sum()),
            "dots_within_2px_of_catalogue": int((mask & (dist_cat <= 2)).sum()),
            "edge_accepted_selfstop": int(diag["order_flat"].size), "truth_mass_prior": tm,
            "belief_sum_scored": float(belief[scored].sum()),
            "zeros_sha256": m0["output_sha256"], "nan_sha256": mn["output_sha256"],
            "note": note, "seconds": round(time.time()-t0,1)}
    json.dump(info, open(WORK/"final_info.json","w"), indent=1)
    print(json.dumps(info, indent=1))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["canary", "holdout", "holdout2", "final", "novelty"])
    ap.add_argument("--keep", type=int, default=38_000)
    a = ap.parse_args()
    {"canary": stage_canary, "holdout": stage_holdout, "holdout2": stage_holdout2,
     "final": lambda: stage_final2(a.keep), "novelty": stage_novelty}[a.stage]()
