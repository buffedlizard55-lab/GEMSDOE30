#!/usr/bin/env python3
"""Execute frozen TDX-1; reuse shared evaluator, writer, sampler and cached stack.

One fixed scientific experiment, not a slot selector. Unknown evidence gates are
fail-closed. Negative results are published only as quarantined research downloads.
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

# Avoid uncontrolled BLAS/OpenMP oversubscription in the two-core research budget.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from gemsdoe30.holdout import (EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION,
                              masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds)
from gemsdoe30.submission import write_submission_file, validate_submission_file
from gemsdoe30.texture import (TRANSFORM_VERSION, SUPPORT_PX, displacement_features, fold_consensus)
from gemsdoe30.emission import poisson_disk_select_ordered
from scripts.check_novelty import audit
from scripts.verify_prepared_cache import verify as verify_prepared_cache
from scripts.feature_value_holdout import sample_training_pixels, fit_standardiser, predict_grid

REPORT = ROOT / "docs/research/texture-displacement"
CACHE = ROOT / "data/processed/texture-displacement"
RUN = ROOT / "outputs/texture-displacement"
SEED = 3070
DOT_BUDGET = 44090
NOTE = "TDX1 gravity-normal magnetic texture lag; 6-feature HGB; negative research result, NOT approved for competition upload."


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def check_time(deadline):
    if time.monotonic() > deadline:
        raise TimeoutError("Experimental time cap reached; stop, do not retune or spend a slot")


def load_cache(base, valid, manifest, *, report_dir=REPORT):
    """Reuse the hash-pinned source-independent cache; optionally record elsewhere.

    A continuation must not overwrite the original experiment's frozen receipts.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    signature = {"transform_version": TRANSFORM_VERSION,
                 "transform_code_sha256": sha(ROOT / "src/gemsdoe30/texture.py"),
                 "dataset_signature": manifest["dataset_signature"]}
    receipt_path = CACHE / "receipt.json"
    names = ["mag_texture", "rtp_texture", "gravity_edge", "supported"]
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("signature") != signature:
            raise ValueError("stale derived cache: explicitly remove ignored cache before rebuilding")
        for name in names:
            if sha(CACHE / f"{name}.npy") != receipt["sha256"][name]:
                raise ValueError(f"derived cache hash mismatch: {name}")
    else:
        print("Constructing registered label-independent texture features", flush=True)
        fields = displacement_features(base[0], base[1], base[12], valid)
        for name, values in fields.items():
            np.save(CACHE / f"{name}.npy", values)
        receipt = {"signature": signature, "source_bands_1based": [1, 2, 13],
                   "sha256": {name: sha(CACHE / f"{name}.npy") for name in names},
                   "support_px": SUPPORT_PX,
                   "supported_pixels": int(fields["supported"].sum()),
                   "uses_catalogue_geometry": False, "uses_registry_values": False,
                   "uses_template_values_as_features": False}
        dump(receipt_path, receipt)
    fields = {name: np.load(CACHE / f"{name}.npy", mmap_mode="r") for name in names}
    if report_dir is not None:
        dump(report_dir / "feature-receipt.json", receipt)
    return fields


def candidate_stack(base, fields, train):
    consensus, scale = fold_consensus(fields["mag_texture"], fields["rtp_texture"],
                                      fields["gravity_edge"], train)
    candidate = np.stack([base[0], base[1], base[12], fields["mag_texture"],
                          fields["rtp_texture"], consensus])
    return candidate, scale


def fit_model(x, y, *, seed, iterations=120, leaves=31):
    median, scale = fit_standardiser(x)
    x = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(max_iter=iterations, learning_rate=0.1,
                                           max_leaf_nodes=leaves, early_stopping=False,
                                           random_state=seed)
    with threadpool_limits(limits=2):
        model.fit((x - median) / scale, y)
    return model, median, scale


def select_dots(surface, mask, count):
    if count < 1:
        raise ValueError("a positive predeclared dot budget is required")
    rows, cols = poisson_disk_select_ordered(surface, 3.0, mask=mask, max_kept=count)
    if len(rows) != count:
        raise ValueError(f"count gate invalid: pool can supply {len(rows)} of {count} requested dots")
    dots = np.zeros(surface.shape, dtype=np.float32)
    dots[rows, cols] = 1.0
    return dots


def feature_canaries(base, candidate, labels, fold, seed, deadline):
    """Single-feature training/heldout checks; evaluate every feature, no thresholds fitted on test."""
    train, domain = fold["train_mask"], fold["score_valid"] & ~fold["visible"]
    # Existing sampler yields identical pixel coordinates for identical labels,
    # mask and seed, regardless of channel stack. Never resample per arm.
    xb, y = sample_training_pixels(base, labels, train, negatives_per_positive=6, seed=seed)
    xc, yc = sample_training_pixels(candidate, labels, train, negatives_per_positive=6, seed=seed)
    if not np.array_equal(y, yc):
        raise AssertionError("training labels differ between paired arms")
    rng = np.random.default_rng(seed + 10000)
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(domain & ~fold["hidden"])
    negatives = rng.choice(negatives, min(60000, negatives.size), replace=False)
    test = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])
    names = json.loads((ROOT / "data/processed/manifest.json").read_text())["feature_band_names"]
    names = [name.split(" - ")[0] for name in names] + ["mag_texture", "rtp_texture", "texture_consensus"]
    rows = []
    for j, name in enumerate(names):
        check_time(deadline)
        training = xb[:, j:j + 1] if j < 19 else xc[:, j - 16:j - 15]
        values = base[j].ravel()[test] if j < 19 else candidate[j - 16].ravel()[test]
        model, median, scale = fit_model(training, y, seed=seed + j, iterations=32, leaves=7)
        filled = np.where(np.isfinite(values), values, median[0])
        raw_auc = float(roc_auc_score(target, filled))
        with threadpool_limits(limits=2):
            probabilities = model.predict_proba(((filled - median[0]) / scale[0])[:, None])[:, 1]
        model_auc = float(roc_auc_score(target, probabilities))
        raw_either = max(raw_auc, 1 - raw_auc)
        rows.append({"feature": name, "label": "LEAKAGE-CANARY AUC (not DTI)",
                     "raw_auc": raw_auc, "raw_auc_either_direction": raw_either,
                     "univariate_training_only_hgb_auc": model_auc,
                     "alarm_above_0_90": raw_either > .90 or model_auc > .90,
                     "heldout_positives": int(positives.size), "sampled_negatives": int(negatives.size)})
    return rows, xb, xc, y


def summarize_novelty(surface, dots):
    def maxima(report):
        rows = report.get("comparisons", [])
        correlations = [r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None]
        overlaps = [r["candidate_fraction_within_3px_of_reference"] for r in rows
                    if r["candidate_fraction_within_3px_of_reference"] is not None]
        return {"decision": report["decision"], "registry_entries_compared": len(rows),
                "max_spearman": max(correlations) if correlations else None,
                "max_fraction_within_3px": max(overlaps) if overlaps else None,
                "errors": report.get("errors", [])}
    return {"complete": False, "surface": maxima(surface), "dots": maxima(dots),
            "coverage": "all published aligned TIFFs at nine recorded repository snapshots; missing other sessions and most original surfaces",
            "receipt_surface": "docs/research/texture-displacement/novelty-surface.json",
            "receipt_dots": "docs/research/texture-displacement/novelty-dots.json"}


def run(max_seconds):
    started, start_time = time.monotonic(), datetime.now(timezone.utc)
    deadline = started + max_seconds
    REPORT.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)
    prereg_sha = sha(REPORT / "preregistration.md")
    correction = json.loads((REPORT / "correction-v1-retirement.json").read_text())
    previous_seconds = correction["original_elapsed_seconds"]
    execution_ordinal = correction["correction_execution_ordinal"]
    if execution_ordinal != 2 or SUPPORT_PX != 17:
        raise ValueError("corrective execution must match its frozen 17px/ordinal-2 amendment")
    dump(REPORT / "started.json", {"started_utc": start_time.isoformat(timespec="seconds"),
                                   "preregistration_sha256": prereg_sha,
                                   "experiment_count": execution_ordinal, "fixed_arms": ["tdx6", "physics3", "core19"],
                                   "script_sha256": sha(__file__), "max_experimental_seconds": max_seconds})
    dump(REPORT / "cache-verification.json", verify_prepared_cache(ROOT / "data/processed"))
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT / "data/processed/labels.npy", mmap_mode="r") > .5
    valid = np.load(ROOT / "data/processed/valid.npy", mmap_mode="r").copy()
    label_valid = np.load(ROOT / "data/processed/label_valid.npy", mmap_mode="r")
    if np.any(valid & ~label_valid):
        raise ValueError("unknown training labels inside footprint")
    labels &= valid
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    template = ROOT / "data/raw/sample_submission.tif"
    # Reverify actual raw source bytes before accepting a prepared-cache identity.
    for row in manifest["source_files"].values():
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("prepared input source hash mismatch")
    registry = REPORT / "registry.json"
    fields = load_cache(base, valid, manifest)
    check_time(deadline)

    # Fit the fixed final method without looking at any holdout outcomes. The
    # full catalogue is legal here, but is never used by a holdout fold model.
    candidate, full_scale = candidate_stack(base, fields, valid)
    x, y = sample_training_pixels(candidate, labels, valid, negatives_per_positive=6, seed=SEED)
    model, median, scale = fit_model(x, y, seed=SEED)
    del x, y
    print("Fitted fixed final tdx6 method; predicting surface before placement", flush=True)
    with threadpool_limits(limits=2):
        surface = predict_grid(model, candidate, median, scale, valid)
    surface_manifest = write_submission_file(surface, template, RUN / "tdx1-surface.tif",
                                              note="Continuous TDX1 research surface; not a competition submission.",
                                              run_name="gems30-tdx1-surface")
    surface_audit = audit(RUN / "tdx1-surface.tif", template, registry, "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    print("Surface novelty:", surface_audit["decision"], flush=True)
    if surface_audit["decision"] == "duplicate-stop":
        dump(REPORT / "duplicate-stop.json", {"stage": "surface", "decision": "duplicate-stop",
                                              "no_placement_or_further_experiment": True})
        raise ValueError("duplicate-stop on surface; no dots may be placed")
    check_time(deadline)
    dots = select_dots(surface, valid & ~labels, DOT_BUDGET)
    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    run_name = f"gems30-TDX1-44090-20261025-{identity[:12]}"
    generated = RUN / f"{run_name}.tif"
    manifest_output = write_submission_file(dots, template, generated, run_name=run_name, note=NOTE)
    dots_audit = audit(generated, template, registry, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    print("Final-dot novelty:", dots_audit["decision"], flush=True)
    if dots_audit["decision"] == "duplicate-stop":
        dump(REPORT / "duplicate-stop.json", {"stage": "dots", "decision": "duplicate-stop",
                                              "no_further_experiment": True})
        raise ValueError("duplicate-stop on final dots; no further experiment or publication")
    del candidate, model, surface

    arms = ("physics3", "core19", "tdx6")
    block_rows = {name: [] for name in arms}
    folds, canaries = [], []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)
    for fold in spatial_segment_folds(labels, valid, buffer_px=SUPPORT_PX):
        check_time(deadline)
        f = fold["fold"]
        hidden_total += fold["hidden"]
        candidate, normalizer = candidate_stack(base, fields, fold["train_mask"])
        print(f"Fold {f}: single-feature leakage canaries", flush=True)
        checks, xb, xc, y = feature_canaries(base, candidate, fold["visible"], fold, SEED + f, deadline)
        canaries.append({"fold": f, "features": checks})
        dump(REPORT / "canaries-partial.json", {"folds": canaries, "status": "partial until results.json exists"})
        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(DOT_BUDGET * active.sum() / valid.sum()))
        fold_result = {**fold["metadata"], "normalization": normalizer,
                       "dot_budget_each_arm": count, "arms": {}}
        for name in arms:
            check_time(deadline)
            features, training = ((candidate[:3], xc[:, :3]) if name == "physics3" else
                                  (base, xb) if name == "core19" else (candidate, xc))
            model, median, scale = fit_model(training, y, seed=SEED + f)
            with threadpool_limits(limits=2):
                prediction = predict_grid(model, features, median, scale, active)
            # Capacity is checked before metrics. A shortfall is a construction
            # error, not a lower-count precision advantage in a paired comparison.
            emitted = select_dots(prediction, active, count)
            score = masked_dti_by_blocks(emitted, fold["hidden"], fold["visible"],
                                         fold["score_valid"], block_size_px=128)
            block_rows[name].extend(score["spatial_blocks"])
            fold_result["arms"][name] = {key: value for key, value in score["pooled"].items() if key != "dti"}
            print(f"Fold {f}: {name}, {int(emitted.sum())} active dots (not a score)", flush=True)
            del model, prediction, emitted
        folds.append(fold_result)
        del candidate, xb, xc, y
    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("each withheld positive must be counted exactly once")
    summary = spatial_bootstrap(block_rows, candidate="tdx6", replicates=2000, seed=3071)
    alarms = [dict(fold=f["fold"], **row) for f in canaries for row in f["features"] if row["alarm_above_0_90"]]
    beats = all(delta["value"] > 0 and delta["ci95"][0] > 0 for delta in summary["candidate_minus"].values())
    scientific_pass = beats and not alarms
    novelty = summarize_novelty(surface_audit, dots_audit)
    validation = validate_submission_file(generated, template).to_dict()
    with rasterio.open(generated) as ds, rasterio.open(template) as reference:
        output = ds.read(1)
        validator = {"status": "passed" if validation["passed"] else "failed",
                     "no_nan_inside_footprint": bool(np.isfinite(output[valid]).all()),
                     "values_in_0_1": bool(np.all((output[valid] >= 0) & (output[valid] <= 1))),
                     "crs_match": ds.crs == reference.crs, "shape_match": ds.shape == reference.shape,
                     "transform_match": ds.transform == reference.transform,
                     "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
                     "nan_nodata_outside_footprint": bool(np.isnan(output[~valid]).all()),
                     "positive_catalogue_pixels": int(np.count_nonzero(output[labels] > 0)),
                     "emitted_dots": int(np.count_nonzero(output[valid] > 0)),
                     "organizer_acceptance_confirmed": False}
    if not validation["passed"] or validator["positive_catalogue_pixels"]:
        raise AssertionError("shared format/exact catalogue mask gate failed")
    dump(REPORT / "validation.json", validation)
    blockers = []
    if not scientific_pass:
        blockers.append("Candidate failed paired HOLDOUT-DTI improvement gate or feature leakage canary")
    blockers += ["Complete parallel-run raster/surface registry unavailable",
                 "No externally assigned lane paragraph was supplied; research lane selected autonomously",
                 "Historical best UNet checkpoints absent: comparable historical-best rerun unavailable",
                 "Current portal cap, eligibility, deadline and organizer acceptance unverified"]
    elapsed = time.monotonic() - started
    card = {"schema_version": 2, "run_id": run_name,
            "hypothesis": "Magnetic texture correspondence with a persistent nonzero lag across gravity edges improves recovery of concealed faults.",
            "mechanism": "Opposite-flank normalized profile matching at two scales; raw physics plus displacement features in a fixed six-feature HGB.",
            "non_fault_mimic": "Intrusive lithologic contact; gridding seam",
            "lane": "TDX-1 gravity-normal magnetic profile displacement (research continuation, not externally assigned)",
            "experiments_run": execution_ordinal, "fixed_arms": list(arms), "experiment_cap": 3,
            "experimental_elapsed_seconds": round(previous_seconds + elapsed, 2), "time_cap_hours": 2,
            "this_execution_seconds": round(elapsed, 2),
            "corrective_execution": True, "physical_support_px": SUPPORT_PX,
            "confirmation_scope": "Corrective guard-bound bug fix on previously inspected folds; not fresh independent confirmation",
            "previous_execution_receipt": "docs/research/texture-displacement/correction-v1-retirement.json",
            "holdout": {**summary["arms"]["tdx6"], "evaluator_version": EVALUATOR_VERSION,
                        "protocol_version": SEGMENT_PROTOCOL_VERSION,
                        "scope": "buffered whole-segment catalogue-recovery proxy; NOT organizer performance",
                        "comparators": {name: summary["arms"][name] for name in ("physics3", "core19")},
                        "candidate_minus": summary["candidate_minus"], "bootstrap": summary["bootstrap"]},
            "feature_canaries": {"features_per_fold": len(canaries[0]["features"]), "folds": 4,
                                  "alarm_count": len(alarms), "alarms": alarms,
                                  "receipt": "docs/research/texture-displacement/results.json"},
            "registry": novelty, "raster_sha256": sha(generated),
            "validator_output": validator, "submission_name": run_name, "note": NOTE,
            "published_tiff": f"docs/downloads/{generated.name}",
            "download_ok": True, "submission_approved": False, "slot_selected": False,
            "verdict": "negative", "scientific_gate_passed": scientific_pass,
            "verdict_scope": "scientific and/or readiness gates; no competition performance claim",
            "blockers": blockers, "preregistration_sha256": prereg_sha,
            "dataset_signature": manifest["dataset_signature"],
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if len(NOTE) > 140:
        raise AssertionError("note exceeds 140 characters")
    results = {"schema_version": 1, "summary": summary, "folds": folds,
               "feature_canaries": canaries, "bootstrap_sufficient_statistics": block_rows,
               "full_fit_normalization": full_scale, "raster_sha256": sha(generated),
               "source_band_semantics": "Organizer reference notebook cell 5, pinned aebe92f7c8a990f0e3443451b7a825d9afd6336b",
               "preregistration_sha256": prereg_sha,
               "evaluator_version": EVALUATOR_VERSION,
               "protocol_version": SEGMENT_PROTOCOL_VERSION,
               "experimental_elapsed_seconds": round(previous_seconds + elapsed, 2), "this_execution_seconds": round(elapsed, 2), "scientific_gate_passed": scientific_pass}
    dump(REPORT / "results.json", results)
    dump(REPORT / "run-card.json", card)
    manifest_output.update({"submission_approved": False, "download_ok": True,
                            "submission_recommendation": False,
                            "note": NOTE, "scientific_gate_passed": scientific_pass,
                            "run_card": "docs/research/texture-displacement/run-card.json",
                            "lineage": "New fit of TDX1; no previous submission values used as model inputs or predictions",
                            "method": TRANSFORM_VERSION, "preregistration_sha256": prereg_sha,
                            "dataset_signature": manifest["dataset_signature"]})
    dest = ROOT / "docs/downloads" / generated.name
    shutil.copyfile(generated, dest)
    dump(dest.with_suffix(".json"), manifest_output)
    dump(REPORT / "run-card.json", card)
    (REPORT / "canaries-partial.json").unlink(missing_ok=True)
    print(json.dumps(card, indent=2), flush=True)
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=int, default=5400,
                        help="experimental computation cap; must also fit remaining two-hour session budget")
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
