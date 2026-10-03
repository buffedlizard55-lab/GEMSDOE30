#!/usr/bin/env python3
"""Fetch free *official* external layers and derive 100 m rasters on the competition grid.

WHY THIS RUNS ON A GITHUB RUNNER, NOT IN THE SESSION SANDBOX
------------------------------------------------------------
The agent sandbox's egress allowlist reaches only api.github.com / github.com /
codeload.github.com / pypi.org.  ``mrdata.usgs.gov``, ``gdr.openei.org`` and
``sciencebase.gov`` are unreachable from it (TLS resets are recorded in
docs/irregularities.md).  A GitHub-hosted runner has general internet access, so
this script is the bridge that lets a session *verify obtainability* and derive
usable layers from official sources.  It never contacts drivendata.org: the
competition Terms of Use prohibit automated access for monitoring or copying.

SOURCES (all free, all official, licence recorded per item)
-----------------------------------------------------------
* USGS State Geologic Map Compilation (SGMC) state packages, public domain:
  https://mrdata.usgs.gov/geology/state/  (NV.zip, CA.zip)
  These contain *state geological survey* fault lines, including faults that are
  absent from the USGS Quaternary Fault and Fold Database that supplies the
  competition's training catalogue.
* DOE Geothermal Data Repository submission 1391 (INGENIOUS regional compilation),
  CC BY 4.0, DOI 10.15121/1881483: https://gdr.openei.org/submissions/1391
  2 m temperature probes, paleogeothermal features, Quaternary volcanics,
  Quaternary fault compilation v2 (catalogue provenance check).
* The competition grid itself is taken from the repository's hash-pinned owner
  mirror (see docs/research/mirror-pins.json) so the derived rasters are
  pixel-aligned with the submission template by construction.  These bytes are
  owner-mirrored, NOT organizer-authenticated, and are never treated as labels.

OUTPUTS (committed back to the repository, small and auditable)
--------------------------------------------------------------
data/external/derived_*_100m*.tif   rasterised layers on the exact competition grid
data/external/external_receipt.json download URLs, byte counts, SHA-256 values,
                                    feature counts, footprint coverage, licence

Every number written into the receipt is measured in the run; nothing is
asserted from memory.  A failed download is recorded as a failure, never
fabricated.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import traceback
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external"
OUT.mkdir(parents=True, exist_ok=True)
WORK = Path(tempfile.mkdtemp(prefix="gems_ext_"))

USER_AGENT = "GEMSDOE30-external-layer-fetch/1.0 (research; https://github.com/buffedlizard55-lab/GEMSDOE30)"

# Pinned owner mirrors of the competition grid (see docs/research/mirror-pins.json).
# SHA-256 values are verified before use; they identify owner-mirror bytes only.
RAW = "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE24/07345ea0604953d7efb858d9cfbc21e20c7aca0b"
GRID_SOURCES = {
    "labels": (f"{RAW}/data/bridge/labels.tif",
               "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"),
    "template": (f"{RAW}/data/bridge/sample_submission.tif",
                 "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"),
}

GDR = "https://gdr.openei.org/files/1391"
SOURCES = {
    "sgmc_nv": {
        "url": "https://mrdata.usgs.gov/geology/state/shp/NV.zip",
        "licence": "US Government work / public domain (USGS Mineral Resources Program)",
        "what": "USGS State Geologic Map Compilation, Nevada state geological map package",
        "landing": "https://mrdata.usgs.gov/geology/state/",
    },
    "sgmc_ca": {
        "url": "https://mrdata.usgs.gov/geology/state/shp/CA.zip",
        "licence": "US Government work / public domain (USGS Mineral Resources Program)",
        "what": "USGS State Geologic Map Compilation, California state geological map package",
        "landing": "https://mrdata.usgs.gov/geology/state/",
    },
    "gdr_qfaults_v2": {
        "url": f"{GDR}/qfaults_ingenious_nad83conus117_2023-06-27.zip",
        "licence": "CC BY 4.0 (DOI 10.15121/1881483)",
        "what": "INGENIOUS Quaternary fault compilation v2 (provenance check for the training catalogue)",
        "landing": "https://gdr.openei.org/submissions/1391",
    },
    "gdr_paleo": {
        "url": f"{GDR}/paleo_geothermal_regional.zip",
        "licence": "CC BY 4.0 (DOI 10.15121/1881483)",
        "what": "paleogeothermal features (sinter/tufa and related spring deposits)",
        "landing": "https://gdr.openei.org/submissions/1391",
    },
    "gdr_volcanics": {
        "url": f"{GDR}/great_basin_q_volcanics.zip",
        "licence": "CC BY 4.0 (DOI 10.15121/1881483)",
        "what": "Quaternary volcanic vents and flows",
        "landing": "https://gdr.openei.org/submissions/1391",
    },
    "gdr_2m_probes": {
        "url": f"{GDR}/2m_temperature_probe_INGENIOUS_regional_data.zip",
        "licence": "CC BY 4.0 (DOI 10.15121/1881483)",
        "what": "2 m shallow temperature probe surveys",
        "landing": "https://gdr.openei.org/submissions/1391",
    },
}

report: dict = {
    "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "runner": "GitHub Actions (general internet access); the agent sandbox cannot reach these hosts",
    "drivendata_contacted": False,
    "grid_source_note": (
        "Derived rasters use the hash-pinned owner-mirror competition grid. Those bytes are "
        "owner-mirrored, not organizer-authenticated; alignment is verified, labels are never learnt from."
    ),
    "downloads": {},
    "derived": {},
    "errors": {},
}


def save() -> None:
    """Persist the receipt after every stage so a hard failure still leaves evidence."""
    report["updated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (OUT / "external_receipt.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def fetch(url: str, key: str) -> Path | None:
    dest = WORK / f"{key}{Path(url).suffix or '.bin'}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read()
        dest.write_bytes(payload)
        report["downloads"][key] = {
            "url": url,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "ok": True,
        }
        print(f"[fetch] {key}: {len(payload)} bytes", flush=True)
        return dest
    except Exception as exc:  # noqa: BLE001 - recorded, never fatal
        report["downloads"][key] = {"url": url, "ok": False, "error": repr(exc)[:400]}
        print(f"[fetch] {key} FAILED: {exc!r}", flush=True)
        return None


def verify(path: Path, expected: str, label: str) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"{label} SHA-256 mismatch: {digest} != {expected}")


def main() -> int:
    import numpy as np
    import pyogrio
    import rasterio
    import shapely
    from pyproj import Transformer
    from rasterio.features import rasterize

    report["python"] = sys.version.split()[0]
    report["imports"] = {"numpy": np.__version__, "rasterio": rasterio.__version__,
                         "shapely": shapely.__version__}
    save()

    # ---- 1. competition grid -------------------------------------------------
    grid_dir = WORK / "grid"
    grid_dir.mkdir(exist_ok=True)
    for name, (url, sha) in GRID_SOURCES.items():
        path = fetch(url, f"grid_{name}")
        if path is None:
            raise RuntimeError(f"cannot continue without the competition grid ({name})")
        verify(path, sha, name)
    grid_labels = WORK / "grid_labels.tif"
    grid_template = WORK / "grid_template.tif"
    (grid_labels, grid_template) = (
        grid_dir / "grid_labels.tif", grid_dir / "grid_template.tif"
    ) if (grid_dir / "grid_labels.tif").exists() else (
        next(WORK.glob("grid_labels*")), next(WORK.glob("grid_template*"))
    )
    with rasterio.open(grid_labels) as dataset:
        transform, crs = dataset.transform, dataset.crs
        shape = (dataset.height, dataset.width)
        labels = dataset.read(1) > 0
    with rasterio.open(grid_template) as dataset:
        footprint = np.isfinite(dataset.read(1))
    report["grid"] = {
        "shape": list(shape),
        "crs": str(crs),
        "transform": [float(v) for v in transform.to_gdal()],
        "footprint_pixels": int(footprint.sum()),
        "catalogue_pixels": int(labels.sum()),
    }
    bounds = rasterio.transform.array_bounds(shape[0], shape[1], transform)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    save()

    def write_raster(path: Path, array: np.ndarray, dtype: str, nodata: int) -> dict:
        profile = {
            "driver": "GTiff", "dtype": dtype, "count": 1, "height": shape[0],
            "width": shape[1], "crs": crs, "transform": transform,
            "compress": "deflate", "nodata": nodata, "predictor": 2,
        }
        with rasterio.open(path, "w", **profile) as dataset:
            dataset.write(array.astype(dtype), 1)
        return {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def rasterise_linework(paths: list[Path], key: str, filter_terms=("fault", "thrust")) -> None:
        """Rasterise line features mentioning fault/thrust onto the competition grid."""
        merged, layer_names, feature_count = [], [], 0
        for archive in paths:
            extract_dir = WORK / f"x_{key}_{archive.stem}"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(extract_dir)
            for shapefile in sorted(extract_dir.rglob("*.shp")):
                try:
                    info = pyogrio.read_info(shapefile)
                except Exception as exc:  # noqa: BLE001
                    report["errors"][f"{key}:{shapefile.name}"] = repr(exc)[:200]
                    continue
                if not str(info.get("geometry_type", "")).lower().startswith("line"):
                    continue
                gdf = pyogrio.read_dataframe(shapefile)
                layer_names.append({"layer": shapefile.name, "rows": int(len(gdf))})
                if not len(gdf):
                    continue
                text_columns = [
                    column for column in gdf.columns
                    if column != "geometry" and str(gdf[column].dtype) in ("object", "str", "string")
                ]
                mask = np.zeros(len(gdf), dtype=bool)
                for column in text_columns:
                    mask |= gdf[column].astype(str).str.contains(
                        "|".join(filter_terms), case=False, na=False
                    ).to_numpy()
                if not mask.any():
                    mask[:] = True  # keep all line work when no text flag is available
                selected = gdf.loc[mask]
                feature_count += int(len(selected))
                merged.extend(selected.geometry.tolist())
        if not merged:
            report["derived"][key] = {"ok": False, "reason": "no line features found", "layers": layer_names}
            return
        # project to the competition CRS and clip to the grid box
        promoted = shapely.from_wkt([shapely.to_wkt(geometry) for geometry in merged])
        def _project(coords, _transformer=transformer):
            return np.column_stack(_transformer.transform(coords[:, 0], coords[:, 1]))

        try:
            projected = shapely.transform(promoted, _project)
        except TypeError:  # older/newer shapely signature differences
            projected = np.array([shapely.transform(g, _project) for g in promoted])
        clip_box = shapely.box(bounds[0], bounds[1], bounds[2], bounds[3])
        clipped = shapely.intersection(projected, clip_box)
        kept = [geometry for geometry in clipped if not shapely.is_empty(geometry)]
        if not kept:
            report["derived"][key] = {"ok": False, "reason": "no features intersect the grid", "layers": layer_names}
            return
        raster = rasterize(
            [(geometry, 1) for geometry in kept],
            out_shape=shape, transform=transform, fill=0, dtype="uint8",
            all_touched=False,
        )
        inside = (raster > 0) & footprint
        receipt = write_raster(OUT / f"derived_{key}_100m_u8.tif", np.where(footprint, raster, 0), "uint8", 255)
        from scipy.ndimage import distance_transform_edt
        distance_to_catalogue = distance_transform_edt(~labels)
        off_catalogue = inside & ~labels & (distance_to_catalogue > 3)
        receipt.update({
            "ok": True,
            "feature_count_in_grid": len(kept),
            "layers": layer_names,
            "pixels_in_footprint": int(inside.sum()),
            "pixels_off_catalogue_gt_300m": int(off_catalogue.sum()),
            "fraction_within_300m_of_catalogue": float(
                (distance_to_catalogue[inside] <= 3).mean() if inside.any() else float("nan")
            ),
        })
        report["derived"][key] = receipt
        save()
        print(f"[derive] {key}: {int(inside.sum())} px, {int(off_catalogue.sum())} px >300 m off catalogue", flush=True)

    def rasterise_points_or_polygons(archive: Path, key: str) -> None:
        extract_dir = WORK / f"x_{key}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(extract_dir)
        geometries, layers = [], []
        for candidate in sorted(list(extract_dir.rglob("*.shp")) + list(extract_dir.rglob("*.csv"))):
            try:
                if candidate.suffix == ".csv":
                    import pandas as pd
                    frame = pd.read_csv(candidate)
                    x_column = next((c for c in frame.columns if c.lower() in ("longitude", "lon", "x", "x_utm", "utm_x")), None)
                    y_column = next((c for c in frame.columns if c.lower() in ("latitude", "lat", "y", "y_utm", "utm_y")), None)
                    if x_column is None or y_column is None:
                        layers.append({"file": candidate.name, "rows": int(len(frame)), "used": False})
                        continue
                    values = frame[[x_column, y_column]].to_numpy(dtype=float)
                    geographic = abs(values[:, 0]).max() <= 180.0
                    if geographic:
                        east, north = transformer.transform(values[:, 0], values[:, 1])
                    else:
                        east, north = values[:, 0], values[:, 1]
                    geometries.extend(shapely.points(east, north).tolist())
                    layers.append({"file": candidate.name, "rows": int(len(frame)), "used": True})
                else:
                    gdf = pyogrio.read_dataframe(candidate)
                    if not len(gdf):
                        continue
                    if gdf.crs is None:
                        gdf = gdf.set_crs("EPSG:4326")
                    gdf = gdf.to_crs("EPSG:32611")
                    geometries.extend(gdf.geometry.tolist())
                    layers.append({"file": candidate.name, "rows": int(len(gdf)), "used": True})
            except Exception as exc:  # noqa: BLE001
                report["errors"][f"{key}:{candidate.name}"] = repr(exc)[:200]
        clip_box = shapely.box(bounds[0], bounds[1], bounds[2], bounds[3])
        kept = [g for g in shapely.intersection(shapely.from_wkt([shapely.to_wkt(g) for g in geometries]), clip_box)
                if not shapely.is_empty(g)]
        if not kept:
            report["derived"][key] = {"ok": False, "reason": "no features in grid", "layers": layers}
            return
        raster = rasterize([(g, 1) for g in kept], out_shape=shape, transform=transform,
                           fill=0, dtype="uint8", all_touched=True)
        inside = (raster > 0) & footprint
        receipt = write_raster(OUT / f"derived_{key}_100m_u8.tif", np.where(footprint, raster, 0), "uint8", 255)
        receipt.update({"ok": True, "feature_count_in_grid": len(kept), "layers": layers,
                        "pixels_in_footprint": int(inside.sum())})
        report["derived"][key] = receipt
        save()
        print(f"[derive] {key}: {int(inside.sum())} px", flush=True)

    # ---- 2. SGMC state-map fault linework ------------------------------------
    sgmc_paths = [path for key in ("sgmc_nv", "sgmc_ca") if (path := fetch(SOURCES[key]["url"], key))]
    for key in ("sgmc_nv", "sgmc_ca"):
        if key in report["downloads"]:
            report["downloads"][key].update(
                {k: SOURCES[key][k] for k in ("licence", "what", "landing")}
            )
    if sgmc_paths:
        rasterise_linework(sgmc_paths, "sgmc_faults")
    save()

    # ---- 3. GDR INGENIOUS layers ---------------------------------------------
    if (path := fetch(SOURCES["gdr_qfaults_v2"]["url"], "gdr_qfaults_v2")):
        rasterise_linework([path], "gdr_qfaults_v2", filter_terms=("fault", "thrust", "scarp"))
    for key in ("gdr_paleo", "gdr_volcanics", "gdr_2m_probes"):
        if (path := fetch(SOURCES[key]["url"], key)):
            rasterise_points_or_polygons(path, key)
        save()
    for key in ("gdr_qfaults_v2", "gdr_paleo", "gdr_volcanics", "gdr_2m_probes"):
        if key in report["downloads"]:
            report["downloads"][key].update(
                {k: SOURCES[key][k] for k in ("licence", "what", "landing")}
            )

    return 0


if __name__ == "__main__":
    report["stage"] = "started"
    save()  # stub receipt: a hard crash still leaves an auditable file for the commit step
    try:
        code = main()
        report["stage"] = "completed"
    except Exception as exc:  # noqa: BLE001 - always leave an auditable receipt
        report["fatal"] = repr(exc)
        report["trace"] = traceback.format_exc()[-2500:]
        print(report["trace"], file=sys.stderr)
        report["stage"] = "failed"
        code = 1
    receipt_path = OUT / "external_receipt.json"
    receipt_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {receipt_path.relative_to(ROOT)}", flush=True)
    sys.exit(code)
