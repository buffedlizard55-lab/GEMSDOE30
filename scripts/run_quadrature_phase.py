#!/usr/bin/env python3
"""Run the frozen QPC-1 lane once; no tuning, private evaluator, or uploader."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
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
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from threadpoolctl import threadpool_limits

import lane_fflidar as ffl
from gemsdoe30.experiments import CORE_FEATURES, LayerStack
from gemsdoe30.holdout import EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION, masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds
from gemsdoe30.lidar_morphology import LIDAR_LAYERS, StackedFeatures
from gemsdoe30.msdb import (MSDB_FEATURE_NAMES, MSDB_RAW_KEEP_INDICES, build_or_load_msdb_cache,
                            calibrate_case_control_probabilities, compute_curvilinear_discontinuity_gate,
                            fit_curvilinear_gate_scales)
from gemsdoe30.quadrature_phase import FEATURE_NAMES, GUARD_PX, SUPPORT_PX, compute_features
from gemsdoe30.readiness import assess
from gemsdoe30.submission import validate_submission_file, write_submission_file
from scripts.check_novelty import audit
from scripts.feature_value_holdout import predict_grid, sample_training_pixels
from scripts.run_geothermal_chemistry import canaries
from scripts.run_phase_tilt_asymmetry import fit_model, select_dots
from scripts.verify_prepared_cache import verify as verify_cache

REPORT = ROOT / "docs/research/2026-10-26-qpc"
WORK = ROOT / "outputs/qpc1"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"
MSDB_RESULTS = ROOT / "docs/research/msdb-piedmont/results.json"
MSDB_CARD = ROOT / "docs/research/msdb-piedmont/run-card.json"
FFL_RESULTS = ROOT / "docs/research/2026-10-26-fflidar/results-confirmation.json"
FFL_CARD = ROOT / "docs/research/2026-10-26-fflidar/run-card.json"
EXPECTED = {
    "registry.json": "251430967cd4e85cd81775be747146caa9f131e2d8bd9fe4bebd74839546a72f",
    str(MSDB_RESULTS): "aa303c861dcaea1e3ccceb5f143f0df1b1e2564255e93795bee69fd3f5087842",
    str(MSDB_CARD): "d279ed302c0888f72c89eb8b6e3aa0e74e9738ac02e72e47beac89cc2bbd0e0e",
    str(FFL_RESULTS): "6d310609524ec5d4ff0e129db6354a7731dedc1fb9c902d4be619a324f1e4b99",
    str(FFL_CARD): "1c79260c01298fa838da4eb0c1234df07d70ca0e1faa896ec9d67117246c00e3",
}
DATASET_SIGNATURE = "291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed"
SEED, FFL_SEED, DOT_BUDGET = 3041, 3063, 44090
NOTE = "QPC1 magnetic-gravity quadrature phase, 44090 dots; research only, not approved for competition submission."
ARMS = {
    "core19": tuple(range(19)),
    "persistence21": (*range(19), 21, 22),
    "qpc23": tuple(range(23)),
}


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def lock_once(path, payload):
    """An existing start marker forbids resumption, retuning or re-execution."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w") as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_frozen_inputs():
    for name, expected in EXPECTED.items():
        path = REPORT / name if name == "registry.json" else Path(name)
        if sha(path) != expected:
            raise ValueError(f"frozen source hash changed: {path}")
    msdb, mc = json.loads(MSDB_RESULTS.read_text()), json.loads(MSDB_CARD.read_text())
    old, fc = json.loads(FFL_RESULTS.read_text()), json.loads(FFL_CARD.read_text())
    for card in (mc, fc):
        if card.get("dataset_signature") != DATASET_SIGNATURE:
            raise ValueError("historic comparator dataset signature mismatch")
    for result in (msdb, old):
        if (result["summary"]["evaluator_version"] != EVALUATOR_VERSION or
                result["summary"]["protocol_version"] != SEGMENT_PROTOCOL_VERSION):
            raise ValueError("historic comparator protocol mismatch")
    if old.get("seed") != FFL_SEED or old["summary"]["arms"]["fusion_edge"]["withheld_positives"] != 60988:
        raise ValueError("unexpected strongest comparator confirmation")
    return msdb, old


def novelty_summary(report):
    rows = report.get("comparisons", [])
    correlations = [r["spearman_full_footprint"] for r in rows if r.get("spearman_full_footprint") is not None]
    overlaps = [r["candidate_fraction_within_3px_of_reference"] for r in rows
                if r.get("candidate_fraction_within_3px_of_reference") is not None]
    return {"decision": report.get("decision"), "registry_entries_compared": len(rows),
            "max_spearman": max(correlations) if correlations else None,
            "max_fraction_within_3px": max(overlaps) if overlaps else None,
            "errors": report.get("errors", [])}


def assert_audit_research_only(report):
    """Duplicate-stop is absolute; malformed in-footprint refs remain UNKNOWN.

    Only the specific malformed-value class in the preregistration can be
    explored. Missing files, wrong hashes/grids, or read errors stop execution.
    Unknowns never grant uniqueness or upload permission.
    """
    rows = report.get("comparisons", [])
    duplicate = any(r.get("identical_inside_footprint") or
                    (r.get("spearman_full_footprint") is not None and r["spearman_full_footprint"] > .90) or
                    (report.get("stage") == "dots" and r.get("candidate_fraction_within_3px_of_reference") is not None
                     and r["candidate_fraction_within_3px_of_reference"] > .70) for r in rows)
    if report.get("decision") == "duplicate-stop" or duplicate:
        raise DuplicateStop(report.get("stage", "unknown"))
    if not rows:
        raise ValueError("no registry references could be compared")
    unexpected = [e for e in report.get("errors", []) if "non-finite values inside footprint" not in e]
    if unexpected:
        raise ValueError("unresolved registry I/O/hash/grid error: " + "; ".join(unexpected[:3]))


def assert_matching_fold(fold, archived, count):
    """Block reuse unless the full whole-component fold and budget match."""
    keys = ("protocol_version", "fold", "buffer_px", "metric_halo_px", "withheld_components",
            "withheld_positives", "visible_positives", "guard_positives_not_truth",
            "training_pixels", "scored_pixels", "hidden_component_ids")
    if any(fold["metadata"][k] != archived[k] for k in keys):
        raise ValueError("archived MSDB fold identity or counts do not match current fold")
    if count != archived["dot_budget_each_arm"]:
        raise ValueError("archived MSDB dot budget mismatch")


def assert_pooled_parity(actual, expected, label):
    for key in ("tp_weight", "fp_weight", "truth_pixels", "emitted_pixels"):
        if not np.isclose(actual[key], expected[key], atol=1e-6, rtol=0):
            raise ValueError(f"{label} replay mismatch for {key}: {actual[key]} vs {expected[key]}")


def assert_block_parity(current, previous):
    keys = ("block_row", "block_col", "truth_pixels", "scored_pixels")
    if len(current) != len(previous) or any(
        any(a[k] != b[k] for k in keys) for a, b in zip(current, previous)
    ):
        raise ValueError("archived MSDB geographic blocks/masks/truth differ")


class DuplicateStop(Exception):
    pass


def negative_card(reason, *, state, started):
    card = {
        "schema_version": 1, "experiment_spec": "qpc1",
        "hypothesis": "Co-located magnetic and gravity quadrature-phase proxies identify concealed fault boundaries.",
        "mechanism": "Two-scale high-pass/gradient normalized vector concordance, with within-field persistence.",
        "non_fault_mimic": "Volcanic-flow or intrusive contacts, dike swarms, and survey leveling artifacts.",
        "holdout": state.get("holdout", {"label": "HOLDOUT-DTI", "value": None, "ci95": None,
                    "withheld_positives": None, "evaluator_version": EVALUATOR_VERSION,
                    "reason": "experiment stopped before a trusted pooled result"}),
        "registry": state.get("registry", {"complete": False}),
        "raster_sha256": state.get("raster_sha256"), "validator_output": state.get("validator_output"),
        "submission_name": state.get("submission_name"), "note": NOTE,
        "published_tiff": None, "download_ok": False, "ok_to_submit": False,
        "submission_approved": False, "slot_selected": False, "verdict": "negative",
        "reason": reason, "experiments_run": state.get("experiments_run", 1),
        "experiment_cap": 3, "experimental_elapsed_seconds": round(time.monotonic() - started, 3),
        "organizer_score": None, "leaderboard_estimate": None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    dump(REPORT / "run-card.json", card)
    dump(REPORT / "failure.json", {"reason": reason, "verdict": "negative", "no_resume": True})
    return card


def execute(max_seconds, state, started):
    deadline = started + max_seconds

    def check_time():
        if time.monotonic() >= deadline:
            raise TimeoutError("lane time budget reached; stop without further work")

    if SUPPORT_PX + 3 > GUARD_PX or not 0 < max_seconds <= 7200 or len(NOTE) > 140:
        raise ValueError("invalid support, timer, or note contract")
    msdb_archive, ffl_archive = validate_frozen_inputs()
    cache_receipt = verify_cache(ROOT / "data/processed")
    if cache_receipt["dataset_signature"] != DATASET_SIGNATURE:
        raise ValueError("prepared data differ from frozen input")
    dump(REPORT / "cache-verification.json", cache_receipt)
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT / "data/processed/labels.npy") > .5
    valid = np.load(ROOT / "data/processed/valid.npy")
    label_valid = np.load(ROOT / "data/processed/label_valid.npy")
    if not np.all(label_valid[valid]) or np.any(labels & ~valid):
        raise ValueError("template footprint contains unknown labels")
    WORK.mkdir(parents=True, exist_ok=True)
    out = np.lib.format.open_memmap(WORK / "qpc-features.npy", mode="w+", dtype="float32",
                                    shape=(len(FEATURE_NAMES), *valid.shape))
    print("Building frozen catalogue-free QPC phase proxies...", flush=True)
    compute_features(base, valid, out=out)
    out.flush()
    del out
    extra = np.load(WORK / "qpc-features.npy", mmap_mode="r")
    stack = LayerStack([base[i] for i in range(19)] + [extra[i] for i in range(4)])
    stacks = {name: LayerStack([stack.layers[j] for j in cols]) for name, cols in ARMS.items()}
    names = CORE_FEATURES + FEATURE_NAMES
    dump(REPORT / "feature-receipt.json", {
        "dataset_signature": manifest["dataset_signature"], "feature_names": list(names),
        "derived_array_sha256": sha(WORK / "qpc-features.npy"),
        "transform_sha256": sha(ROOT / "src/gemsdoe30/quadrature_phase.py"),
        "physical_support_px": SUPPORT_PX, "guard_px": GUARD_PX,
        "catalogue_or_template_values_used_as_features": False,
    })
    check_time()
    # An actual full-fit surface is compared before any candidate placement.
    x, y = sample_training_pixels(stacks["qpc23"], labels, valid, negatives_per_positive=6, seed=SEED)
    model, med, scale = fit_model(x, y, seed=SEED)
    with threadpool_limits(limits=2):
        surface = predict_grid(model, stacks["qpc23"], med, scale, valid)
    del model, x, y
    surface_path = WORK / "qpc1-preplacement-surface.tif"
    write_submission_file(surface, TEMPLATE, surface_path, run_name="gems30-QPC1-surface",
                          note="Pre-placement continuous research surface; not a submission.")
    print("Auditing the pre-placement surface against the frozen public registry...", flush=True)
    surface_audit = audit(surface_path, TEMPLATE, REPORT / "registry.json", "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    state["registry"] = {"complete": False, "surface_receipt": "docs/research/2026-10-26-qpc/novelty-surface.json",
                         "surface": novelty_summary(surface_audit)}
    assert_audit_research_only(surface_audit)
    check_time()
    # The comparator replay is a fixed control, not a new final prediction.
    print("Restoring strongest fixed FFL comparator features...", flush=True)
    pin = next(r for r in json.loads((ROOT / "docs/research/mirror-pins-extra.json").read_text())["files"]
               if r["id"] == "ext_lidar_scarp_features_u8")
    if sha(ROOT / "data/raw" / pin["dest"]) != pin["sha256"]:
        raise ValueError("LiDAR comparator source SHA mismatch")
    msdb = build_or_load_msdb_cache(base, valid, ffl.MSDB_CACHE, DATASET_SIGNATURE)
    lidar = ffl.stage_build(valid)
    ffl_stack = StackedFeatures(base, msdb, lidar)
    ffl_names = list(CORE_FEATURES) + list(MSDB_FEATURE_NAMES) + list(LIDAR_LAYERS)
    parts = [base, msdb, lidar]
    part_channels = [(0, j) for j in range(19)] + [(1, j) for j in range(18)] + [(2, j) for j in range(17)]
    fusion_cols = list(MSDB_RAW_KEEP_INDICES) + [19 + j for j in range(18)] + [37 + j for j in range(17)]
    state["experiments_run"] = 2
    candidate_canaries, baseline_canaries = [], []
    # Canary each exact feature of both systems, in each blocked fold, before
    # evaluating either system. Data-derived catalog features are prohibited.
    for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
        check_time()
        f = fold["fold"]
        print(f"Fold {f}: individual candidate and comparator leakage canaries...", flush=True)
        xq, yq = sample_training_pixels(stack, fold["visible"], fold["train_mask"],
                                        negatives_per_positive=6, seed=SEED + f)
        qc = canaries(xq, yq, stack, names, fold, seed=SEED + f)
        del xq, yq
        xf, yf = sample_training_pixels(ffl_stack, fold["visible"], fold["train_mask"],
                                        negatives_per_positive=6, seed=FFL_SEED + f)
        fc = ffl.canaries(parts, part_channels, ffl_names, xf, yf, fold, FFL_SEED + f)
        del xf, yf
        candidate_canaries.append(qc)
        baseline_canaries.append({"fold": f, "features": fc})
        dump(REPORT / "canaries-partial.json", {"candidate": candidate_canaries, "ffl": baseline_canaries,
                                                  "complete": False})
        if any(r["alarm_above_0_90"] for r in qc["features"] + fc):
            raise ValueError(f"leakage-canary alarm in fold {f}; stop before holdout performance")
    check_time()
    blocks = {name: [] for name in (*ARMS, "ffl_confirm")}
    folds_out = []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)
    for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
        check_time()
        f = fold["fold"]
        hidden_total += fold["hidden"]
        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(DOT_BUDGET * int(active.sum()) / int(valid.sum())))
        old_fold = msdb_archive["folds"][f]
        assert_matching_fold(fold, old_fold, count)
        row = {**fold["metadata"], "dot_budget_each_arm": count,
               "arms": {"msdb_edge": old_fold["arms"]["msdb_edge"]}}
        xq, yq = sample_training_pixels(stack, fold["visible"], fold["train_mask"],
                                        negatives_per_positive=6, seed=SEED + f)
        for name, cols in ARMS.items():
            check_time()
            model, med, scale = fit_model(xq[:, cols], yq, seed=SEED + f)
            with threadpool_limits(limits=2):
                p = predict_grid(model, stacks[name], med, scale, active)
            dots = select_dots(p, active, count)
            scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                          fold["score_valid"], block_size_px=128)
            blocks[name].extend(scored["spatial_blocks"])
            row["arms"][name] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
            if name == "core19":
                assert_pooled_parity(scored["pooled"], old_fold["arms"]["core19"], "MSDB core19")
            del model, p, dots
            print(f"Fold {f}: evaluated {name}", flush=True)
        del xq, yq
        check_time()
        xf, yf = sample_training_pixels(ffl_stack, fold["visible"], fold["train_mask"],
                                        negatives_per_positive=6, seed=FFL_SEED + f)
        pop_pos = int(np.count_nonzero(fold["train_mask"] & fold["visible"]))
        pop_neg = int(np.count_nonzero(fold["train_mask"] & ~fold["visible"]))
        gate_scales = fit_curvilinear_gate_scales(xf[:, 19:37])
        model, med, scale = ffl.fit_model(xf[:, fusion_cols], yf, seed=FFL_SEED + f)
        raw = ffl.predict_ordered(model, ffl_stack, fusion_cols, med, scale, active)
        del model
        cal = calibrate_case_control_probabilities(raw, population_positives=pop_pos, population_negatives=pop_neg,
                sample_positives=int(np.count_nonzero(yf > .5)), sample_negatives=int(np.count_nonzero(yf < .5)))
        psi = compute_curvilinear_discontinuity_gate(msdb, gate_scales, active)
        gated = (cal * psi).astype(np.float32)
        dots = ffl.edge_dots(gated, active, count)
        scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
        assert_pooled_parity(scored["pooled"], ffl_archive["folds"][f]["arms"]["fusion_edge"], "FFL confirmation")
        blocks["ffl_confirm"].extend(scored["spatial_blocks"])
        row["arms"]["ffl_confirm"] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
        folds_out.append(row)
        del xf, yf, raw, cal, psi, gated, dots
        print(f"Fold {f}: strongest FFL comparator replay matched frozen receipt", flush=True)
    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("every catalogue positive must be withheld exactly once")
    historic = msdb_archive["bootstrap_sufficient_statistics"]["msdb_edge"]
    assert_block_parity(blocks["qpc23"], historic)
    blocks["msdb_edge"] = historic
    summary = spatial_bootstrap(blocks, candidate="qpc23", replicates=2000, seed=3071)
    old_expected = msdb_archive["summary"]["arms"]["msdb_edge"]["value"]
    ffl_expected = ffl_archive["summary"]["arms"]["fusion_edge"]["value"]
    if not np.isclose(summary["arms"]["msdb_edge"]["value"], old_expected, atol=1e-12, rtol=0):
        raise ValueError("MSDB pooled bootstrap reproduction failed")
    if not np.isclose(summary["arms"]["ffl_confirm"]["value"], ffl_expected, atol=1e-9, rtol=0):
        raise ValueError("FFL pooled confirmation reproduction failed")
    results = {"schema_version": 1, "experiment_spec": "qpc1", "summary": summary,
               "folds": folds_out, "feature_canaries": candidate_canaries, "ffl_feature_canaries": baseline_canaries,
               "bootstrap_sufficient_statistics": blocks, "strongest_replay_matches_receipt": True,
               "msdb_archive_block_parity": True, "preregistration_sha256": sha(REPORT / "preregistration.md")}
    results["scientific_gate_passed"] = all(summary["candidate_minus"][n]["ci95"][0] > 0
                                             for n in ("persistence21", "msdb_edge", "ffl_confirm"))
    dump(REPORT / "results.json", results)
    state["holdout"] = {**summary["arms"]["qpc23"], "evaluator_version": EVALUATOR_VERSION,
                        "protocol_version": SEGMENT_PROTOCOL_VERSION, "comparators": {k: v for k, v in summary["arms"].items() if k != "qpc23"},
                        "candidate_minus": summary["candidate_minus"], "bootstrap": summary["bootstrap"],
                        "scope": "mapped-fault holdout proxy; not an organizer score or leaderboard projection"}
    check_time()
    # Only after canaries and paired testing do we create final dots.
    final_domain = valid & ~labels
    dots = select_dots(surface, final_domain, DOT_BUDGET)
    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    run_name = f"gems30-QPC1-44090-20261026-{identity[:12]}"
    output = WORK / f"{run_name}.tif"
    sidecar = write_submission_file(dots, TEMPLATE, output, run_name=run_name, note=NOTE)
    state.update(raster_sha256=sha(output), submission_name=run_name)
    print("Auditing final dots against the same frozen public registry...", flush=True)
    dots_audit = audit(output, TEMPLATE, REPORT / "registry.json", "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    state["registry"]["dots_receipt"] = "docs/research/2026-10-26-qpc/novelty-dots.json"
    state["registry"]["dots"] = novelty_summary(dots_audit)
    assert_audit_research_only(dots_audit)
    check_time()
    report = validate_submission_file(output, TEMPLATE)
    with rasterio.open(output) as ds, rasterio.open(TEMPLATE) as tpl:
        values = ds.read(1)
        validator = {"status": "passed" if report.passed else "failed",
                     "no_nan_inside_footprint": bool(np.isfinite(values[valid]).all()),
                     "values_in_0_1": bool(np.all((values[valid] >= 0) & (values[valid] <= 1))),
                     "crs_match": ds.crs == tpl.crs, "shape_match": ds.shape == tpl.shape,
                     "transform_match": ds.transform == tpl.transform,
                     "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
                     "nan_nodata_outside_footprint": bool(np.isnan(values[~valid]).all()),
                     "positive_catalogue_pixels": int(np.count_nonzero(values[labels] > 0)),
                     "emitted_dots": int(np.count_nonzero(values[valid] > 0)),
                     "organizer_acceptance_confirmed": False}
    state["validator_output"] = validator
    if not report.passed or validator["positive_catalogue_pixels"] or validator["emitted_dots"] != DOT_BUDGET:
        raise ValueError("final format or catalogue masking failed")
    dump(REPORT / "validation.json", report.to_dict())
    published = REPORT / output.name
    card = {
        "schema_version": 1, "experiment_spec": "qpc1", "run_id": run_name,
        "lane": "QPC-1 autonomous exploratory lane; no externally assigned paragraph",
        "hypothesis": "Co-located magnetic and gravity quadrature-phase proxies identify concealed fault boundaries.",
        "mechanism": "Two-scale high-pass/gradient normalized vector concordance and within-field persistence, followed by fixed HGB and 3-pixel emission.",
        "non_fault_mimic": "Volcanic-flow or intrusive contacts, dike swarms, and survey leveling artifacts.",
        "holdout": state["holdout"],
        "feature_canaries": {"candidate_features_per_fold": len(names), "ffl_features_per_fold": len(ffl_names),
                              "folds": 4, "alarms": []},
        "registry": state["registry"], "raster_sha256": sha(output), "surface_sha256": sha(surface_path),
        "validator_output": validator, "submission_name": run_name, "note": NOTE,
        "published_tiff": str(published.relative_to(ROOT)), "organizer_score": None, "leaderboard_estimate": None,
        "externally_assigned_lane_verified": False,
        "historical_best_rerun": {"verified": True, "evaluator_version": EVALUATOR_VERSION,
                                  "protocol_version": SEGMENT_PROTOCOL_VERSION,
                                  "candidate_beats_best_with_paired_ci": summary["candidate_minus"]["ffl_confirm"]["ci95"][0] > 0},
        "scientific_gate_passed": results["scientific_gate_passed"], "experiments_run": 2,
        "experiment_cap": 3, "experimental_elapsed_seconds": round(time.monotonic() - started, 3), "time_cap_hours": 2,
        "preregistration_sha256": sha(REPORT / "preregistration.md"), "registry_sha256": sha(REPORT / "registry.json"),
        "dataset_signature": DATASET_SIGNATURE, "submission_approved": False, "slot_selected": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    registry = json.loads((REPORT / "registry.json").read_text())
    readiness = assess(card, results, format_passed=report.passed, hash_matches=card["raster_sha256"] == sha(output),
                       surface_audit=surface_audit, dots_audit=dots_audit, registry=registry)
    if not readiness["download_ok"]:
        raise ValueError("readiness forbids publication of the research raster")
    shutil.copyfile(output, published)
    if sha(published) != card["raster_sha256"]:
        published.unlink(missing_ok=True)
        raise ValueError("published raster bytes differ from the verified output")
    card.update(verdict=readiness["research_verdict"], download_ok=readiness["download_ok"], ok_to_submit=False)
    card["registry"].update(readiness["observed_registry"])
    card["blockers"] = [g["name"] + ": " + g["detail"] for g in readiness["gates"] if g["status"] != "passed"]
    card["blockers"].append("Independent confirmation, organizer authentication and a separate slot selector remain required")
    dump(REPORT / "readiness.json", readiness)
    dump(REPORT / "run-card.json", card)
    sidecar.update(submission_approved=False, slot_selected=False, ok_to_submit=False,
                   download_scope="research only; no leaderboard estimate", run_card="docs/research/2026-10-26-qpc/run-card.json")
    dump(published.with_suffix(".json"), sidecar)
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=int, default=6000)
    args = parser.parse_args()
    if not 0 < args.max_seconds <= 7200:
        parser.error("time cap must be between 1 and 7200 seconds")
    started = time.monotonic()
    packages = {name: metadata.version(name) for name in ("numpy", "scipy", "rasterio", "scikit-learn", "threadpoolctl")}
    try:
        lock_once(REPORT / "started.json", {
            "started_utc": datetime.now(timezone.utc).isoformat(), "preregistration_sha256": sha(REPORT / "preregistration.md"),
            "registry_sha256": sha(REPORT / "registry.json"), "runner_sha256": sha(__file__),
            "transform_sha256": sha(ROOT / "src/gemsdoe30/quadrature_phase.py"),
            "packages": packages, "max_seconds": args.max_seconds, "experiment_cap": 3,
            "externally_assigned_lane_verified": False,
        })
    except FileExistsError:
        print("Start marker exists: no resumption or additional experiments allowed.", file=sys.stderr)
        return 2
    state = {"experiments_run": 1}
    try:
        card = execute(args.max_seconds, state, started)
    except DuplicateStop as exc:
        card = negative_card(f"duplicate-stop at {exc}; no perturbation or publication", state=state, started=started)
    except Exception as exc:
        card = negative_card(f"{type(exc).__name__}: {exc}", state=state, started=started)
    print(json.dumps(card, indent=2, allow_nan=False), flush=True)
    return 0 if card.get("published_tiff") else 2


if __name__ == "__main__":
    raise SystemExit(main())
