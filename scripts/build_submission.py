#!/usr/bin/env python3
"""Convert a probability grid into a template-matched, locally checked GeoTIFF."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Keep the repository's command-line tools runnable directly from a checkout.
# Users should not need to install the package merely to build a validated TIFF.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _read_probabilities(path: Path):
    import numpy as np
    if path.suffix.lower() in {".tif", ".tiff"}:
        try:
            import rasterio
        except ImportError as exc:
            raise RuntimeError("rasterio is required to read GeoTIFF predictions") from exc
        with rasterio.open(path) as src:
            if src.count != 1:
                raise ValueError("input probability GeoTIFF must have one band")
            return src.read(1, masked=False)
    return np.load(path, mmap_mode="r")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probabilities", type=Path, required=True, help="2D .npy or one-band GeoTIFF")
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--name", default="candidate", help="short safe model/method label for the filename")
    parser.add_argument(
        "--note", "--comment", dest="note", default=None,
        help="short method/holdout comment for the submission form, at most 200 characters (alias: --comment)",
    )
    parser.add_argument(
        "--outside",
        choices=("zeros", "nan"),
        default="nan",
        help=(
            "outside-footprint convention: 'nan' (default, matches the published GEMS format); "
            "'zeros' writes finite 0.0 only for a nonstandard whole-array diagnostic and "
            "requires --allow-nonstandard-zero-outside"
        ),
    )
    parser.add_argument(
        "--allow-nonstandard-zero-outside",
        action="store_true",
        help="explicitly allow a zero-outside file that does not match the published null/NaN-outside format",
    )
    args = parser.parse_args()

    try:
        from gemsdoe30.submission import write_submission_file

        if args.outside == "zeros" and not args.allow_nonstandard_zero_outside:
            raise ValueError(
                "zero outside does not match the published GEMS null/NaN-outside format; "
                "pass --allow-nonstandard-zero-outside only for a diagnostic or after organizer clarification"
            )
        if not args.probabilities.is_file() or not args.template.is_file():
            raise FileNotFoundError("probability grid or sample template is missing")
        values = _read_probabilities(args.probabilities)
        slug = re.sub(r"[^A-Za-z0-9_-]+", "-", args.name).strip("-_")[:40] or "candidate"
        digest = hashlib.sha256(args.probabilities.read_bytes()).hexdigest()[:8]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        suffix = "-nan" if args.outside == "nan" else "-zeros"
        run_name = f"GEMSDOE30_{slug}_{timestamp}_{digest}{suffix}"
        note = args.note or f"{run_name} | method label: {slug}; holdout status: unverified"
        if len(note) > 200:
            raise ValueError("note must be no more than 200 characters")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = args.output_dir / f"{run_name}.tif"
        manifest = write_submission_file(
            values,
            args.template,
            output_path,
            note=note,
            run_name=run_name,
            outside_value=0.0 if args.outside == "zeros" else float("nan"),
        )
        print(json.dumps(manifest, indent=2))
        print(f"\nGeoTIFF file: {output_path.name}")
        print(f"Note (optional): {note}")
        print(f"Outside convention: {manifest['outside_convention']}")
        print(f"Published GEMS format compliant: {manifest['published_format_compliant']}")
        if not manifest['published_format_compliant']:
            print("WARNING: this zero-outside diagnostic does not meet the published null/NaN-outside requirement.")
        print("Gate: local format check only; no holdout promotion or competition score is implied.")
        return 0
    except (ImportError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"SUBMISSION BUILD BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
