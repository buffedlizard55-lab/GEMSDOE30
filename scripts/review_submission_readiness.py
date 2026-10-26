#!/usr/bin/env python3
"""Dated, read-only artifact review. Never generates predictions or selects a slot."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from gemsdoe30.submission import validate_submission_file

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (
    ("H-NEARSPLAY", "docs/research/nearsplay/run-card.json", "docs/research/nearsplay/readiness.json",
     "docs/downloads/GEMSDOE30-nearslay-annulus-d3-offcat-20261025T235837Z-662af003-nan.tif", "submission_sha256"),
    ("MSDB-1v2", "docs/research/msdb-piedmont/run-card.json", "docs/research/msdb-piedmont/readiness.json",
     "docs/downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif", "raster_sha256"),
)


def adjudicate(*, format_passed, hash_matches, readiness):
    """Local download eligibility is not evidence of complete scientific validation."""
    gates = {g["name"]: g["status"] for g in readiness.get("gates", [])}
    return {
        "download_ok": format_passed is True and hash_matches is True,
        "recorded_research_verdict": readiness.get("research_verdict", "unknown"),
        "recorded_failed_or_unknown_gates": {k: v for k, v in gates.items() if v != "passed"},
        # These are absent in the current public evidence; do not infer them
        # from a matched-control win, a format check, or a public registry subset.
        "assigned_lane_verified": False,
        "complete_parallel_registry_verified": False,
        "identical_protocol_current_best_beaten": False,
        "submission_approved": False,
        "slot_selected": False,
        "decision": "DO NOT SUBMIT: full scientific and selector gates unresolved",
    }


def review(root=ROOT):
    artifacts = []
    for label, card_path, readiness_path, raster_path, hash_key in ARTIFACTS:
        card = json.loads((root / card_path).read_text())
        readiness = json.loads((root / readiness_path).read_text())
        row = {"name": label, "file": raster_path, "card": card_path,
               "readiness": readiness_path, "validation_errors": []}
        try:
            with (root / raster_path).open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            report = validate_submission_file(root / raster_path, root / "data/raw/sample_submission.tif")
            row.update(sha256=digest, format_passed=bool(report.passed),
                       hash_matches=digest == card.get(hash_key))
        except (OSError, ValueError) as exc:
            row.update(sha256=None, format_passed=False, hash_matches=False)
            row["validation_errors"].append(str(exc))
        row.update(adjudicate(format_passed=row["format_passed"], hash_matches=row["hash_matches"], readiness=readiness))
        artifacts.append(row)
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Current local TIFF bytes and archived receipts only; no model/holdout rerun or live leaderboard read",
        "artifacts": artifacts,
        "new_experiments": 0,
        "new_tiff_generated": False,
        "verdict": "negative",
        "submission_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(review(), indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
