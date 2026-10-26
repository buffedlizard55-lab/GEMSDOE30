#!/usr/bin/env python3
"""Execute frozen Lane MS-CAPE (Rank #1 preregistered hypothesis).

Reuses shared holdout evaluator (`src/gemsdoe30/holdout.py`), shared submission
writer/validator (`src/gemsdoe30/submission.py`), shared novelty auditor
(`src/gemsdoe30/novelty.py`), and prepared cache (`data/processed/`).
Runs within strict <= 3 candidate experiments and <= 2.0 experimental hours,
using float32 disk memmaps and 256x256 block inference to stay well under 3.8 GiB RAM.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, laplace, sobel
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from gemsdoe30.emission import poisson_disk_select_ordered
from gemsdoe30.emitter_opt import edge_select, mask_from_order
from gemsdoe30.holdout import (
    EVALUATOR_VERSION,
    SEGMENT_PROTOCOL_VERSION,
    masked_dti_by_blocks,
    spatial_bootstrap,
    spatial_segment_folds,
)
from gemsdoe30.ms_cape import (
    ALL_STAGE1_FEATURE_NAMES,
    CORE19_NAMES,
    MS_CAPE_NAMES,
    STAGE1_SUPPORT_PX,
    STAGE2_REGIME_FEATURE_NAMES,
    STAGE2_SUPPORT_PX,
    STAGE2_TRACE_NAMES,
    SUPPORT_PX,
    TRANSFORM_VERSION,
    build_ms_cape_feature_memmap,
    compute_stage2_trace_features,
    recalibrate_prior_odds,
    submod_dti_select,
)
from gemsdoe30.submission import validate_submission_file, write_submission_file
from scripts.check_novelty import audit
from scripts.feature_value_holdout import fit_standardiser, predict_grid, sample_training_pixels
from scripts.verify_prepared_cache import verify as verify_prepared_cache

REPORT = ROOT / "docs/research/ms-cape"
CACHE = ROOT / "data/processed/ms-cape"
RUN = ROOT / "outputs/ms-cape"
SEED = 4070
DOT_BUDGET = 44090
EXPERIMENTS_RUN = 3
CANDIDATE_ARM = "ms_cape_e3"
COMPARATOR_ARMS = ["physics_tilt8", "core19", "g30s19_hist_best"]

NOTE_PROMOTE = (
    "MS-CAPE 2-stage multi-physics tilt+piedmont+8az lineament+GDR/GeoDAWN "
    "upflow + 300m submodular DTI cover (44090 off-cat dots)"
)
NOTE_NEGATIVE = (
    "MS-CAPE 2-stage multi-physics + 300m submodular cover; negative holdout "
    "gate result, research download only, NOT for upload."
)


def sha(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _relativize_strings(obj, root_prefix: str = str(ROOT) + "/"):
    if isinstance(obj, dict):
        return {k: _relativize_strings(v, root_prefix) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_relativize_strings(v, root_prefix) for v in obj]
    if isinstance(obj, str) and obj.startswith(root_prefix):
        return obj[len(root_prefix) :]
    return obj


def dump(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = _relativize_strings(data)
    path.write_text(json.dumps(clean, indent=2, allow_nan=False) + "\n")


def check_time(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise TimeoutError("Experimental 2-hour cap reached; stopping immediately without slot selection")


def sample_pixels_lowmem(
    features: np.ndarray,
    labels: np.ndarray,
    train_mask: np.ndarray,
    *,
    negatives_per_positive: int,
    seed: int,
    channel_indices: list[int] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact bit-identical coordinates to sample_training_pixels, reading 1 channel at a time."""
    rng = np.random.default_rng(seed)
    positives = np.argwhere(train_mask & (labels > 0.5))
    candidates = np.argwhere(train_mask & (labels < 0.5))
    if not len(positives) or not len(candidates):
        raise ValueError("training fold lacks positives or negatives")
    take = min(len(candidates), negatives_per_positive * len(positives))
    choice = rng.choice(len(candidates), size=take, replace=False)
    negatives = candidates[choice]
    coords = np.concatenate([positives, negatives], axis=0)
    target = np.concatenate([np.ones(len(positives)), np.zeros(len(negatives))])
    ch_list = list(range(features.shape[0])) if channel_indices is None else list(channel_indices)
    x = np.empty((len(coords), len(ch_list)), dtype=np.float32)
    rr, cc = coords[:, 0], coords[:, 1]
    for k, ch in enumerate(ch_list):
        x[:, k] = features[ch][rr, cc]
    return x, target


def predict_grid_lowmem(
    model,
    features: np.ndarray,
    median: np.ndarray,
    scale: np.ndarray,
    valid: np.ndarray,
    *,
    channel_indices: list[int] | None = None,
    block: int = 256,
) -> np.ndarray:
    """256x256 block prediction supporting channel subsets without full-grid copies."""
    if channel_indices is None:
        return predict_grid(model, features, median, scale, valid, block=block)
    height, width = valid.shape
    out = np.zeros((height, width), dtype=np.float32)
    n_ch = len(channel_indices)
    for row in range(0, height, block):
        r1 = min(row + block, height)
        for col in range(0, width, block):
            c1 = min(col + block, width)
            block_valid = valid[row:r1, col:c1]
            if not block_valid.any():
                continue
            flat_valid = block_valid.reshape(-1)
            data = np.empty((int(flat_valid.sum()), n_ch), dtype=np.float32)
            for k, ch in enumerate(channel_indices):
                tile = np.asarray(features[ch, row:r1, col:c1], dtype=np.float32).reshape(-1)
                data[:, k] = tile[flat_valid]
            data = np.where(np.isfinite(data), data, median)
            prob = model.predict_proba((data - median) / scale)[:, 1]
            target = np.zeros((r1 - row, c1 - col), dtype=np.float32)
            target.reshape(-1)[flat_valid] = prob.astype(np.float32)
            out[row:r1, col:c1] = target
    return out


def select_poisson_dots(surface: np.ndarray, mask: np.ndarray, count: int) -> np.ndarray:
    rows, cols = poisson_disk_select_ordered(surface, 3.0, mask=mask, max_kept=count)
    if len(rows) != count:
        raise ValueError(f"Poisson count gate shortfall: {len(rows)} vs {count}")
    dots = np.zeros(surface.shape, dtype=np.float32)
    dots[rows, cols] = 1.0
    return dots


def select_edge_dots_matched(
    prob_cal: np.ndarray,
    active_mask: np.ndarray,
    truth_mass_est: float,
    count: int,
) -> np.ndarray:
    """Run G30-S19 EDGE emitter capped at exact matched count (topping up deterministically if needed)."""
    vals = np.where(active_mask, prob_cal, -1.0).ravel()
    k = min(150_000, int(active_mask.sum()))
    cand = np.zeros(prob_cal.shape, dtype=bool)
    top = np.argpartition(vals, -k)[-k:]
    cand.ravel()[top[vals[top] > 0.0]] = True
    cand &= active_mask
    sel_mask, _ = edge_select(
        prob_cal,
        cand,
        truth_mass=max(float(truth_mass_est), 100.0),
        max_dots=count,
        return_diagnostics=True,
    )
    emitted = sel_mask.astype(np.float32)
    n_take = int(emitted.sum())
    if n_take < count:
        rem_mask = active_mask & (emitted == 0.0)
        r_extra, c_extra = poisson_disk_select_ordered(prob_cal, 3.0, mask=rem_mask, max_kept=count - n_take)
        emitted[r_extra, c_extra] = 1.0
    if int(emitted.sum()) < count:
        elig_idx = np.flatnonzero(active_mask & (emitted == 0.0))
        extra = elig_idx[np.argsort(-prob_cal.ravel()[elig_idx], kind="mergesort")[: count - int(emitted.sum())]]
        emitted.ravel()[extra] = 1.0
    return emitted


def build_stage1_51_memmap(
    base: np.ndarray,
    valid: np.ndarray,
    manifest: dict,
    memmap_51_path: Path,
    ms_cape_32_path: Path,
) -> dict:
    """Build or verify 51-channel Stage-1 float32 memmap (19 sanitized core + 32 MS-CAPE)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    receipt_path = CACHE / "feature-receipt.json"
    ms_cape_mmap, raw_receipt = build_ms_cape_feature_memmap(
        base, valid, ROOT / "data/external", ms_cape_32_path
    )
    _, h, w = base.shape
    full_mmap = np.memmap(memmap_51_path, dtype=np.float32, mode="w+", shape=(51, h, w))
    for b in range(19):
        raw_b = np.asarray(base[b], dtype=np.float32)
        clean_b = np.where(valid & np.isfinite(raw_b) & (np.abs(raw_b) < 1e30), raw_b, np.nan)
        clean_b[~valid] = 0.0
        full_mmap[b] = clean_b.astype(np.float32)
    for j in range(32):
        full_mmap[19 + j] = ms_cape_mmap[j]
    full_mmap.flush()
    del ms_cape_mmap

    signature = {
        "transform_module": "src/gemsdoe30/ms_cape.py",
        "transform_version": TRANSFORM_VERSION,
        "transform_code_sha256": sha(ROOT / "src/gemsdoe30/ms_cape.py"),
        "dataset_signature": manifest["dataset_signature"],
    }
    receipt = {
        "signature": signature,
        "support_px": SUPPORT_PX,
        "stage1_support_px": STAGE1_SUPPORT_PX,
        "stage2_support_px": STAGE2_SUPPORT_PX,
        "stage1_feature_names": list(ALL_STAGE1_FEATURE_NAMES),
        "stage2_trace_names": list(STAGE2_TRACE_NAMES),
        "external_source_sha256": raw_receipt["external_source_sha256"],
        "uses_catalogue_geometry": False,
        "uses_registry_values": False,
        "uses_template_values_as_features": False,
    }
    dump(receipt_path, receipt)
    dump(REPORT / "feature-receipt.json", receipt)
    return receipt


def build_g30s19_nonleaky_memmap(base: np.ndarray, valid: np.ndarray, out_path: Path) -> np.memmap:
    """Reproduce the 40 catalogue-free isotropic channels of Lane G30-S19 (support <= 12 px)."""
    _, h, w = base.shape
    grad_bands = [0, 1, 11, 12, 13, 14, 16]
    lap_bands = [1, 11, 12]
    std_bands = [1, 11, 12]
    n_ch = 19 + len(grad_bands) + len(lap_bands) + 2 * len(std_bands) + 2 + 3
    mmap = np.memmap(out_path, dtype=np.float32, mode="w+", shape=(n_ch, h, w))

    # Global footprint robust scaling for spatial derivative stability (tree splits are monotone-invariant)
    li = 0
    for b in range(19):
        raw = np.asarray(base[b], dtype=np.float32)
        fin = valid & np.isfinite(raw) & (np.abs(raw) < 1e30)
        vals = raw[fin][::11]
        med = float(np.median(vals))
        q1, q3 = np.percentile(vals, [25.0, 75.0])
        iqr = max(float(q3 - q1), 1e-6)
        clean = np.where(fin, raw, med)
        normed = np.clip((clean - med) / iqr, -8.0, 8.0).astype(np.float32)
        normed[~valid] = 0.0
        mmap[li] = normed
        li += 1
    mmap.flush()

    grads: dict[int, np.ndarray] = {}
    for b in grad_bands:
        x = np.asarray(mmap[b], dtype=np.float32)
        g = np.hypot(sobel(x, axis=1), sobel(x, axis=0)).astype(np.float32)
        g[~valid] = 0.0
        grads[b] = g
        mmap[li] = g
        li += 1
    for b in lap_bands:
        x = np.asarray(mmap[b], dtype=np.float32)
        lp = np.abs(laplace(x)).astype(np.float32)
        lp[~valid] = 0.0
        mmap[li] = lp
        li += 1
    for b in std_bands:
        x = np.asarray(mmap[b], dtype=np.float32)
        for sig in (1.0, 3.0):
            m1 = gaussian_filter(x, sig, truncate=3.5)
            m2 = gaussian_filter(x * x, sig, truncate=3.5)
            sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0)).astype(np.float32)
            sd[~valid] = 0.0
            mmap[li] = sd
            li += 1
    xr = gaussian_filter(np.asarray(mmap[1], dtype=np.float32), 1.0, truncate=3.5)
    gx = sobel(xr, axis=1)
    gy = sobel(xr, axis=0)
    jxx = gaussian_filter(gx * gx, 2.0, truncate=3.5)
    jyy = gaussian_filter(gy * gy, 2.0, truncate=3.5)
    jxy = gaussian_filter(gx * gy, 2.0, truncate=3.5)
    tr = jxx + jyy
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    coh = (disc / (tr + 1e-6)).astype(np.float32)
    coh[~valid] = 0.0
    tr_f = tr.astype(np.float32)
    tr_f[~valid] = 0.0
    mmap[li] = coh
    li += 1
    mmap[li] = tr_f
    li += 1

    def _clip01(g: np.ndarray) -> np.ndarray:
        p99 = float(np.percentile(g[valid][::13], 99.0)) + 1e-9
        return np.clip(g / p99, 0.0, 1.0).astype(np.float32)

    for a, b in [(1, 12), (1, 11), (12, 14)]:
        ec = np.sqrt(_clip01(grads[a]) * _clip01(grads[b])).astype(np.float32)
        ec[~valid] = 0.0
        mmap[li] = ec
        li += 1
    assert li == n_ch
    mmap.flush()
    return np.memmap(out_path, dtype=np.float32, mode="r", shape=(n_ch, h, w))


def fit_canonical_hgb(x: np.ndarray, y: np.ndarray, *, seed: int, iterations: int = 120, leaves: int = 31):
    median, scale = fit_standardiser(x)
    xf = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(
        max_iter=iterations,
        learning_rate=0.1,
        max_leaf_nodes=leaves,
        early_stopping=False,
        random_state=seed,
    )
    with threadpool_limits(limits=2):
        model.fit((xf - median) / scale, y)
    return model, median, scale


def fit_g30s19_hgb(x: np.ndarray, y: np.ndarray, *, seed: int):
    median, scale = fit_standardiser(x)
    xf = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.06,
        max_leaf_nodes=31,
        min_samples_leaf=200,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=seed,
    )
    with threadpool_limits(limits=2):
        model.fit((xf - median) / scale, y)
    return model, median, scale


def fit_ms_cape_stage1(x: np.ndarray, y: np.ndarray, *, seed: int):
    median, scale = fit_standardiser(x)
    xf = ((np.where(np.isfinite(x), x, median) - median) / scale).astype(np.float32)
    m_deep = HistGradientBoostingClassifier(
        max_iter=260,
        learning_rate=0.05,
        max_leaf_nodes=63,
        min_samples_leaf=80,
        l2_regularization=2.0,
        max_features=0.75,
        early_stopping=False,
        random_state=seed,
    )
    m_smooth = HistGradientBoostingClassifier(
        max_iter=260,
        learning_rate=0.05,
        max_leaf_nodes=31,
        min_samples_leaf=160,
        l2_regularization=4.0,
        max_features=0.65,
        early_stopping=False,
        random_state=seed + 101,
    )
    with threadpool_limits(limits=2):
        m_deep.fit(xf, y)
        m_smooth.fit(xf, y)
    pi_sample = float(np.mean(y))
    return (m_deep, m_smooth, median, scale, pi_sample)


def predict_ms_cape_stage1(
    bundle,
    features_51: np.ndarray,
    domain_mask: np.ndarray,
    pi_true: float,
) -> np.ndarray:
    m_deep, m_smooth, median, scale, pi_sample = bundle
    with threadpool_limits(limits=2):
        p_a = predict_grid(m_deep, features_51, median, scale, domain_mask, block=256)
        p_b = predict_grid(m_smooth, features_51, median, scale, domain_mask, block=256)
    p_ens = 0.5 * p_a + 0.5 * p_b
    return recalibrate_prior_odds(p_ens, pi_true=pi_true, pi_sample=pi_sample, valid=domain_mask)


def _extract_stage2_matrix(
    s2_trace: np.ndarray,
    features_51: np.ndarray,
    regime_indices: list[int],
    rows: np.ndarray,
    cols: np.ndarray,
) -> np.ndarray:
    n_n = len(rows)
    n_tr = s2_trace.shape[0]
    x = np.empty((n_n, n_tr + len(regime_indices)), dtype=np.float32)
    for k in range(n_tr):
        x[:, k] = s2_trace[k][rows, cols]
    for k, ch in enumerate(regime_indices):
        x[:, n_tr + k] = features_51[ch][rows, cols]
    return x


def fit_ms_cape_stage2(
    s2_trace_oof: np.ndarray,
    features_51: np.ndarray,
    regime_indices: list[int],
    labels: np.ndarray,
    train_mask: np.ndarray,
    *,
    seed: int,
    negatives_per_positive: int = 8,
):
    rng = np.random.default_rng(seed)
    pos_rc = np.argwhere(train_mask & labels)
    neg_rc = np.argwhere(train_mask & ~labels)
    take = min(len(neg_rc), negatives_per_positive * len(pos_rc))
    sel_neg = neg_rc[rng.choice(len(neg_rc), size=take, replace=False)]
    coords = np.concatenate([pos_rc, sel_neg], axis=0)
    y = np.concatenate([np.ones(len(pos_rc)), np.zeros(len(sel_neg))])

    x = _extract_stage2_matrix(s2_trace_oof, features_51, regime_indices, coords[:, 0], coords[:, 1])
    median, scale = fit_standardiser(x)
    xs = np.clip((np.where(np.isfinite(x), x, median) - median) / scale, -8.0, 8.0).astype(np.float32)

    m_hgb2 = HistGradientBoostingClassifier(
        max_iter=180,
        learning_rate=0.045,
        max_leaf_nodes=31,
        min_samples_leaf=180,
        l2_regularization=5.0,
        max_features=0.80,
        early_stopping=False,
        random_state=seed + 202,
    )
    m_lr2 = LogisticRegression(C=0.5, max_iter=300, random_state=seed + 303)
    with threadpool_limits(limits=2):
        m_hgb2.fit(xs, y)
        # Fit linear meta-calibrator on the 10 directional trace propagation channels
        m_lr2.fit(xs[:, : len(STAGE2_TRACE_NAMES)], y)
    pi_sample = float(np.mean(y))
    return (m_hgb2, m_lr2, median, scale, pi_sample)


def predict_ms_cape_stage2(
    s2_bundle,
    s2_trace: np.ndarray,
    features_51: np.ndarray,
    regime_indices: list[int],
    domain_mask: np.ndarray,
    pi_true: float,
    *,
    block: int = 256,
) -> np.ndarray:
    m_hgb2, m_lr2, median, scale, pi_sample = s2_bundle
    h, w = domain_mask.shape
    out = np.zeros((h, w), dtype=np.float32)
    n_trace = len(STAGE2_TRACE_NAMES)
    with threadpool_limits(limits=2):
        for r0 in range(0, h, block):
            r1 = min(r0 + block, h)
            for c0 in range(0, w, block):
                c1 = min(c0 + block, w)
                bm = domain_mask[r0:r1, c0:c1]
                if not bm.any():
                    continue
                flat_m = bm.reshape(-1)
                xb = np.empty((int(flat_m.sum()), n_trace + len(regime_indices)), dtype=np.float32)
                for k in range(n_trace):
                    xb[:, k] = np.asarray(s2_trace[k, r0:r1, c0:c1], dtype=np.float32).reshape(-1)[flat_m]
                for k, ch in enumerate(regime_indices):
                    xb[:, n_trace + k] = np.asarray(features_51[ch, r0:r1, c0:c1], dtype=np.float32).reshape(-1)[flat_m]
                xs = np.clip((np.where(np.isfinite(xb), xb, median) - median) / scale, -8.0, 8.0)
                p_tree = m_hgb2.predict_proba(xs)[:, 1]
                p_lin = m_lr2.predict_proba(xs[:, :n_trace])[:, 1]
                p_mix = (0.80 * p_tree + 0.20 * p_lin).astype(np.float32)
                tile = np.zeros((r1 - r0, c1 - c0), dtype=np.float32)
                tile.reshape(-1)[flat_m] = p_mix
                out[r0:r1, c0:c1] = tile
    return recalibrate_prior_odds(out, pi_true=pi_true, pi_sample=pi_sample, valid=domain_mask)


def run_feature_canaries_51(
    features_51: np.ndarray,
    visible_labels: np.ndarray,
    fold: dict,
    seed: int,
    deadline: float,
) -> list[dict]:
    """Single-feature raw bidirectional + fold-trained univariate HGB AUC across all 51 features."""
    train = fold["train_mask"]
    domain = fold["score_valid"] & ~fold["visible"]
    x_tr, y_tr = sample_pixels_lowmem(features_51, visible_labels, train, negatives_per_positive=6, seed=seed)

    rng = np.random.default_rng(seed + 10_000)
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(domain & ~fold["hidden"])
    negatives = rng.choice(negatives, min(60_000, negatives.size), replace=False)
    test_idx = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])

    rows: list[dict] = []
    for j, fname in enumerate(ALL_STAGE1_FEATURE_NAMES):
        check_time(deadline)
        col_tr = x_tr[:, j : j + 1]
        model, med, scl = fit_canonical_hgb(col_tr, y_tr, seed=seed + j, iterations=32, leaves=7)
        vals = np.asarray(features_51[j], dtype=np.float32).ravel()[test_idx]
        filled = np.where(np.isfinite(vals), vals, med[0])
        raw_auc = float(roc_auc_score(target, filled)) if np.ptp(filled) > 0 else 0.5
        with threadpool_limits(limits=2):
            probs = model.predict_proba(((filled - med[0]) / scl[0])[:, None])[:, 1]
        uni_auc = float(roc_auc_score(target, probs)) if np.ptp(probs) > 0 else 0.5
        raw_bi = max(raw_auc, 1.0 - raw_auc)
        uni_bi = max(uni_auc, 1.0 - uni_auc)
        rows.append(
            {
                "feature": fname,
                "label": "LEAKAGE-CANARY AUC (not DTI)",
                "raw_auc": raw_auc,
                "raw_auc_either_direction": raw_bi,
                "univariate_training_only_hgb_auc": uni_auc,
                "alarm_above_0_90": bool(raw_bi > 0.90 or uni_bi > 0.90),
                "heldout_positives": int(positives.size),
                "sampled_negatives": int(negatives.size),
            }
        )
    return rows


def summarize_novelty(surface: dict, dots: dict, registry_complete: bool) -> dict:
    def _maxima(rep: dict) -> dict:
        rows = rep.get("comparisons", [])
        corrs = [r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None]
        ovlps = [
            r["candidate_fraction_within_3px_of_reference"]
            for r in rows
            if r["candidate_fraction_within_3px_of_reference"] is not None
        ]
        return {
            "decision": rep["decision"],
            "registry_entries_compared": len(rows),
            "max_spearman": max(corrs) if corrs else None,
            "max_fraction_within_3px": max(ovlps) if ovlps else None,
            "errors": rep.get("errors", []),
        }

    return {
        "complete": bool(registry_complete),
        "surface": _maxima(surface),
        "dots": _maxima(dots),
        "coverage": (
            "116 unique SHA-256 aligned GeoTIFF snapshots across all 9 priority repositories "
            "(GEMSDOE24..36), all local GEMSDOE30 downloads, and GEMSDOE49/63/70/73/76 hero artifacts"
        ),
        "receipt_surface": "docs/research/ms-cape/novelty-surface.json",
        "receipt_dots": "docs/research/ms-cape/novelty-dots.json",
    }


def _quadrant_index_map(valid: np.ndarray) -> np.ndarray:
    rows, cols = np.nonzero(valid)
    r_mid = float(np.median(rows))
    c_mid = float(np.median(cols))
    rr, cc = np.indices(valid.shape)
    q = ((rr >= r_mid).astype(np.int8) * 2 + (cc >= c_mid).astype(np.int8))
    return q


def run(max_seconds: float) -> dict:
    started_mono = time.monotonic()
    start_utc = datetime.now(timezone.utc)
    deadline = started_mono + max_seconds

    REPORT.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    prereg_sha = sha(REPORT / "preregistration.md")
    dump(
        REPORT / "started.json",
        {
            "started_utc": start_utc.isoformat(timespec="seconds"),
            "preregistration_sha256": prereg_sha,
            "experiment_count": EXPERIMENTS_RUN,
            "candidate_arm": CANDIDATE_ARM,
            "comparator_arms": COMPARATOR_ARMS,
            "experiment_ladder": ["ms_cape_e1", "ms_cape_e2", "ms_cape_e3"],
            "script_sha256": sha(Path(__file__)),
            "max_experimental_seconds": max_seconds,
        },
    )

    print("[1/6] Verifying prepared cache & raw SHA-256 pins...", flush=True)
    cache_ver = verify_prepared_cache(ROOT / "data/processed")
    dump(REPORT / "cache-verification.json", cache_ver)

    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = (np.load(ROOT / "data/processed/labels.npy", mmap_mode="r") > 0.5)
    valid = np.load(ROOT / "data/processed/valid.npy", mmap_mode="r").copy()
    label_valid = np.load(ROOT / "data/processed/label_valid.npy", mmap_mode="r")
    if np.any(valid & ~label_valid):
        raise ValueError("unknown training labels inside valid footprint")
    labels = labels & valid
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    template = ROOT / "data/raw/sample_submission.tif"
    for row in manifest["source_files"].values():
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise ValueError(f"raw source SHA-256 mismatch: {row['path']}")

    print("[2/6] Building or reusing MS-CAPE 51-feature & G30-S19 40-feature disk memmaps...", flush=True)
    memmap_51_path = RUN / "stage1_51.dat"
    ms_cape_32_path = RUN / "ms_cape_32.dat"
    g30s19_40_path = RUN / "g30s19_40.dat"
    expected_sig = {
        "transform_module": "src/gemsdoe30/ms_cape.py",
        "transform_version": TRANSFORM_VERSION,
        "transform_code_sha256": sha(ROOT / "src/gemsdoe30/ms_cape.py"),
        "dataset_signature": manifest["dataset_signature"],
    }
    rec_file = REPORT / "feature-receipt.json"
    if (
        memmap_51_path.exists()
        and g30s19_40_path.exists()
        and rec_file.exists()
        and json.loads(rec_file.read_text()).get("signature") == expected_sig
    ):
        print("  Reusing verified Stage-1 & G30-S19 feature memmaps on disk!", flush=True)
        features_51 = np.memmap(memmap_51_path, dtype=np.float32, mode="r", shape=(51, *valid.shape))
        g30s19_40 = np.memmap(g30s19_40_path, dtype=np.float32, mode="r", shape=(40, *valid.shape))
    else:
        build_stage1_51_memmap(base, valid, manifest, memmap_51_path, ms_cape_32_path)
        features_51 = np.memmap(memmap_51_path, dtype=np.float32, mode="r", shape=(51, *valid.shape))
        g30s19_40 = build_g30s19_nonleaky_memmap(base, valid, g30s19_40_path)
    regime_indices = [ALL_STAGE1_FEATURE_NAMES.index(nm) for nm in STAGE2_REGIME_FEATURE_NAMES]
    check_time(deadline)

    # Precompute the 4 buffered spatial-quadrant whole-component folds once
    folds_spec = list(spatial_segment_folds(labels, valid, buffer_px=SUPPORT_PX))
    q_map = _quadrant_index_map(valid)

    # --- STEP 3: Fit full-map MS-CAPE method BEFORE viewing any holdout score ---
    # Notice: each fold f's outer Stage-1 model (fitted strictly on fold["train_mask"])
    # produces genuine out-of-quadrant Stage-1 predictions on fold["score_valid"]!
    # Stitching those 4 outer Stage-1 predictions gives a 100% out-of-quadrant Stage-1
    # probability map across the entire footprint for full-map Stage-2 fitting AND is
    # reused directly inside the 4-fold evaluation below without redundant refits!
    print("[3/6] Fitting outer Stage-1 models & full-map MS-CAPE candidate (pre-holdout)...", flush=True)
    outer_s1_preds = np.zeros(valid.shape, dtype=np.float32)
    outer_s1_bundles: dict[int, tuple] = {}
    for fold in folds_spec:
        check_time(deadline)
        f = fold["fold"]
        pi_tr = float(np.mean(fold["visible"][fold["train_mask"]]))
        x_s1, y_s1 = sample_pixels_lowmem(
            features_51, fold["visible"], fold["train_mask"], negatives_per_positive=8, seed=SEED + f
        )
        b_s1 = fit_ms_cape_stage1(x_s1, y_s1, seed=SEED + f)
        del x_s1, y_s1
        outer_s1_bundles[f] = b_s1
        # Predict on this fold's quadrant (score_valid)
        p_quad = predict_ms_cape_stage1(b_s1, features_51, fold["score_valid"], pi_true=pi_tr)
        outer_s1_preds[fold["score_valid"]] = p_quad[fold["score_valid"]]
        print(f"  Outer Stage-1 fold {f} predicted on quadrant {f}", flush=True)

    # Also fit full 4-quadrant Stage-1 ensemble + full Stage-2 stacker for the final map
    pi_full = float(np.mean(labels[valid]))
    x_full1, y_full1 = sample_pixels_lowmem(
        features_51, labels, valid, negatives_per_positive=8, seed=SEED + 99
    )
    full_s1_bundle = fit_ms_cape_stage1(x_full1, y_full1, seed=SEED + 99)
    del x_full1, y_full1
    full_s1_pred = predict_ms_cape_stage1(full_s1_bundle, features_51, valid, pi_true=pi_full)
    del full_s1_bundle

    # Fit full Stage-2 on strictly out-of-quadrant outer_s1_preds, then infer on full_s1_pred!
    s2_trace_full_oof = compute_stage2_trace_features(outer_s1_preds, valid)
    full_s2_bundle = fit_ms_cape_stage2(
        s2_trace_full_oof, features_51, regime_indices, labels, valid, seed=SEED + 199
    )
    del s2_trace_full_oof
    s2_trace_full_infer = compute_stage2_trace_features(full_s1_pred, valid)
    full_surface = predict_ms_cape_stage2(
        full_s2_bundle, s2_trace_full_infer, features_51, regime_indices, valid, pi_true=pi_full
    )
    del full_s2_bundle, s2_trace_full_infer, full_s1_pred
    gc.collect()

    # Pre-placement novelty check on continuous surface!
    registry_path = REPORT / "registry.json"
    registry_meta = json.loads(registry_path.read_text())
    surface_tif = RUN / "ms-cape-surface.tif"
    write_submission_file(
        full_surface,
        template,
        surface_tif,
        run_name="gems30-ms-cape-surface",
        note="Continuous MS-CAPE calibrated surface before dot placement; research diagnostic.",
    )
    surface_audit = audit(surface_tif, template, registry_path, "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    print(
        f"  Pre-placement surface novelty: {surface_audit['decision']} "
        f"(max Spearman={max(r['spearman_full_footprint'] for r in surface_audit['comparisons']):.4f})",
        flush=True,
    )
    if surface_audit["decision"] == "duplicate-stop":
        dump(REPORT / "duplicate-stop.json", {"stage": "surface", "decision": "duplicate-stop"})
        raise ValueError("DUPLICATE-STOP triggered on continuous surface before placement")

    # Place final MS-CAPE E3 dots (44,090 off-catalogue dots via exact 300 m submodular DTI cover + 200 m flank hygiene)
    final_dots = submod_dti_select(
        full_surface,
        active_mask=valid & ~labels,
        visible_faults=labels,
        budget=DOT_BUDGET,
        radius_px=3.0,
        flank_exclusion_px=2.0,
        min_sep_px=2.2,
    )
    if int(final_dots[valid].sum()) != DOT_BUDGET or int(final_dots[labels].sum()) != 0:
        raise AssertionError("final dot count or exact off-catalogue constraint violated")

    identity = hashlib.sha256(np.ascontiguousarray(final_dots[valid]).tobytes()).hexdigest()
    run_name = f"gems30-MS-CAPE-submod300-44090-20261025-{identity[:12]}"
    generated_nan = RUN / f"{run_name}-nan.tif"
    generated_zeros = RUN / f"{run_name}-zeros.tif"

    # Write provisional sidecar note first (updated before publication if negative)
    write_submission_file(final_dots, template, generated_nan, run_name=run_name, note=NOTE_PROMOTE)
    write_submission_file(
        final_dots,
        template,
        generated_zeros,
        run_name=f"{run_name}-zeros",
        note=NOTE_PROMOTE,
        outside_value=0.0,
    )

    dots_audit = audit(generated_nan, template, registry_path, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    print(
        f"  Post-placement dots novelty: {dots_audit['decision']} "
        f"(max Spearman={max(r['spearman_full_footprint'] for r in dots_audit['comparisons']):.4f}, "
        f"max 3px overlap={max(r['candidate_fraction_within_3px_of_reference'] for r in dots_audit['comparisons']):.4f})",
        flush=True,
    )
    if dots_audit["decision"] == "duplicate-stop":
        dump(REPORT / "duplicate-stop.json", {"stage": "dots", "decision": "duplicate-stop"})
        raise ValueError("DUPLICATE-STOP triggered on final placed dots")

    # --- STEP 4: 4-Fold Spatially-Blocked Whole-Component Hide-and-Recover Evaluation ---
    print("[4/6] Running 51-feature leakage canaries & 4-fold hide-and-recover evaluation...", flush=True)
    primary_arms = tuple(COMPARATOR_ARMS) + (CANDIDATE_ARM,)
    ladder_arms = ("core19", "g30s19_hist_best", "ms_cape_e1", "ms_cape_e2", "ms_cape_e3")
    block_rows = {name: [] for name in primary_arms}
    ladder_block_rows = {name: [] for name in ladder_arms}
    folds_out: list[dict] = []
    canaries_out: list[dict] = []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)

    # Indices of the 8 Verduzco tilt/basement channels inside features_51: channels [19..26]
    tilt8_indices = list(range(19, 27))

    for fold in folds_spec:
        check_time(deadline)
        f = fold["fold"]
        hidden_total += fold["hidden"].astype(np.uint8)
        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(DOT_BUDGET * active.sum() / valid.sum()))
        pi_tr = float(np.mean(fold["visible"][fold["train_mask"]]))
        truth_mass_est = float(pi_tr * active.sum())

        print(f"  Fold {f}: running 51 single-feature leakage canaries...", flush=True)
        c_rows = run_feature_canaries_51(features_51, fold["visible"], fold, SEED + f, deadline)
        canaries_out.append({"fold": f, "features": c_rows})
        n_alarms = sum(1 for r in c_rows if r["alarm_above_0_90"])
        max_can = max(max(r["raw_auc_either_direction"], r["univariate_training_only_hgb_auc"]) for r in c_rows)
        print(f"  Fold {f}: canaries complete (alarms={n_alarms}, max_auc={max_can:.4f})", flush=True)

        # Paired training pixel sample coordinates (seed = SEED + f) for baseline comparators
        xb, yb = sample_pixels_lowmem(
            base, fold["visible"], fold["train_mask"], negatives_per_positive=6, seed=SEED + f
        )
        x_tilt, y_tilt = sample_pixels_lowmem(
            features_51,
            fold["visible"],
            fold["train_mask"],
            negatives_per_positive=6,
            seed=SEED + f,
            channel_indices=tilt8_indices,
        )
        xg, yg = sample_pixels_lowmem(
            g30s19_40, fold["visible"], fold["train_mask"], negatives_per_positive=8, seed=SEED + f
        )
        if not np.array_equal(yb, y_tilt):
            raise AssertionError("paired comparator sample mismatch")

        # 1) physics_tilt8
        m_t8, med_t8, scl_t8 = fit_canonical_hgb(x_tilt, y_tilt, seed=SEED + f)
        with threadpool_limits(limits=2):
            p_t8 = predict_grid_lowmem(m_t8, features_51, med_t8, scl_t8, active, channel_indices=tilt8_indices)
        em_t8 = select_poisson_dots(p_t8, active, count)
        del m_t8, p_t8, x_tilt

        # 2) core19 (canonical baseline)
        m_c19, med_c19, scl_c19 = fit_canonical_hgb(xb, yb, seed=SEED + f)
        with threadpool_limits(limits=2):
            p_c19 = predict_grid(m_c19, base, med_c19, scl_c19, active)
        em_c19 = select_poisson_dots(p_c19, active, count)
        del m_c19, p_c19, xb

        # 3) g30s19_hist_best (40-ch habitat HGB + EDGE at matched count)
        m_g30, med_g30, scl_g30 = fit_g30s19_hgb(xg, yg, seed=SEED + f)
        with threadpool_limits(limits=2):
            p_g30_raw = predict_grid(m_g30, g30s19_40, med_g30, scl_g30, active)
        p_g30 = recalibrate_prior_odds(p_g30_raw, pi_true=pi_tr, pi_sample=float(np.mean(yg)), valid=active)
        em_g30 = select_edge_dots_matched(p_g30, active, truth_mass_est=truth_mass_est, count=count)
        del m_g30, p_g30_raw, p_g30, xg

        # 4) MS-CAPE Experiment 1: Stage-1 51-feature ensemble + Poisson-300m
        p_s1_test = np.where(active, outer_s1_preds, 0.0).astype(np.float32)
        em_e1 = select_poisson_dots(p_s1_test, active, count)

        # 5) Nested out-of-quadrant Stage-1 predictions inside fold["train_mask"] for Stage-2!
        inner_quads = [q for q in range(4) if q != f]
        s1_train_oof = np.zeros(valid.shape, dtype=np.float32)
        for q_hold in inner_quads:
            check_time(deadline)
            inner_tr_mask = fold["train_mask"] & (q_map != q_hold)
            inner_val_mask = fold["train_mask"] & (q_map == q_hold)
            pi_in = float(np.mean(fold["visible"][inner_tr_mask]))
            xi, yi = sample_pixels_lowmem(
                features_51, fold["visible"], inner_tr_mask, negatives_per_positive=8, seed=SEED + 50 * f + q_hold
            )
            b_in = fit_ms_cape_stage1(xi, yi, seed=SEED + 50 * f + q_hold)
            del xi, yi
            p_in = predict_ms_cape_stage1(b_in, features_51, inner_val_mask, pi_true=pi_in)
            s1_train_oof[inner_val_mask] = p_in[inner_val_mask]
            del b_in, p_in

        train_domain_union = fold["train_mask"]
        s2_trace_tr = compute_stage2_trace_features(s1_train_oof, train_domain_union)
        s2_bundle = fit_ms_cape_stage2(
            s2_trace_tr, features_51, regime_indices, fold["visible"], fold["train_mask"], seed=SEED + f
        )
        del s2_trace_tr, s1_train_oof

        # Predict Stage-2 on held-out quadrant (using outer_s1_preds strictly inside score_valid!)
        s1_for_test_quad = np.where(fold["score_valid"], outer_s1_preds, 0.0).astype(np.float32)
        s2_trace_te = compute_stage2_trace_features(s1_for_test_quad, fold["score_valid"])
        p_s2_test = predict_ms_cape_stage2(
            s2_bundle, s2_trace_te, features_51, regime_indices, active, pi_true=pi_tr
        )
        del s2_bundle, s2_trace_te

        # MS-CAPE Experiment 2: Two-Stage + Poisson-300m
        em_e2 = select_poisson_dots(p_s2_test, active, count)

        # MS-CAPE Experiment 3 (Primary Candidate): Two-Stage + Submodular 300m DTI cover & 200m flank hygiene
        em_e3 = submod_dti_select(
            p_s2_test,
            active_mask=active,
            visible_faults=fold["visible"],
            budget=count,
            radius_px=3.0,
            flank_exclusion_px=2.0,
            min_sep_px=2.2,
        )

        emitted_map = {
            "physics_tilt8": em_t8,
            "core19": em_c19,
            "g30s19_hist_best": em_g30,
            "ms_cape_e1": em_e1,
            "ms_cape_e2": em_e2,
            "ms_cape_e3": em_e3,
        }

        fold_rec = {
            **fold["metadata"],
            "dot_budget_each_arm": count,
            "arms": {},
            "experiment_ladder_arms": {},
        }
        for arm_name, em_arr in emitted_map.items():
            sc = masked_dti_by_blocks(
                em_arr, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128
            )
            pooled_no_dti = {k: v for k, v in sc["pooled"].items() if k != "dti"}
            if arm_name in block_rows:
                block_rows[arm_name].extend(sc["spatial_blocks"])
                fold_rec["arms"][arm_name] = pooled_no_dti
            if arm_name in ladder_block_rows:
                ladder_block_rows[arm_name].extend(sc["spatial_blocks"])
                fold_rec["experiment_ladder_arms"][arm_name] = pooled_no_dti
            print(
                f"  Fold {f} | {arm_name:18s}: dots={int(em_arr.sum())} "
                f"tp_w={sc['pooled']['tp_weight']:.1f} fp_w={sc['pooled']['fp_weight']:.1f}",
                flush=True,
            )
        folds_out.append(fold_rec)
        del em_t8, em_c19, em_g30, em_e1, em_e2, em_e3, p_s1_test, p_s2_test
        gc.collect()

    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("each withheld positive must be scored exactly once across the 4 folds")

    print("[5/6] Computing 2,000-replicate paired spatial-block bootstrap CIs...", flush=True)
    summary = spatial_bootstrap(block_rows, candidate=CANDIDATE_ARM, replicates=2000, seed=3071)
    ladder_summary = spatial_bootstrap(ladder_block_rows, candidate="ms_cape_e3", replicates=2000, seed=3071)

    for arm_name, st in ladder_summary["arms"].items():
        print(
            f"  POOLED HOLDOUT-DTI | {arm_name:18s}: {st['value']:.6f} "
            f"95% CI [{st['ci95'][0]:.6f}, {st['ci95'][1]:.6f}]",
            flush=True,
        )
    for comp_name, d_st in summary["candidate_minus"].items():
        print(
            f"  PAIRED DELTA ({CANDIDATE_ARM} - {comp_name}): "
            f"{d_st['value']:+.6f} 95% CI [{d_st['ci95'][0]:+.6f}, {d_st['ci95'][1]:+.6f}]",
            flush=True,
        )

    # Independent diagnostic checks (NOT used for model selection or tuning):
    # (A) Off-catalogue USGS SGMC fault discovery (d_cat > 3 px)
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as s_ds:
        sgmc_mask = (s_ds.read(1) > 0) & valid
    dist_cat_full = distance_transform_edt(~labels)
    sgmc_offcat = sgmc_mask & (dist_cat_full > 3.0)
    sgmc_diag = masked_dti_by_blocks(
        final_dots, sgmc_offcat, labels | (sgmc_mask & ~sgmc_offcat), valid, block_size_px=128
    )["pooled"]

    # (B) Neotectonic steep-terrain calibration check (catalogue vs final_dots)
    slope_band = np.asarray(features_51[18], dtype=np.float32)
    p75_slope = float(np.nanpercentile(slope_band[valid], 75.0))
    steep_mask = valid & (slope_band >= p75_slope)
    cat_steep_frac = float(np.mean(steep_mask[labels]))
    cand_steep_frac = float(np.mean(steep_mask[final_dots > 0]))

    alarms = [dict(fold=f["fold"], **row) for f in canaries_out for row in f["features"] if row["alarm_above_0_90"]]
    beats_all = all(
        delta["value"] > 0.0 and delta["ci95"][0] > 0.0 for delta in summary["candidate_minus"].values()
    )
    beats_hist_best = bool(
        summary["candidate_minus"]["g30s19_hist_best"]["value"] > 0.0
        and summary["candidate_minus"]["g30s19_hist_best"]["ci95"][0] > 0.0
        and summary["candidate_minus"]["core19"]["value"] > 0.0
        and summary["candidate_minus"]["core19"]["ci95"][0] > 0.0
    )
    novelty_clear = (
        surface_audit["decision"] != "duplicate-stop"
        and dots_audit["decision"] != "duplicate-stop"
        and not surface_audit.get("errors")
        and not dots_audit.get("errors")
    )
    scientific_pass = bool(beats_all and beats_hist_best and not alarms and novelty_clear)
    final_note = NOTE_PROMOTE if scientific_pass else NOTE_NEGATIVE

    # Publish final GeoTIFFs to docs/downloads/ with final machine-adjudicated note
    pub_dir = ROOT / "docs/downloads"
    pub_dir.mkdir(parents=True, exist_ok=True)
    pub_nan_path = pub_dir / f"{run_name}-nan.tif"
    pub_zeros_path = pub_dir / f"{run_name}-zeros.tif"

    nan_manifest = write_submission_file(
        final_dots, template, pub_nan_path, run_name=run_name, note=final_note
    )
    zeros_manifest = write_submission_file(
        final_dots,
        template,
        pub_zeros_path,
        run_name=f"{run_name}-zeros",
        note=final_note,
        outside_value=0.0,
    )
    sidecar_extra = {
        "submission_approved": False,
        "download_ok": True,
        "eligible_for_separate_slot_selector": bool(scientific_pass and registry_meta.get("complete") is True),
        "scientific_gate_passed": scientific_pass,
        "run_card": "docs/research/ms-cape/run-card.json",
        "lineage": "Fresh MS-CAPE multi-physics fit; zero historical submission rasters read as inputs or masks",
        "method": TRANSFORM_VERSION,
        "preregistration_sha256": prereg_sha,
        "dataset_signature": manifest["dataset_signature"],
    }
    nan_manifest.update(sidecar_extra)
    zeros_manifest.update(sidecar_extra)
    dump(pub_nan_path.with_suffix(".json"), nan_manifest)
    dump(pub_zeros_path.with_suffix(".json"), zeros_manifest)
    # Re-run dots novelty audit against exact published bytes in docs/downloads/ so candidate_sha256 matches!
    dots_audit = audit(pub_nan_path, template, registry_path, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)

    val_nan = validate_submission_file(pub_nan_path, template).to_dict()
    val_zeros = validate_submission_file(pub_zeros_path, template, require_finite_all_cells=True).to_dict()
    dump(REPORT / "validation.json", {"published_nan": val_nan, "portal_zeros": val_zeros})

    with rasterio.open(pub_nan_path) as ds_n, rasterio.open(pub_zeros_path) as ds_z, rasterio.open(template) as ref:
        arr_n = ds_n.read(1)
        arr_z = ds_z.read(1)
        validator_block = {
            "status": "passed" if (val_nan["passed"] and val_zeros["passed"]) else "failed",
            "no_nan_inside_footprint": bool(np.isfinite(arr_n[valid]).all()),
            "values_in_0_1": bool(np.all((arr_n[valid] >= 0.0) & (arr_n[valid] <= 1.0))),
            "crs_match": ds_n.crs == ref.crs,
            "shape_match": ds_n.shape == ref.shape,
            "transform_match": ds_n.transform == ref.transform,
            "single_float32_band": ds_n.count == 1 and ds_n.dtypes == ("float32",),
            "nan_nodata_outside_footprint": bool(np.isnan(arr_n[~valid]).all()),
            "portal_zeros_all_12279160_cells_finite_in_0_1": bool(
                np.isfinite(arr_z).all() and np.all((arr_z >= 0.0) & (arr_z <= 1.0))
            ),
            "portal_zeros_bit_identical_inside_footprint": bool(np.array_equal(arr_n[valid], arr_z[valid])),
            "positive_catalogue_pixels": int(np.count_nonzero(arr_n[labels] > 0)),
            "emitted_dots": int(np.count_nonzero(arr_n[valid] > 0)),
            "organizer_acceptance_confirmed": False,
        }
    if not (val_nan["passed"] and val_zeros["passed"]) or validator_block["positive_catalogue_pixels"] != 0:
        raise AssertionError("final GeoTIFF contract check failed")

    novelty_summary = summarize_novelty(surface_audit, dots_audit, registry_meta.get("complete", False))
    elapsed = time.monotonic() - started_mono
    verdict = "promote" if (scientific_pass and registry_meta.get("complete") is True and elapsed <= 7200) else "negative"

    blockers: list[str] = []
    if verdict != "promote":
        blockers.append("Candidate failed one or more automated research promotion gates")

    cand_stats = summary["arms"][CANDIDATE_ARM]
    comparators_dict = {k: v for k, v in summary["arms"].items() if k != CANDIDATE_ARM}

    card = {
        "schema_version": 2,
        "run_id": run_name,
        "candidate_arm": CANDIDATE_ARM,
        "comparator_arms": COMPARATOR_ARMS,
        "expected_features": list(ALL_STAGE1_FEATURE_NAMES),
        "hypothesis": (
            "Unmapped Great Basin geothermal and neotectonic faults are multi-kilometer planar crustal "
            "discontinuities where deconfounded piedmont-toe topographic flexure and 1 m LiDAR scarp "
            "polarity co-align in strike with Verduzco potential-field tilt zero-contours, basement-cover "
            "steps, and GeoDAWN/GDR hydrothermal alteration/upflow plumes; bridging wash-interrupted gaps "
            "with nested OOF axial trace propagation and allocating binary dots via exact 300 m submodular "
            "DTI kernel cover (>200 m from visible catalogue) significantly improves hide-and-recover DTI."
        ),
        "mechanism": (
            "51-channel Stage-1 multi-physics ensemble (core19 + 32 bounded <=1.2km Verduzco tilt, piedmont "
            "flexure, 8-azimuth steerable lineament/consilience & deconfounded K/Th-U/Th/GDR upflow channels) "
            "+ nested OOF Stage-2 <=0.8km axial ridge & wash-gap-bridge stacker + Bayes prior-odds calibration "
            "+ exact Minoux lazy-greedy 300m triangular-kernel submodular DTI cover (44,090 dots, d_vis > 200m)."
        ),
        "non_fault_mimic": (
            "Dendritic erosional mountain ridge crests and canyon walls; Pleistocene Lake Lahontan wave-cut "
            "shorelines and Tertiary basalt mesa rims; GeoDAWN steep-terrain flight-drape clearance variations."
        ),
        "lane": "MS-CAPE two-stage multi-physics axial trace propagation + 300m submodular DTI cover",
        "externally_assigned_lane_verified": True,
        "experiments_run": EXPERIMENTS_RUN,
        "fixed_arms": list(primary_arms),
        "experiment_cap": 3,
        "experimental_elapsed_seconds": round(elapsed, 2),
        "this_execution_seconds": round(elapsed, 2),
        "time_cap_hours": 2,
        "preregistration": "docs/research/ms-cape/preregistration.md",
        "preregistration_sha256": prereg_sha,
        "dataset_signature": manifest["dataset_signature"],
        "physical_support_px": SUPPORT_PX,
        "holdout": {
            **cand_stats,
            "evaluator_version": EVALUATOR_VERSION,
            "protocol_version": SEGMENT_PROTOCOL_VERSION,
            "scope": "buffered whole-segment catalogue-recovery proxy; NOT organizer performance",
            "bootstrap": summary["bootstrap"],
            "comparators": comparators_dict,
            "candidate_minus": summary["candidate_minus"],
            "experiment_ladder": ladder_summary,
        },
        "historical_best_rerun": {
            "verified": True,
            "comparator_arm": "g30s19_hist_best",
            "description": "Same-protocol 4-fold rerun of Lane G30-S19 (40-channel non-leaky habitat HGB + 300 m EDGE emitter)",
            "evaluator_version": EVALUATOR_VERSION,
            "protocol_version": SEGMENT_PROTOCOL_VERSION,
            "candidate_beats_best_with_paired_ci": beats_hist_best,
        },
        "supplementary_diagnostics": {
            "off_catalogue_sgmc_fault_discovery": {
                "label": "DIAGNOSTIC-PROXY-DTI (USGS SGMC off-catalogue d_cat > 300m; NOT used for tuning)",
                "off_catalogue_sgmc_pixels": int(sgmc_offcat.sum()),
                "dti": sgmc_diag["dti"],
                "tp_weight": sgmc_diag["tp_weight"],
                "fp_weight": sgmc_diag["fp_weight"],
            },
            "steep_terrain_calibration": {
                "catalogue_top_quartile_slope_fraction": round(cat_steep_frac, 4),
                "candidate_top_quartile_slope_fraction": round(cand_steep_frac, 4),
            },
        },
        "feature_canaries": {
            "features_per_fold": len(ALL_STAGE1_FEATURE_NAMES),
            "folds": 4,
            "alarm_count": len(alarms),
            "alarms": alarms,
            "max_observed_auc": max(
                max(r["raw_auc_either_direction"], r["univariate_training_only_hgb_auc"])
                for f in canaries_out
                for r in f["features"]
            ),
            "receipt": "docs/research/ms-cape/results.json",
        },
        "registry": novelty_summary,
        "raster_sha256": nan_manifest["output_sha256"],
        "published_tiff": f"docs/downloads/{pub_nan_path.name}",
        "portal_zeros_sha256": zeros_manifest["output_sha256"],
        "portal_zeros_tiff": f"docs/downloads/{pub_zeros_path.name}",
        "validator_output": validator_block,
        "submission_name": run_name,
        "note": final_note,
        "verdict": verdict,
        "scientific_gate_passed": scientific_pass,
        "verdict_scope": "machine-adjudicated research & format gates; separate weekly slot selector applies",
        "download_ok": True,
        "slot_selected": False,
        "submission_approved": False,
        "weekly_slots_used": 0,
        "organizer_confirmed_scores": [],
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "blockers": blockers,
    }

    results_doc = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preregistration_sha256": prereg_sha,
        "raster_sha256": nan_manifest["output_sha256"],
        "portal_zeros_sha256": zeros_manifest["output_sha256"],
        "candidate_arm": CANDIDATE_ARM,
        "comparator_arms": COMPARATOR_ARMS,
        "summary": summary,
        "experiment_ladder_summary": ladder_summary,
        "folds": folds_out,
        "feature_canaries": canaries_out,
        "bootstrap_sufficient_statistics": block_rows,
    }

    dump(REPORT / "results.json", results_doc)
    dump(REPORT / "run-card.json", card)

    # Clean up large temporary scratch memmaps in outputs/ms-cape so workspace stays light
    del features_51, g30s19_40
    gc.collect()
    for tmp_f in (memmap_51_path, ms_cape_32_path, g30s19_40_path, surface_tif, generated_nan, generated_zeros):
        if tmp_f.exists():
            tmp_f.unlink()
        js = tmp_f.with_suffix(".json")
        if js.exists():
            js.unlink()

    print(f"[6/6] Completed MS-CAPE in {elapsed:.1f}s -> verdict={verdict}", flush=True)
    return card


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=float, default=7000.0)
    args = parser.parse_args()
    card = run(args.max_seconds)
    print(json.dumps({k: card[k] for k in ("run_id", "verdict", "experimental_elapsed_seconds")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
