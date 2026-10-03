#!/usr/bin/env python3
"""Create a nonstandard zero-outside diagnostic copy of a NaN-outside GeoTIFF.

The public GEMS problem description requires null/NaN outside the data bounds.
This legacy utility is retained only to test a strict whole-array finite-range
hypothesis; its output is not compliant with that published outside-value rule
unless the organizer explicitly confirms otherwise. It copies in-footprint
predictions unchanged and records both validation results in a sidecar.

Usage (requires an explicit acknowledgement):
    python scripts/make_portal_safe.py SOURCE.tif --confirm-nonstandard-outside
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Run from an uninstalled checkout exactly as documented (`python scripts/<name>.py`):
# make the in-repo package importable without `pip install -e .`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="NaN-outside GeoTIFF to convert")
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--output", type=Path, default=None, help="default: SOURCE stem + '-zeros.tif'")
    parser.add_argument("--name", default=None, help="run-name label; default derives from the source filename")
    parser.add_argument("--note", default=None, help="short method note for the diagnostic artifact")
    parser.add_argument(
        "--confirm-nonstandard-outside",
        action="store_true",
        help="acknowledge that zero outside does not match the published null/NaN-outside requirement",
    )
    args = parser.parse_args()

    try:
        from gemsdoe30.submission import convert_to_portal_safe

        if not args.confirm_nonstandard_outside:
            raise ValueError(
                "this zero-outside diagnostic conflicts with the published GEMS format; "
                "pass --confirm-nonstandard-outside only for a diagnostic or after organizer clarification"
            )
        if not args.source.is_file():
            raise FileNotFoundError(args.source)
        if not args.template.is_file():
            raise FileNotFoundError(args.template)
        output = args.output
        if output is None:
            output = args.source.with_name(args.source.stem + "-zeros.tif")
        label = args.name or re.sub(r"[^A-Za-z0-9_-]+", "-", args.source.stem).strip("-_")[:60] or "candidate"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        run_name = f"{label}_{timestamp}"
        note = args.note or f"{run_name} | nonstandard zero-outside diagnostic | not a submission recommendation"
        if len(note) > 200:
            raise ValueError("note must be no more than 200 characters")
        manifest = convert_to_portal_safe(
            args.source,
            args.template,
            output,
            note=note,
            run_name=run_name,
        )
        print(json.dumps(manifest, indent=2))
        print(f"\nNonstandard diagnostic TIFF: {output}")
        print(f"Note (optional): {note}")
        print("In-footprint predictions are unchanged; only outside NaNs were replaced by 0.0.")
        print("WARNING: the public GEMS specification requires null/NaN outside; this is not an upload recommendation.")
        return 0
    except (ImportError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ZERO-OUTSIDE DIAGNOSTIC BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
