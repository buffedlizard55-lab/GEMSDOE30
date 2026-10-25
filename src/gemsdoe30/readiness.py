"""Machine-adjudicated research gates; no human-inspector flag or upload capability."""
from __future__ import annotations

import math
from typing import Any

READINESS_VERSION = "research-readiness-v2-parallel-evidence-20261025"
EXPECTED_FEATURES = frozenset({
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15", "cond_surf",
    "iso_grav_anom_hg", "det_elev_slope", "mag_texture", "rtp_texture", "texture_consensus",
})


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def interval(ci, low=0, high=1):
    return isinstance(ci, list) and len(ci) == 2 and all(number(v) for v in ci) and low <= ci[0] <= ci[1] <= high


def assess(card: dict, results: dict, *, format_passed: bool, hash_matches: bool,
           surface_audit: dict, dots_audit: dict, registry: dict) -> dict[str, Any]:
    """Separate file validity, research promotion and slot selection.

    Evidence absent from this function is unknown, never implicitly passed. A
    selector must separately verify current portal constraints and allocation;
    this function cannot approve or spend a competition slot.
    """
    gates = []

    def gate(name, status, detail):
        if status not in ("passed", "failed", "unknown"):
            raise ValueError("invalid gate status")
        gates.append({"name": name, "status": status, "detail": detail})

    gate("file_contract", "passed" if format_passed and hash_matches else "failed",
         "Reopened shared-writer GeoTIFF matches template; SHA-256 binds this decision to its exact bytes")
    summary = results.get("summary", {})
    arms = summary.get("arms", {})
    measures_valid = set(arms) == {"tdx6", "physics3", "core19"}
    for arm in arms.values():
        ci = arm.get("ci95", [])
        value = arm.get("value")
        n = arm.get("withheld_positives")
        measures_valid &= (arm.get("label") == "HOLDOUT-DTI" and number(value) and 0 <= value <= 1
                           and isinstance(n, int) and not isinstance(n, bool) and n > 0
                           and interval(ci))
    measures_valid &= len({a.get("withheld_positives") for a in arms.values()}) == 1
    measures_valid &= bool(summary.get("evaluator_version") and summary.get("protocol_version"))
    gate("labelled_holdout_evidence", "passed" if measures_valid else "failed",
         "HOLDOUT-DTI requires evaluator/protocol, withheld positives and spatial-bootstrap 95% CI")
    deltas = summary.get("candidate_minus", {})
    wins = set(deltas) == {"physics3", "core19"} and all(
        number(row.get("value")) and row["value"] > 0
        and interval(row.get("ci95"), -1, 1) and row["ci95"][0] > 0 for row in deltas.values())
    gate("paired_improvement", "passed" if wins else "failed",
         "Fixed candidate must improve both same-protocol controls with positive paired CI lower bound")
    features = results.get("feature_canaries", [])
    complete_canaries = (len(features) == 4 and {f.get("fold") for f in features} == set(range(4))
                         and all(len(fold.get("features", [])) == len(EXPECTED_FEATURES)
                                 and {r.get("feature") for r in fold["features"]} == EXPECTED_FEATURES
                                 for fold in features))
    alarm = False
    for fold in features:
        for row in fold.get("features", []):
            raw, uni = row.get("raw_auc"), row.get("univariate_training_only_hgb_auc")
            valid_auc = number(raw) and 0 <= raw <= 1 and number(uni) and 0 <= uni <= 1
            # Recompute, do not trust a mutable "alarm=false" boolean.
            if not valid_auc or max(raw, 1 - raw, uni, 1 - uni) > .90 or row.get("alarm_above_0_90") is not False:
                alarm = True
    gate("single_feature_leakage_canaries", "passed" if complete_canaries and not alarm else "failed",
         "All 22 raw/derived inputs tested alone in four folds; raw bidirectional and training-only univariate AUC")
    folds = results.get("folds", [])
    counts_valid = len(folds) == 4 and {f.get("fold") for f in folds} == set(range(4)) and all(
        isinstance(fold.get("dot_budget_each_arm"), int) and not isinstance(fold["dot_budget_each_arm"], bool)
        and fold["dot_budget_each_arm"] > 0
        and set(fold.get("arms", {})) == {"tdx6", "physics3", "core19"}
        and all(isinstance(arm.get("emitted_pixels"), int) and not isinstance(arm["emitted_pixels"], bool)
                and arm["emitted_pixels"] == fold["dot_budget_each_arm"] for arm in fold["arms"].values())
        for fold in folds)
    gate("count_matched_construction", "passed" if counts_valid else "failed",
         "All fixed arms must realize the same predeclared active-domain budget in every fold")
    observed = {}
    for stage, report in (("surface", surface_audit), ("dots", dots_audit)):
        rows = report.get("comparisons", [])
        duplicate = any(row.get("identical_inside_footprint")
                        or (number(row.get("spearman_full_footprint")) and row["spearman_full_footprint"] > .90)
                        or (stage == "dots" and number(row.get("candidate_fraction_within_3px_of_reference"))
                            and row["candidate_fraction_within_3px_of_reference"] > .70) for row in rows)
        defined = all(number(row.get("spearman_full_footprint")) and -1 <= row["spearman_full_footprint"] <= 1
                      and (stage != "dots" or (number(row.get("candidate_fraction_within_3px_of_reference"))
                           and 0 <= row["candidate_fraction_within_3px_of_reference"] <= 1)) for row in rows)
        known_clear = bool(rows) and not duplicate and defined and not report.get("errors")
        status = "failed" if duplicate else "passed" if known_clear else "unknown"
        gate(f"{stage}_observed_registry", status,
             f"{len(rows)} recorded comparisons; threshold rho >0.90 or dot overlap >0.70 is duplicate-stop")
        observed[stage] = {
            "registry_entries_compared": len(rows),
            "max_spearman": max((r["spearman_full_footprint"] for r in rows
                                  if number(r.get("spearman_full_footprint"))), default=None),
            "max_fraction_within_3px": max((r["candidate_fraction_within_3px_of_reference"] for r in rows
                                            if number(r.get("candidate_fraction_within_3px_of_reference"))), default=None),
            "status": status,
        }
    complete = registry.get("complete") is True and not registry.get("missing_evidence")
    gate("complete_parallel_registry", "passed" if complete else "unknown",
         "Nine-site public snapshots cannot attest all parallel rasters or missing original surfaces")
    assigned = card.get("externally_assigned_lane_verified")
    gate("assigned_lane", "passed" if assigned is True else "unknown",
         "Autonomous research continuation is not an externally supplied lane assignment")
    best = card.get("historical_best_rerun", {})
    best_verified = (best.get("verified") is True and best.get("evaluator_version") == summary.get("evaluator_version")
                     and best.get("protocol_version") == summary.get("protocol_version")
                     and best.get("candidate_beats_best_with_paired_ci") is True)
    gate("comparable_historical_best", "passed" if best_verified else "unknown",
         "Do not substitute an archived metric or a new comparator for a missing historical-best rerun")
    within_budget = (isinstance(card.get("experiments_run"), int) and not isinstance(card["experiments_run"], bool)
                     and 0 < card["experiments_run"] <= 3
                     and number(card.get("experimental_elapsed_seconds"))
                     and 0 < card["experimental_elapsed_seconds"] <= 7200)
    gate("experimental_budget", "passed" if within_budget else "failed", "At most three experiments / two experimental hours")
    named = (isinstance(card.get("submission_name"), str) and bool(card["submission_name"].strip())
             and isinstance(card.get("note"), str) and len(card["note"]) <= 140)
    gate("artifact_identity", "passed" if named else "failed", "Named artifact and note of at most 140 characters")
    promoted = all(row["status"] == "passed" for row in gates)
    return {"schema_version": 1, "readiness_version": READINESS_VERSION,
            "raster_sha256": card.get("raster_sha256"), "gates": gates,
            "observed_registry": observed,
            "download_ok": bool(format_passed and hash_matches and named),
            "research_verdict": "promote" if promoted else "negative",
            "eligible_for_separate_slot_selector": promoted,
            "submission_approved": False, "slot_selected": False,
            "display_status": "RESEARCH PROMOTED; SLOT NOT SELECTED" if promoted else "NOT APPROVED FOR SUBMISSION",
            "organizer_score": None, "organizer_acceptance_confirmed": False}
