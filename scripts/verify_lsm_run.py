#!/usr/bin/env python3
"""Machine-adjudicated OK-TO-SUBMIT decision for the G30-LSM artifact (no human inspector).

Needs only committed receipts plus the hash-pinned template (restorable in CI with
``scripts/restore_public_mirrors.py --ids sample_submission``). It:

1. reopens BOTH published TIFFs, rechecks SHA-256, the shared validator, the whole-array
   [0, 1] contract of the primary file, exact {0,1} values, the dot count, and that no dot sits
   on or within 2 px of a known fault (the template's 1-valued pixels are the catalogue,
   verified identical to the labels on 2026-10-25);
2. recomputes the E1 paired spatial-block bootstrap from the stored block statistics and
   requires an exact match with the recorded summary and gate;
3. recomputes every leakage-canary alarm from the stored AUC rows;
4. checks that the preregistration/amendment hashes match the start receipts and results;
5. checks that the novelty receipts are bound to the published dot identity and pass the thresholds;
6. writes/compares ``readiness.json`` with a single explicit ``ok_to_submit`` boolean.

Exit 0 = verified (decision may be OK or NOT OK); 1 = verification failure; with
``--require-promote`` exit 2 when the verified decision is NOT OK TO SUBMIT.
Slot selection stays a separate step: this script never uploads or spends a slot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

READINESS_VERSION = "lsm-readiness-v1-20261025"
THRESH_RHO, THRESH_OVERLAP, THRESH_AUC = 0.90, 0.70, 0.90


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"evidence root must be an object: {path}")
    return value


def inside(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(ROOT):
        raise ValueError("evidence path must stay inside the repository")
    return path


def close(a, b, where):
    if isinstance(b, dict):
        if not isinstance(a, dict) or set(a) != set(b):
            raise ValueError(f"key mismatch at {where}")
        for k in b:
            close(a[k], b[k], f"{where}/{k}")
    elif isinstance(b, list):
        if not isinstance(a, list) or len(a) != len(b):
            raise ValueError(f"length mismatch at {where}")
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, f"{where}/{i}")
    elif isinstance(b, float):
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isclose(a, b, abs_tol=1e-10, rel_tol=0):
            raise ValueError(f"numeric mismatch at {where}")
    elif a != b:
        raise ValueError(f"value mismatch at {where}")


def verify(pointer: Path, template: Path, *, write: bool = False) -> dict:
    import numpy as np
    import rasterio
    from scipy.ndimage import distance_transform_edt

    from gemsdoe30.holdout import spatial_bootstrap
    from gemsdoe30.submission import valid_template_mask, validate_submission_file

    selection = load(pointer)
    card_path = inside(selection["run_card"])
    report = card_path.parent
    card = load(card_path)
    gates = []

    def gate(name, ok, detail):
        gates.append({"name": name, "status": "passed" if ok else "failed", "detail": detail})
        return ok

    duplicate = card.get("verdict") == "duplicate-stop"
    if duplicate:
        return verify_duplicate_stop(pointer, template, selection, card, report, write=write)
    # 1. File contract on both published files.
    with rasterio.open(template) as tpl:
        valid = valid_template_mask(tpl, np)
        catalogue = (tpl.read(1) == 1) & valid
        grid = (tpl.shape, tpl.crs, tpl.transform)
    if int(catalogue.sum()) != 60988:
        raise ValueError("template catalogue pixel count changed; re-verify template/label identity")
    near = distance_transform_edt(~catalogue) <= 2
    files = {}
    for key in ("primary_zeros_outside", "alternate_nan_outside"):
        entry = card["files"][key]
        path = inside(entry["path"])
        digest = sha(path)
        if digest != entry["sha256"]:
            raise ValueError(f"{key}: SHA-256 differs from run card")
        rep = validate_submission_file(path, template)
        with rasterio.open(path) as ds:
            a = ds.read(1)
            same_grid = (ds.shape, ds.crs, ds.transform) == grid and ds.count == 1 and ds.dtypes == ("float32",)
        inner = a[valid]
        files[key] = {
            "sha256": digest, "shared_validator_passed": bool(rep.passed), "grid_match": bool(same_grid),
            "no_nan_inside": bool(np.isfinite(inner).all()),
            "values_exactly_0_or_1_inside": bool(np.isin(inner, (0.0, 1.0)).all()),
            "whole_array_finite_in_0_1": bool(np.isfinite(a).all() and ((a >= 0) & (a <= 1)).all()),
            "outside": "zeros" if np.all(a[~valid] == 0) else ("nan" if np.isnan(a[~valid]).all() else "mixed"),
            "dots": int((inner > 0).sum()), "dots_on_catalogue": int((a[catalogue] > 0).sum()),
            "dots_within_2px_of_catalogue": int(((a > 0) & valid & near).sum()),
            "values_identity_sha256": hashlib.sha256(np.ascontiguousarray(inner.astype(np.float32)).tobytes()).hexdigest(),
        }
    z, n = files["primary_zeros_outside"], files["alternate_nan_outside"]
    identity = z["values_identity_sha256"]
    contract = (z["shared_validator_passed"] and n["shared_validator_passed"] and z["grid_match"] and n["grid_match"]
                and z["no_nan_inside"] and z["values_exactly_0_or_1_inside"] and z["whole_array_finite_in_0_1"]
                and z["outside"] == "zeros" and n["outside"] == "nan" and z["dots"] == n["dots"] == 38000
                and z["dots_on_catalogue"] == 0 and z["dots_within_2px_of_catalogue"] == 0
                and identity == n["values_identity_sha256"] and card["run_id"].endswith(identity[:12]))
    gate("file_contract", contract,
         "Both TIFFs reopened: shared validator, exact grid, single float32 band, values {0,1}, primary finite in [0,1] "
         "everywhere (portal range check), 38,000 dots, none on/within 200 m of known faults, identity bound to the name")
    note = card["submission_note"]
    gate("name_and_note", len(note) <= 140 and card["submission_name"] == card["run_id"],
         f"Unique name {card['run_id']}; note {len(note)}/140 characters")

    # 2. Preregistration binding.
    prereg = sha(report / "preregistration.md")
    amend = sha(report / "preregistration-e3.md")
    e1 = load(report / "results-e1.json")
    e2 = load(report / "results-e2.json")
    e3 = load(report / "results-e3.json")
    starts = [load(report / f"started-e{i}.json") for i in (1, 2, 3)]
    bound = (all(s["preregistration_sha256"] == prereg for s in starts) and e1["preregistration_sha256"] == prereg
             and e3["preregistration_sha256"] == prereg and e3["amendment_sha256"] == amend
             and starts[2]["amendment_sha256"] == amend)
    gate("preregistration_binding", bound, "Frozen preregistration and E3 amendment hashes match every start receipt and result")

    # 3. Recompute the E1 bootstrap and gate from stored block statistics.
    blocks = load(report / "bootstrap-blocks-e1.json")["blocks"]
    recomputed = {e: spatial_bootstrap(blocks[e], candidate="lsm42", replicates=2000, seed=3071) for e in ("primary", "production")}
    close(e1["summary"], recomputed, "results-e1/summary")
    first = load(report / "results-e1.first-execution.json")["summary"]
    close(first, recomputed, "results-e1.first-execution/summary")
    p, q = recomputed["primary"], recomputed["production"]
    labelled = all(v["label"] == "HOLDOUT-DTI" and v["withheld_positives"] == 60988 for v in p["arms"].values())
    gate("labelled_holdout_evidence", labelled and e1["evaluator_version"] == p["evaluator_version"],
         f"HOLDOUT-DTI, evaluator {p['evaluator_version']}, protocol {p['protocol_version']}, 60,988 withheld positives, "
         "paired 128 px spatial-block bootstrap (2,000 draws)")
    d = p["candidate_minus"]["core19"]
    beats = d["value"] > 0 and d["ci95"][0] > 0 and q["candidate_minus"]["core19"]["value"] >= 0
    gate("beats_current_holdout_best", beats,
         f"lsm42 - core19 = {d['value']:+.5f} [{d['ci95'][0]:+.5f}, {d['ci95'][1]:+.5f}] (primary); "
         f"production-emission delta {q['candidate_minus']['core19']['value']:+.5f}")
    gate("comparator_reproduced", abs(p["arms"]["core19"]["value"] - e1["core19_recorded_tdx1"]["value"]) < 1e-9,
         "Same-run core19 reproduces the recorded TDX-1 holdout best exactly (same folds, budget, emission)")

    # 4. Canaries recomputed from stored AUC rows.
    rows = [r for f in e1["feature_canaries"] for r in f["features"]]
    alarm = any(max(r["raw_auc"], 1 - r["raw_auc"], r["univariate_training_only_hgb_auc"],
                    1 - r["univariate_training_only_hgb_auc"]) > THRESH_AUC for r in rows)
    complete = len(e1["feature_canaries"]) == 4 and all(len(f["features"]) == 42 for f in e1["feature_canaries"])
    gate("single_feature_leakage_canaries", complete and not alarm,
         f"{len(rows)} checks (42 inputs x 4 folds); max AUC "
         f"{max(max(r['raw_auc_either_direction'], r['univariate_training_only_hgb_auc']) for r in rows):.4f} <= 0.90")

    # 5. Independent-frame confirmation and E3 decision.
    gate("independent_frame_confirmation", bool(e2["arms"]["lsm42"]["dti"] >= e2["arms"]["core19"]["dti"]),
         f"SGMC-new frame: lsm42 {e2['arms']['lsm42']['dti']:.5f} >= core19 {e2['arms']['core19']['dti']:.5f} (reported frame; not a leaderboard proxy)")
    gate("e3_decision_followed", e3["gate"]["passed"] is False and "plain" in card["e3_crest_line_emission"]["verdict"],
         "E3 crest-line emission failed its gate; plain emission kept as preregistered")

    # 6. Novelty receipts bound to the published dots.
    surf = load(report / "novelty-surface.json")
    dots = load(report / "novelty-dots.json")
    def max_of(rows_, key):
        vals = [r[key] for r in rows_ if r.get(key) is not None]
        return max(vals) if vals else None
    novelty_ok = (dots.get("candidate_values_sha256") == identity
                  and surf["decision"].startswith("novelty-check-passed") and dots["decision"].startswith("novelty-check-passed")
                  and not surf["errors"] and not dots["errors"]
                  and max_of(surf["rows"], "spearman_full_footprint") <= THRESH_RHO
                  and max_of(dots["rows"], "spearman_full_footprint") <= THRESH_RHO
                  and max_of(dots["rows"], "candidate_fraction_within_3px_of_reference") <= THRESH_OVERLAP
                  and surf["max_spearman"] == max_of(surf["rows"], "spearman_full_footprint")
                  and dots["max_fraction_within_3px"] == max_of(dots["rows"], "candidate_fraction_within_3px_of_reference"))
    gate("novelty_surface_and_dots", novelty_ok,
         f"{dots['references_compared']} references; max surface rho {surf['max_spearman']:.3f}, max dot rho "
         f"{dots['max_spearman']:.3f}, max dots within 3 px {dots['max_fraction_within_3px']:.3f} (thresholds 0.90 / 0.70)")
    budget = card["experiments_run"] <= 3 and card["experiment_seconds"] <= 7200
    gate("experiment_budget", budget, f"{card['experiments_run']} experiments, {card['experiment_seconds']:.0f} s of experiment compute (cap 3 / 7,200 s)")

    ok = all(g["status"] == "passed" for g in gates)
    if card.get("verdict") != ("promote" if ok else "negative") or card.get("ok_to_submit") is not ok:
        raise ValueError("run card verdict contradicts the machine-adjudicated gates")
    readiness = {
        "schema_version": 1, "readiness_version": READINESS_VERSION, "run_id": card["run_id"],
        "ok_to_submit": ok, "decision": "OK TO SUBMIT" if ok else "DO NOT SUBMIT",
        "research_verdict": card["verdict"], "download_ok": bool(contract),
        "display_status": ("OK TO SUBMIT - all automated research gates passed; slot selection is a separate step" if ok
                           else "DO NOT SUBMIT - at least one automated gate failed"),
        "eligible_for_separate_slot_selector": ok,
        "primary_file": card["files"]["primary_zeros_outside"]["path"],
        "alternate_file": card["files"]["alternate_nan_outside"]["path"],
        "primary_sha256": z["sha256"], "alternate_sha256": n["sha256"],
        "submission_name": card["submission_name"], "submission_note": note,
        "gates": gates, "files": files,
        "leaderboard_expectation": card["leaderboard_expectation"],
        "slot_selection": "NOT performed here: a separate selector must choose within the current weekly cap",
        "organizer_score": None,
    }
    target = inside(selection["readiness"])
    if write:
        tmp = target.with_suffix(".partial.json")
        tmp.write_text(json.dumps(readiness, indent=2, allow_nan=False) + "\n")
        tmp.replace(target)
    elif not target.exists() or load(target) != readiness:
        raise ValueError("readiness receipt missing or stale; regenerate with --write")
    return readiness


def common_gates(report: Path, card: dict, gate) -> dict:
    """Holdout recomputation, canaries, preregistration binding and budget (shared by both outcomes)."""
    from gemsdoe30.holdout import spatial_bootstrap
    prereg = sha(report / "preregistration.md")
    amend = sha(report / "preregistration-e3.md")
    e1 = load(report / "results-e1.json")
    e3 = load(report / "results-e3.json")
    starts = [load(report / f"started-e{i}.json") for i in (1, 2, 3)]
    gate("preregistration_binding",
         all(s["preregistration_sha256"] == prereg for s in starts) and e1["preregistration_sha256"] == prereg
         and e3["preregistration_sha256"] == prereg and e3["amendment_sha256"] == amend and starts[2]["amendment_sha256"] == amend,
         "Frozen preregistration and E3 amendment hashes match every start receipt and result")
    blocks = load(report / "bootstrap-blocks-e1.json")["blocks"]
    recomputed = {e: spatial_bootstrap(blocks[e], candidate="lsm42", replicates=2000, seed=3071) for e in ("primary", "production")}
    close(e1["summary"], recomputed, "results-e1/summary")
    close(load(report / "results-e1.first-execution.json")["summary"], recomputed, "results-e1.first-execution/summary")
    p, q = recomputed["primary"], recomputed["production"]
    d = p["candidate_minus"]["core19"]
    gate("beats_current_holdout_best", d["value"] > 0 and d["ci95"][0] > 0 and q["candidate_minus"]["core19"]["value"] >= 0,
         f"HOLDOUT-DTI ({p['evaluator_version']}, 60,988 withheld positives): lsm42 - core19 = {d['value']:+.5f} "
         f"[{d['ci95'][0]:+.5f}, {d['ci95'][1]:+.5f}]; production-emission delta {q['candidate_minus']['core19']['value']:+.5f}")
    rows = [r for f in e1["feature_canaries"] for r in f["features"]]
    alarm = any(max(r["raw_auc"], 1 - r["raw_auc"], r["univariate_training_only_hgb_auc"],
                    1 - r["univariate_training_only_hgb_auc"]) > THRESH_AUC for r in rows)
    gate("single_feature_leakage_canaries", len(rows) == 168 and not alarm,
         f"{len(rows)} checks (42 inputs x 4 folds); max AUC "
         f"{max(max(r['raw_auc_either_direction'], r['univariate_training_only_hgb_auc']) for r in rows):.4f} <= 0.90")
    gate("experiment_budget", card["experiments_run"] <= 3 and card["experiment_seconds"] <= 7200,
         f"{card['experiments_run']} experiments, {card['experiment_seconds']:.0f} s of experiment compute (cap 3 / 7,200 s)")
    return recomputed


def verify_duplicate_stop(pointer, template, selection, card, report, *, write=False) -> dict:
    gates = []

    def gate(name, ok, detail):
        gates.append({"name": name, "status": "passed" if ok else "failed", "detail": detail})
        return ok

    common_gates(report, card, gate)
    surf = load(report / "novelty-surface.json")
    dots = load(report / "novelty-dots.json")
    gate("novelty_surface", surf["decision"].startswith("novelty-check-passed") and surf["max_spearman"] <= THRESH_RHO,
         f"max surface rank correlation {surf['max_spearman']:.3f} vs {surf['references_compared']} references (limit 0.90)")
    over = [r for r in dots["rows"] if (r.get("candidate_fraction_within_3px_of_reference") or 0) > THRESH_OVERLAP]
    sparse = [r for r in over if r["reference_dots"] <= 150000]
    recomputed_duplicate = bool(over) or any((r.get("spearman_full_footprint") or 0) > THRESH_RHO for r in dots["rows"])
    if dots["decision"] != ("duplicate-stop" if recomputed_duplicate else dots["decision"]) or not recomputed_duplicate:
        raise ValueError("duplicate-stop verdict is not supported by the stored dot-stage comparisons")
    if dots.get("candidate_values_sha256") != card["candidate_values_sha256"] or not card["run_id"].endswith(card["candidate_values_sha256"][:12]):
        raise ValueError("dot-stage receipt is not bound to the logged candidate identity")
    unique_sparse = {r["values_sha256"] for r in sparse}
    gate("novelty_dots", False,
         f"DUPLICATE: {len(unique_sparse)} distinct sparse registry rasters ({len(sparse)} files) hold >70% of the dots within 3 px "
         f"(max {max(r['candidate_fraction_within_3px_of_reference'] for r in sparse):.3f}); protocol stop")
    gate("file_contract", False, "No TIFF published: the protocol stops at a dot-stage duplicate before writing")
    readiness = {
        "schema_version": 1, "readiness_version": READINESS_VERSION, "run_id": card["run_id"],
        "ok_to_submit": False, "decision": "DO NOT SUBMIT", "research_verdict": "duplicate-stop",
        "download_ok": False, "eligible_for_separate_slot_selector": False,
        "display_status": "DO NOT SUBMIT - duplicate-stop at the dot stage; no TIFF published this session",
        "primary_file": None, "alternate_file": None,
        "stop_reason": card["stop_reason"], "gates": gates,
        "slot_selection": "NOT performed here", "organizer_score": None,
    }
    target = inside(selection["readiness"])
    if write:
        tmp = target.with_suffix(".partial.json")
        tmp.write_text(json.dumps(readiness, indent=2, allow_nan=False) + "\n")
        tmp.replace(target)
    elif not target.exists() or load(target) != readiness:
        raise ValueError("readiness receipt missing or stale; regenerate with --write")
    return readiness


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pointer", type=Path, default=ROOT / "docs/research/2026-10-25-lsm/current-run.json")
    ap.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--require-promote", action="store_true")
    a = ap.parse_args()
    try:
        result = verify(a.pointer, a.template, write=a.write)
    except (KeyError, ValueError, OSError) as exc:
        print(f"Verification FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({k: result.get(k) for k in ("run_id", "decision", "ok_to_submit", "primary_file", "submission_note", "stop_reason")}, indent=2))
    for g in result["gates"]:
        print(f"  [{g['status']:6s}] {g['name']}: {g['detail']}")
    return 2 if a.require_promote and not result["ok_to_submit"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
