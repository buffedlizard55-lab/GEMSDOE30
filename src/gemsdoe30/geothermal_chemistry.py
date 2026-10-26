"""GDX-1 label-free, site-weighted geothermal chemistry contrasts.

Never reads catalogue distance, site names, thermal classifications or labels.
Repeated records contribute one site-pixel median per *paired* contrast. Each
chemical map is normalized by its own observation effort, not by unrelated sites.
These are exploratory reservoir-cooling/mixing proxies, not vent/fault labels.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

VERSION = "gdx1-site-paired-effort-normalized-v1-20261026"
SIGMA_PX = 10.0
TRUNCATE = 3.0
GUARD_PX = 46
SUPPORT_PX = math.ceil(math.sqrt(2) * 30)  # 43 px; plus metric reach <46
MARK_NAMES = ("gdx_quartz_cooling", "gdx_cation_discordance", "gdx_shared_reservoir_excess")
EXTRA_NAMES = (
    "gdx_surface15_gradient", "gdx_surface17_gradient", "gdx_sampling_effort",
    *MARK_NAMES, *(name + "_observed" for name in MARK_NAMES),
)
# Indices in CORE_FEATURES + EXTRA_NAMES. Raw levels/coordinates are deliberately
# absent from the candidate, but are retained in the core19 comparison.
CANDIDATE_COLUMNS = (2, 4, 18, *range(19, 28))
EFFORT_COLUMNS = (2, 4, 18, 19, 20, 21)


def _temperature(value):
    try:
        x = float(value)
    except (ValueError, TypeError):
        return None
    return x if math.isfinite(x) and -50 <= x <= 400 else None


def site_marks(csv_path: Path, valid: np.ndarray):
    """Return deduplicated site effort and paired contrast impulses + provenance."""
    valid = np.asarray(valid, dtype=bool)
    if valid.ndim != 2 or not valid.any():
        raise ValueError("nonempty 2D footprint required")
    sites, marks = set(), [dict() for _ in MARK_NAMES]
    rejected, records = 0, 0
    required = {"row", "col", "temp_c", "geothermquartz_c", "geothermcat_c"}
    with Path(csv_path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not required <= set(reader.fieldnames or []):
            raise ValueError("missing required paired-chemistry CSV columns")
        for record in reader:
            records += 1
            try:
                r, c = int(record["row"]), int(record["col"])
            except (TypeError, ValueError):
                rejected += 1
                continue
            if not (0 <= r < valid.shape[0] and 0 <= c < valid.shape[1] and valid[r, c]):
                rejected += 1
                continue
            t, q, k = (_temperature(record[name]) for name in
                       ("temp_c", "geothermquartz_c", "geothermcat_c"))
            if all(x is None for x in (t, q, k)):
                continue
            key = (r, c)
            sites.add(key)
            pairs = (
                None if q is None or t is None else (q - t) / 100,
                None if q is None or k is None else (k - q) / 100,
                None if None in (t, q, k) else (min(q, k) - t) / 100,
            )
            for bucket, value in zip(marks, pairs):
                if value is not None:
                    bucket.setdefault(key, []).append(float(np.clip(value, -3, 3)))
    effort = np.zeros(valid.shape, dtype=np.float32)
    for key in sites:
        effort[key] = 1
    result = []
    for bucket in marks:
        values, observed = np.zeros_like(effort), np.zeros_like(effort)
        for key, samples in bucket.items():
            values[key] = np.median(samples)
            observed[key] = 1
        result.append((values, observed))
    if not sites or any(not obs.any() for _, obs in result):
        raise ValueError("each chemical contrast needs at least one observed site")
    return effort, result, {
        "records_read": records, "invalid_grid_records": rejected,
        "unique_observed_sites": len(sites),
        "sites_per_mark": {name: len(bucket) for name, bucket in zip(MARK_NAMES, marks)},
        "used_csv_fields": sorted(required),
        "forbidden_fields_read": [],
        "aggregation": "median of co-measured paired contrasts per unique grid cell, equal site weight",
    }


def smooth_marks(effort, marks, valid):
    """Compact-support, effort-normalized marked Gaussian fields + missingness."""
    valid = np.asarray(valid, dtype=bool)
    kwargs = dict(sigma=SIGMA_PX, truncate=TRUNCATE, mode="constant", cval=0.0)
    peak_scale = 2 * np.pi * SIGMA_PX ** 2
    density = gaussian_filter(np.asarray(effort, dtype=np.float32), **kwargs) * peak_scale
    out = {"gdx_sampling_effort": np.where(valid, np.log1p(density), np.nan).astype(np.float32)}
    for name, (values, observed) in zip(MARK_NAMES, marks, strict=True):
        denom = gaussian_filter(observed.astype(np.float32), **kwargs)
        numerator = gaussian_filter((values * observed).astype(np.float32), **kwargs)
        has_support = (denom * peak_scale) >= 0.05
        normalized = np.zeros(valid.shape, dtype=np.float32)
        np.divide(numerator, denom, out=normalized, where=has_support)
        out[name] = np.where(valid, normalized, np.nan).astype(np.float32)
        out[name + "_observed"] = np.where(valid, has_support, np.nan).astype(np.float32)
    return out


def local_gradient(array, valid):
    """Finite-normalized 100 m derivative proxy, without edge/sentinel leakage."""
    a = np.asarray(array, dtype=np.float32)
    ok = np.asarray(valid, dtype=bool) & np.isfinite(a) & (a > -1e30)
    kwargs = dict(sigma=1.0, truncate=2.0, mode="constant", cval=0)
    denominator = gaussian_filter(ok.astype(np.float32), **kwargs)
    smoothed = gaussian_filter(np.where(ok, a, 0), **kwargs)
    np.divide(smoothed, denominator, out=smoothed, where=denominator > 0)
    dy, dx = np.gradient(smoothed, 100.0)
    # radius sqrt(3^2+3^2) <=5 px covers blur then finite difference.
    safe = distance_transform_edt(np.pad(ok, 1, constant_values=False))[1:-1, 1:-1] > 5
    return np.where(safe, np.hypot(dx, dy), np.nan).astype(np.float32)


def build_features(base, valid, csv_path):
    """Produce the nine extra layers, with no label/catalogue argument at all."""
    effort, marks, receipt = site_marks(csv_path, valid)
    out = {
        "gdx_surface15_gradient": local_gradient(base[14], valid),
        "gdx_surface17_gradient": local_gradient(base[16], valid),
        **smooth_marks(effort, marks, valid),
    }
    assert set(out) == set(EXTRA_NAMES)
    receipt.update(transform_version=VERSION, support_px=SUPPORT_PX, guard_px=GUARD_PX,
                   sigma_px=SIGMA_PX, truncate=TRUNCATE, minimum_effective_sites=0.05)
    return out, receipt
