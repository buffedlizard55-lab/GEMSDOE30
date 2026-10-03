#!/usr/bin/env python3
"""Fail-closed local GeoTIFF format validation against the official template."""

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
        "--portal-safe",
        action="store_true",
        help=(
            "require the upload-safe convention: every cell finite and in [0, 1], "
            "0.0 outside the template footprint (use this before any portal upload)"
        ),
    )
    args = parser.parse_args()
    try:
        from gemsdoe30.submission import validate_submission_file

        report = validate_submission_file(args.submission, args.template, portal_safe=args.portal_safe)
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
