"""Fail-closed GeoTIFF writer and validator for the GEMS submission contract."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SubmissionCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class SubmissionReport:
    path: str
    checks: tuple[SubmissionCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
        }


def validate_probability_values(values: Any, valid_mask: Any) -> None:
    """Raise on non-finite or out-of-range values inside the scoring footprint."""

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional raster dependency
        raise RuntimeError("NumPy is required to validate raster values") from exc
    arr = np.asarray(values)
    valid = np.asarray(valid_mask, dtype=bool)
    if arr.ndim != 2 or arr.shape != valid.shape:
        raise ValueError("probability values and valid_mask must be same-shaped 2D arrays")
    if not np.issubdtype(arr.dtype, np.number) or np.iscomplexobj(arr):
        raise ValueError("probability values must be real numeric values")
    inside = arr[valid]
    if not np.all(np.isfinite(inside)):
        raise ValueError("prediction has NaN or Inf inside the template footprint")
    if np.any((inside < 0.0) | (inside > 1.0)):
        lo, hi = float(inside.min()), float(inside.max())
        raise ValueError(f"prediction range [{lo}, {hi}] is outside [0, 1]")


def validate_portal_range(values: Any) -> None:
    """Raise unless *every* cell is finite and inside [0, 1].

    The DrivenData submission form reports "Predicted values must be in range
    [0, 1]" for files that fail its range check. A NaN anywhere in the raster
    (including outside the template footprint) fails an elementwise range test
    because every comparison against NaN is false, so a portal-safe file must
    hold finite, in-range values in every cell.
    """

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional raster dependency
        raise RuntimeError("NumPy is required to validate raster values") from exc
    arr = np.asarray(values)
    if arr.ndim != 2:
        raise ValueError("portal range check expects a 2D array")
    if not np.issubdtype(arr.dtype, np.number) or np.iscomplexobj(arr):
        raise ValueError("prediction values must be real numeric values")
    if not np.all(np.isfinite(arr)):
        bad = int(np.count_nonzero(~np.isfinite(arr)))
        raise ValueError(f"prediction has {bad} NaN/Inf cell(s); the portal rejects NaN values anywhere in the raster")
    if np.any((arr < 0.0) | (arr > 1.0)):
        lo, hi = float(arr.min()), float(arr.max())
        raise ValueError(f"prediction range [{lo}, {hi}] is outside [0, 1]")


def _rasterio_modules() -> tuple[Any, Any]:
    try:
        import numpy as np
        import rasterio
    except ImportError as exc:  # pragma: no cover - optional geospatial dependency
        raise RuntimeError(
            "rasterio and NumPy are required for GeoTIFF I/O. "
            "Install with `pip install -e '.[train]'`."
        ) from exc
    return np, rasterio


def valid_template_mask(template: Any, np: Any) -> Any:
    """Return the template's finite, non-nodata data footprint."""

    raw = template.read(1, masked=False)
    valid = np.isfinite(raw)
    nodata = template.nodata
    if nodata is not None:
        if np.isnan(nodata):
            valid &= ~np.isnan(raw)
        else:
            valid &= raw != nodata
    valid &= template.dataset_mask() != 0
    return valid


def validate_submission_file(
    submission_path: str | Path,
    template_path: str | Path,
    *,
    expected_epsg: int = 32611,
    expected_resolution_m: float = 100.0,
    portal_safe: bool = False,
) -> SubmissionReport:
    """Validate one single-band float32 output against the supplied official template.

    This checks local file structure and range; it cannot certify organizer-side
    acceptance, eligibility, scientific quality, or competition performance.

    Two outside-footprint conventions are supported. The default (``portal_safe=
    False``) requires null/NaN cells outside the template footprint, matching the
    official sample template's own encoding. ``portal_safe=True`` instead requires
    *finite* in-range values everywhere (the writer uses 0.0 outside) and adds a
    strict whole-raster ``[0, 1]`` check, because the submission form's range
    error is triggered by NaN cells anywhere in the file, including outside the
    footprint. Upload the portal-safe variant when in doubt.
    """

    np, rasterio = _rasterio_modules()
    submission_path = Path(submission_path)
    template_path = Path(template_path)
    if not submission_path.is_file():
        raise FileNotFoundError(submission_path)
    if not template_path.is_file():
        raise FileNotFoundError(template_path)

    checks: list[SubmissionCheck] = []
    with rasterio.open(template_path) as template, rasterio.open(submission_path) as output:
        valid = valid_template_mask(template, np)
        out_data = output.read(1, masked=False) if output.count >= 1 else np.empty((0, 0))
        template_data = template.read(1, masked=False) if template.count >= 1 else np.empty((0, 0))

        checks.append(SubmissionCheck("template_single_band", template.count == 1, f"count={template.count}"))
        checks.append(SubmissionCheck("single_band", output.count == 1, f"count={output.count}"))
        checks.append(SubmissionCheck("float32", output.dtypes == ("float32",), f"dtypes={output.dtypes}"))
        checks.append(SubmissionCheck("epsg", output.crs is not None and output.crs.to_epsg() == expected_epsg, f"crs={output.crs}"))
        checks.append(SubmissionCheck("template_epsg", template.crs is not None and template.crs.to_epsg() == expected_epsg, f"crs={template.crs}"))
        checks.append(SubmissionCheck("shape_matches_template", (output.height, output.width) == (template.height, template.width), f"output={(output.height, output.width)} template={(template.height, template.width)}"))
        checks.append(SubmissionCheck("transform_matches_template", output.transform == template.transform, f"output={output.transform} template={template.transform}"))

        transform = output.transform
        resolution_ok = (
            abs(transform.a - expected_resolution_m) < 1e-6
            and abs(transform.e + expected_resolution_m) < 1e-6
            and abs(transform.b) < 1e-9
            and abs(transform.d) < 1e-9
        )
        checks.append(SubmissionCheck("100m_north_up_grid", resolution_ok, f"transform={transform}"))

        grid_matches = out_data.shape == valid.shape
        if grid_matches:
            try:
                validate_probability_values(out_data, valid)
                range_detail = (
                    f"valid_pixels={int(valid.sum())} min={float(out_data[valid].min()) if valid.any() else 'n/a'} "
                    f"max={float(out_data[valid].max()) if valid.any() else 'n/a'}"
                )
                range_passed = bool(valid.any())
            except ValueError as exc:
                range_detail = str(exc)
                range_passed = False
        else:
            range_detail = f"output_shape={out_data.shape} template_shape={valid.shape}"
            range_passed = False
        checks.append(SubmissionCheck("finite_and_in_range_inside_footprint", range_passed, range_detail))

        if grid_matches:
            outside = ~valid
            if outside.any():
                outside_values = out_data[outside]
                if portal_safe:
                    outside_ok = bool(np.all(np.isfinite(outside_values)) and np.all((outside_values >= 0.0) & (outside_values <= 1.0)))
                    zeros = int(np.count_nonzero(outside_values == 0.0))
                    outside_detail = (
                        f"outside_pixels={int(outside.sum())}; finite [0,1] required "
                        f"(zeros={zeros}); convention: 0.0 outside"
                    )
                else:
                    outside_is_nan = np.isnan(outside_values)
                    nodata = output.nodata
                    if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
                        outside_is_nan |= outside_values == nodata
                    outside_ok = bool(np.all(outside_is_nan))
                    outside_detail = f"outside_pixels={int(outside.sum())}; null/NaN/nodata required"
            else:
                outside_ok = True
                outside_detail = "template has no outside-footprint pixels"
        else:
            outside_ok = False
            outside_detail = "grid shape mismatch prevents footprint comparison"
        if portal_safe:
            checks.append(SubmissionCheck("finite_in_range_outside_footprint", outside_ok, outside_detail))
        else:
            checks.append(SubmissionCheck("null_outside_template_footprint", outside_ok, outside_detail))

        if grid_matches:
            try:
                validate_portal_range(out_data)
                portal_detail = f"all_pixels={out_data.size} finite and in [0, 1]"
                portal_passed = True
            except ValueError as exc:
                portal_detail = str(exc)
                portal_passed = False
        else:
            portal_detail = "grid shape mismatch prevents whole-raster range check"
            portal_passed = False
        checks.append(
            SubmissionCheck(
                "portal_range_all_pixels" if portal_safe else "portal_range_all_pixels_informational",
                portal_passed if portal_safe else True,
                portal_detail if portal_safe else f"advisory: {portal_detail}",
            )
        )

        template_data_ok = template_data.shape == valid.shape
        checks.append(SubmissionCheck("template_readable", template_data_ok, f"shape={template_data.shape}"))

    return SubmissionReport(str(submission_path), tuple(checks))


def _sha256_array(array: Any) -> str:
    return hashlib.sha256(memoryview(array).cast("B")).hexdigest()


def write_submission_file(
    probabilities: Any,
    template_path: str | Path,
    output_path: str | Path,
    *,
    note: str,
    run_name: str,
    metadata_path: str | Path | None = None,
    outside_value: float = float("nan"),
) -> dict[str, Any]:
    """Write predictions on the template grid and emit a provenance sidecar.

    The function never clips, rescales, or silently repairs in-footprint values.
    It fails before writing if in-footprint predictions are non-finite or outside
    [0, 1]. Outside the valid template footprint it writes ``outside_value``:

    * ``nan`` (default) matches the official sample template's own encoding and
      sets the band nodata tag to NaN.
    * ``0.0`` produces the portal-safe variant: every cell finite and in [0, 1]
      with no nodata tag, which satisfies whole-raster range checks of the kind
      behind the form error "Predicted values must be in range [0, 1]".
    """

    np, rasterio = _rasterio_modules()
    outside = float(outside_value)
    if not (math.isnan(outside) or outside == 0.0):
        raise ValueError("outside_value must be NaN (template convention) or 0.0 (portal-safe convention)")
    portal_safe = not math.isnan(outside)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as template:
        if template.count != 1:
            raise ValueError("submission template must have exactly one band")
        valid = valid_template_mask(template, np)
        raw_probs = np.asarray(probabilities)
        if raw_probs.ndim != 2 or raw_probs.shape != (template.height, template.width):
            raise ValueError(
                f"probability shape {raw_probs.shape} does not match template {(template.height, template.width)}"
            )
        # Check before float32 conversion too; a slightly out-of-range float64 can
        # round back to exactly 0 or 1 and otherwise evade the portal-range guard.
        validate_probability_values(raw_probs, valid)
        probs = raw_probs.astype(np.float32)
        validate_probability_values(probs, valid)
        output = np.full(probs.shape, outside, dtype=np.float32)
        output[valid] = probs[valid]

        profile = template.profile.copy()
        profile.update(
            driver="GTiff",
            count=1,
            dtype="float32",
            compress="deflate",
            predictor=3,
        )
        if portal_safe:
            profile.update(nodata=None)
        else:
            profile.update(nodata=np.nan)
        # Keep the template's CRS, transform, width, and height unchanged.
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(output, 1)
            dst.set_band_description(1, "fault probability")
            dst.update_tags(
                AREA_OR_POINT="Area",
                GEMS_RUN_NAME=run_name,
                GEMS_NOTE=note,
                GEMS_METRIC="distance-weighted Tversky; R=300 m; alpha=0.2; beta=0.8",
                GEMS_OUTSIDE_CONVENTION="0.0 portal-safe" if portal_safe else "NaN template-conformant",
            )

    report = validate_submission_file(output_path, template_path, portal_safe=portal_safe)
    if not report.passed:
        failed = [check.name for check in report.checks if not check.passed]
        raise ValueError(f"written GeoTIFF failed local format checks: {', '.join(failed)}")

    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 2,
        "run_name": run_name,
        "note": note,
        "output_file": output_path.name,
        "output_sha256": digest,
        "prediction_array_sha256": _sha256_array(np.ascontiguousarray(probs)),
        "outside_convention": "0.0 portal-safe (finite everywhere)" if portal_safe else "NaN template-conformant",
        "template_file": str(Path(template_path)),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "format_validation": report.to_dict(),
        "performance_status": "unscored; format validation is not a score",
    }
    manifest_file = Path(metadata_path) if metadata_path else output_path.with_suffix(".json")
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def convert_to_portal_safe(
    source_path: str | Path,
    template_path: str | Path,
    output_path: str | Path,
    *,
    note: str,
    run_name: str,
    metadata_path: str | Path | None = None,
) -> dict[str, Any]:
    """Rewrite an existing NaN-outside raster as the portal-safe 0.0-outside variant.

    Prediction values inside the template footprint are copied unchanged and the
    manifest records SHA-256 digests for both files plus proof that the
    in-footprint arrays are identical. Fails closed on out-of-range or non-finite
    values inside the footprint.
    """

    np, rasterio = _rasterio_modules()
    source_path = Path(source_path)
    output_path = Path(output_path)
    with rasterio.open(source_path) as source, rasterio.open(template_path) as template:
        if source.count != 1:
            raise ValueError("source raster must have exactly one band")
        if (source.height, source.width) != (template.height, template.width):
            raise ValueError("source raster grid does not match the template")
        if source.transform != template.transform:
            raise ValueError("source raster transform does not match the template")
        valid = valid_template_mask(template, np)
        values = np.asarray(source.read(1, masked=False), dtype=np.float32)
    validate_probability_values(values, valid)
    manifest = write_submission_file(
        values,
        template_path,
        output_path,
        note=note,
        run_name=run_name,
        metadata_path=metadata_path,
        outside_value=0.0,
    )
    with rasterio.open(source_path) as source, rasterio.open(output_path) as rewritten:
        src_vals = source.read(1, masked=False)
        dst_vals = rewritten.read(1, masked=False)
    same_inside = bool(np.array_equal(src_vals[valid], dst_vals[valid]))
    if not same_inside:
        raise ValueError("portal-safe conversion changed an in-footprint value; refusing to publish")
    manifest["source_file"] = source_path.name
    manifest["source_sha256"] = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    manifest["in_footprint_identical_to_source"] = True
    manifest_file = Path(metadata_path) if metadata_path else output_path.with_suffix(".json")
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
