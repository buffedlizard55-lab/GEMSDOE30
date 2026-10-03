#!/usr/bin/env python3
"""Fail-closed local GeoTIFF format validation against the available sample template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow this validation gate to work when called as documented:
# `python scripts/validate_submission.py ...` from an uninstalled checkout.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--json", type=Path, default=None, help="optional path for a machine-readable receipt")
    parser.add_argument(
        "--finite-all-cells",
        "--portal-safe",
        dest="finite_all_cells",
        action="store_true",
        help=(
            "strict local diagnostic: require every raster cell finite and in [0, 1]. "
            "This is not the published GEMS outside-value rule; the public spec requires "
            "null/NaN outside. --portal-safe is a legacy alias, not an acceptance claim."
        ),
    )
    args = parser.parse_args()
    try:
        from gemsdoe30.submission import validate_submission_file

        report = validate_submission_file(
            args.submission,
            args.template,
            require_finite_all_cells=args.finite_all_cells,
        )
        payload = report.to_dict()
        text = json.dumps(payload, indent=2)
        print(text)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(text + "\n", encoding="utf-8")
        return 0 if report.passed else 1
    except (ImportError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"FORMAT CHECK FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
