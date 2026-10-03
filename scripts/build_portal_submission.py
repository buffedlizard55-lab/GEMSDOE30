#!/usr/bin/env python3
"""Build a range-error-hardened GEMS submission GeoTIFF from any prediction source.

Why this script exists
----------------------
The DrivenData GEMS portal rejects an upload with ``Predicted values must be in
range [0, 1]`` when the raster contains anything that is not a finite float in
``[0, 1]``.  Two independent, locally measured mechanisms produce that condition
on this competition's own data (verified 2026-10-03 against the SHA-256-pinned
owner mirrors):

1. ``training_features.tif`` stores its nodata as the float32 sentinel
   ``-3.4028234663852886e+38``.  Every one of its 19 bands carries that
   sentinel on **3,061 pixels inside the scoring footprint** (band 6 ``tc``:
   3,073).  Any pipeline that forgets to sanitise it emits values near
   -3.4e38 -- wildly outside ``[0, 1]``.
2. The feature raster's own valid mask is *smaller* than the template's: band 1
   calls 5,165,852 pixels valid against the template's 5,167,373, i.e. **3,061
   template-valid pixels are sentinel in band 1**.  A footprint mask derived
   from a feature band therefore leaves those 3,061 scored pixels as NaN.

Both are eliminated here by construction: the footprint is taken *only* from
``np.isfinite(sample_submission.tif)``, every value is sanitised and clipped
before writing, and the default ``--outside zeros`` mode writes a raster in
which **all 12,279,160 cells** are finite floats in ``[0, 1]`` with no NaN
anywhere and no nodata tag.

Is the all-finite variant legal?
--------------------------------
Yes, on two independently verified grounds:

* The organiser's own reference solution
  (``drivendataorg/gems-prize-reference-solution``, notebook cell
  "Save final prediction in required format") writes its example prediction
  with ``rasterio.open(..., "w", driver="GTiff", count=1, dtype=..., crs=...,
  transform=...)`` and **never sets a nodata value**; its sigmoid output is
  finite everywhere.
* The owner's own submission ledger records
  ``r7-nms3-dem10-scarp_0c9199f14e62`` = 0.1294 and
  ``r7-nms3-dem10-scarp_0c9199f14e62_allfinite`` = 0.1294 -- the identical
  score for the NaN-outside and all-finite encodings of the same prediction.
  Cells outside the template footprint therefore carry no scoring weight.

``--outside nan`` remains available for a literal reading of the published
specification ("data outside the bounds is null or nan").  Both variants are
validated; only the all-finite one is immune to a whole-raster range check.

The script fails closed: any failed assertion or validation check exits
non-zero and writes no sidecar claiming success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

FLOAT32_SENTINEL = -3.4028234663852886e38


def _sha256(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build(
    source: Path,
    template: Path,
    out_path: Path,
    *,
    run_name: str,
    note: str,
    outside: str = "zeros",
    sidecar: Path | None = None,
    json_out: Path | None = None,
) -> dict:
    """Sanitise ``source`` onto the template grid and write a portal-safe GeoTIFF."""

    import numpy as np
    import rasterio

    from gemsdoe30.submission import validate_submission_file

    if outside not in ("zeros", "nan"):
        raise ValueError("outside must be 'zeros' or 'nan'")

    source = Path(source)
    template = Path(template)
    out_path = Path(out_path)
    for required in (source, template):
        if not required.is_file():
            raise FileNotFoundError(required)

    with rasterio.open(template) as tpl:
        tpl_data = tpl.read(1, masked=False)
        footprint = np.isfinite(tpl_data)
        profile = tpl.profile.copy()
        transform = tpl.transform
        crs = tpl.crs
        shape = (tpl.height, tpl.width)
        template_sha = _sha256(template)

    with rasterio.open(source) as src:
        raw = src.read(1, masked=False)
        if (src.height, src.width) != shape:
            raise ValueError(
                f"source grid {(src.height, src.width)} != template grid {shape}"
            )
        source_sha = _sha256(source)

    # --- sanitise: the exact step whose absence causes the portal range error ---
    sentinel_hits_in_footprint = int(np.count_nonzero((raw == np.float32(FLOAT32_SENTINEL)) & footprint))
    nonfinite_in_footprint_before = int(np.count_nonzero(~np.isfinite(raw[footprint])))
    cleaned = np.nan_to_num(
        np.asarray(raw, dtype=np.float64), nan=0.0, posinf=1.0, neginf=0.0
    )
    clipped = np.clip(cleaned, 0.0, 1.0)
    clipped[~footprint] = np.nan if outside == "nan" else 0.0

    output = clipped.astype(np.float32)

    # --- hard pre-write assertions -------------------------------------------
    if output.shape != shape:
        raise AssertionError("output shape drifted from template shape")
    inside = output[footprint]
    if not np.all(np.isfinite(inside)):
        raise AssertionError("non-finite value survived sanitisation inside footprint")
    if inside.size and (float(inside.min()) < 0.0 or float(inside.max()) > 1.0):
        raise AssertionError("in-footprint value outside [0, 1] survived sanitisation")
    if outside == "zeros":
        if not np.all(np.isfinite(output)):
            raise AssertionError("all-finite mode produced a non-finite cell")
        if float(output.min()) < 0.0 or float(output.max()) > 1.0:
            raise AssertionError("all-finite mode produced a value outside [0, 1]")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        width=shape[1],
        height=shape[0],
        crs=crs,
        transform=transform,
        compress="lzw",
        tiled=False,
        nodata=None if outside == "zeros" else float("nan"),
    )
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)

    # Write to a sibling temp path and only move it into place once every gate
    # has passed. Writing straight to `out_path` would leave a rejected raster
    # sitting in the published downloads directory -- a fail-open bug in a
    # script whose entire purpose is to fail closed.
    staging = out_path.with_name(out_path.name + ".partial")
    try:
        return _stage_validate_and_publish(
            staging=staging,
            out_path=out_path,
            profile=profile,
            output=output,
            inside=inside,
            footprint=footprint,
            shape=shape,
            crs=crs,
            transform=transform,
            source=source,
            source_sha=source_sha,
            template=template,
            template_sha=template_sha,
            run_name=run_name,
            note=note,
            outside=outside,
            sidecar=sidecar,
            json_out=json_out,
            sentinel_hits_in_footprint=sentinel_hits_in_footprint,
            nonfinite_in_footprint_before=nonfinite_in_footprint_before,
            np=np,
            validate_submission_file=validate_submission_file,
        )
    finally:
        # Never leave a rejected or half-written raster in the published
        # downloads directory, whatever the reason for stopping.
        staging.unlink(missing_ok=True)


def _stage_validate_and_publish(
    *,
    staging: Path,
    out_path: Path,
    profile: dict,
    output,
    inside,
    footprint,
    shape,
    crs,
    transform,
    source: Path,
    source_sha: str,
    template: Path,
    template_sha: str,
    run_name: str,
    note: str,
    outside: str,
    sidecar: Path | None,
    json_out: Path | None,
    sentinel_hits_in_footprint: int,
    nonfinite_in_footprint_before: int,
    np,
    validate_submission_file,
) -> dict:
    """Write to ``staging``, gate it, and only then publish it as ``out_path``."""

    import rasterio

    with rasterio.open(staging, "w", **profile) as dst:
        dst.write(output, 1)

    # --- re-read from disk and validate the bytes we actually shipped ---------
    with rasterio.open(staging) as chk:
        reread = chk.read(1, masked=False)
    if not np.array_equal(reread[footprint], inside.astype(np.float32)):
        raise AssertionError("round-trip through disk changed in-footprint values")

    whole_finite = bool(np.all(np.isfinite(reread)))
    whole_in_range = bool(
        whole_finite and float(reread.min()) >= 0.0 and float(reread.max()) <= 1.0
    )

    published = validate_submission_file(staging, template, require_finite_all_cells=False)
    strict = validate_submission_file(staging, template, require_finite_all_cells=True)

    active_pixels = int(np.count_nonzero(inside > 0))
    report = {
        "schema_version": 4,
        "artifact_type": "portal-safe submission GeoTIFF",
        "run_name": run_name,
        "drivendata_note": note,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "built_by": "scripts/build_portal_submission.py",
        "outside_convention": outside,
        "source_file": str(source),
        "source_sha256": source_sha,
        "template_file": str(template),
        "template_sha256": template_sha,
        "output_file": str(out_path),
        "output_sha256": _sha256(staging),
        "output_bytes": staging.stat().st_size,
        "grid": {
            "shape": list(shape),
            "epsg": crs.to_epsg() if crs is not None else None,
            "transform": list(transform)[:6],
            "resolution_m": [transform.a, -transform.e],
            "total_cells": int(output.size),
            "footprint_cells": int(footprint.sum()),
            "outside_footprint_cells": int((~footprint).sum()),
        },
        "value_guarantees": {
            "all_cells_finite": whole_finite,
            "all_cells_in_0_1": whole_in_range,
            "nan_cells_anywhere": int(np.count_nonzero(~np.isfinite(reread))),
            "in_footprint_min": float(inside.min()) if inside.size else None,
            "in_footprint_max": float(inside.max()) if inside.size else None,
            "active_prediction_pixels_gt0": active_pixels,
        },
        "sanitisation": {
            "float32_sentinel_hits_inside_footprint": sentinel_hits_in_footprint,
            "nonfinite_inside_footprint_before": nonfinite_in_footprint_before,
            "policy": "nan->0.0, +inf->1.0, -inf->0.0, then clip to [0, 1]",
        },
        "range_error_immunity": {
            "immune_to_whole_raster_range_check": outside == "zeros" and whole_in_range,
            "basis": (
                "every one of the %d cells is a finite float32 in [0, 1], so no "
                "range check -- whole-raster or footprint-only -- can fire" % output.size
            ),
        },
        "validation_published_format": published.to_dict(),
        "validation_all_cells_finite": strict.to_dict(),
        "caveats": [
            "Local format validation is not organiser acceptance.",
            "No competition score is claimed for this artifact by this script.",
            "Template/feature rasters are SHA-256-pinned owner mirrors, not organiser-authenticated downloads.",
        ],
    }

    # --- mode-appropriate gate -----------------------------------------------
    # `zeros` and `nan` encode the outside-footprint cells differently, so the
    # two validators cannot both pass.  Each mode is gated on the contract that
    # actually applies to it, and the mismatch is recorded explicitly rather
    # than silently ignored.
    published_failures = [c.name for c in published.checks if not c.passed]
    strict_failures = [c.name for c in strict.checks if not c.passed]
    report["validation_published_format_failures"] = published_failures
    report["validation_all_cells_finite_failures"] = strict_failures

    if outside == "zeros":
        if not whole_in_range:
            raise AssertionError("all-finite artifact failed its own whole-raster guarantee")
        if strict_failures:
            raise AssertionError(f"all-finite artifact failed strict validation: {strict_failures}")
        # The only published-format clause a zero-outside file can legitimately
        # fail is the null/NaN-outside encoding.  Anything else is a real defect.
        unexpected = [name for name in published_failures if name != "null_outside_template_footprint"]
        if unexpected:
            raise AssertionError(f"unexpected published-format failures: {unexpected}")
        report["outside_encoding_tradeoff"] = (
            "zero-outside deliberately does not satisfy the published "
            "'data outside the bounds is null or nan' clause; it is chosen "
            "because it is immune to the portal's [0, 1] range check and the "
            "owner ledger shows an identical score for the two encodings "
            "(0.1294 vs 0.1294). The failing clause is "
            f"{published_failures}."
        )
    else:
        if published_failures:
            raise AssertionError(f"NaN-outside artifact failed published-format validation: {published_failures}")

    # --- every gate passed: publish the staged bytes --------------------------
    staging.replace(out_path)
    published_sha = _sha256(out_path)
    if published_sha != report["output_sha256"]:
        raise AssertionError("publish step changed the artifact bytes")

    # The validators ran against the staging path; record the published one.
    for key in ("validation_published_format", "validation_all_cells_finite"):
        report[key]["path"] = str(out_path)
    report["published_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report["output_bytes"] = out_path.stat().st_size

    text = json.dumps(report, indent=2)
    if sidecar is not None:
        Path(sidecar).parent.mkdir(parents=True, exist_ok=True)
        Path(sidecar).write_text(text + "\n", encoding="utf-8")
    if json_out is not None:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="prediction raster on the template grid")
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, default=None, help="JSON receipt written next to the GeoTIFF")
    parser.add_argument("--json", type=Path, default=None, help="additional JSON receipt path")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--note", required=True, help="short DrivenData submission note")
    parser.add_argument(
        "--outside",
        choices=("zeros", "nan"),
        default="zeros",
        help="outside-footprint encoding; 'zeros' (default) is range-error-immune",
    )
    args = parser.parse_args()
    try:
        build(
            args.source,
            args.template,
            args.out,
            run_name=args.run_name,
            note=args.note,
            outside=args.outside,
            sidecar=args.sidecar,
            json_out=args.json,
        )
    except (AssertionError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
