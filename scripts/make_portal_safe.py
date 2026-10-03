#!/usr/bin/env python3
"""Rewrite a NaN-outside candidate GeoTIFF as the portal-safe 0.0-outside variant.

Background: the DrivenData submission form reports "Predicted values must be in
range [0, 1]" when a raster fails its range check. An elementwise check treats
NaN cells as out of range even when they sit outside the scoring footprint, and
the official sample template itself encodes the outside area as NaN. A file with
finite 0.0 outside the footprint passes both elementwise and min/max style range
checks. This tool copies the in-footprint predictions unchanged, writes 0.0
outside, and emits a manifest proving the two files agree inside the footprint.

Usage:
    python scripts/make_portal_safe.py SOURCE.tif --output outputs/SOURCE-zeros.tif
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
    parser.add_argument("--note", default=None, help="paste-ready submission note")
    args = parser.parse_args()

    try:
        from gemsdoe30.submission import convert_to_portal_safe

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
        note = args.note or f"{run_name} | portal-safe zeros-outside variant | format check only, not a score"
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
        print(f"\nPortal-safe upload file: {output}")
        print(f"Note (optional): {note}")
        print("In-footprint predictions are identical to the source; only NaN cells were replaced by 0.0.")
        return 0
    except (ImportError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"PORTAL-SAFE CONVERSION BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
