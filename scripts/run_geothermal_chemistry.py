#!/usr/bin/env python3
"""Execute the frozen GDX-1 plan; no tuning, private metric, writer, or uploader."""
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
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from gemsdoe30.experiments import CORE_FEATURES, LayerStack, contract
from gemsdoe30.geothermal_chemistry import (
    CANDIDATE_COLUMNS, EFFORT_COLUMNS, EXTRA_NAMES, GUARD_PX, build_features,
)
from gemsdoe30.holdout import (
    EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION, masked_dti_by_blocks,
    spatial_bootstrap, spatial_segment_folds,
)
from gemsdoe30.readiness import assess
from gemsdoe30.submission import validate_submission_file, write_submission_file
from scripts.check_novelty import audit
from scripts.feature_value_holdout import predict_grid, sample_training_pixels
from scripts.run_phase_tilt_asymmetry import fit_model, select_dots
from scripts.verify_prepared_cache import verify as verify_cache

REPORT = ROOT / "docs/research/2026-10-26-gdx"
WORK = ROOT / "outputs/geothermal-chemistry"
SEED, DOT_BUDGET = 3070, 44090
NOTE = "GDX1 site-deduped, effort-normalized geothermal chemistry + local edges; 44090 dots; research only, NOT slot-approved."
TEMPLATE = ROOT / "data/raw/sample_submission.tif"
ARMS = {"core19": tuple(range(19)), "effort6": EFFORT_COLUMNS, "gdx12": CANDIDATE_COLUMNS}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def canaries(x, y, stack, names, fold, *, seed, columns=None):
    """Each exact feature alone; training-only fit, both AUC directions checked."""
    mask = fold["score_valid"] & ~fold["visible"]
    positive = np.flatnonzero((fold["hidden"] & mask).ravel())
    negative = np.flatnonzero((mask & ~fold["hidden"]).ravel())
    rng = np.random.default_rng(seed)
    negative = rng.choice(negative, min(100000, len(negative)), replace=False)
    idx = np.concatenate([positive, negative])
    target = np.r_[np.ones(len(positive)), np.zeros(len(negative))]
    rows = []
    for j in (range(len(names)) if columns is None else columns):
        model, med, scale = fit_model(x[:, j:j + 1], y, seed=seed + j, iterations=32, leaves=7)
        v = np.asarray(stack.layers[j], dtype=np.float32).ravel()[idx]
        v = np.where(np.isfinite(v), v, med[0])
        raw = float(roc_auc_score(target, v)) if np.ptp(v) > 0 else 0.5
        with threadpool_limits(limits=2):
            p = model.predict_proba(((v - med[0]) / scale[0])[:, None])[:, 1]
        uni = float(roc_auc_score(target, p)) if np.ptp(p) > 0 else 0.5
        alarm = max(raw, 1 - raw, uni, 1 - uni) > 0.90
        rows.append({"feature": names[j], "label": "LEAKAGE-CANARY AUC (not DTI)",
                     "raw_auc": raw, "univariate_training_only_hgb_auc": uni,
                     "alarm_above_0_90": bool(alarm), "heldout_positives": int(len(positive)),
                     "sampled_negatives": int(len(negative))})
    return {"fold": fold["fold"], "features": rows}


def assert_clear(report):
    if report["decision"] == "duplicate-stop":
        raise DuplicateStop(report["stage"])
    if report.get("errors") or not report.get("comparisons"):
        raise ValueError("registry errors/missing observations: do not continue placement")


class DuplicateStop(Exception):
    pass


def run(seconds):
    # Guard BEFORE any fitting or overwriting locked scientific evidence.
    if (REPORT / "started.json").exists():
        raise FileExistsError("GDX-1 was already started; no rerun/retuning is allowed")
    for name in ("preregistration.md", "registry.json"):
        if not (REPORT / name).is_file():
            raise FileNotFoundError(name)
    if not 0 < seconds <= 7200 or len(NOTE) > 140:
        raise ValueError("time or note budget invalid")
    spec = contract({"experiment_spec": "gdx1"})
    started = time.monotonic()
    deadline = started + seconds

    def time_check():
        if time.monotonic() >= deadline:
            raise TimeoutError("two-hour cap reached; no further experiments")

    WORK.mkdir(parents=True, exist_ok=True)
    dump(REPORT / "started.json", {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_sha256": sha(REPORT / "preregistration.md"),
        "registry_sha256": sha(REPORT / "registry.json"),
        "runner_sha256": sha(__file__),
        "transform_sha256": sha(ROOT / spec["transform_path"]),
        "experiment_cap": 3, "planned_experiments": 2, "max_seconds": seconds,
        "externally_assigned_lane_verified": False,
    })
    dump(REPORT / "cache-verification.json", verify_cache(ROOT / "data/processed"))
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT / "data/processed/labels.npy") > 0.5
    valid = np.load(ROOT / "data/processed/valid.npy")
    label_valid = np.load(ROOT / "data/processed/label_valid.npy")
    if np.any(valid & ~label_valid):
        raise ValueError("unknown labels in footprint")
    labels &= valid
    data_manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    csv_file = ROOT / "data/raw/external/gdr_wellspring_in_footprint.csv"
    pins = json.loads((ROOT / "docs/research/mirror-pins-extra.json").read_text())
    pin = next(r for r in pins["files"] if r["id"] == "ext_gdr_wellspring_in_footprint")
    if sha(csv_file) != pin["sha256"]:
        raise ValueError("chemistry mirror SHA mismatch")
    print("Build site-deduplicated, paired chemistry maps (no catalogue inputs)...", flush=True)
    fields, features_receipt = build_features(base, valid, csv_file)
    extra = np.lib.format.open_memmap(WORK / "extra.npy", mode="w+", dtype=np.float32,
                                     shape=(len(EXTRA_NAMES), *valid.shape))
    for j, name in enumerate(EXTRA_NAMES):
        extra[j] = fields.pop(name)
    extra.flush()
    stack = LayerStack([base[i] for i in range(19)] + [extra[i] for i in range(len(EXTRA_NAMES))])
    stacks = {name: LayerStack([stack.layers[j] for j in columns]) for name, columns in ARMS.items()}
    names = CORE_FEATURES + EXTRA_NAMES
    dump(REPORT / "feature-receipt.json", {
        **features_receipt, "csv_sha256": sha(csv_file),
        "dataset_signature": data_manifest["dataset_signature"],
        "transform_sha256": sha(ROOT / spec["transform_path"]),
        "feature_names": list(names), "candidate_columns": list(CANDIDATE_COLUMNS),
        "all_feature_array_sha256": sha(WORK / "extra.npy"),
    })
    time_check()
    x, y = sample_training_pixels(stacks["gdx12"], labels, valid,
                                  negatives_per_positive=6, seed=SEED)
    model, med, scale = fit_model(x, y, seed=SEED)
    with threadpool_limits(limits=2):
        surface = predict_grid(model, stacks["gdx12"], med, scale, valid)
    del model, x, y
    surface_path = WORK / "gdx1-surface.tif"
    write_submission_file(surface, TEMPLATE, surface_path, run_name="gems30-GDX1-surface",
                          note="Saved pre-placement continuous research surface, NOT a submission.")
    print("Pre-placement audit against all public-snapshot registry rasters...", flush=True)
    surface_audit = audit(surface_path, TEMPLATE, REPORT / "registry.json", "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    assert_clear(surface_audit)
    time_check()
    final_domain = valid & (distance_transform_edt(~labels) > 2)
    dots = select_dots(surface, final_domain, DOT_BUDGET)
    del surface
    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    run_name = f"gems30-GDX1-44090-20261026-{identity[:12]}"
    output = WORK / f"{run_name}.tif"
    sidecar = write_submission_file(dots, TEMPLATE, output, run_name=run_name, note=NOTE)
    dots_audit = audit(output, TEMPLATE, REPORT / "registry.json", "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    assert_clear(dots_audit)
    del dots
    time_check()
    # No metric is inspected before BOTH novelty gates. Every feature is tested
    # alone before each fold's paired models are interpreted.
    block_rows = {name: [] for name in ARMS}
    folds, checks = [], []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)
    for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
        time_check()
        f = fold["fold"]
        hidden_total += fold["hidden"]
        print(f"Fold {f}: canaries for all {len(names)} exact features...", flush=True)
        x, y = sample_training_pixels(stack, labels, fold["train_mask"],
                                      negatives_per_positive=6, seed=SEED + f)
        check = canaries(x, y, stack, names, fold, seed=SEED + f)
        checks.append(check)
        dump(REPORT / "canaries-partial.json", {"folds": checks, "complete": False})
        domain = fold["score_valid"] & ~fold["visible"]
        # Only the visible catalogue participates in the emission halo.
        domain &= distance_transform_edt(~fold["visible"]) > 2
        count = int(round(DOT_BUDGET * domain.sum() / valid.sum()))
        row = {**fold["metadata"], "dot_budget_each_arm": count, "arms": {}}
        for name, columns in ARMS.items():
            time_check()
            model, med, scale = fit_model(x[:, columns], y, seed=SEED + f)
            with threadpool_limits(limits=2):
                p = predict_grid(model, stacks[name], med, scale, domain)
            np.save(WORK / f"fold-{f}-{name}-surface.npy", p)
            emission = select_dots(p, domain, count)
            scored = masked_dti_by_blocks(emission, fold["hidden"], fold["visible"],
                                          fold["score_valid"], block_size_px=128)
            block_rows[name].extend(scored["spatial_blocks"])
            row["arms"][name] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
            print(f"Fold {f}: {name}, {int(emission.sum())} dots", flush=True)
            del model, emission, p
        folds.append(row)
        del x, y
    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("withheld positives must be counted once")
    summary = spatial_bootstrap(block_rows, candidate="gdx12", replicates=2000, seed=3071)
    alarms = [dict(fold=c["fold"], **r) for c in checks for r in c["features"] if r["alarm_above_0_90"]]
    results = {"schema_version": 1, "experiment_spec": "gdx1", "summary": summary,
               "folds": folds, "feature_canaries": checks, "bootstrap_sufficient_statistics": block_rows,
               "preregistration_sha256": sha(REPORT / "preregistration.md"),
               "scientific_gate_passed": not alarms and all(d["ci95"][0] > 0 for d in summary["candidate_minus"].values())}
    dump(REPORT / "results.json", results)

    # Conservative experiment count: the separate archived-protocol parity rerun
    # is experiment 2, not a new comparison to be pooled with experiment 1.
    parity_blocks, parity_folds, parity_canaries = [], [], []
    for fold in spatial_segment_folds(labels, valid, buffer_px=17):
        time_check()
        f = fold["fold"]
        x, y = sample_training_pixels(stacks["core19"], labels, fold["train_mask"],
                                      negatives_per_positive=6, seed=SEED + f)
        parity_canaries.append(canaries(x, y, stacks["core19"], CORE_FEATURES, fold, seed=SEED + f))
        model, med, scale = fit_model(x, y, seed=SEED + f)
        domain = fold["score_valid"] & ~fold["visible"]
        count = int(round(DOT_BUDGET * domain.sum() / valid.sum()))
        with threadpool_limits(limits=2):
            p = predict_grid(model, stacks["core19"], med, scale, domain)
        emission = select_dots(p, domain, count)
        scored = masked_dti_by_blocks(emission, fold["hidden"], fold["visible"],
                                      fold["score_valid"], block_size_px=128)
        parity_blocks.extend(scored["spatial_blocks"])
        parity_folds.append({**fold["metadata"], "dot_budget_each_arm": count,
                             "arms": {"core19": scored["pooled"]}})
        del x, y, model, p, emission
    parity_summary = spatial_bootstrap({"core19": parity_blocks}, candidate="core19", replicates=2000, seed=3071)
    parity_value = parity_summary["arms"]["core19"]["value"]
    parity_ok = bool(np.isclose(parity_value, 0.13982063017811727, atol=1e-9, rtol=0))
    dump(REPORT / "comparator-parity.json", {
        "summary": parity_summary, "folds": parity_folds, "feature_canaries": parity_canaries,
        "bootstrap_sufficient_statistics": {"core19": parity_blocks}, "exact_archive_parity": parity_ok,
        "expected_value": 0.13982063017811727, "purpose": "reproduction only; 17px folds NOT the candidate's 46px trial"})
    if not parity_ok:
        results["comparator_parity_unknown"] = True
        dump(REPORT / "results.json", results)
    report = validate_submission_file(output, TEMPLATE)
    with rasterio.open(output) as ds, rasterio.open(TEMPLATE) as tpl:
        a = ds.read(1)
        validator = {"status": "passed" if report.passed else "failed",
                     "no_nan_inside_footprint": bool(np.isfinite(a[valid]).all()),
                     "values_in_0_1": bool(np.all((a[valid] >= 0) & (a[valid] <= 1))),
                     "crs_match": ds.crs == tpl.crs, "shape_match": ds.shape == tpl.shape,
                     "transform_match": ds.transform == tpl.transform,
                     "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
                     "nan_nodata_outside_footprint": bool(np.isnan(a[~valid]).all()),
                     "positive_catalogue_pixels": int(np.count_nonzero(a[labels] > 0)),
                     "emitted_dots": int(np.count_nonzero(a[valid] > 0)),
                     "dots_within_2px_of_catalogue": int(np.count_nonzero((a > 0) & valid & ~final_domain)),
                     "organizer_acceptance_confirmed": False}
    if not report.passed or validator["positive_catalogue_pixels"] or validator["dots_within_2px_of_catalogue"]:
        raise ValueError("mandatory final file or catalogue mask failed")
    dump(REPORT / "validation.json", report.to_dict())
    published = REPORT / output.name
    shutil.copyfile(output, published)
    elapsed = time.monotonic() - started
    time_check()
    card = {
        "schema_version": 1, "experiment_spec": "gdx1", "run_id": run_name,
        "lane": "GDX-1 autonomous geothermal-corridor continuation; not externally assigned",
        "hypothesis": "Effort-normalized paired geothermal chemistry localizes cooling/mixing upflow conduits beyond surface-mapped faults.",
        "mechanism": "Site-median reservoir/surface temperature contrasts and cation-quartz discordance normalized by chemical sampling effort; 12-channel local-physics HGB, 3px Poisson dots.",
        "non_fault_mimic": "Aquifer mixing or steam loss at a lithologic contact; preferential sampling around developed geothermal fields.",
        "holdout": {**summary["arms"]["gdx12"], "evaluator_version": EVALUATOR_VERSION,
                    "protocol_version": SEGMENT_PROTOCOL_VERSION, "buffer_px": GUARD_PX,
                    "scope": "catalogue hide-and-recover proxy; NOT organizer performance or leaderboard estimate",
                    "bootstrap": summary["bootstrap"],
                    "comparators": {n: summary["arms"][n] for n in ("core19", "effort6")},
                    "candidate_minus": summary["candidate_minus"]},
        "feature_canaries": {"features_per_fold": len(names), "folds": 4, "alarm_count": len(alarms), "alarms": alarms},
        "registry": {"complete": False, "receipt_surface": str((REPORT / "novelty-surface.json").relative_to(ROOT)),
                     "receipt_dots": str((REPORT / "novelty-dots.json").relative_to(ROOT))},
        "raster_sha256": sha(published), "surface_sha256": sha(surface_path),
        "validator_output": validator, "submission_name": run_name, "note": NOTE,
        "published_tiff": str(published.relative_to(ROOT)), "download_ok": True,
        "organizer_score": None, "leaderboard_estimate": None,
        "externally_assigned_lane_verified": False,
        "scientific_gate_passed": results["scientific_gate_passed"],
        "experiments_run": 2, "experiment_cap": 3,
        "experimental_elapsed_seconds": round(elapsed, 3), "time_cap_hours": 2,
        "archive_core19_parity_verified": parity_ok,
        "preregistration_sha256": sha(REPORT / "preregistration.md"),
        "registry_sha256": sha(REPORT / "registry.json"),
        "dataset_signature": data_manifest["dataset_signature"],
        "submission_approved": False, "slot_selected": False, "ok_to_submit": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    registry = json.loads((REPORT / "registry.json").read_text())
    readiness = assess(card, results, format_passed=report.passed, hash_matches=True,
                       surface_audit=surface_audit, dots_audit=dots_audit, registry=registry)
    card["verdict"] = readiness["research_verdict"]
    card["registry"]["surface"] = readiness["observed_registry"]["surface"]
    card["registry"]["dots"] = readiness["observed_registry"]["dots"]
    card["blockers"] = [g["name"] + ": " + g["detail"] for g in readiness["gates"] if g["status"] != "passed"]
    card["blockers"].extend(["Calibration and perturbation confirmation not completed; not eligible for slot selection",
                              "Current portal weekly cap, deadline and eligibility unverified"])
    dump(REPORT / "run-card.json", card)
    dump(REPORT / "readiness.json", readiness)
    sidecar.update(submission_approved=False, slot_selected=False, ok_to_submit=False,
                   download_scope="research artifact only; no leaderboard estimate", run_card=str((REPORT / "run-card.json").relative_to(ROOT)))
    dump(published.with_suffix(".json"), sidecar)
    print(json.dumps(card, indent=2), flush=True)
    return card


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-seconds", type=int, default=6000)
    args = p.parse_args()
    try:
        run(args.max_seconds)
    except DuplicateStop as exc:
        stage = str(exc)
        dump(REPORT / "duplicate-stop.json", {"stage": stage, "decision": "duplicate-stop", "no_further_experiment": True})
        dump(REPORT / "run-card.json", {
            "hypothesis": "Effort-normalized paired geothermal chemistry localizes concealed upflow conduits",
            "mechanism": "Site-deduplicated chemistry/effort maps plus local geophysical derivatives",
            "non_fault_mimic": "Aquifer mixing and preferential sampling of developed geothermal fields",
            "holdout": {"label": "HOLDOUT-DTI", "value": None, "ci95": None, "withheld_positives": None,
                        "evaluator_version": EVALUATOR_VERSION, "reason": "mandatory novelty stop precedes scientific scoring"},
            "registry": {"decision": "duplicate-stop", "stage": stage},
            "raster_sha256": json.loads((REPORT / f"novelty-{stage}.json").read_text())["candidate_sha256"],
            "validator_output": {"status": "not-published"},
            "submission_name": None, "note": "GDX1 duplicate-stop; no publication, no retuning, no competition slot.",
            "verdict": "negative", "download_ok": False, "submission_approved": False,
            "slot_selected": False, "ok_to_submit": False, "experiments_run": 1})
        print(f"DUPLICATE-STOP at {stage}; no further fitting, no download, no slot", flush=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
