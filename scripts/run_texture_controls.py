#!/usr/bin/env python3
"""Execute the frozen TDX-C2 continuation; shared caches/evaluator/writer only.

One fixed four-arm experiment; not an uploader or slot selector. Duplicate-stop
means immediate stop with no new public TIFF, never perturbation to game novelty.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from gemsdoe30.experiments import CORE_FEATURES, TDX_FEATURES, CONTROL_FEATURES, LayerStack, contract
from gemsdoe30.holdout import (EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION,
                              masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds)
from gemsdoe30.submission import write_submission_file, validate_submission_file
from gemsdoe30.texture import SUPPORT_PX, fold_consensus
from gemsdoe30.texture_controls import TRANSFORM_VERSION, PHASES, control_features
from scripts.run_texture_displacement import load_cache, fit_model, select_dots, sha, dump, check_time
from scripts.feature_value_holdout import sample_training_pixels, predict_grid
from scripts.verify_prepared_cache import verify as verify_prepared_cache
from scripts.check_novelty import audit

REPORT = ROOT / "docs/research/texture-controls"
CACHE = ROOT / "data/processed/texture-controls"
RUN = ROOT / "outputs/texture-controls"
SPEC = contract({"experiment_spec": "tdxc2"})
NAMES = SPEC["features"]
SEED, DOT_BUDGET = 3070, 44090
NOTE = "TDX-C2 core19 plus magnetic profile lag; matched zero-lag/phase controls; research only, NOT approved for competition upload."


def cached_controls(base, valid, fields, manifest):
    CACHE.mkdir(parents=True, exist_ok=True)
    signature = {"transform_version": TRANSFORM_VERSION,
                 "transform_code_sha256": sha(ROOT / SPEC["transform_path"]),
                 "parent_transform_code_sha256": sha(ROOT / SPEC["parent_transform_path"]),
                 "parent_transform_version": SPEC["parent_transform_version"],
                 "dataset_signature": manifest["dataset_signature"],
                 "original_cache_receipt_sha256": sha(ROOT / "data/processed/texture-displacement/receipt.json")}
    receipt_path = CACHE / "receipt.json"
    names = ("zero_mag", "zero_rtp", "phase_mag", "phase_rtp")
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("signature") != signature:
            raise ValueError("stale control cache; never silently rebuild under new code")
        for name in names:
            if sha(CACHE / f"{name}.npy") != receipt["sha256"][name]:
                raise ValueError(f"control cache hash mismatch: {name}")
    else:
        print("Constructing preregistered zero-lag and local phase controls", flush=True)
        values = control_features(base[0], base[1], base[12], valid, fields["supported"])
        for name, array in values.items():
            np.save(CACHE / f"{name}.npy", array)
        receipt = {"signature": signature, "sha256": {name: sha(CACHE / f"{name}.npy") for name in names},
                   "support_px": SUPPORT_PX, "supported_pixels": int(fields["supported"].sum()),
                   "phase_radians": list(PHASES), "source_bands_1based": [1, 2, 13],
                   "uses_catalogue_geometry": False, "uses_registry_values": False,
                   "uses_template_values_as_features": False,
                   "original_feature_receipt": json.loads((ROOT / "data/processed/texture-displacement/receipt.json").read_text())}
        dump(receipt_path, receipt)
    dump(REPORT / "feature-receipt.json", receipt)
    return {name: np.load(CACHE / f"{name}.npy", mmap_mode="r") for name in names}


def feature_layers(base, original, controls, train):
    derived = [original["mag_texture"], original["rtp_texture"]]
    consensus, normalizer = fold_consensus(*derived, original["gravity_edge"], train)
    derived.append(consensus)
    for prefix in ("zero", "phase"):
        a, b = controls[f"{prefix}_mag"], controls[f"{prefix}_rtp"]
        consensus, check = fold_consensus(a, b, original["gravity_edge"], train)
        if check != normalizer:
            raise AssertionError("matched controls must share training-only gravity normalization")
        derived.extend([a, b, consensus])
    return [base[j] for j in range(19)] + derived, normalizer


def arm_columns(name):
    return list(range(19)) + ({"core19": [], "tdx22": [19, 20, 21],
                              "zero22": [22, 23, 24], "phase22": [25, 26, 27]}[name])


def canaries(layers, training, y, fold, seed, deadline):
    active = fold["score_valid"] & ~fold["visible"]
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(active & ~fold["hidden"])
    negatives = np.random.default_rng(seed + 10000).choice(negatives, min(60000, negatives.size), replace=False)
    test = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])
    checks = []
    for j, name in enumerate(NAMES):
        check_time(deadline)
        values = layers[j].ravel()[test]
        model, median, scale = fit_model(training[:, j:j + 1], y, seed=seed + j, iterations=32, leaves=7)
        values = np.where(np.isfinite(values), values, median[0])
        raw_auc = float(roc_auc_score(target, values))
        with threadpool_limits(limits=2):
            probabilities = model.predict_proba(((values - median[0]) / scale[0])[:, None])[:, 1]
        model_auc = float(roc_auc_score(target, probabilities))
        checks.append({"feature": name, "label": "LEAKAGE-CANARY AUC (not DTI)",
                       "raw_auc": raw_auc, "raw_auc_either_direction": max(raw_auc, 1 - raw_auc),
                       "univariate_training_only_hgb_auc": model_auc,
                       "alarm_above_0_90": max(raw_auc, 1 - raw_auc, model_auc, 1 - model_auc) > .90,
                       "heldout_positives": int(positives.size), "sampled_negatives": int(negatives.size)})
    return checks


def novelty_summary(report):
    rows = report["comparisons"]
    return {"decision": report["decision"], "registry_entries_compared": len(rows),
            "max_spearman": max((r["spearman_full_footprint"] for r in rows
                                  if r["spearman_full_footprint"] is not None), default=None),
            "max_fraction_within_3px": max((r["candidate_fraction_within_3px_of_reference"] for r in rows
                                            if r["candidate_fraction_within_3px_of_reference"] is not None), default=None),
            "errors": report["errors"]}


def duplicate_guard(receipt, stage):
    if receipt["decision"] == "duplicate-stop":
        dump(REPORT / "duplicate-stop.json", {"stage": stage, "decision": "duplicate-stop",
                                              "no_further_experiment": True, "submission_approved": False})
        raise ValueError(f"duplicate-stop on {stage}; stop, no public TIFF or retuning")
    if receipt["errors"]:
        raise ValueError(f"registry input error during {stage}; cannot accept an incomplete transfer")


def run(max_seconds):
    started = time.monotonic()
    deadline = started + max_seconds
    RUN.mkdir(parents=True, exist_ok=True)
    if (REPORT / "started.json").exists():
        raise ValueError("execution already registered; do not silently overwrite an inspected experiment")
    prereg = sha(REPORT / "preregistration.md")
    registration = json.loads((REPORT / "registration.json").read_text())
    if (registration["registered_plan_sha256"] != prereg
            or registration["registry_sha256"] != sha(REPORT / "registry.json")):
        raise ValueError("frozen plan/registry changed after registration")
    dump(REPORT / "started.json", {"started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                   "experiment_count": 1, "fixed_arms": list(SPEC["arms"]),
                                   "preregistration_sha256": prereg, "script_sha256": sha(__file__),
                                   "max_experimental_seconds": max_seconds})
    dump(REPORT / "cache-verification.json", verify_prepared_cache(ROOT / "data/processed"))
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    valid = np.load(ROOT / "data/processed/valid.npy").astype(bool)
    labels = np.load(ROOT / "data/processed/labels.npy", mmap_mode="r") > .5
    label_valid = np.load(ROOT / "data/processed/label_valid.npy", mmap_mode="r")
    if np.any(valid & ~label_valid):
        raise ValueError("unknown training labels inside footprint")
    labels &= valid
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    for row in manifest["source_files"].values():
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("raw source identity mismatch")
    original = load_cache(base, valid, manifest, report_dir=None)
    controls = cached_controls(base, valid, original, manifest)
    blocks = {name: [] for name in SPEC["arms"]}
    folds, all_canaries = [], []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)
    for fold in spatial_segment_folds(labels, valid, buffer_px=SUPPORT_PX):
        check_time(deadline)
        f = fold["fold"]; hidden_total += fold["hidden"]
        layers, normalizer = feature_layers(base, original, controls, fold["train_mask"])
        x, y = sample_training_pixels(LayerStack(layers), fold["visible"], fold["train_mask"],
                                      negatives_per_positive=6, seed=SEED + f)
        print(f"Fold {f}: testing all 28 individual feature canaries", flush=True)
        checks = canaries(layers, x, y, fold, SEED + f, deadline)
        all_canaries.append({"fold": f, "features": checks})
        dump(REPORT / "canaries-partial.json", {"folds": all_canaries, "status": "partial until results.json exists"})
        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(DOT_BUDGET * active.sum() / valid.sum()))
        row = {**fold["metadata"], "normalization": normalizer, "dot_budget_each_arm": count, "arms": {}}
        for name in SPEC["arms"]:
            check_time(deadline)
            columns = arm_columns(name)
            model, median, scale = fit_model(x[:, columns], y, seed=SEED + f)
            with threadpool_limits(limits=2):
                prediction = predict_grid(model, LayerStack([layers[j] for j in columns]), median, scale, active)
            emitted = select_dots(prediction, active, count)
            scored = masked_dti_by_blocks(emitted, fold["hidden"], fold["visible"],
                                          fold["score_valid"], block_size_px=128)
            blocks[name].extend(scored["spatial_blocks"])
            row["arms"][name] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
            print(f"Fold {f}: {name}; {count} dots (construction diagnostic)", flush=True)
            del prediction, emitted, model
        folds.append(row)
        del layers, x, y
    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("each withheld positive must occur exactly once")
    summary = spatial_bootstrap(blocks, candidate="tdx22", replicates=2000, seed=3071)
    alarms = [dict(fold=f["fold"], **r) for f in all_canaries for r in f["features"] if r["alarm_above_0_90"]]
    science_pass = not alarms and all(d["ci95"][0] > 0 for d in summary["candidate_minus"].values())
    # Save negative evidence even if a later novelty stop prevents a public TIFF.
    results = {"schema_version": 2, "experiment_spec": "tdxc2", "summary": summary,
               "bootstrap_sufficient_statistics": blocks, "folds": folds, "feature_canaries": all_canaries,
               "preregistration_sha256": prereg, "scientific_gate_passed": science_pass,
               "scope": "Continuation on previously inspected catalogue folds; not independent confirmation"}
    dump(REPORT / "results.json", results)
    print("Fitting only the frozen tdx22 final method, not the best control", flush=True)
    layers, normalization = feature_layers(base, original, controls, valid)
    candidate = LayerStack(layers[:22])
    x, y = sample_training_pixels(candidate, labels, valid, negatives_per_positive=6, seed=SEED)
    model, median, scale = fit_model(x, y, seed=SEED)
    with threadpool_limits(limits=2):
        surface = predict_grid(model, candidate, median, scale, valid)
    del candidate, layers, model, x, y
    template, registry = ROOT / "data/raw/sample_submission.tif", REPORT / "registry.json"
    write_submission_file(surface, template, RUN / "tdxc2-surface.tif",
                          run_name="gems30-tdxc2-surface", note="Continuous TDX-C2 research surface; not a submission.")
    surface_audit = audit(RUN / "tdxc2-surface.tif", template, registry, "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    duplicate_guard(surface_audit, "surface")
    check_time(deadline)
    dots = select_dots(surface, valid & ~labels, DOT_BUDGET)
    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    name = f"gems30-TDXC2-44090-20261025-{identity[:12]}"
    generated = RUN / f"{name}.tif"
    sidecar = write_submission_file(dots, template, generated, run_name=name, note=NOTE)
    dots_audit = audit(generated, template, registry, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    duplicate_guard(dots_audit, "dots")
    check_time(deadline)
    validation = validate_submission_file(generated, template).to_dict()
    with rasterio.open(generated) as ds, rasterio.open(template) as reference:
        a = ds.read(1)
        validator = {"status": "passed" if validation["passed"] else "failed",
                     "no_nan_inside_footprint": bool(np.isfinite(a[valid]).all()),
                     "values_in_0_1": bool(np.all((a[valid] >= 0) & (a[valid] <= 1))),
                     "crs_match": ds.crs == reference.crs, "shape_match": ds.shape == reference.shape,
                     "transform_match": ds.transform == reference.transform,
                     "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
                     "nan_nodata_outside_footprint": bool(np.isnan(a[~valid]).all()),
                     "positive_catalogue_pixels": int(np.count_nonzero(a[labels] > 0)),
                     "emitted_dots": int(np.count_nonzero(a[valid] > 0)),
                     "organizer_acceptance_confirmed": False}
    if not validation["passed"] or validator["positive_catalogue_pixels"] or len(NOTE) > 140:
        raise ValueError("file contract/exact catalogue mask/artifact identity failed")
    elapsed = round(time.monotonic() - started, 2)
    novelty = {"complete": False, "surface": novelty_summary(surface_audit), "dots": novelty_summary(dots_audit),
               "coverage": "164 observed aligned byte identities at nine frozen repository snapshots; missing private lanes/original surfaces"}
    card = {"schema_version": 2, "experiment_spec": "tdxc2", "run_id": name,
            "hypothesis": "Nonzero-lag magnetic profile correspondence adds displacement-specific fault recovery beyond the full 19-band stack.",
            "mechanism": "Full-stack HGB plus cross-scale opposite-flank lag gain; matched zero-lag and local Fourier-phase controls.",
            "non_fault_mimic": "Intrusive lithologic contact; survey/gridding seam",
            "lane": "TDX-C2 magnetic profile displacement continuation; not externally assigned",
            "experiments_run": 1, "fixed_arms": list(SPEC["arms"]), "experiment_cap": 3,
            "experimental_elapsed_seconds": elapsed, "time_cap_hours": 2,
            "physical_support_px": SUPPORT_PX,
            "confirmation_scope": "Previously inspected regional catalogue folds; exploratory continuation, not independent confirmation",
            "holdout": {**summary["arms"]["tdx22"], "evaluator_version": EVALUATOR_VERSION,
                        "protocol_version": SEGMENT_PROTOCOL_VERSION,
                        "scope": "buffered whole-segment catalogue recovery; NOT organizer performance",
                        "comparators": {n: summary["arms"][n] for n in SPEC["arms"] if n != "tdx22"},
                        "candidate_minus": summary["candidate_minus"], "bootstrap": summary["bootstrap"]},
            "feature_canaries": {"features_per_fold": 28, "folds": 4, "alarm_count": len(alarms), "alarms": alarms,
                                  "receipt": "docs/research/texture-controls/results.json"},
            "registry": novelty, "raster_sha256": sha(generated), "validator_output": validator,
            "submission_name": name, "note": NOTE, "published_tiff": f"docs/downloads/{generated.name}",
            "download_ok": True, "submission_approved": False, "slot_selected": False,
            "verdict": "negative", "scientific_gate_passed": science_pass,
            "blockers": (["Failed paired improvement against all matched controls"] if not science_pass else []) + [
                "Complete parallel registry and externally assigned lane unavailable",
                "Comparable historical-best checkpoint/rerun unavailable",
                "Current portal allowance, eligibility, deadline and acceptance unverified"],
            "preregistration_sha256": prereg, "dataset_signature": manifest["dataset_signature"],
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    results.update({"raster_sha256": card["raster_sha256"], "experimental_elapsed_seconds": elapsed})
    dump(REPORT / "results.json", results); dump(REPORT / "run-card.json", card)
    dump(REPORT / "validation.json", validation)
    sidecar.update({"submission_approved": False, "download_ok": True, "submission_recommendation": False,
                    "scientific_gate_passed": science_pass, "run_card": "docs/research/texture-controls/run-card.json",
                    "lineage": "New full-stack model fit; no historical prediction values used as inputs or output",
                    "method": TRANSFORM_VERSION, "preregistration_sha256": prereg,
                    "dataset_signature": manifest["dataset_signature"], "normalization": normalization})
    dest = ROOT / card["published_tiff"]
    shutil.copyfile(generated, dest); dump(dest.with_suffix(".json"), sidecar)
    (REPORT / "canaries-partial.json").unlink(missing_ok=True)
    print(json.dumps(card, indent=2), flush=True)
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=int, default=3600)
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 7200:
        parser.error("max-seconds must be in [1,7200]")
    try:
        run(args.max_seconds)
    except Exception as exc:
        dump(REPORT / "failure.json", {"verdict": "negative", "submission_approved": False,
                                        "error": f"{type(exc).__name__}: {exc}",
                                        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        raise


if __name__ == "__main__":
    main()
