"""Unit-consistent 3D potential-field phase-tilt & dip-contact asymmetry transforms (PTA-1).

All transforms are deterministic, label-free local operators with fixed physical unit
floors and strictly bounded Euclidean spatial support ``SUPPORT_PX = 12`` (1,200 m on
the 100 m EPSG:32611 grid; analytic worst-case reach ``6 + sqrt(2) + sqrt(13) = 11.02 px``).
No global statistics or held-out pixels are read here; fold-specific normalization happens
downstream strictly inside each fold's buffered training mask.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

TIGHT_SUPPORT_PX = 12  # Analytic Euclidean bound: 6 + sqrt(2) + sqrt(13) = 11.02 px <= 12 px
SUPPORT_PX = 17  # Shared buffered-fold guard radius (>= 12 px + 3 px metric reach; matches TDX-1/TDX-C2)
TRANSFORM_VERSION = "phase-tilt-dip-asymmetry-v1-support17px-20261025"

# Official 0-based band indices in training_features.tif (verified against manifest.json)
SUB8_INDICES: tuple[int, ...] = (1, 2, 8, 12, 4, 10, 14, 16)
SUB8_NAMES: tuple[str, ...] = (
    "rtp",
    "tmi_hg",
    "tmi_vg",
    "iso_grav_anom",
    "iso_grav_anom_slope",
    "iso_grav_anom_vg",
    "depth_to_base_surf",
    "cond_surf",
)

CANDIDATE_DERIVED_NAMES: tuple[str, ...] = (
    "pta_mag_tilt",
    "pta_mag_hd_tdr",
    "pta_mag_as3d_log",
    "pta_grav_tilt",
    "pta_grav_hd_tdr",
    "pta_mg_phase_concord",
    "pta_strike_persist",
    "pta_dip_grav_mig",
    "pta_dip_cover_step",
    "pta_dip_cond_step",
)

CONTROL_DERIVED_NAMES: tuple[str, ...] = (
    "ctrl_naive_mag_tilt",
    "ctrl_naive_mag_hd_tdr",
    "ctrl_naive_mag_as3d_log",
    "ctrl_naive_mg_concord",
    "ctrl_normal_blur",
    "ctrl_sym_grav_mig",
    "ctrl_sym_cover_step",
    "ctrl_sym_cond_step",
)

ALL_DERIVED_NAMES: tuple[str, ...] = CANDIDATE_DERIVED_NAMES + CONTROL_DERIVED_NAMES

# Fixed physical constants (never fitted to data)
VG_TO_NT_PER_KM = 1000.0  # tmi_vg is in nT/m; tmi_hg is in nT/km (IR-TILT-01)
EPS_MAG_NT_KM = 2.0
EPS_GRAV_SLOPE = 0.01
COVER_FLOOR_M = 50.0
TRUNCATE = 2.0
TANGENT_OFFSETS_PX: tuple[float, ...] = (-4.0, -2.0, 2.0, 4.0)
DIP_OFFSETS_PX: tuple[float, ...] = (3.0, 6.0)


def _nan_smooth(values: np.ndarray, valid: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    """Normalized truncated Gaussian smooth ignoring invalid/NaN cells within bounded support."""
    arr = np.asarray(values, dtype=np.float32)
    usable = np.asarray(valid, dtype=bool) & np.isfinite(arr)
    filled = np.where(usable, arr, np.float32(0.0))
    weights = gaussian_filter(
        usable.astype(np.float32), sigma=sigma, mode="constant", cval=0.0, truncate=TRUNCATE
    )
    num = gaussian_filter(filled, sigma=sigma, mode="constant", cval=0.0, truncate=TRUNCATE)
    out = np.zeros_like(arr, dtype=np.float32)
    ok = usable & (weights > 1e-5)
    np.divide(num, weights, out=out, where=ok)
    out[~ok] = np.nan
    return out, ok


def _central_gradient(field: np.ndarray, ok_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """1-px central finite differences returning ``(gy, gx, mag)`` with NaN where neighbors lack support."""
    f = np.asarray(field, dtype=np.float32)
    ok = np.asarray(ok_mask, dtype=bool) & np.isfinite(f)
    H, W = f.shape
    gy = np.full((H, W), np.nan, dtype=np.float32)
    gx = np.full((H, W), np.nan, dtype=np.float32)

    ok_y = np.zeros((H, W), dtype=bool)
    ok_y[1:-1, :] = ok[2:, :] & ok[:-2, :] & ok[1:-1, :]
    gy[1:-1, :] = np.where(ok_y[1:-1, :], 0.5 * (f[2:, :] - f[:-2, :]), np.nan)

    ok_x = np.zeros((H, W), dtype=bool)
    ok_x[:, 1:-1] = ok[:, 2:] & ok[:, :-2] & ok[:, 1:-1]
    gx[:, 1:-1] = np.where(ok_x[:, 1:-1], 0.5 * (f[:, 2:] - f[:, :-2]), np.nan)

    both = ok_y & ok_x
    gy = np.where(both, gy, np.nan)
    gx = np.where(both, gx, np.nan)
    mag = np.where(both, np.hypot(gy, gx), np.nan).astype(np.float32)
    return gy, gx, mag


def _bilinear_sample(field: np.ndarray, y_coords: np.ndarray, x_coords: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """NaN-aware order-1 bilinear sampling strictly inside ``valid``."""
    f = np.asarray(field, dtype=np.float32)
    usable = np.asarray(valid, dtype=bool) & np.isfinite(f)
    filled = np.where(usable, f, np.float32(0.0))
    coords = np.array([y_coords, x_coords], dtype=np.float32)
    val = map_coordinates(filled, coords, order=1, mode="constant", cval=0.0, prefilter=False)
    w = map_coordinates(usable.astype(np.float32), coords, order=1, mode="constant", cval=0.0, prefilter=False)
    out = np.full(f.shape, np.nan, dtype=np.float32)
    good = usable & (w > 0.999)
    out[good] = val[good]
    return out


def compute_phase_tilt_features(
    raw_features: np.ndarray,
    valid: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute all 10 candidate and 10 matched-control features from the 19-band array."""
    valid_mask = np.asarray(valid, dtype=bool)
    if raw_features.ndim != 3 or raw_features.shape[0] < 19 or raw_features.shape[1:] != valid_mask.shape:
        raise ValueError("expected (19, H, W) raw_features matching valid shape")

    tmi_hg = np.asarray(raw_features[2], dtype=np.float32)
    tmi_vg = np.asarray(raw_features[8], dtype=np.float32)
    grav_slope = np.asarray(raw_features[4], dtype=np.float32)
    grav_vg = np.asarray(raw_features[10], dtype=np.float32)
    grav = np.asarray(raw_features[12], dtype=np.float32)
    cover = np.asarray(raw_features[14], dtype=np.float32)
    cond = np.asarray(raw_features[16], dtype=np.float32)

    fin_mag = valid_mask & np.isfinite(tmi_hg) & np.isfinite(tmi_vg) & (tmi_hg >= 0.0)
    fin_grav_t = valid_mask & np.isfinite(grav_slope) & np.isfinite(grav_vg) & (grav_slope >= 0.0)

    # 1. Unit-consistent vs unit-naive magnetic tilt & 3D analytic signal
    vdr_unit = np.where(fin_mag, VG_TO_NT_PER_KM * tmi_vg, np.nan).astype(np.float32)
    vdr_naive = np.where(fin_mag, tmi_vg, np.nan).astype(np.float32)
    thdr_mag_reg = np.where(fin_mag, np.hypot(tmi_hg, np.float32(EPS_MAG_NT_KM)), np.nan).astype(np.float32)

    pta_mag_tilt = np.where(fin_mag, np.arctan2(vdr_unit, thdr_mag_reg), np.nan).astype(np.float32)
    ctrl_naive_mag_tilt = np.where(fin_mag, np.arctan2(vdr_naive, thdr_mag_reg), np.nan).astype(np.float32)

    pta_mag_as3d_log = np.where(
        fin_mag, np.log1p(np.hypot(np.maximum(tmi_hg, 0.0), vdr_unit)), np.nan
    ).astype(np.float32)
    ctrl_naive_mag_as3d_log = np.where(
        fin_mag, np.log1p(np.hypot(np.maximum(tmi_hg, 0.0), vdr_naive)), np.nan
    ).astype(np.float32)

    mag_tilt_sm, mag_ok = _nan_smooth(pta_mag_tilt, valid_mask, sigma=1.0)
    m_gy, m_gx, pta_mag_hd_tdr = _central_gradient(mag_tilt_sm, mag_ok)

    nmag_tilt_sm, nmag_ok = _nan_smooth(ctrl_naive_mag_tilt, valid_mask, sigma=1.0)
    nm_gy, nm_gx, ctrl_naive_mag_hd_tdr = _central_gradient(nmag_tilt_sm, nmag_ok)

    # 2. Gravity tilt & horizontal tilt-gradient ridge
    thdr_grav_reg = np.where(fin_grav_t, np.hypot(grav_slope, np.float32(EPS_GRAV_SLOPE)), np.nan).astype(np.float32)
    pta_grav_tilt = np.where(fin_grav_t, np.arctan2(grav_vg, thdr_grav_reg), np.nan).astype(np.float32)
    grav_tilt_sm, grav_t_ok = _nan_smooth(pta_grav_tilt, valid_mask, sigma=1.0)
    g_gy, g_gx, pta_grav_hd_tdr = _central_gradient(grav_tilt_sm, grav_t_ok)

    # 3. Axial magnetic-gravity phase-gradient concordance (candidate vs unit-naive control)
    del vdr_unit, vdr_naive, thdr_mag_reg, mag_tilt_sm, nmag_tilt_sm, thdr_grav_reg, grav_tilt_sm
    f32_zero, f32_one, f32_nan = np.float32(0.0), np.float32(1.0), np.float32(np.nan)
    both_mg = np.isfinite(pta_mag_hd_tdr) & np.isfinite(pta_grav_hd_tdr)
    dot_mg = np.where(both_mg, np.abs(m_gy * g_gy + m_gx * g_gx), f32_zero)
    denom_mg = np.where(both_mg, pta_mag_hd_tdr * pta_grav_hd_tdr + np.float32(1e-6), f32_one)
    cos_mg = dot_mg / denom_mg
    pta_mg_phase_concord = np.where(
        both_mg, cos_mg * np.sqrt(np.maximum(pta_mag_hd_tdr * pta_grav_hd_tdr, f32_zero)), f32_nan
    ).astype(np.float32)
    del both_mg, dot_mg, denom_mg, cos_mg, m_gy, m_gx

    both_nmg = np.isfinite(ctrl_naive_mag_hd_tdr) & np.isfinite(pta_grav_hd_tdr)
    dot_nmg = np.where(both_nmg, np.abs(nm_gy * g_gy + nm_gx * g_gx), f32_zero)
    denom_nmg = np.where(both_nmg, ctrl_naive_mag_hd_tdr * pta_grav_hd_tdr + np.float32(1e-6), f32_one)
    ctrl_naive_mg_concord = np.where(
        both_nmg,
        (dot_nmg / denom_nmg) * np.sqrt(np.maximum(ctrl_naive_mag_hd_tdr * pta_grav_hd_tdr, f32_zero)),
        f32_nan,
    ).astype(np.float32)
    del both_nmg, dot_nmg, denom_nmg, nm_gy, nm_gx, g_gy, g_gx

    # 4. Gravity-low hanging-wall unit normal n = -grad(g)/|grad(g)| and unit tangent t
    grav_sm, grav_ok = _nan_smooth(grav, valid_mask, sigma=1.5)
    ggy, ggx, gmag = _central_gradient(grav_sm, grav_ok)
    del grav_sm, grav_ok
    n_ok = np.isfinite(gmag) & (gmag > 1e-6)
    safe_gmag = np.where(n_ok, gmag, f32_one)
    ny = np.where(n_ok, -ggy / safe_gmag, f32_zero).astype(np.float32)
    nx = np.where(n_ok, -ggx / safe_gmag, f32_zero).astype(np.float32)
    del ggy, ggx, gmag, safe_gmag
    ty = -nx
    tx = ny

    H, W = valid_mask.shape
    yy, xx = np.meshgrid(np.arange(H, dtype=np.float32), np.arange(W, dtype=np.float32), indexing="ij")

    # 5. Gravity-tangent persistence vs cross-normal blur control on magnetic tilt ridge
    persist_acc = np.zeros((H, W), dtype=np.float32)
    persist_ok = n_ok & np.isfinite(pta_mag_hd_tdr)
    blur_acc = np.zeros((H, W), dtype=np.float32)
    blur_ok = n_ok & np.isfinite(ctrl_naive_mag_hd_tdr)
    for s in TANGENT_OFFSETS_PX:
        sf = np.float32(s)
        ts = _bilinear_sample(pta_mag_hd_tdr, yy + sf * ty, xx + sf * tx, valid_mask)
        persist_ok &= np.isfinite(ts)
        persist_acc += np.where(np.isfinite(ts), ts, f32_zero)
        del ts

        ns = _bilinear_sample(ctrl_naive_mag_hd_tdr, yy + sf * ny, xx + sf * nx, valid_mask)
        blur_ok &= np.isfinite(ns)
        blur_acc += np.where(np.isfinite(ns), ns, f32_zero)
        del ns

    pta_strike_persist = np.where(persist_ok, persist_acc / np.float32(len(TANGENT_OFFSETS_PX)), f32_nan).astype(np.float32)
    ctrl_normal_blur = np.where(blur_ok, blur_acc / np.float32(len(TANGENT_OFFSETS_PX)), f32_nan).astype(np.float32)
    del persist_acc, persist_ok, blur_acc, blur_ok, ty, tx

    # 6. Signed hanging-wall minus footwall dip asymmetry vs symmetric flank curvature controls
    cover_sm, _ = _nan_smooth(cover, valid_mask, sigma=1.0)
    cond_sm, _ = _nan_smooth(cond, valid_mask, sigma=1.0)

    dip_grav = np.zeros((H, W), dtype=np.float32)
    sym_grav = np.zeros((H, W), dtype=np.float32)
    ok_dg = n_ok & np.isfinite(pta_grav_hd_tdr)

    dip_cov = np.zeros((H, W), dtype=np.float32)
    sym_cov = np.zeros((H, W), dtype=np.float32)
    ok_dc = n_ok & np.isfinite(cover_sm)

    dip_cnd = np.zeros((H, W), dtype=np.float32)
    sym_cnd = np.zeros((H, W), dtype=np.float32)
    ok_dn = n_ok & np.isfinite(cond_sm)

    for d in DIP_OFFSETS_PX:
        yp, xp = yy + d * ny, xx + d * nx
        ym, xm = yy - d * ny, xx - d * nx

        gp = _bilinear_sample(pta_grav_hd_tdr, yp, xp, valid_mask)
        gm = _bilinear_sample(pta_grav_hd_tdr, ym, xm, valid_mask)
        ok_dg &= np.isfinite(gp) & np.isfinite(gm)
        dip_grav += np.where(np.isfinite(gp) & np.isfinite(gm), gp - gm, 0.0)
        sym_grav += np.where(
            np.isfinite(gp) & np.isfinite(gm) & np.isfinite(pta_grav_hd_tdr),
            0.5 * (gp + gm) - pta_grav_hd_tdr,
            0.0,
        )

        cp = _bilinear_sample(cover_sm, yp, xp, valid_mask)
        cm = _bilinear_sample(cover_sm, ym, xm, valid_mask)
        ok_dc &= np.isfinite(cp) & np.isfinite(cm)
        cov_denom = np.abs(cp) + np.abs(cm) + np.float32(COVER_FLOOR_M)
        cov_center = np.abs(cover_sm) + np.float32(COVER_FLOOR_M)
        dip_cov += np.where(np.isfinite(cp) & np.isfinite(cm), (cp - cm) / cov_denom, 0.0)
        sym_cov += np.where(
            np.isfinite(cp) & np.isfinite(cm) & np.isfinite(cover_sm),
            (0.5 * (cp + cm) - cover_sm) / cov_center,
            0.0,
        )

        sp = _bilinear_sample(cond_sm, yp, xp, valid_mask)
        sm = _bilinear_sample(cond_sm, ym, xm, valid_mask)
        ok_dn &= np.isfinite(sp) & np.isfinite(sm)
        dip_cnd += np.where(np.isfinite(sp) & np.isfinite(sm), sp - sm, 0.0)
        sym_cnd += np.where(
            np.isfinite(sp) & np.isfinite(sm) & np.isfinite(cond_sm),
            0.5 * (sp + sm) - cond_sm,
            0.0,
        )

    inv_nd = 1.0 / float(len(DIP_OFFSETS_PX))
    out: dict[str, np.ndarray] = {
        "pta_mag_tilt": pta_mag_tilt,
        "pta_mag_hd_tdr": pta_mag_hd_tdr,
        "pta_mag_as3d_log": pta_mag_as3d_log,
        "pta_grav_tilt": pta_grav_tilt,
        "pta_grav_hd_tdr": pta_grav_hd_tdr,
        "pta_mg_phase_concord": pta_mg_phase_concord,
        "pta_strike_persist": pta_strike_persist,
        "pta_dip_grav_mig": np.where(ok_dg, dip_grav * inv_nd, np.nan).astype(np.float32),
        "pta_dip_cover_step": np.where(ok_dc, dip_cov * inv_nd, np.nan).astype(np.float32),
        "pta_dip_cond_step": np.where(ok_dn, dip_cnd * inv_nd, np.nan).astype(np.float32),
        "ctrl_naive_mag_tilt": ctrl_naive_mag_tilt,
        "ctrl_naive_mag_hd_tdr": ctrl_naive_mag_hd_tdr,
        "ctrl_naive_mag_as3d_log": ctrl_naive_mag_as3d_log,
        "ctrl_naive_mg_concord": ctrl_naive_mg_concord,
        "ctrl_normal_blur": ctrl_normal_blur,
        "ctrl_sym_grav_mig": np.where(ok_dg, sym_grav * inv_nd, np.nan).astype(np.float32),
        "ctrl_sym_cover_step": np.where(ok_dc, sym_cov * inv_nd, np.nan).astype(np.float32),
        "ctrl_sym_cond_step": np.where(ok_dn, sym_cnd * inv_nd, np.nan).astype(np.float32),
    }
    for name, arr in out.items():
        arr[~valid_mask] = np.nan
        if tuple(arr.shape) != tuple(valid_mask.shape) or arr.dtype != np.float32:
            raise AssertionError(f"invalid derived array for {name}")
    if tuple(out.keys()) != ALL_DERIVED_NAMES:
        raise AssertionError("derived feature order mismatch")
    return out


def load_or_build_cache(
    raw_features: np.ndarray,
    valid: np.ndarray,
    manifest: Mapping[str, object],
    cache_dir: Path,
    *,
    report_dir: Path | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    """Build or verify SHA-256-pinned memory-mapped feature planes under ``cache_dir``."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = cache_dir / "pta1-feature-receipt.json"

    def _sha(path: Path) -> str:
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    expected_sig = {
        "transform_version": TRANSFORM_VERSION,
        "transform_code_sha256": _sha(Path(__file__).resolve()),
        "dataset_signature": manifest["dataset_signature"],
        "valid_mask_sha256": manifest["valid_mask_sha256"],
    }

    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("signature") == expected_sig and receipt.get("support_px") == SUPPORT_PX:
            files = receipt.get("sha256", {})
            if set(files) == set(ALL_DERIVED_NAMES) and all(
                (cache_dir / f"{name}.npy").is_file() and _sha(cache_dir / f"{name}.npy") == digest
                for name, digest in files.items()
            ):
                loaded = {name: np.load(cache_dir / f"{name}.npy", mmap_mode="r") for name in ALL_DERIVED_NAMES}
                if report_dir is not None:
                    report_dir.mkdir(parents=True, exist_ok=True)
                    (report_dir / "feature-receipt.json").write_text(
                        json.dumps(receipt, indent=2, allow_nan=False) + "\n"
                    )
                return loaded, receipt

    computed = compute_phase_tilt_features(raw_features, valid)
    files: dict[str, str] = {}
    for name in ALL_DERIVED_NAMES:
        out_path = cache_dir / f"{name}.npy"
        np.save(out_path, computed[name])
        files[name] = _sha(out_path)
    supported_px = int(
        np.all([np.isfinite(computed[name]) for name in CANDIDATE_DERIVED_NAMES], axis=0).sum()
    )
    del computed
    receipt = {
        "schema_version": 1,
        "signature": expected_sig,
        "source_bands_1based": [idx + 1 for idx in SUB8_INDICES],
        "sha256": files,
        "support_px": SUPPORT_PX,
        "tight_analytic_support_px": TIGHT_SUPPORT_PX,
        "supported_pixels": supported_px,
        "uses_catalogue_geometry": False,
        "uses_registry_values": False,
        "uses_template_values_as_features": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "feature-receipt.json").write_text(
            json.dumps(receipt, indent=2, allow_nan=False) + "\n"
        )
    loaded = {name: np.load(cache_dir / f"{name}.npy", mmap_mode="r") for name in ALL_DERIVED_NAMES}
    return loaded, receipt
