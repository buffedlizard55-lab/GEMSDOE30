#!/usr/bin/env python3
"""Execute frozen PTA-1 subsurface phase-tilt & dip-asymmetry experiment.

Reuses shared evaluator (gemsdoe30.holdout), submission writer/validator
(gemsdoe30.submission), ordered 3 px Poisson emitter (gemsdoe30.emission),
and zero-copy LayerStack (gemsdoe30.experiments). One frozen experiment,
four fixed arms, zero hyperparameter or emitter tuning.
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
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from gemsdoe30.emission import poisson_disk_select_ordered
from gemsdoe30.experiments import CORE_FEATURES, LayerStack, contract
from gemsdoe30.holdout import (
    EVALUATOR_VERSION,
    SEGMENT_PROTOCOL_VERSION,
    masked_dti_by_blocks,
    spatial_bootstrap,
    spatial_segment_folds,
)
from gemsdoe30.phase_tilt import (
    ALL_DERIVED_NAMES,
    CANDIDATE_DERIVED_NAMES,
    SUB8_INDICES,
    SUPPORT_PX,
    TIGHT_SUPPORT_PX,
    TRANSFORM_VERSION,
    load_or_build_cache,
)
from gemsdoe30.readiness import assess
from gemsdoe30.submission import validate_submission_file, write_submission_file
from scripts.check_novelty import audit
from scripts.feature_value_holdout import fit_standardiser, predict_grid, sample_training_pixels
from scripts.verify_prepared_cache import verify as verify_prepared_cache

REPORT = ROOT / "docs/research/phase-tilt-asymmetry"
CACHE = ROOT / "data/processed/phase-tilt-asymmetry"
RUN = ROOT / "outputs/phase-tilt-asymmetry"
SEED = 3070
DOT_BUDGET = 44090
NOTE = "PTA1 subsurface 3D tilt-phase + dip-asymmetry 18-feat HGB; 44090d; research artifact, NOT slot-approved."


def sha(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path: str | Path, data: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".partial")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temp.replace(target)


def check_time(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise TimeoutError("Experimental time cap reached; stop, do not retune or spend a slot")


def fit_model(x: np.ndarray, y: np.ndarray, *, seed: int, iterations: int = 120, leaves: int = 31):
    median, scale = fit_standardiser(x)
    filled = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(
        max_iter=iterations,
        learning_rate=0.1,
        max_leaf_nodes=leaves,
        early_stopping=False,
        random_state=seed,
    )
    with threadpool_limits(limits=2):
        model.fit((filled - median) / scale, y)
    return model, median, scale


def select_dots(surface: np.ndarray, mask: np.ndarray, count: int) -> np.ndarray:
    if count < 1:
        raise ValueError("a positive predeclared dot budget is required")
    rows, cols = poisson_disk_select_ordered(surface, 3.0, mask=mask, max_kept=count)
    if len(rows) != count:
        raise ValueError(f"count gate invalid: pool can supply {len(rows)} of {count} requested dots")
    dots = np.zeros(surface.shape, dtype=np.float32)
    dots[rows, cols] = 1.0
    return dots


def build_arm_stacks(base: np.ndarray, fields: dict[str, np.ndarray]) -> dict[str, LayerStack]:
    sub8 = [base[idx] for idx in SUB8_INDICES]
    ctrl10 = [
        fields["ctrl_naive_mag_tilt"],
        fields["ctrl_naive_mag_hd_tdr"],
        fields["ctrl_naive_mag_as3d_log"],
        fields["pta_grav_tilt"],
        fields["pta_grav_hd_tdr"],
        fields["ctrl_naive_mg_concord"],
        fields["ctrl_normal_blur"],
        fields["ctrl_sym_grav_mig"],
        fields["ctrl_sym_cover_step"],
        fields["ctrl_sym_cond_step"],
    ]
    cand10 = [fields[name] for name in CANDIDATE_DERIVED_NAMES]
    return {
        "core19": LayerStack([base[i] for i in range(19)]),
        "sub8_raw": LayerStack(sub8),
        "pta_naive_sym": LayerStack(sub8 + ctrl10),
        "pta1_cand": LayerStack(sub8 + cand10),
        "all37": LayerStack([base[i] for i in range(19)] + [fields[name] for name in ALL_DERIVED_NAMES]),
    }


def summarize_novelty(surface: dict, dots: dict) -> dict:
    def maxima(report: dict) -> dict:
        rows = report.get("comparisons", [])
        correlations = [r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None]
        overlaps = [
            r["candidate_fraction_within_3px_of_reference"]
            for r in rows
            if r["candidate_fraction_within_3px_of_reference"] is not None
        ]
        return {
            "decision": report["decision"],
            "registry_entries_compared": len(rows),
            "max_spearman": max(correlations) if correlations else None,
            "max_fraction_within_3px": max(overlaps) if overlaps else None,
            "errors": report.get("errors", []),
        }

    return {
        "complete": False,
        "surface": maxima(surface),
        "dots": maxima(dots),
        "coverage": "all published aligned TIFFs at nine recorded repository snapshots; missing other sessions and most original surfaces",
        "receipt_surface": "docs/research/phase-tilt-asymmetry/novelty-surface.json",
        "receipt_dots": "docs/research/phase-tilt-asymmetry/novelty-dots.json",
    }


def preflight_no_overwrite(report_dir: Path) -> None:
    existing = [
        name
        for name in ("started.json", "results.json", "run-card.json", "duplicate-stop.json", "failure.json")
        if (report_dir / name).exists()
    ]
    if existing:
        raise FileExistsError(f"frozen PTA-1 evidence already exists ({existing}); refusing overwrite")
    for required in ("preregistration.md", "registry.json"):
        if not (report_dir / required).is_file():
            raise FileNotFoundError(f"missing frozen prerequisite {report_dir / required}")


def run(max_seconds: int) -> dict:
    spec = contract({"experiment_spec": "pta1"})
    started, start_time = time.monotonic(), datetime.now(timezone.utc)
    deadline = started + max_seconds
    REPORT.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)
    prereg_sha = sha(REPORT / "preregistration.md")
    arms = spec["arms"]
    dump(
        REPORT / "started.json",
        {
            "started_utc": start_time.isoformat(timespec="seconds"),
            "preregistration_sha256": prereg_sha,
            "experiment_spec": "pta1",
            "experiment_count": 1,
            "fixed_arms": list(arms),
            "script_sha256": sha(__file__),
            "max_experimental_seconds": max_seconds,
        },
    )
    print("Verifying full-cell prepared cache against raw SHA-256 sources...", flush=True)
    dump(REPORT / "cache-verification.json", verify_prepared_cache(ROOT / "data/processed"))
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT / "data/processed/labels.npy", mmap_mode="r") > 0.5
    valid = np.load(ROOT / "data/processed/valid.npy", mmap_mode="r").copy()
    label_valid = np.load(ROOT / "data/processed/label_valid.npy", mmap_mode="r")
    if np.any(valid & ~label_valid):
        raise ValueError("unknown training labels inside footprint")
    labels &= valid
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    template = ROOT / "data/raw/sample_submission.tif"
    for row in manifest["source_files"].values():
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("prepared input source hash mismatch")
    registry = REPORT / "registry.json"

    print("Building/verifying label-free PTA-1 phase-tilt & dip-asymmetry cache...", flush=True)
    fields, _ = load_or_build_cache(base, valid, manifest, CACHE, report_dir=REPORT)
    stacks = build_arm_stacks(base, fields)
    check_time(deadline)

    # 1. Fit fixed final candidate BEFORE inspecting any holdout fold result.
    print("Fitting fixed full-footprint pta1_cand model for chronological novelty gate...", flush=True)
    x_full, y_full = sample_training_pixels(stacks["pta1_cand"], labels, valid, negatives_per_positive=6, seed=SEED)
    full_model, full_median, full_scale = fit_model(x_full, y_full, seed=SEED)
    full_norm = {
        "median": [float(v) for v in full_median],
        "scale": [float(v) for v in full_scale],
    }
    del x_full, y_full
    with threadpool_limits(limits=2):
        surface = predict_grid(full_model, stacks["pta1_cand"], full_median, full_scale, valid)
    del full_model
    write_submission_file(
        surface,
        template,
        RUN / "pta1-surface.tif",
        note="Continuous PTA1 subsurface research surface; not a competition submission.",
        run_name="gems30-pta1-surface",
    )
    print("Auditing continuous surface novelty against 194 registry rasters...", flush=True)
    surface_audit = audit(RUN / "pta1-surface.tif", template, registry, "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    print("Surface novelty decision:", surface_audit["decision"], flush=True)
    if surface_audit["decision"] == "duplicate-stop":
        dump(
            REPORT / "duplicate-stop.json",
            {"stage": "surface", "decision": "duplicate-stop", "no_further_experiment": True},
        )
        raise ValueError("duplicate-stop on continuous surface; no dots placed")
    check_time(deadline)

    dots = select_dots(surface, valid & ~labels, DOT_BUDGET)
    del surface
    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    run_name = f"gems30-PTA1-44090-20261025-{identity[:12]}"
    generated = RUN / f"{run_name}.tif"
    manifest_output = write_submission_file(dots, template, generated, run_name=run_name, note=NOTE)
    del dots
    print("Auditing final-dot novelty against 194 registry rasters...", flush=True)
    dots_audit = audit(generated, template, registry, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    print("Final-dot novelty decision:", dots_audit["decision"], flush=True)
    if dots_audit["decision"] == "duplicate-stop":
        dump(
            REPORT / "duplicate-stop.json",
            {"stage": "dots", "decision": "duplicate-stop", "no_further_experiment": True},
        )
        raise ValueError("duplicate-stop on final dots; no further experiment or publication")

    # 2. Buffered whole-component holdout + 37-feature single-feature leakage canaries.
    feature_names = list(CORE_FEATURES) + list(ALL_DERIVED_NAMES)
    if tuple(feature_names) != spec["features"]:
        raise AssertionError("feature canary list mismatch against experiment contract")

    sub8_cols = list(SUB8_INDICES)
    cand_cols = sub8_cols + [19 + ALL_DERIVED_NAMES.index(n) for n in CANDIDATE_DERIVED_NAMES]
    ctrl_names_in_arm = (
        "ctrl_naive_mag_tilt",
        "ctrl_naive_mag_hd_tdr",
        "ctrl_naive_mag_as3d_log",
        "pta_grav_tilt",
        "pta_grav_hd_tdr",
        "ctrl_naive_mg_concord",
        "ctrl_normal_blur",
        "ctrl_sym_grav_mig",
        "ctrl_sym_cover_step",
        "ctrl_sym_cond_step",
    )
    ctrl_cols = sub8_cols + [19 + ALL_DERIVED_NAMES.index(n) for n in ctrl_names_in_arm]
    arm_col_slices = {
        "core19": list(range(19)),
        "sub8_raw": sub8_cols,
        "pta_naive_sym": ctrl_cols,
        "pta1_cand": cand_cols,
    }

    block_rows: dict[str, list[dict]] = {name: [] for name in arms}
    folds, canaries = [], []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)

    for fold in spatial_segment_folds(labels, valid, buffer_px=SUPPORT_PX):
        check_time(deadline)
        f = fold["fold"]
        hidden_total += fold["hidden"]
        train_mask = fold["train_mask"]
        domain = fold["score_valid"] & ~fold["visible"]

        print(f"Fold {f}: sampling training coordinates and running 37-feature leakage canaries...", flush=True)
        x_all, y = sample_training_pixels(
            stacks["all37"], fold["visible"], train_mask, negatives_per_positive=6, seed=SEED + f
        )
        rng = np.random.default_rng(SEED + f + 10000)
        positives = np.flatnonzero(fold["hidden"])
        negatives = np.flatnonzero(domain & ~fold["hidden"])
        negatives = rng.choice(negatives, min(60000, negatives.size), replace=False)
        test_idx = np.concatenate([positives, negatives])
        target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])

        canary_rows = []
        for j, fname in enumerate(feature_names):
            check_time(deadline)
            col_train = x_all[:, j : j + 1]
            layer_2d = base[j] if j < 19 else fields[ALL_DERIVED_NAMES[j - 19]]
            vals = np.asarray(layer_2d, dtype=np.float32).ravel()[test_idx]
            u_model, u_med, u_scale = fit_model(col_train, y, seed=SEED + f + j, iterations=32, leaves=7)
            filled = np.where(np.isfinite(vals), vals, u_med[0])
            raw_auc = float(roc_auc_score(target, filled)) if np.ptp(filled) > 0 else 0.5
            with threadpool_limits(limits=2):
                probs = u_model.predict_proba(((filled - u_med[0]) / u_scale[0])[:, None])[:, 1]
            model_auc = float(roc_auc_score(target, probs)) if np.ptp(probs) > 0 else 0.5
            raw_either = max(raw_auc, 1.0 - raw_auc)
            canary_rows.append(
                {
                    "feature": fname,
                    "label": "LEAKAGE-CANARY AUC (not DTI)",
                    "raw_auc": raw_auc,
                    "raw_auc_either_direction": raw_either,
                    "univariate_training_only_hgb_auc": model_auc,
                    "alarm_above_0_90": bool(raw_either > 0.90 or model_auc > 0.90),
                    "heldout_positives": int(positives.size),
                    "sampled_negatives": int(negatives.size),
                }
            )
        canaries.append({"fold": f, "features": canary_rows})
        dump(REPORT / "canaries-partial.json", {"folds": canaries, "status": "partial until results.json exists"})

        count = int(round(DOT_BUDGET * domain.sum() / valid.sum()))
        fold_result = {
            **fold["metadata"],
            "dot_budget_each_arm": count,
            "arms": {},
            "arm_normalization": {},
        }
        emitted_hashes: dict[str, str] = {}
        for name in arms:
            check_time(deadline)
            cols = arm_col_slices[name]
            model, med, scale = fit_model(x_all[:, cols], y, seed=SEED + f)
            fold_result["arm_normalization"][name] = {
                "median": [float(v) for v in med],
                "scale": [float(v) for v in scale],
            }
            with threadpool_limits(limits=2):
                pred = predict_grid(model, stacks[name], med, scale, domain)
            emitted = select_dots(pred, domain, count)
            emitted_hashes[name] = hashlib.sha256(np.packbits(emitted > 0).tobytes()).hexdigest()
            score = masked_dti_by_blocks(
                emitted, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128
            )
            block_rows[name].extend(score["spatial_blocks"])
            fold_result["arms"][name] = {k: v for k, v in score["pooled"].items() if k != "dti"}
            print(f"Fold {f}: {name:14s} -> {int(emitted.sum())} active dots", flush=True)
            del model, pred, emitted
        if len(set(emitted_hashes.values())) < len(arms):
            raise AssertionError(f"degenerate identical emitted masks across distinct arms in fold {f}")
        folds.append(fold_result)
        del x_all, y

    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("each withheld positive must be counted exactly once")

    summary = spatial_bootstrap(block_rows, candidate="pta1_cand", replicates=2000, seed=3071)
    alarms = [dict(fold=f["fold"], **row) for f in canaries for row in f["features"] if row["alarm_above_0_90"]]
    beats_all = all(delta["value"] > 0 and delta["ci95"][0] > 0 for delta in summary["candidate_minus"].values())
    beats_subsurface_controls = all(
        summary["candidate_minus"][ctrl]["value"] > 0 and summary["candidate_minus"][ctrl]["ci95"][0] > 0
        for ctrl in ("sub8_raw", "pta_naive_sym")
    )
    scientific_pass = beats_all and not alarms

    novelty = summarize_novelty(surface_audit, dots_audit)
    validation_report = validate_submission_file(generated, template)
    validation = validation_report.to_dict()
    with rasterio.open(generated) as ds, rasterio.open(template) as reference:
        output = ds.read(1)
        validator = {
            "status": "passed" if validation["passed"] else "failed",
            "no_nan_inside_footprint": bool(np.isfinite(output[valid]).all()),
            "values_in_0_1": bool(np.all((output[valid] >= 0) & (output[valid] <= 1))),
            "crs_match": ds.crs == reference.crs,
            "shape_match": ds.shape == reference.shape,
            "transform_match": ds.transform == reference.transform,
            "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
            "nan_nodata_outside_footprint": bool(np.isnan(output[~valid]).all()),
            "positive_catalogue_pixels": int(np.count_nonzero(output[labels] > 0)),
            "emitted_dots": int(np.count_nonzero(output[valid] > 0)),
            "organizer_acceptance_confirmed": False,
        }
    if not validation["passed"] or validator["positive_catalogue_pixels"]:
        raise AssertionError("shared format/exact catalogue mask gate failed")
    dump(REPORT / "validation.json", validation)

    blockers = []
    if not scientific_pass:
        blockers.append("Candidate failed paired HOLDOUT-DTI improvement gate against core19 or feature leakage canary")
    blockers += [
        "Complete parallel-run raster/surface registry unavailable",
        "No externally assigned lane paragraph was supplied; research lane selected autonomously",
        "Historical best UNet checkpoints absent: comparable historical-best rerun unavailable",
        "Current portal cap, eligibility, deadline and organizer acceptance unverified",
    ]
    elapsed = round(time.monotonic() - started, 2)
    raster_digest = sha(generated)

    results = {
        "schema_version": 1,
        "experiment_spec": "pta1",
        "summary": summary,
        "subsurface_specificity_passed": beats_subsurface_controls,
        "folds": folds,
        "feature_canaries": canaries,
        "bootstrap_sufficient_statistics": block_rows,
        "full_fit_normalization": full_norm,
        "raster_sha256": raster_digest,
        "source_band_semantics": "Organizer reference notebook cell 5 (aebe92f7c8) + official forum 11557/2 & label-free unit audit",
        "preregistration_sha256": prereg_sha,
        "evaluator_version": EVALUATOR_VERSION,
        "protocol_version": SEGMENT_PROTOCOL_VERSION,
        "tight_analytic_support_px": TIGHT_SUPPORT_PX,
        "experimental_elapsed_seconds": elapsed,
        "this_execution_seconds": elapsed,
        "scientific_gate_passed": scientific_pass,
    }
    if len(NOTE) > 140:
        raise AssertionError("note exceeds 140 characters")

    card = {
        "schema_version": 3,
        "experiment_spec": "pta1",
        "run_id": run_name,
        "hypothesis": "Unit-consistent 3D potential-field phase-tilt ridges paired with signed Grauch-Hudson hanging-wall dip migration and conductive-cover thickening improve concealed fault recovery over raw subsurface fields and unit-naive/symmetric controls.",
        "mechanism": "Topography-free 18-feature HGB on 8 subsurface GeoDAWN/gravity/MT bands + 10 unit-corrected (1000x tmi_vg) tilt-phase curvature, strike persistence, and signed hanging-wall asymmetry transforms; matched unit-naive/symmetric and core19 comparators.",
        "non_fault_mimic": "Buried caldera-margin or dipping volcanic flow-front unconformity; GeoDAWN E-W (90 deg, 200-400 m) airborne survey leveling seam",
        "lane": "PTA-1 zero-topography subsurface 3D phase-tilt & dip-contact asymmetry (autonomous research lane, not externally assigned)",
        "experiments_run": 1,
        "fixed_arms": list(arms),
        "experiment_cap": 3,
        "experimental_elapsed_seconds": elapsed,
        "time_cap_hours": 2,
        "this_execution_seconds": elapsed,
        "corrective_execution": False,
        "physical_support_px": SUPPORT_PX,
        "tight_analytic_support_px": TIGHT_SUPPORT_PX,
        "confirmation_scope": "Buffered whole-component quadrant folds on public catalogue; proxy for concealed fault recovery, NOT organizer score",
        "holdout": {
            **summary["arms"]["pta1_cand"],
            "evaluator_version": EVALUATOR_VERSION,
            "protocol_version": SEGMENT_PROTOCOL_VERSION,
            "scope": "buffered whole-segment catalogue-recovery proxy; NOT organizer performance",
            "comparators": {name: summary["arms"][name] for name in arms if name != "pta1_cand"},
            "candidate_minus": summary["candidate_minus"],
            "subsurface_specificity_passed": beats_subsurface_controls,
            "bootstrap": summary["bootstrap"],
        },
        "feature_canaries": {
            "features_per_fold": len(canaries[0]["features"]),
            "folds": 4,
            "alarm_count": len(alarms),
            "alarms": alarms,
            "receipt": "docs/research/phase-tilt-asymmetry/results.json",
        },
        "registry": novelty,
        "raster_sha256": raster_digest,
        "validator_output": validator,
        "submission_name": run_name,
        "note": NOTE,
        "published_tiff": f"docs/downloads/{generated.name}",
        "download_ok": True,
        "submission_approved": False,
        "slot_selected": False,
        "verdict": "negative",
        "scientific_gate_passed": scientific_pass,
        "verdict_scope": "machine-adjudicated scientific and readiness gates; no competition performance claim",
        "blockers": blockers,
        "preregistration_sha256": prereg_sha,
        "dataset_signature": manifest["dataset_signature"],
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    registry_manifest = json.loads(registry.read_text())
    readiness = assess(
        card,
        results,
        format_passed=validation_report.passed,
        hash_matches=True,
        surface_audit=surface_audit,
        dots_audit=dots_audit,
        registry=registry_manifest,
    )
    card["verdict"] = readiness["research_verdict"]
    card["download_ok"] = readiness["download_ok"]

    dump(REPORT / "results.json", results)
    dump(REPORT / "run-card.json", card)
    dump(REPORT / "readiness.json", readiness)

    manifest_output.update(
        {
            "submission_approved": False,
            "download_ok": readiness["download_ok"],
            "submission_recommendation": False,
            "note": NOTE,
            "scientific_gate_passed": scientific_pass,
            "subsurface_specificity_passed": beats_subsurface_controls,
            "run_card": "docs/research/phase-tilt-asymmetry/run-card.json",
            "lineage": "New fit of PTA-1 subsurface phase-tilt & dip-asymmetry lane; zero previous submission pixels used as inputs or predictions",
            "method": TRANSFORM_VERSION,
            "preregistration_sha256": prereg_sha,
            "dataset_signature": manifest["dataset_signature"],
        }
    )
    dest = ROOT / "docs/downloads" / generated.name
    shutil.copyfile(generated, dest)
    dump(dest.with_suffix(".json"), manifest_output)
    (REPORT / "canaries-partial.json").unlink(missing_ok=True)
    print(json.dumps(card, indent=2), flush=True)
    return card


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=int, default=5400)
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 7200:
        parser.error("max-seconds must be in [1, 7200]")
    preflight_no_overwrite(REPORT)
    try:
        run(args.max_seconds)
    except Exception as exc:
        dump(
            REPORT / "failure.json",
            {
                "verdict": "negative",
                "submission_approved": False,
                "error": f"{type(exc).__name__}: {exc}",
                "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        )
        raise


if __name__ == "__main__":
    main()
