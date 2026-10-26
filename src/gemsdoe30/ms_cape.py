"""Multi-Scale Consilient Axial Potential-Edge & Hydrothermal Trace Physics (MS-CAPE).

All Stage-1 spatial operators have exact bounded stencil support <= 12 px (1,200 m,
2.5 km full span) and all Stage-2 trace-continuation operators have exact bounded
stencil support <= 8 px (800 m, 1.7 km gap-bridge span), giving a strictly bounded
composed receptive field <= 20 px (2,000 m). Zero catalogue, label, or registry
rasters are ever read by feature derivation.
"""
from __future__ import annotations

import csv
import hashlib
import heapq
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

TRANSFORM_VERSION = "ms-cape-multiphysics-trace-v1-20261025"
STAGE1_SUPPORT_PX = 12
STAGE2_SUPPORT_PX = 8
SUPPORT_PX = STAGE1_SUPPORT_PX + STAGE2_SUPPORT_PX  # 20 px composed guard

CORE19_NAMES: tuple[str, ...] = (
    "mag_anom",
    "rtp",
    "tmi_hg",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "tc",
    "geod_shearrate",
    "geod_dilaterate",
    "tmi_vg",
    "deq_n100a15",
    "iso_grav_anom_vg",
    "det_elev",
    "iso_grav_anom",
    "tmi",
    "depth_to_base_surf",
    "ieq_n100a15",
    "cond_surf",
    "iso_grav_anom_hg",
    "det_elev_slope",
)

MS_CAPE_NAMES: tuple[str, ...] = (
    # Group 1: Verduzco potential-field tilt & basement contact mechanics (8)
    "grav_tilt",
    "grav_tilt_zero_prox",
    "grav_verduzco_hd_tilt",
    "mag_tilt",
    "mag_verduzco_hd_tilt",
    "rtp_total_horiz_grad",
    "tmi_upward_residual",
    "basement_step_grad",
    # Group 2: Piedmont-toe flexure & mountain-slope deconfounding (8)
    "piedmont_concavity_300m",
    "piedmont_concavity_900m",
    "deconfounded_slope_prominence",
    "slope_break_gradient",
    "basin_margin_transition",
    "lidar_scarp_step",
    "lidar_signed_polarity",
    "lidar_valid_flag",
    # Group 3: 8-azimuth steerable axial lineaments & strike consilience (10)
    "surf_axial_max_1p1km",
    "surf_axial_aniso_1p1km",
    "surf_axial_max_2p5km",
    "surf_axial_aniso_2p5km",
    "surf_cross_ridge_nms",
    "sub_axial_max_2p5km",
    "sub_axial_aniso_2p5km",
    "sub_cross_ridge_nms",
    "cross_modal_strike_consilience",
    "great_basin_anderson_strike",
    # Group 4: Deconfounded GeoDAWN radiometrics & GDR hydrothermal upflow (6)
    "rad_k_th_alteration",
    "rad_u_th_fracture_radon",
    "mt_clay_cap_edge",
    "hydro_upflow_thermal_plume",
    "hydro_upgradient_source_focus",
    "paleo_probe_geothermal_halo",
)

STAGE2_TRACE_NAMES: tuple[str, ...] = (
    "p1_raw",
    "p1_logit",
    "p1_axial_max_900m",
    "p1_axial_max_1700m",
    "p1_gap_bridge_1700m",
    "p1_tip_continuation_1700m",
    "p1_axial_anisotropy",
    "p1_cross_strike_sharpness_300m",
    "p1_cross_strike_sharpness_600m",
    "p1_local_contrast_800m",
)

ALL_STAGE1_FEATURE_NAMES: tuple[str, ...] = CORE19_NAMES + MS_CAPE_NAMES

# Indices in Stage-1 stack [0..50] kept as physical regime conditioning in Stage 2
STAGE2_REGIME_FEATURE_NAMES: tuple[str, ...] = (
    "det_elev",
    "depth_to_base_surf",
    "cond_surf",
    "grav_tilt_zero_prox",
    "grav_verduzco_hd_tilt",
    "mag_verduzco_hd_tilt",
    "basement_step_grad",
    "piedmont_concavity_300m",
    "piedmont_concavity_900m",
    "deconfounded_slope_prominence",
    "basin_margin_transition",
    "lidar_signed_polarity",
    "lidar_valid_flag",
    "surf_axial_aniso_2p5km",
    "sub_axial_aniso_2p5km",
    "cross_modal_strike_consilience",
    "rad_k_th_alteration",
    "hydro_upflow_thermal_plume",
)


def _clean_band(raw: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sanitize float32 band (replacing -3.4e38 sentinels / non-finites with median inside valid)."""
    arr = np.asarray(raw, dtype=np.float32)
    fin = valid & np.isfinite(arr) & (arr > -1e30) & (arr < 1e30)
    out = np.zeros(arr.shape, dtype=np.float32)
    if np.any(fin):
        med = float(np.median(arr[fin]))
        out[fin] = arr[fin]
        missing_in_valid = valid & ~fin
        if np.any(missing_in_valid):
            out[missing_in_valid] = med
    return out, fin


def masked_box_mean(field: np.ndarray, valid: np.ndarray, radius: int) -> np.ndarray:
    """Exact footprint-normalized (2*radius+1)^2 box mean via 2D integral images.

    Support is strictly bounded to Chebyshev distance <= radius with zero outside bleed.
    """
    if radius <= 0:
        out = np.zeros_like(field, dtype=np.float32)
        out[valid] = field[valid]
        return out
    h, w = field.shape
    r = int(radius)
    val_f = np.where(valid, field, 0.0).astype(np.float64)
    msk_f = valid.astype(np.float64)

    def _window_sum(a: np.ndarray) -> np.ndarray:
        pad = np.pad(a, ((r + 1, r), (r + 1, r)), mode="constant", constant_values=0.0)
        cs = pad.cumsum(axis=0).cumsum(axis=1)
        y1 = np.arange(2 * r + 1, h + 2 * r + 1)
        y0 = np.arange(0, h)
        x1 = np.arange(2 * r + 1, w + 2 * r + 1)
        x0 = np.arange(0, w)
        return cs[np.ix_(y1, x1)] - cs[np.ix_(y0, x1)] - cs[np.ix_(y1, x0)] + cs[np.ix_(y0, x0)]

    num = _window_sum(val_f)
    den = np.maximum(_window_sum(msk_f), 1e-8)
    out = (num / den).astype(np.float32)
    out[~valid] = 0.0
    return out


def masked_smooth(field: np.ndarray, valid: np.ndarray, radius: int) -> np.ndarray:
    """Smooth tent/B-spline isotropic filter with exact support <= radius."""
    if radius <= 1:
        return masked_box_mean(field, valid, radius)
    r1 = radius // 2
    r2 = radius - r1
    return masked_box_mean(masked_box_mean(field, valid, r1), valid, r2)


def masked_grad(field: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Footprint-safe 3x3 central differences (support = 1 px) with boundary reflection."""
    f = np.where(valid, field, 0.0).astype(np.float32)
    v = np.asarray(valid, dtype=bool)
    up = np.zeros_like(f)
    dn = np.zeros_like(f)
    lf = np.zeros_like(f)
    rt = np.zeros_like(f)

    up[1:, :] = np.where(v[:-1, :], f[:-1, :], f[1:, :])
    up[0, :] = f[0, :]
    dn[:-1, :] = np.where(v[1:, :], f[1:, :], f[:-1, :])
    dn[-1, :] = f[-1, :]

    lf[:, 1:] = np.where(v[:, :-1], f[:, :-1], f[:, 1:])
    lf[:, 0] = f[:, 0]
    rt[:, :-1] = np.where(v[:, 1:], f[:, 1:], f[:, :-1])
    rt[:, -1] = f[:, -1]

    gy = 0.5 * (dn - up)
    gx = 0.5 * (rt - lf)
    gy[~v] = 0.0
    gx[~v] = 0.0
    mag = np.hypot(gx, gy).astype(np.float32)
    mag[~v] = 0.0
    return gy, gx, mag


def _shift2d(arr: np.ndarray, dr: int, dc: int) -> np.ndarray:
    """Zero-padded 2D integer shift without wraparound."""
    h, w = arr.shape
    out = np.zeros_like(arr)
    r_src0 = max(0, -dr)
    r_src1 = min(h, h - dr)
    c_src0 = max(0, -dc)
    c_src1 = min(w, w - dc)
    if r_src1 <= r_src0 or c_src1 <= c_src0:
        return out
    out[r_src0 + dr : r_src1 + dr, c_src0 + dc : c_src1 + dc] = arr[r_src0:r_src1, c_src0:c_src1]
    return out


def axial_line_bank(
    field: np.ndarray,
    valid: np.ndarray,
    half_len: int,
    *,
    n_azimuths: int = 8,
) -> dict[str, np.ndarray]:
    """Evaluate n_azimuths steerable axial rays of exact Euclidean support <= half_len.

    Streams orthogonal azimuth pairs (m, m + n_azimuths // 2) so peak memory stays
    O(H * W) instead of O(n_azimuths * H * W), while producing exact bit-identical
    maxima, orthogonal anisotropy, wash-gap bridge, and tip continuation maps.
    """
    if half_len < 1 or n_azimuths % 2 != 0:
        raise ValueError("half_len >= 1 and even n_azimuths required")
    f = np.where(valid, field, 0.0).astype(np.float32)
    v = valid.astype(np.float32)
    h, w = f.shape
    half_az = n_azimuths // 2

    def _eval_azimuth(m: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        phi = m * np.pi / n_azimuths
        sin_p = float(np.sin(phi))
        cos_p = float(np.cos(phi))
        fwd_num = np.zeros((h, w), dtype=np.float32)
        fwd_den = np.zeros((h, w), dtype=np.float32)
        bwd_num = np.zeros((h, w), dtype=np.float32)
        bwd_den = np.zeros((h, w), dtype=np.float32)
        seen_steps: set[tuple[int, int]] = set()
        for t in range(1, half_len + 1):
            dr = int(round(-t * cos_p))
            dc = int(round(t * sin_p))
            if dr == 0 and dc == 0:
                continue
            if dr * dr + dc * dc > half_len * half_len:
                continue
            if (dr, dc) in seen_steps:
                continue
            seen_steps.add((dr, dc))
            fwd_num += _shift2d(f, -dr, -dc)
            fwd_den += _shift2d(v, -dr, -dc)
            bwd_num += _shift2d(f, dr, dc)
            bwd_den += _shift2d(v, dr, dc)
        fwd_m = np.where(fwd_den > 0, fwd_num / np.maximum(fwd_den, 1.0), f)
        bwd_m = np.where(bwd_den > 0, bwd_num / np.maximum(bwd_den, 1.0), f)
        tot_m = (fwd_num + bwd_num + f) / np.maximum(fwd_den + bwd_den + v, 1.0)
        fwd_m[~valid] = 0.0
        bwd_m[~valid] = 0.0
        tot_m[~valid] = 0.0
        return tot_m, fwd_m, bwd_m

    axial_max = np.full((h, w), -np.inf, dtype=np.float32)
    axial_ortho = np.zeros((h, w), dtype=np.float32)
    best_idx = np.zeros((h, w), dtype=np.uint8)
    gap_bridge = np.full((h, w), -np.inf, dtype=np.float32)
    best_pair_max = np.full((h, w), -np.inf, dtype=np.float32)

    # First pass over orthogonal pairs (m, m + half_az) keeps only 2 azimuths in RAM at a time!
    for m in range(half_az):
        m_ort = m + half_az
        tot_a, fwd_a, bwd_a = _eval_azimuth(m)
        tot_b, fwd_b, bwd_b = _eval_azimuth(m_ort)

        # Update from m (whose orthogonal partner is m_ort -> tot_b; tie-break favors smaller m)
        better_a = (tot_a > axial_max) | ((tot_a == axial_max) & (m < best_idx))
        axial_max = np.where(better_a, tot_a, axial_max)
        axial_ortho = np.where(better_a, tot_b, axial_ortho)
        best_idx = np.where(better_a, np.uint8(m), best_idx)

        gap_bridge = np.maximum(gap_bridge, np.minimum(fwd_a, bwd_a))
        best_pair_max = np.maximum(best_pair_max, np.maximum(fwd_a, bwd_a))
        del fwd_a, bwd_a

        # Update from m_ort (whose orthogonal partner is m -> tot_a)
        better_b = (tot_b > axial_max) | ((tot_b == axial_max) & (m_ort < best_idx))
        axial_max = np.where(better_b, tot_b, axial_max)
        axial_ortho = np.where(better_b, tot_a, axial_ortho)
        best_idx = np.where(better_b, np.uint8(m_ort), best_idx)

        gap_bridge = np.maximum(gap_bridge, np.minimum(fwd_b, bwd_b))
        best_pair_max = np.maximum(best_pair_max, np.maximum(fwd_b, bwd_b))
        del tot_a, tot_b, fwd_b, bwd_b

    denom = np.abs(axial_max) + np.abs(axial_ortho) + 1e-5
    axial_aniso = ((axial_max - axial_ortho) / denom).astype(np.float32)
    axial_aniso[~valid] = 0.0
    axial_max[~valid] = 0.0
    best_idx[~valid] = 0

    tip_cont = (best_pair_max - gap_bridge).astype(np.float32)
    gap_bridge[~valid] = 0.0
    tip_cont[~valid] = 0.0

    best_phi = (best_idx.astype(np.float32) * (np.pi / n_azimuths)).astype(np.float32)
    best_phi[~valid] = 0.0

    return {
        "axial_max": axial_max,
        "axial_aniso": axial_aniso,
        "best_idx": best_idx,
        "best_phi": best_phi,
        "gap_bridge": gap_bridge.astype(np.float32),
        "tip_cont": tip_cont,
    }


def cross_strike_sharpness(
    field: np.ndarray,
    valid: np.ndarray,
    best_idx: np.ndarray,
    offset_px: int,
    *,
    n_azimuths: int = 8,
) -> np.ndarray:
    """Contrast between center ridge value and orthogonal flank mean at +-offset_px."""
    f = np.where(valid, field, 0.0).astype(np.float32)
    v = valid.astype(np.float32)
    flank = np.zeros_like(f)
    for m in range(n_azimuths):
        mask_m = valid & (best_idx == m)
        if not np.any(mask_m):
            continue
        phi_norm = m * np.pi / n_azimuths + 0.5 * np.pi
        dr = int(round(-offset_px * np.cos(phi_norm)))
        dc = int(round(offset_px * np.sin(phi_norm)))
        p_val = _shift2d(f, -dr, -dc)
        p_msk = _shift2d(v, -dr, -dc)
        n_val = _shift2d(f, dr, dc)
        n_msk = _shift2d(v, dr, dc)
        den = p_msk + n_msk
        avg_flank = np.where(den > 0, (p_val + n_val) / np.maximum(den, 1.0), f)
        flank[mask_m] = f[mask_m] - avg_flank[mask_m]
    flank[~valid] = 0.0
    return flank


def _robust_unit_norm(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Map positive/signed physical field to bounded dimensionless scale using global footprint IQR."""
    vals = arr[valid]
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    scale = max(float(q75 - q25), float(np.std(vals)), 1e-6)
    out = np.clip((arr - med) / scale, -6.0, 6.0).astype(np.float32)
    out[~valid] = 0.0
    return out


def _radial_cone_convolve(impulse: np.ndarray, valid: np.ndarray, radius_px: int) -> np.ndarray:
    """Bounded Euclidean radial cone kernel (support strictly <= radius_px)."""
    r = int(radius_px)
    acc = np.zeros_like(impulse, dtype=np.float32)
    w_sum = 0.0
    for dr in range(-r, r + 1):
        for dc in range(-r, r + 1):
            d = float(np.hypot(dr, dc))
            if d > r:
                continue
            w = max(0.0, 1.0 - d / (r + 1.0))
            acc += w * _shift2d(impulse, dr, dc)
            w_sum += w
    if w_sum > 0:
        acc /= float(w_sum)
    acc[~valid] = 0.0
    return acc


def load_wellspring_thermal_impulse(
    csv_path: Path,
    shape: tuple[int, int],
    valid: np.ndarray,
) -> np.ndarray:
    """Rasterize GDR-1391 well/spring thermal excess strictly without catalogue columns."""
    Forbidden = {"dist_known_fault_px"}
    impulse = np.zeros(shape, dtype=np.float32)
    h, w = shape
    with csv_path.open("r", encoding="utf-8", errors="replace") as stream:
        reader = csv.DictReader(stream)
        allowed_cols = ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c")
        for col_name in allowed_cols:
            if col_name in Forbidden:
                raise AssertionError("forbidden column requested")
        for rec in reader:
            try:
                r = int(float(rec["row"]))
                c = int(float(rec["col"]))
            except (KeyError, ValueError):
                continue
            if not (0 <= r < h and 0 <= c < w) or not valid[r, c]:
                continue

            def _num(key: str) -> float:
                raw = (rec.get(key) or "").strip()
                if not raw:
                    return 0.0
                try:
                    val = float(raw)
                    return val if np.isfinite(val) and -50.0 < val < 450.0 else 0.0
                except ValueError:
                    return 0.0

            t_obs = _num("temp_c")
            t_qtz = _num("geothermquartz_c")
            t_chl = _num("geothermchalc_c")
            t_chem = max(t_qtz, t_chl)
            # Thermal anomaly above 20 C Great Basin ambient groundwater + chemical disequilibrium
            excess = max(0.0, t_obs - 20.0) + 0.35 * max(0.0, t_chem - 80.0)
            score = float(np.log1p(excess))
            if score > impulse[r, c]:
                impulse[r, c] = score
    return impulse


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build_ms_cape_feature_memmap(
    base_features: np.ndarray,
    valid: np.ndarray,
    external_dir: Path,
    memmap_path: Path,
) -> tuple[np.memmap, dict[str, Any]]:
    """Compute all 32 MS-CAPE physical channels into a float32 disk memmap (low RAM).

    Every operator has spatial support <= STAGE1_SUPPORT_PX (12 px = 1,200 m).
    """
    _, h, w = base_features.shape
    if valid.shape != (h, w):
        raise ValueError("valid mask shape mismatch")
    memmap_path.parent.mkdir(parents=True, exist_ok=True)
    out = np.memmap(memmap_path, dtype=np.float32, mode="w+", shape=(len(MS_CAPE_NAMES), h, w))

    # Load clean needed base bands one-by-one
    rtp, _ = _clean_band(base_features[1], valid)
    tmi_hg, _ = _clean_band(base_features[2], valid)
    geod_2nd, _ = _clean_band(base_features[3], valid)
    geod_shear, _ = _clean_band(base_features[6], valid)
    tmi_vg, _ = _clean_band(base_features[8], valid)
    grav_vg, _ = _clean_band(base_features[10], valid)
    det_elev, _ = _clean_band(base_features[11], valid)
    tmi, _ = _clean_band(base_features[13], valid)
    depth_base, _ = _clean_band(base_features[14], valid)
    cond_surf, _ = _clean_band(base_features[16], valid)
    grav_hg, _ = _clean_band(base_features[17], valid)
    elev_slope, _ = _clean_band(base_features[18], valid)

    # External verified inputs (zero catalogue layers!)
    ext_files = {
        "lidar_scarp": external_dir / "lidar_scarp_features_u8.tif",
        "geodawn_rad": external_dir / "geodawn_rad_u8.tif",
        "geodawn_ext": external_dir / "geodawn_extensions_u8.tif",
        "gdr_probes": external_dir / "derived_gdr_2m_probes_100m_u8.tif",
        "gdr_paleo": external_dir / "derived_gdr_paleo_100m_u8.tif",
        "gdr_volcanics": external_dir / "derived_gdr_volcanics_100m_u8.tif",
        "gdr_wellspring": external_dir / "gdr_wellspring_in_footprint.csv",
    }
    ext_hashes = {k: _file_sha256(p) for k, p in ext_files.items()}

    # --- Group 1: Verduzco Potential-Field Contact Mechanics (support <= 6 px) ---
    grav_hg_pos = np.maximum(np.abs(grav_hg), 1e-5)
    grav_tilt = np.arctan2(grav_vg, grav_hg_pos).astype(np.float32)
    grav_tilt[~valid] = 0.0
    grav_tilt_zero = np.cos(grav_tilt).astype(np.float32)
    grav_tilt_zero[~valid] = 0.0
    _, _, grav_hd_tilt = masked_grad(grav_tilt, valid)

    mag_hg_pos = np.maximum(np.abs(tmi_hg), 1e-5)
    mag_tilt = np.arctan2(tmi_vg, mag_hg_pos).astype(np.float32)
    mag_tilt[~valid] = 0.0
    _, _, mag_hd_tilt_raw = masked_grad(mag_tilt, valid)
    mag_hd_tilt = (mag_hd_tilt_raw * np.cos(mag_tilt)).astype(np.float32)
    mag_hd_tilt[~valid] = 0.0

    _, _, rtp_hgrad = masked_grad(rtp, valid)

    with rasterio.open(ext_files["geodawn_ext"]) as ds:
        uk_u8 = ds.read(2).astype(np.float32)
        tmi_up150_u8 = ds.read(4).astype(np.float32)
    # Local 600m high-pass comparison of TMI vs 150m upward-continued TMI (support <= 6 px)
    tmi_hp = tmi - masked_smooth(tmi, valid, 6)
    up_hp = tmi_up150_u8 - masked_smooth(tmi_up150_u8, valid, 6)
    tmi_up_res = (_robust_unit_norm(tmi_hp, valid) - 0.75 * _robust_unit_norm(up_hp, valid)).astype(np.float32)
    tmi_up_res[~valid] = 0.0

    _, _, base_step = masked_grad(masked_smooth(depth_base, valid, 1), valid)

    out[0] = grav_tilt
    out[1] = grav_tilt_zero
    out[2] = grav_hd_tilt
    out[3] = mag_tilt
    out[4] = mag_hd_tilt
    out[5] = rtp_hgrad
    out[6] = tmi_up_res
    out[7] = base_step
    out.flush()
    del rtp, tmi_hg, tmi_vg, grav_vg, tmi, grav_hg, grav_tilt, mag_tilt, mag_hd_tilt, tmi_up150_u8, tmi_hp, up_hp, tmi_up_res

    # --- Group 2: Piedmont-Toe Flexure & Ridge Deconfounding (support <= 10 px) ---
    elev_s3 = masked_smooth(det_elev, valid, 3)
    elev_s9 = masked_smooth(det_elev, valid, 8)  # Chebyshev 8 -> Euclidean 11.31 <= 12 px
    # Concave piedmont toe has det_elev < regional mean -> (elev_s3 - det_elev) > 0
    pied_concav_300 = (elev_s3 - det_elev).astype(np.float32)
    pied_concav_300[~valid] = 0.0
    pied_concav_900 = (elev_s9 - det_elev).astype(np.float32)
    pied_concav_900[~valid] = 0.0

    slope_pos = np.maximum(elev_slope, 0.0)
    slope_floor = max(float(np.percentile(slope_pos[valid], 30.0)), 1e-4)
    reg_slope = masked_smooth(slope_pos, valid, 8)  # Chebyshev 8 -> Euclidean 11.31 <= 12 px
    deconf_slope = (slope_pos / (reg_slope + slope_floor)).astype(np.float32)
    deconf_slope[~valid] = 0.0

    _, _, slope_break = masked_grad(slope_pos, valid)
    _, _, elev_grad = masked_grad(det_elev, valid)
    basin_trans = (np.log1p(np.maximum(depth_base, 0.0)) * elev_grad).astype(np.float32)
    basin_trans[~valid] = 0.0

    with rasterio.open(ext_files["lidar_scarp"]) as ds:
        ex_max = ds.read(1).astype(np.float32) / 255.0
        step_max = ds.read(3).astype(np.float32) / 255.0
        downface = ds.read(6).astype(np.float32)
        upface = ds.read(7).astype(np.float32)
        coh100 = ds.read(10).astype(np.float32) / 255.0
        lidar_val = (ds.read(12) > 0) & valid

    lidar_step_raw = 0.5 * (ex_max + step_max)
    # Smoothly impute non-LiDAR footprint with scaled deconfounded 100m slope prominence
    fallback_step = np.clip(deconf_slope / (float(np.percentile(deconf_slope[valid], 95.0)) + 1e-5), 0.0, 1.0)
    lidar_step = np.where(lidar_val, lidar_step_raw, 0.65 * fallback_step).astype(np.float32)
    lidar_step[~valid] = 0.0

    polarity_raw = (np.abs(downface - upface) / (downface + upface + 5.0)) * coh100
    lidar_polarity = np.where(lidar_val, polarity_raw, 0.0).astype(np.float32)
    lidar_polarity[~valid] = 0.0
    lidar_flag = lidar_val.astype(np.float32)

    out[8] = pied_concav_300
    out[9] = pied_concav_900
    out[10] = deconf_slope
    out[11] = slope_break
    out[12] = basin_trans
    out[13] = lidar_step
    out[14] = lidar_polarity
    out[15] = lidar_flag
    out.flush()
    del elev_s3, elev_s9, pied_concav_300, pied_concav_900, reg_slope, elev_grad, basin_trans
    del ex_max, step_max, downface, upface, coh100, lidar_val, lidar_step_raw, fallback_step, polarity_raw, lidar_flag

    # --- Group 3: 8-Azimuth Steerable Axial Lineaments & Strike Consilience (support <= 12 px) ---
    e_surf = np.maximum(
        0.0,
        0.40 * _robust_unit_norm(deconf_slope, valid)
        + 0.30 * _robust_unit_norm(slope_break, valid)
        + 0.30 * _robust_unit_norm(lidar_step + lidar_polarity, valid),
    ).astype(np.float32)
    e_surf[~valid] = 0.0

    e_sub = np.maximum(
        0.0,
        0.40 * _robust_unit_norm(grav_hd_tilt * grav_tilt_zero, valid)
        + 0.30 * _robust_unit_norm(rtp_hgrad, valid)
        + 0.30 * _robust_unit_norm(base_step, valid),
    ).astype(np.float32)
    e_sub[~valid] = 0.0

    surf_b5 = axial_line_bank(e_surf, valid, half_len=5, n_azimuths=8)
    surf_b12 = axial_line_bank(e_surf, valid, half_len=12, n_azimuths=8)
    sub_b12 = axial_line_bank(e_sub, valid, half_len=12, n_azimuths=8)

    surf_nms = cross_strike_sharpness(e_surf, valid, surf_b12["best_idx"], offset_px=3, n_azimuths=8)
    sub_nms = cross_strike_sharpness(e_sub, valid, sub_b12["best_idx"], offset_px=3, n_azimuths=8)

    dphi = surf_b12["best_phi"] - sub_b12["best_phi"]
    aniso_prod = np.sqrt(np.maximum(surf_b12["axial_aniso"], 0.0) * np.maximum(sub_b12["axial_aniso"], 0.0))
    strike_consil = (np.cos(2.0 * dphi) * aniso_prod).astype(np.float32)
    strike_consil[~valid] = 0.0

    # Northwestern Great Basin dominant N22E Andersonian normal-fault strike + Walker Lane shear modulation
    phi_gb = np.deg2rad(22.5)
    phi_wl = np.deg2rad(145.0)  # N35W dextral/transtensional Walker Lane strike
    shear_frac = np.clip(np.abs(geod_shear) / ( np.abs(geod_2nd) + 1e-6 ), 0.0, 1.0)
    joint_phi = np.where(e_surf >= e_sub, surf_b12["best_phi"], sub_b12["best_phi"])
    anderson_align = (
        (1.0 - 0.35 * shear_frac) * np.cos(2.0 * (joint_phi - phi_gb))
        + 0.35 * shear_frac * np.cos(2.0 * (joint_phi - phi_wl))
    ).astype(np.float32)
    anderson_align[~valid] = 0.0

    out[16] = surf_b5["axial_max"]
    out[17] = surf_b5["axial_aniso"]
    out[18] = surf_b12["axial_max"]
    out[19] = surf_b12["axial_aniso"]
    out[20] = surf_nms
    out[21] = sub_b12["axial_max"]
    out[22] = sub_b12["axial_aniso"]
    out[23] = sub_nms
    out[24] = strike_consil
    out[25] = anderson_align
    out.flush()
    del grav_tilt_zero, grav_hd_tilt, rtp_hgrad, base_step, deconf_slope, slope_break, lidar_step, lidar_polarity
    del e_surf, e_sub, surf_b5, surf_b12, sub_b12, surf_nms, sub_nms, dphi, aniso_prod, strike_consil, anderson_align
    del geod_2nd, geod_shear, depth_base, elev_slope

    # --- Group 4: Deconfounded GeoDAWN Radiometrics & GDR Hydrothermal Upflow (support <= 12 px) ---
    with rasterio.open(ext_files["geodawn_rad"]) as ds:
        rad_k = ds.read(1).astype(np.float32)
        rad_th = ds.read(2).astype(np.float32)
        rad_u = ds.read(3).astype(np.float32)

    k_th_ratio = rad_k / (rad_th + 10.0)
    k_th_hp = (k_th_ratio - masked_smooth(k_th_ratio, valid, 8)).astype(np.float32)
    k_th_hp[~valid] = 0.0

    u_th_ratio = rad_u / (rad_th + 10.0) + 0.5 * (uk_u8 / 255.0)
    u_th_hp = (u_th_ratio - masked_smooth(u_th_ratio, valid, 8)).astype(np.float32)
    u_th_hp[~valid] = 0.0

    _, _, cond_grad = masked_grad(cond_surf, valid)
    cond_hp = cond_surf - masked_smooth(cond_surf, valid, 8)
    mt_edge = (0.6 * _robust_unit_norm(cond_grad, valid) + 0.4 * _robust_unit_norm(cond_hp, valid)).astype(np.float32)
    mt_edge[~valid] = 0.0

    ws_imp = load_wellspring_thermal_impulse(ext_files["gdr_wellspring"], (h, w), valid)
    thermal_plume = _radial_cone_convolve(ws_imp, valid, radius_px=11)

    # Up-hydraulic-gradient back-projection: positive upslope of thermal outflow plumes!
    elev_gy, elev_gx, elev_gmag = masked_grad(masked_smooth(det_elev, valid, 3), valid)
    plume_gy, plume_gx, _ = masked_grad(thermal_plume, valid)
    # Upslope side of plume has nabla(elev) pointing away from basin AND nabla(plume) pointing toward spring (downslope),
    # so nabla(elev) . nabla(plume) < 0 -> -(nabla(elev) . nabla(plume)) > 0 on the piedmont source fault!
    elev_norm = np.maximum(elev_gmag, 1e-4)
    upgrad_focus = np.maximum(0.0, -(elev_gy * plume_gy + elev_gx * plume_gx) / elev_norm).astype(np.float32)
    upgrad_focus[~valid] = 0.0

    with rasterio.open(ext_files["gdr_paleo"]) as ds:
        paleo_u8 = (ds.read(1) > 0).astype(np.float32)
    with rasterio.open(ext_files["gdr_probes"]) as ds:
        probes_u8 = (ds.read(1) > 0).astype(np.float32)
    with rasterio.open(ext_files["gdr_volcanics"]) as ds:
        volc_u8 = (ds.read(1) > 0).astype(np.float32)
    geoth_imp = (2.0 * paleo_u8 + 1.0 * probes_u8 + 0.35 * volc_u8) * valid.astype(np.float32)
    paleo_probe_halo = _radial_cone_convolve(geoth_imp, valid, radius_px=11)

    out[26] = k_th_hp
    out[27] = u_th_hp
    out[28] = mt_edge
    out[29] = thermal_plume
    out[30] = upgrad_focus
    out[31] = paleo_probe_halo
    out.flush()

    receipt = {
        "transform_module": "src/gemsdoe30/ms_cape.py",
        "transform_version": TRANSFORM_VERSION,
        "stage1_support_px": STAGE1_SUPPORT_PX,
        "stage2_support_px": STAGE2_SUPPORT_PX,
        "support_px": SUPPORT_PX,
        "feature_names": list(MS_CAPE_NAMES),
        "external_source_sha256": ext_hashes,
        "shape": [int(len(MS_CAPE_NAMES)), int(h), int(w)],
    }
    return out, receipt


def compute_stage2_trace_features(prob_s1: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Derive 10 anisotropic ridge-continuation & wash-gap-bridge features (support <= 8 px)."""
    p = np.where(valid, np.clip(prob_s1, 1e-6, 1.0 - 1e-6), 0.0).astype(np.float32)
    h, w = p.shape
    feats = np.zeros((len(STAGE2_TRACE_NAMES), h, w), dtype=np.float32)

    logit = np.log(np.clip(p, 1e-6, 1.0 - 1e-6) / np.clip(1.0 - p, 1e-6, 1.0)).astype(np.float32)
    logit[~valid] = 0.0

    b4 = axial_line_bank(p, valid, half_len=4, n_azimuths=8)
    b8 = axial_line_bank(p, valid, half_len=8, n_azimuths=8)

    sharp_3 = cross_strike_sharpness(p, valid, b8["best_idx"], offset_px=3, n_azimuths=8)
    sharp_6 = cross_strike_sharpness(p, valid, b8["best_idx"], offset_px=6, n_azimuths=8)
    loc_mean_8 = masked_smooth(p, valid, 5)  # Chebyshev 5 -> Euclidean 7.07 <= 8 px
    loc_contrast = (p - loc_mean_8).astype(np.float32)
    loc_contrast[~valid] = 0.0

    feats[0] = p
    feats[1] = logit
    feats[2] = b4["axial_max"]
    feats[3] = b8["axial_max"]
    feats[4] = b8["gap_bridge"]
    feats[5] = b8["tip_cont"]
    feats[6] = b8["axial_aniso"]
    feats[7] = sharp_3
    feats[8] = sharp_6
    feats[9] = loc_contrast
    return feats


def recalibrate_prior_odds(
    prob_subsampled: np.ndarray,
    pi_true: float,
    pi_sample: float,
    valid: np.ndarray,
) -> np.ndarray:
    """Exact Bayes prior-odds adjustment from subsampled training base rate to population base rate."""
    p = np.clip(np.asarray(prob_subsampled, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    w_pos = float(pi_true) / max(float(pi_sample), 1e-9)
    w_neg = (1.0 - float(pi_true)) / max(1.0 - float(pi_sample), 1e-9)
    num = w_pos * p
    cal = (num / np.maximum(num + w_neg * (1.0 - p), 1e-12)).astype(np.float32)
    cal[~valid] = 0.0
    return cal


def _dti_kernel_offsets(radius_px: float = 3.0) -> list[tuple[int, int, float]]:
    r_lim = int(np.ceil(radius_px))
    offsets: list[tuple[int, int, float]] = []
    for dr in range(-r_lim, r_lim + 1):
        for dc in range(-r_lim, r_lim + 1):
            d = float(np.hypot(dr, dc))
            if d < radius_px:
                k_val = float(1.0 - d / radius_px)
                offsets.append((dr, dc, k_val))
    return offsets


def submod_dti_select(
    calibrated_prob: np.ndarray,
    active_mask: np.ndarray,
    visible_faults: np.ndarray,
    budget: int,
    *,
    radius_px: float = 3.0,
    flank_exclusion_px: float = 2.0,
    min_sep_px: float = 2.2,
    pool_multiplier: int = 24,
) -> np.ndarray:
    """Exact Minoux lazy-greedy submodular 300 m DTI kernel cover with flank hygiene.

    Maximizes E[TP_w(S)] = sum_{y in active} q(y) max_{x in S} k(d(x, y)) over binary
    unit-amplitude dot sets S of exact cardinality ``budget``, excluding the unrewarded
    <= flank_exclusion_px collar around visible_faults and enforcing minimum Euclidean
    dot spacing >= min_sep_px to prevent overconfident local ridge clumping.
    """
    if budget <= 0:
        return np.zeros_like(calibrated_prob, dtype=np.float32)
    h, w = calibrated_prob.shape
    active = np.asarray(active_mask, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool)

    if flank_exclusion_px > 0 and np.any(vis):
        dist_vis = distance_transform_edt(~vis)
        eligible = active & (dist_vis > flank_exclusion_px)
        if int(eligible.sum()) < budget * 6:
            eligible = active
    else:
        eligible = active

    q = np.where(active, np.maximum(calibrated_prob, 0.0), 0.0).astype(np.float32)
    offsets = _dti_kernel_offsets(radius_px)

    # Initial marginal gain g_0(x) = sum_{(dr,dc)} q(x + d) * k(|d|) + tiny spine-centering tie-break
    g0 = 0.05 * q.copy()
    for dr, dc, k_val in offsets:
        g0 += k_val * _shift2d(q, -dr, -dc)
    g0[~eligible] = -1.0

    elig_coords = np.flatnonzero(eligible)
    if elig_coords.size < budget:
        raise ValueError(f"eligible domain ({elig_coords.size}) smaller than dot budget ({budget})")

    pool_size = min(int(elig_coords.size), max(int(budget * pool_multiplier), 280_000))
    flat_g0 = g0.ravel()
    elig_scores = flat_g0[elig_coords]
    if pool_size < elig_coords.size:
        part_idx = np.argpartition(-elig_scores, pool_size - 1)[:pool_size]
        cand_flat = elig_coords[part_idx]
    else:
        cand_flat = elig_coords

    # Deterministic tie-break by flat coordinate index
    heap: list[tuple[float, int]] = [(-float(flat_g0[idx]), int(idx)) for idx in cand_flat]
    heapq.heapify(heap)

    # Pad arrays by r_pad so inner scalar loop needs zero bounds checks!
    r_pad = max(int(np.ceil(radius_px)), int(np.ceil(min_sep_px))) + 1
    hp, wp = h + 2 * r_pad, w + 2 * r_pad
    q_pad = np.zeros((hp, wp), dtype=np.float32)
    q_pad[r_pad : r_pad + h, r_pad : r_pad + w] = q
    cov_pad = np.zeros((hp, wp), dtype=np.float32)
    blocked_pad = np.zeros((hp, wp), dtype=np.uint8)

    q_1d = q_pad.ravel()
    cov_1d = cov_pad.ravel()
    blk_1d = blocked_pad.ravel()

    k_strides = tuple((dr * wp + dc, float(kv)) for dr, dc, kv in offsets)
    sep_lim = int(np.ceil(min_sep_px))
    sep_strides = tuple(
        dr * wp + dc
        for dr in range(-sep_lim, sep_lim + 1)
        for dc in range(-sep_lim, sep_lim + 1)
        if (dr * dr + dc * dc) < (min_sep_px * min_sep_px)
    )

    emitted = np.zeros((h, w), dtype=np.float32)
    accepted = 0

    while accepted < budget and heap:
        neg_ub, idx = heapq.heappop(heap)
        r = idx // w
        c = idx % w
        p_idx = (r + r_pad) * wp + (c + r_pad)
        if blk_1d[p_idx]:
            continue

        # Recompute exact submodular marginal gain against current kernel coverage cov_1d
        gain = 0.05 * float(q_1d[p_idx]) * max(0.0, 1.0 - float(cov_1d[p_idx]))
        for d_off, kv in k_strides:
            n_idx = p_idx + d_off
            rem = kv - float(cov_1d[n_idx])
            if rem > 0.0:
                gain += float(q_1d[n_idx]) * rem

        # Minoux lazy check: if gain >= next best upper bound in heap, accept immediately!
        next_ub = -heap[0][0] if heap else -1.0
        if gain + 1e-12 >= next_ub:
            emitted[r, c] = 1.0
            accepted += 1
            for d_off, kv in k_strides:
                n_idx = p_idx + d_off
                if kv > cov_1d[n_idx]:
                    cov_1d[n_idx] = kv
            for s_off in sep_strides:
                blk_1d[p_idx + s_off] = 1
        else:
            heapq.heappush(heap, (-gain, idx))

    # Deterministic fallback over remaining unblocked eligible pixels if candidate pool saturated
    if accepted < budget:
        order = elig_coords[np.argsort(-elig_scores, kind="mergesort")]
        for idx in order:
            if accepted >= budget:
                break
            r = int(idx) // w
            c = int(idx) % w
            if emitted[r, c] > 0:
                continue
            p_idx = (r + r_pad) * wp + (c + r_pad)
            if blk_1d[p_idx]:
                continue
            emitted[r, c] = 1.0
            accepted += 1
            for s_off in sep_strides:
                blk_1d[p_idx + s_off] = 1

    # Final ultra-defensive fallback if min_sep packing ever exhausted tiny synthetic grids
    if accepted < budget:
        order = elig_coords[np.argsort(-elig_scores, kind="mergesort")]
        for idx in order:
            if accepted >= budget:
                break
            r = int(idx) // w
            c = int(idx) % w
            if emitted[r, c] == 0.0:
                emitted[r, c] = 1.0
                accepted += 1

    return emitted
