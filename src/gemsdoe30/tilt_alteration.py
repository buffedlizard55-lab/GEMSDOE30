"""Translation-invariant tilt-depth, hydrothermal alteration, and dip-slip polarity features (lane G30-TAD).

All 24 features are strictly translation-invariant local operators with exact bounded
Chebyshev impulse support <= 15 px (guarded at SUPPORT_PX = 17 px to match the v3
buffered spatial-segment holdout geometry). No label, template value, catalogue
distance (``dist_known_fault_px``), SGMC fault line, or Qfaults trace enters any
feature computation.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from .lidar_morphology import LIDAR_BANDS, decode as decode_lidar

TRANSFORM_VERSION = "tilt-alt-v1-20261025"
SUPPORT_PX = 17

SUBSURFACE_FEATURES = (
    "tmi_hg",
    "tmi_vg",
    "tc",
    "iso_grav_anom_hg",
    "iso_grav_anom_vg",
    "iso_grav_anom_slope",
    "mag_tilt_cos",
    "mag_salem_tilt_hgrad",
    "mag_buried_contact_score",
    "mag_up150_persistence",
    "grav_tilt_cos",
    "mag_grav_tilt_strike_lock",
    "rad_kd_potassic_resid",
    "rad_efimov_f_local",
    "cond_claycap_boundary",
    "bdepth_hinge_lap",
)

SURFACE_FEATURES = (
    "det_elev_slope",
    "local_slope_highpass",
    "lidar_valid",
    "lidar_dip_slip_polarity",
    "lidar_step_vs_cross_aniso",
    "lidar_subcell_peakedness",
    "lidar_subsurface_strike_lock",
    "hydrothermal_upflow_halo",
)

TAD_FEATURES = SUBSURFACE_FEATURES + SURFACE_FEATURES

# Derived static layers cached once on disk (23 of 24; rad_kd_potassic_resid is fit per training fold).
STATIC_DERIVED_NAMES = (
    "mag_tilt_cos",
    "mag_salem_tilt_hgrad",
    "mag_buried_contact_score",
    "mag_up150_persistence",
    "grav_tilt_cos",
    "mag_grav_tilt_strike_lock",
    "rad_efimov_f_local",
    "cond_claycap_boundary",
    "bdepth_hinge_lap",
    "local_slope_highpass",
    "lidar_valid",
    "lidar_dip_slip_polarity",
    "lidar_step_vs_cross_aniso",
    "lidar_subcell_peakedness",
    "lidar_subsurface_strike_lock",
    "hydrothermal_upflow_halo",
)

# 0-based indices into the 19-band prepared cache (manifest.json order).
BAND_IDX = {
    "mag_anom": 0,
    "rtp": 1,
    "tmi_hg": 2,
    "iso_grav_anom_slope": 4,
    "tc": 5,
    "tmi_vg": 8,
    "iso_grav_anom_vg": 10,
    "iso_grav_anom": 12,
    "depth_to_base_surf": 14,
    "cond_surf": 16,
    "iso_grav_anom_hg": 17,
    "det_elev_slope": 18,
}


def norm_gauss(arr: Any, valid: Any, sigma: float, *, truncate: float = 3.0) -> np.ndarray:
    """Footprint-isolated normalized Gaussian smoothing with exact finite radius."""
    valid_b = np.asarray(valid, dtype=bool)
    x = np.asarray(arr, dtype=np.float32)
    fin = valid_b & np.isfinite(x)
    clean = np.where(fin, x, np.float32(0.0))
    num = gaussian_filter(clean, sigma=float(sigma), truncate=float(truncate), mode="constant", cval=0.0)
    den = gaussian_filter(fin.astype(np.float32), sigma=float(sigma), truncate=float(truncate), mode="constant", cval=0.0)
    out = np.full(x.shape, np.nan, dtype=np.float32)
    ok = valid_b & (den > 1e-6)
    out[ok] = (num[ok] / den[ok]).astype(np.float32)
    return out


def sobel_xy_safe(arr: Any, valid: Any) -> tuple[np.ndarray, np.ndarray]:
    """Footprint-isolated 3x3 Sobel gradient (homogeneous Neumann on missing neighbors, support = 1 px)."""
    valid_b = np.asarray(valid, dtype=bool)
    x = np.asarray(arr, dtype=np.float32)
    fin = valid_b & np.isfinite(x)
    v0 = np.where(fin, x, np.float32(0.0))
    h, w = x.shape
    vp = np.pad(v0, 1, mode="constant", constant_values=0.0)
    fp = np.pad(fin, 1, mode="constant", constant_values=False)

    wx = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]], dtype=np.float32) / 8.0
    wy = np.array([[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]], dtype=np.float32) / 8.0

    gx = np.zeros((h, w), dtype=np.float32)
    gy = np.zeros((h, w), dtype=np.float32)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nb_f = fp[1 + dr : 1 + dr + h, 1 + dc : 1 + dc + w]
            nb_v = vp[1 + dr : 1 + dr + h, 1 + dc : 1 + dc + w]
            diff = np.where(fin & nb_f, nb_v - v0, np.float32(0.0))
            if wx[1 + dr, 1 + dc] != 0.0:
                gx += wx[1 + dr, 1 + dc] * diff
            if wy[1 + dr, 1 + dc] != 0.0:
                gy += wy[1 + dr, 1 + dc] * diff

    gx = np.where(fin, gx, np.float32(np.nan))
    gy = np.where(fin, gy, np.float32(np.nan))
    return gx, gy


def sobel_hgrad(arr: Any, valid: Any) -> np.ndarray:
    """Horizontal gradient magnitude from footprint-isolated 3x3 Sobel."""
    gx, gy = sobel_xy_safe(arr, valid)
    return np.hypot(gx, gy).astype(np.float32)


def axial_strike_rad(arr: Any, valid: Any, *, hp_sigma: float = 3.0) -> np.ndarray:
    """Local contour/strike orientation in [0, pi) from high-pass Sobel gradient."""
    hp = np.asarray(arr, dtype=np.float32) - norm_gauss(arr, valid, sigma=hp_sigma, truncate=3.0)
    gx, gy = sobel_xy_safe(hp, valid)
    # Gradient angle is atan2(gy, gx); strike (level-set tangent) is perpendicular (+pi/2).
    strike = (np.arctan2(gy, gx) + np.float32(0.5 * math.pi)) % np.float32(math.pi)
    return np.where(np.isfinite(gx) & np.isfinite(gy), strike, np.float32(np.nan)).astype(np.float32)


def fit_apply_rad_kd(rad_k_u8: Any, rad_th_u8: Any, valid: Any, train_mask: Any) -> tuple[np.ndarray, dict[str, float]]:
    """Fold-safe Saunders-Dickson Th-normalized potassium excess Kd (OLS strictly inside train_mask)."""
    valid_b = np.asarray(valid, dtype=bool)
    train_b = np.asarray(train_mask, dtype=bool) & valid_b
    rk_raw = np.asarray(rad_k_u8)
    rth_raw = np.asarray(rad_th_u8)
    has_rad = valid_b & np.isfinite(rk_raw) & np.isfinite(rth_raw) & (rk_raw > 0) & (rth_raw > 0)
    fit_sel = train_b & has_rad
    if int(fit_sel.sum()) < 32:
        raise ValueError("insufficient valid training radiometric pixels for fold-safe Kd regression")

    th_tr = rth_raw[fit_sel].astype(np.float64)
    k_tr = rk_raw[fit_sel].astype(np.float64)
    th_mean = float(th_tr.mean())
    k_mean = float(k_tr.mean())
    th_var = float(np.mean((th_tr - th_mean) ** 2))
    slope = float(np.mean((th_tr - th_mean) * (k_tr - k_mean)) / max(th_var, 1e-6))
    intercept = float(k_mean - slope * th_mean)

    out = np.full(valid_b.shape, np.nan, dtype=np.float32)
    th_all = rth_raw[has_rad].astype(np.float32)
    k_all = rk_raw[has_rad].astype(np.float32)
    k_hat = np.float32(slope) * th_all + np.float32(intercept)
    out[has_rad] = ((k_all - k_hat) / np.maximum(k_hat, np.float32(5.0))).astype(np.float32)
    return out, {"ols_slope_k_on_th": slope, "ols_intercept_k_on_th": intercept, "fit_pixels": int(fit_sel.sum())}


def build_hydrothermal_impulse(
    paleo_u8: Any,
    probes_u8: Any,
    wellspring_csv: Path | None,
    valid: Any,
) -> tuple[np.ndarray, dict[str, int]]:
    """Construct label-free hydrothermal upflow impulse grid (never reads dist_known_fault_px)."""
    valid_b = np.asarray(valid, dtype=bool)
    h, w = valid_b.shape
    paleo = valid_b & (np.asarray(paleo_u8) > 0)
    probes = valid_b & (np.asarray(probes_u8) > 0)
    chem = np.zeros((h, w), dtype=bool)

    if wellspring_csv is not None:
        with Path(wellspring_csv).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"row", "col", "geothermcat_c", "geothermquartz_c"}
            if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
                raise ValueError("wellspring CSV missing required geothermometer columns")
            for record in reader:
                # Explicitly ignore dist_known_fault_px; read only grid indices and chemistry.
                try:
                    r = int(record["row"])
                    c = int(record["col"])
                except (TypeError, ValueError):
                    continue
                if not (0 <= r < h and 0 <= c < w and valid_b[r, c]):
                    continue
                qtz_s = (record.get("geothermquartz_c") or "").strip()
                cat_s = (record.get("geothermcat_c") or "").strip()
                qtz = float(qtz_s) if qtz_s else float("nan")
                cat = float(cat_s) if cat_s else float("nan")
                is_diseq = math.isfinite(cat) and math.isfinite(qtz) and (cat - qtz >= 15.0)
                is_high_qtz = math.isfinite(qtz) and (qtz >= 130.0)
                if is_diseq or is_high_qtz:
                    chem[r, c] = True

    impulse = (
        np.float32(2.0) * paleo.astype(np.float32)
        + np.float32(1.5) * chem.astype(np.float32)
        + np.float32(1.0) * probes.astype(np.float32)
    )
    impulse = np.where(valid_b, impulse, np.float32(0.0))
    counts = {
        "paleo_sinter_pixels": int(paleo.sum()),
        "probe_2m_pixels": int(probes.sum()),
        "geothermometer_upflow_pixels": int(chem.sum()),
    }
    return impulse, counts


def compute_static_derived_layers(
    base: Any,
    valid: Any,
    *,
    rad_u8: Any,
    ext_u8: Any,
    lidar_u8: Any,
    hydro_impulse: Any,
) -> dict[str, np.ndarray]:
    """Compute all 16 fold-invariant derived features in float32 within footprint."""
    valid_b = np.asarray(valid, dtype=bool)
    mask_f = lambda a: np.where(valid_b & np.isfinite(a), np.asarray(a, dtype=np.float32), np.float32(np.nan))

    tmi_hg = mask_f(base[BAND_IDX["tmi_hg"]])
    tmi_vg = mask_f(base[BAND_IDX["tmi_vg"]])
    grav_hg = mask_f(base[BAND_IDX["iso_grav_anom_hg"]])
    grav_vg = mask_f(base[BAND_IDX["iso_grav_anom_vg"]])
    rtp = mask_f(base[BAND_IDX["rtp"]])
    grav = mask_f(base[BAND_IDX["iso_grav_anom"]])
    cond = mask_f(base[BAND_IDX["cond_surf"]])
    bdepth = mask_f(base[BAND_IDX["depth_to_base_surf"]])
    slope = mask_f(base[BAND_IDX["det_elev_slope"]])

    out: dict[str, np.ndarray] = {}

    # 1. Magnetic tilt angle, Salem tilt-depth horizontal gradient, and buried contact score.
    mag_abs_hg = np.abs(tmi_hg)
    mag_tilt_cos = (mag_abs_hg / np.sqrt(mag_abs_hg * mag_abs_hg + tmi_vg * tmi_vg + np.float32(1e-6))).astype(np.float32)
    theta_mag = np.arctan2(tmi_vg, mag_abs_hg + np.float32(1e-3)).astype(np.float32)
    mag_salem_hgrad = sobel_hgrad(theta_mag, valid_b)
    mag_buried = (mag_tilt_cos * mag_tilt_cos * np.exp(-mag_salem_hgrad / np.float32(0.35))).astype(np.float32)
    out["mag_tilt_cos"] = mask_f(mag_tilt_cos)
    out["mag_salem_tilt_hgrad"] = mask_f(mag_salem_hgrad)
    out["mag_buried_contact_score"] = mask_f(mag_buried)
    del theta_mag, mag_salem_hgrad, mag_buried

    # 2. 150 m upward-continuation vertical persistence (band index 3 of geodawn_extensions_u8).
    up150_raw = np.asarray(ext_u8[3])
    up150 = np.where(valid_b & np.isfinite(up150_raw) & (up150_raw > 0), up150_raw.astype(np.float32), np.float32(np.nan))
    up150_hg = sobel_hgrad(up150, valid_b)
    u_ratio = np.log(up150_hg + np.float32(0.5)) - np.log(mag_abs_hg + np.float32(0.5))
    out["mag_up150_persistence"] = mask_f(u_ratio - norm_gauss(u_ratio, valid_b, sigma=4.0, truncate=3.0))
    del up150, up150_hg, u_ratio, mag_abs_hg

    # 3. Gravity tilt locus and joint magnetic-gravity tilt-strike lock.
    grav_abs_hg = np.abs(grav_hg)
    grav_tilt_cos = (grav_abs_hg / np.sqrt(grav_abs_hg * grav_abs_hg + grav_vg * grav_vg + np.float32(1e-6))).astype(np.float32)
    out["grav_tilt_cos"] = mask_f(grav_tilt_cos)
    phi_rtp = axial_strike_rad(rtp, valid_b, hp_sigma=3.0)
    phi_grav = axial_strike_rad(grav, valid_b, hp_sigma=3.0)
    out["mag_grav_tilt_strike_lock"] = mask_f(
        mag_tilt_cos * grav_tilt_cos * np.cos(np.float32(2.0) * (phi_rtp - phi_grav))
    )
    del mag_tilt_cos, grav_tilt_cos, grav_abs_hg, tmi_hg, tmi_vg, grav_hg, grav_vg, rtp, grav

    # 4. Efimov hydrothermal alteration F-parameter local contrast.
    rk_raw, rth_raw, ru_raw = np.asarray(rad_u8[0]), np.asarray(rad_u8[1]), np.asarray(rad_u8[2])
    has_rad = valid_b & np.isfinite(rk_raw) & np.isfinite(rth_raw) & np.isfinite(ru_raw) & (rk_raw > 0) & (rth_raw > 0) & (ru_raw > 0)
    efimov = np.full(valid_b.shape, np.nan, dtype=np.float32)
    efimov[has_rad] = np.log(
        (rk_raw[has_rad].astype(np.float32) + np.float32(1.0))
        * (ru_raw[has_rad].astype(np.float32) + np.float32(1.0))
        / ((rth_raw[has_rad].astype(np.float32) + np.float32(5.0)) ** 2)
    ).astype(np.float32)
    out["rad_efimov_f_local"] = mask_f(efimov - norm_gauss(efimov, valid_b, sigma=4.0, truncate=3.0))
    del efimov, has_rad

    # 5. Smectite clay-cap MT conductance lateral boundary & basement-depth DoG hinge curvature.
    cond_log = np.where(np.isfinite(cond), np.log(np.maximum(cond, np.float32(0.0)) + np.float32(1.0)), np.float32(np.nan))
    cond_hg = sobel_hgrad(cond_log, valid_b)
    out["cond_claycap_boundary"] = mask_f(cond_hg - norm_gauss(cond_hg, valid_b, sigma=4.0, truncate=3.0))
    del cond, cond_log, cond_hg

    out["bdepth_hinge_lap"] = mask_f(
        norm_gauss(bdepth, valid_b, sigma=1.0, truncate=3.0) - norm_gauss(bdepth, valid_b, sigma=4.0, truncate=3.0)
    )
    del bdepth

    # 6. High-pass topographic escarpment break.
    out["local_slope_highpass"] = mask_f(slope - norm_gauss(slope, valid_b, sigma=4.0, truncate=3.0))
    del slope

    # 7. 1 m LiDAR dip-slip polarity, step-vs-cross anisotropy, sub-cell peakedness, and subsurface strike lock.
    l_idx = {name: i for i, name in enumerate(LIDAR_BANDS)}
    cov = decode_lidar(lidar_u8[l_idx["valid"]], "valid")
    has_l = valid_b & np.isfinite(cov) & (cov > 0.5)
    lidar_valid_f = np.where(valid_b, has_l.astype(np.float32), np.float32(np.nan))
    out["lidar_valid"] = lidar_valid_f

    step = np.where(has_l, decode_lidar(lidar_u8[l_idx["step_max"]], "step_max"), np.float32(0.0))
    down = np.where(has_l, decode_lidar(lidar_u8[l_idx["downface_max"]], "downface_max"), np.float32(0.0))
    up = np.where(has_l, decode_lidar(lidar_u8[l_idx["upface_max"]], "upface_max"), np.float32(0.0))
    cross = np.where(has_l, decode_lidar(lidar_u8[l_idx["cross_max"]], "cross_max"), np.float32(0.0))
    coh = np.where(has_l, decode_lidar(lidar_u8[l_idx["coh100"]], "coh100"), np.float32(0.0))
    ex_max = np.where(has_l, decode_lidar(lidar_u8[l_idx["ex_max"]], "ex_max"), np.float32(0.0))
    ex_mean = np.where(has_l, decode_lidar(lidar_u8[l_idx["ex_mean"]], "ex_mean"), np.float32(0.0))
    lapneg = np.where(has_l, decode_lidar(lidar_u8[l_idx["lapneg_max"]], "lapneg_max"), np.float32(0.0))
    lappos = np.where(has_l, decode_lidar(lidar_u8[l_idx["lappos_max"]], "lappos_max"), np.float32(0.0))
    l_strike_deg = decode_lidar(lidar_u8[l_idx["strike"]], "strike")
    phi_lidar = np.deg2rad(np.where(has_l, l_strike_deg, np.float32(0.0))).astype(np.float32)

    eps = np.float32(0.02)
    dip_pol = (np.abs(down - up) / (down + up + eps)) * step
    step_aniso = ((step - cross) / (step + cross + eps)) * coh
    peaked = ((ex_max - ex_mean) / (ex_max + ex_mean + eps)) * np.sqrt(np.maximum(lapneg * lappos, np.float32(0.0)))

    align_grav = np.where(np.isfinite(phi_grav), np.cos(np.float32(2.0) * (phi_lidar - phi_grav)), np.float32(0.0))
    align_rtp = np.where(np.isfinite(phi_rtp), np.cos(np.float32(2.0) * (phi_lidar - phi_rtp)), np.float32(0.0))
    strike_lock = coh * np.maximum(align_grav, align_rtp)

    out["lidar_dip_slip_polarity"] = np.where(valid_b, np.where(has_l, dip_pol, np.float32(0.0)), np.float32(np.nan)).astype(np.float32)
    out["lidar_step_vs_cross_aniso"] = np.where(valid_b, np.where(has_l, step_aniso, np.float32(0.0)), np.float32(np.nan)).astype(np.float32)
    out["lidar_subcell_peakedness"] = np.where(valid_b, np.where(has_l, peaked, np.float32(0.0)), np.float32(np.nan)).astype(np.float32)
    out["lidar_subsurface_strike_lock"] = np.where(valid_b, np.where(has_l, strike_lock, np.float32(0.0)), np.float32(np.nan)).astype(np.float32)
    del phi_rtp, phi_grav

    # 8. Bounded-support (15 px) hydrothermal sinter / geothermometer / 2 m probe halo.
    out["hydrothermal_upflow_halo"] = norm_gauss(hydro_impulse, valid_b, sigma=5.0, truncate=3.0)

    if tuple(out.keys()) != STATIC_DERIVED_NAMES:
        raise AssertionError("derived layer ordering mismatch")
    return out


def assemble_tad_layers(
    base: Any,
    static_derived: dict[str, Any],
    rad_kd_fold: Any,
) -> list[Any]:
    """Return the 24-layer TAD stack in exact TAD_FEATURES order (0..15 subsurface16, 0..23 tilt_alt24)."""
    return [
        base[BAND_IDX["tmi_hg"]],
        base[BAND_IDX["tmi_vg"]],
        base[BAND_IDX["tc"]],
        base[BAND_IDX["iso_grav_anom_hg"]],
        base[BAND_IDX["iso_grav_anom_vg"]],
        base[BAND_IDX["iso_grav_anom_slope"]],
        static_derived["mag_tilt_cos"],
        static_derived["mag_salem_tilt_hgrad"],
        static_derived["mag_buried_contact_score"],
        static_derived["mag_up150_persistence"],
        static_derived["grav_tilt_cos"],
        static_derived["mag_grav_tilt_strike_lock"],
        rad_kd_fold,
        static_derived["rad_efimov_f_local"],
        static_derived["cond_claycap_boundary"],
        static_derived["bdepth_hinge_lap"],
        base[BAND_IDX["det_elev_slope"]],
        static_derived["local_slope_highpass"],
        static_derived["lidar_valid"],
        static_derived["lidar_dip_slip_polarity"],
        static_derived["lidar_step_vs_cross_aniso"],
        static_derived["lidar_subcell_peakedness"],
        static_derived["lidar_subsurface_strike_lock"],
        static_derived["hydrothermal_upflow_halo"],
    ]


def calibrate_oof_by_training_quantiles(
    fold_pred: Any,
    train_mask: Any,
    score_mask: Any,
    *,
    knots: int = 1001,
) -> np.ndarray:
    """Map held-out fold predictions onto [0, 1] using strictly training-fold quantiles."""
    p = np.asarray(fold_pred, dtype=np.float32)
    tr = np.asarray(train_mask, dtype=bool) & np.isfinite(p)
    sc = np.asarray(score_mask, dtype=bool) & np.isfinite(p)
    if not np.any(tr):
        raise ValueError("empty training mask for quantile calibration")
    q_grid = np.linspace(0.0, 1.0, int(knots), dtype=np.float64)
    lut_x = np.quantile(p[tr].astype(np.float64), q_grid)
    # Collapse duplicate knots monotonically before linear interpolation.
    uniq_x, uniq_idx = np.unique(lut_x, return_index=True)
    uniq_y = q_grid[uniq_idx]
    out = np.zeros(p.shape, dtype=np.float32)
    if uniq_x.size == 1:
        out[sc] = 0.5
    else:
        out[sc] = np.interp(p[sc].astype(np.float64), uniq_x, uniq_y).astype(np.float32)
    return np.clip(out, 0.0, 1.0)


def decensored_collar_select(
    surface: Any,
    valid: Any,
    visible_catalogue: Any,
    *,
    total_dots: int = 38000,
    min_spacing_px: float = 3.0,
    shares: tuple[float, float, float] = (0.30, 0.40, 0.30),
) -> tuple[np.ndarray, dict[str, int]]:
    """Select binary dots across (2,10], (10,30], >30 px collars with one shared 3 px Poisson disk."""
    if total_dots < 1:
        raise ValueError("total_dots must be positive")
    if min_spacing_px <= 0:
        raise ValueError("min_spacing_px must be positive")
    scores = np.asarray(surface, dtype=np.float32)
    valid_b = np.asarray(valid, dtype=bool)
    vis_b = valid_b & np.asarray(visible_catalogue, dtype=bool)
    d_vis = distance_transform_edt(~vis_b) if np.any(vis_b) else np.full(scores.shape, np.inf, dtype=np.float64)

    elig = valid_b & np.isfinite(scores) & (d_vis > 2.0)
    q_near = int(round(shares[0] * total_dots))
    q_mid = int(round(shares[1] * total_dots))
    q_far = int(total_dots - q_near - q_mid)

    strata = (
        ("far_gt_30px", elig & (d_vis > 30.0), q_far),
        ("mid_10_to_30px", elig & (d_vis > 10.0) & (d_vis <= 30.0), q_mid),
        ("near_2_to_10px", elig & (d_vis <= 10.0), q_near),
    )

    h, w = scores.shape
    reach = max(int(math.ceil(min_spacing_px)), 1)
    r2 = float(min_spacing_px) * float(min_spacing_px)
    offsets = [
        (dy, dx)
        for dy in range(-reach, reach + 1)
        for dx in range(-reach, reach + 1)
        if dy * dy + dx * dx < r2
    ]

    kept = np.zeros((h, w), dtype=bool)
    blocked = np.zeros((h, w), dtype=bool)
    realized: dict[str, int] = {}
    total_kept = 0

    def _fill_from(mask: np.ndarray, quota: int) -> int:
        nonlocal total_kept
        if quota <= 0:
            return 0
        rows, cols = np.nonzero(mask & ~kept & ~blocked)
        if rows.size == 0:
            return 0
        order = np.lexsort((cols, rows, -scores[rows, cols]))
        added = 0
        for idx in order.tolist():
            r = int(rows[idx])
            c = int(cols[idx])
            if blocked[r, c] or kept[r, c]:
                continue
            kept[r, c] = True
            added += 1
            total_kept += 1
            for dy, dx in offsets:
                rr, cc = r + dy, c + dx
                if 0 <= rr < h and 0 <= cc < w:
                    blocked[rr, cc] = True
            if added >= quota:
                break
        return added

    for name, mask, quota in strata:
        realized[name] = _fill_from(mask, quota)

    if total_kept < total_dots:
        realized["fallback_rollover"] = _fill_from(elig, total_dots - total_kept)
    else:
        realized["fallback_rollover"] = 0

    if total_kept != total_dots:
        raise ValueError(f"decensored_collar_select could only place {total_kept} of {total_dots} dots")

    dots = kept.astype(np.float32)
    return dots, realized


def exact_operator_support_px(*, grid_size: int = 49) -> int:
    """Measure the exact worst-case Chebyshev impulse radius across all derived TAD layers."""
    if grid_size < 41 or grid_size % 2 == 0:
        raise ValueError("grid_size must be an odd integer >= 41")
    c = grid_size // 2
    rng = np.random.default_rng(20261025)
    valid = np.ones((grid_size, grid_size), dtype=bool)
    base0 = rng.normal(0.0, 1.0, size=(19, grid_size, grid_size)).astype(np.float32)
    base0[BAND_IDX["cond_surf"]] = np.abs(base0[BAND_IDX["cond_surf"]]) + 1.0
    rad0 = rng.integers(10, 200, size=(4, grid_size, grid_size), dtype=np.uint8)
    ext0 = rng.integers(10, 200, size=(4, grid_size, grid_size), dtype=np.uint8)
    lidar0 = rng.integers(10, 200, size=(12, grid_size, grid_size), dtype=np.uint8)
    lidar0[-1] = 255
    hydro0 = np.zeros((grid_size, grid_size), dtype=np.float32)

    ref = compute_static_derived_layers(
        base0, valid, rad_u8=rad0, ext_u8=ext0, lidar_u8=lidar0, hydro_impulse=hydro0
    )

    base1 = base0.copy()
    base1[:, c, c] += 25.0
    rad1 = rad0.copy()
    rad1[:, c, c] = 250
    ext1 = ext0.copy()
    ext1[:, c, c] = 250
    lidar1 = lidar0.copy()
    lidar1[:-1, c, c] = 250
    hydro1 = hydro0.copy()
    hydro1[c, c] = 5.0

    pert = compute_static_derived_layers(
        base1, valid, rad_u8=rad1, ext_u8=ext1, lidar_u8=lidar1, hydro_impulse=hydro1
    )

    yy, xx = np.ogrid[:grid_size, :grid_size]
    cheb = np.maximum(np.abs(yy - c), np.abs(xx - c))
    max_r = 0
    for name in STATIC_DERIVED_NAMES:
        diff = np.abs(pert[name] - ref[name])
        changed = np.isfinite(diff) & (diff > 1e-7)
        if np.any(changed):
            max_r = max(max_r, int(cheb[changed].max()))
    return max_r
