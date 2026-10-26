"""Cover-Compensated 3D Laplace/Poisson & 1.8 km Radon Curvilinear Discontinuity (`CSR-1`).

Every static operator in this module is strictly label-free, catalogue-free, free
of global normalization quantiles, and bounded in Euclidean spatial support:

* Worst-case exact Euclidean reach from raw pixels: ``14.66 px`` (1-px finite
  difference ``sqrt(2) = 1.414 px`` + ``sigma = 1.0, truncate = 2.0`` Gaussian
  pre-smooth ``hypot(2, 2) = 2.828 px`` + ``9.0 px`` along-strike Radon offset +
  ``sqrt(2) = 1.414 px`` bilinear interpolation = ``14.657 px <= 15.5 px < 16 px``).
* Guarded at ``SUPPORT_PX = 16``, strictly inside the ``17 px`` (``1,700 m``)
  buffered quadrant whole-component holdout guard (``spatial_segment_folds``).
* Any pixel within the exact operator reach of a non-finite source cell or
  footprint boundary is set to ``NaN`` so sentinel/boundary values never bleed
  into valid geophysical features.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

TRANSFORM_VERSION = "csr-laplace-poisson-radon-v1-20261026"
SUPPORT_PX = 16
GUARD_PX = 17

# 0-based indices into 19-band prepared cache (verified against manifest.json)
IDX_RTP = 1
IDX_TMI_HG = 2
IDX_GEOD_2NDINV = 3
IDX_GRAV_SLOPE = 4
IDX_TC = 5
IDX_GEOD_SHEAR = 6
IDX_GEOD_DILATE = 7
IDX_TMI_VG = 8
IDX_GRAV_DY = 10
IDX_DET_ELEV = 11
IDX_ISO_GRAV = 12
IDX_DEPTH_BASE = 14
IDX_COND_SURF = 16
IDX_GRAV_DX = 17
IDX_ELEV_SLOPE = 18

# Raw band subsets (strictly excluding all 7 regional DC coordinate-proxy bands:
# 0 mag_anom, 1 rtp, 9 deq_n100a15, 11 det_elev, 12 iso_grav_anom, 13 tmi, 15 ieq_n100a15)
CSR_SUB_RAW_INDICES: tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 10, 16, 17)
CSR_FULL_RAW_INDICES: tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 10, 14, 16, 17, 18)

CSR_SUBSURFACE_STATIC_NAMES: tuple[str, ...] = (
    "csr_grav_hgrad",
    "csr_grav_laplace_svd_norm",
    "csr_grav_laplace_crest",
    "csr_grav_poisson_tilt",
    "csr_grav_poisson_crest",
    "csr_mag_tilt_rad",
    "csr_mag_tilt_crest",
    "csr_mag_contact_invdepth",
    "csr_mag_as3d_log",
    "csr_mag_up150_persist",
    "csr_cover_comp_grav",
    "csr_cover_comp_mag",
    "csr_frac_base_step",
    "csr_cond_margin_grad",
    "csr_demag_claycap_index",
    "csr_radon_grav_peak",
    "csr_radon_grav_selectivity",
    "csr_radon_grav_ortho",
    "csr_radon_mag_peak",
    "csr_radon_base_peak",
    "csr_radon_mg_strike_lock",
    "csr_transtensional_partition",
)

CSR_TOPO_STATIC_NAMES: tuple[str, ...] = (
    "csr_topo_tub_100m",
    "csr_topo_tub_300m",
    "csr_topo_saddle_300m",
    "csr_topo_coherence",
)

CSR_STATIC_FEATURE_NAMES: tuple[str, ...] = CSR_SUBSURFACE_STATIC_NAMES + CSR_TOPO_STATIC_NAMES
CSR_FOLD_FEATURE_NAMES: tuple[str, ...] = ("csr_rad_kd_resid",)
CSR_ALL_DERIVED_NAMES: tuple[str, ...] = CSR_STATIC_FEATURE_NAMES + CSR_FOLD_FEATURE_NAMES

# Indices into CSR_STATIC_FEATURE_NAMES used by the fold-fitted Rayleigh curvilinear gate
CSR_GATE_AMP_INDICES: tuple[int, ...] = (10, 11, 15, 18, 19, 22, 23)
CSR_GATE_COH_INDICES: tuple[int, ...] = (2, 4, 6, 16, 20, 25)

VG_TO_NT_PER_KM = np.float32(1000.0)
RADON_ANGLES_RAD: tuple[float, ...] = tuple(k * math.pi / 12.0 for k in range(12))
RADON_LINE_OFFSETS: tuple[float, ...] = (-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0)
RADON_FLANK_OFFSETS: tuple[float, ...] = (-6.0, -3.0, 0.0, 3.0, 6.0)
RADON_FLANK_NORMAL_PX = 3.0


def _finite_band(arr: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(arr, dtype=np.float32)
    ok = np.asarray(valid, dtype=bool) & np.isfinite(a) & (np.abs(a) < np.float32(1.0e30))
    return np.where(ok, a, np.float32(0.0)), ok


def _interior_mask(ok: np.ndarray, radius_px: float) -> np.ndarray:
    if radius_px <= 0.0:
        return ok.copy()
    padded = np.pad(ok, 1, mode="constant", constant_values=False)
    dist = distance_transform_edt(padded)[1:-1, 1:-1]
    return ok & (dist > float(radius_px))


def _apply_mask(values: np.ndarray, ok: np.ndarray) -> np.ndarray:
    return np.where(ok, values, np.float32(np.nan)).astype(np.float32, copy=False)


def _grad2d(clean: np.ndarray, sigma: float, *, truncate: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    gx = gaussian_filter(clean, sigma=sigma, order=(0, 1), mode="constant", cval=0.0, truncate=truncate).astype(
        np.float32
    )
    gy = gaussian_filter(clean, sigma=sigma, order=(1, 0), mode="constant", cval=0.0, truncate=truncate).astype(
        np.float32
    )
    return gx, gy


def _hessian_invariants(clean: np.ndarray, sigma: float, *, truncate: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    s2 = np.float32(sigma * sigma)
    hxx = (
        s2 * gaussian_filter(clean, sigma=sigma, order=(0, 2), mode="constant", cval=0.0, truncate=truncate)
    ).astype(np.float32)
    hyy = (
        s2 * gaussian_filter(clean, sigma=sigma, order=(2, 0), mode="constant", cval=0.0, truncate=truncate)
    ).astype(np.float32)
    hxy = (
        s2 * gaussian_filter(clean, sigma=sigma, order=(1, 1), mode="constant", cval=0.0, truncate=truncate)
    ).astype(np.float32)
    tr = hxx + hyy
    diff = hxx - hyy
    disc = np.sqrt(diff * diff + np.float32(4.0) * hxy * hxy)
    lam1 = np.float32(0.5) * (tr + disc)
    lam2 = np.float32(0.5) * (tr - disc)
    swap = np.abs(lam2) > np.abs(lam1)
    l_dom = np.where(swap, lam2, lam1)
    l_sub = np.where(swap, lam1, lam2)
    tub = np.maximum(np.abs(l_dom) - np.abs(l_sub), np.float32(0.0)).astype(np.float32)
    sad = np.sqrt(np.maximum(-(lam1 * lam2), np.float32(0.0))).astype(np.float32)
    return tub, sad


def _structure_tensor_coherence(clean: np.ndarray, sigma_inner: float = 1.0, sigma_outer: float = 2.0) -> np.ndarray:
    gx, gy = _grad2d(clean, sigma_inner, truncate=3.0)
    jxx = gaussian_filter(gx * gx, sigma=sigma_outer, mode="constant", cval=0.0, truncate=3.0).astype(np.float32)
    jyy = gaussian_filter(gy * gy, sigma=sigma_outer, mode="constant", cval=0.0, truncate=3.0).astype(np.float32)
    jxy = gaussian_filter(gx * gy, sigma=sigma_outer, mode="constant", cval=0.0, truncate=3.0).astype(np.float32)
    tr = jxx + jyy
    diff = jxx - jyy
    disc = np.sqrt(diff * diff + np.float32(4.0) * jxy * jxy)
    return np.clip(disc / (tr + np.float32(1.0e-6)), np.float32(0.0), np.float32(1.0)).astype(np.float32)


def _poisson_upward_kernel(height_px: float = 3.0, max_radius_px: int = 8) -> np.ndarray:
    """Compact planar Poisson upward-continuation kernel normalized to unit sum."""
    coords = np.arange(-max_radius_px, max_radius_px + 1, dtype=np.float64)
    dy, dx = np.meshgrid(coords, coords, indexing="ij")
    r2 = dy * dy + dx * dx
    inside = r2 <= float(max_radius_px * max_radius_px)
    h = float(height_px)
    weights = np.where(inside, h / np.power(r2 + h * h, 1.5), 0.0)
    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("empty Poisson kernel")
    return (weights / total).astype(np.float32)


def _convolve_compact_disk(clean: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Exact direct shift-accumulate convolution for a compact 2D kernel in float32."""
    from scipy.ndimage import correlate

    return correlate(clean, kernel, mode="constant", cval=0.0).astype(np.float32)


def _central_grad_mag_1px(clean: np.ndarray, ok: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """1-px central finite-difference magnitude (exact Euclidean reach sqrt(2) px)."""
    h, w = clean.shape
    gx = np.zeros((h, w), dtype=np.float32)
    gy = np.zeros((h, w), dtype=np.float32)
    ok_c = np.zeros((h, w), dtype=bool)
    ok_c[1:-1, 1:-1] = (
        ok[1:-1, 1:-1] & ok[2:, 1:-1] & ok[:-2, 1:-1] & ok[1:-1, 2:] & ok[1:-1, :-2]
    )
    gy[1:-1, 1:-1] = np.float32(0.5) * (clean[2:, 1:-1] - clean[:-2, 1:-1])
    gx[1:-1, 1:-1] = np.float32(0.5) * (clean[1:-1, 2:] - clean[1:-1, :-2])
    mag = np.where(ok_c, np.hypot(gx, gy), np.float32(0.0)).astype(np.float32)
    return mag, ok_c


def _radon_12az_chunked(
    field_clean: np.ndarray,
    ok_interior: np.ndarray,
    *,
    chunk_rows: int = 512,
    halo_px: int = 16,
    return_selectivity_and_ortho: bool = False,
) -> tuple[np.ndarray, ...]:
    """Row-chunked 12-azimuth 1.8 km flank-subtracted Radon ridge operator.

    Peak transient RAM < 80 MB on 3730 x 3292 float32 grids.
    """
    smoothed = gaussian_filter(field_clean, sigma=1.0, mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    h, w = smoothed.shape
    peak_out = np.full((h, w), np.nan, dtype=np.float32)
    win_idx_out = np.zeros((h, w), dtype=np.int8)
    sel_out = np.full((h, w), np.nan, dtype=np.float32) if return_selectivity_and_ortho else None
    ortho_out = np.full((h, w), np.nan, dtype=np.float32) if return_selectivity_and_ortho else None

    n_ang = len(RADON_ANGLES_RAD)
    inv_line = np.float32(1.0 / len(RADON_LINE_OFFSETS))
    inv_flank = np.float32(1.0 / len(RADON_FLANK_OFFSETS))

    for r0 in range(0, h, chunk_rows):
        r1 = min(r0 + chunk_rows, h)
        ok_sub = ok_interior[r0:r1, :]
        if not ok_sub.any():
            continue
        p0 = max(0, r0 - halo_px)
        p1 = min(h, r1 + halo_px)
        patch = smoothed[p0:p1, :]
        local_rows = np.arange(r0 - p0, r1 - p0, dtype=np.float32)
        local_cols = np.arange(w, dtype=np.float32)
        yy, xx = np.meshgrid(local_rows, local_cols, indexing="ij")

        responses = np.empty((n_ang, r1 - r0, w), dtype=np.float32)
        for k, theta in enumerate(RADON_ANGLES_RAD):
            ty = np.float32(math.sin(theta))
            tx = np.float32(math.cos(theta))
            ny = np.float32(-math.cos(theta))
            nx = np.float32(math.sin(theta))

            line_acc = np.zeros((r1 - r0, w), dtype=np.float32)
            for s in RADON_LINE_OFFSETS:
                sf = np.float32(s)
                coords = np.array([yy + sf * ty, xx + sf * tx], dtype=np.float32)
                line_acc += map_coordinates(patch, coords, order=1, mode="constant", cval=0.0, prefilter=False)
            line_mean = line_acc * inv_line

            flank_pos = np.zeros((r1 - r0, w), dtype=np.float32)
            flank_neg = np.zeros((r1 - r0, w), dtype=np.float32)
            nf = np.float32(RADON_FLANK_NORMAL_PX)
            for s in RADON_FLANK_OFFSETS:
                sf = np.float32(s)
                c_pos = np.array([yy + nf * ny + sf * ty, xx + nf * nx + sf * tx], dtype=np.float32)
                c_neg = np.array([yy - nf * ny + sf * ty, xx - nf * nx + sf * tx], dtype=np.float32)
                flank_pos += map_coordinates(patch, c_pos, order=1, mode="constant", cval=0.0, prefilter=False)
                flank_neg += map_coordinates(patch, c_neg, order=1, mode="constant", cval=0.0, prefilter=False)
            flank_max = np.maximum(flank_pos * inv_flank, flank_neg * inv_flank)
            responses[k] = line_mean - flank_max

        best_k = np.argmax(responses, axis=0)
        best_val = np.take_along_axis(responses, best_k[None, :, :], axis=0)[0]
        peak_val = np.maximum(best_val, np.float32(0.0))
        peak_out[r0:r1, :] = np.where(ok_sub, peak_val, np.float32(np.nan))
        win_idx_out[r0:r1, :] = np.where(ok_sub, best_k.astype(np.int8), np.int8(0))

        if return_selectivity_and_ortho and sel_out is not None and ortho_out is not None:
            med_val = np.median(responses, axis=0).astype(np.float32)
            max_abs = np.max(np.abs(responses), axis=0)
            sel = np.clip((best_val - med_val) / (max_abs + np.float32(1.0e-4)), np.float32(0.0), np.float32(1.0))
            sel_out[r0:r1, :] = np.where(ok_sub, sel, np.float32(np.nan))

            ortho_k = (best_k + 6) % n_ang
            ortho_val = np.maximum(
                np.take_along_axis(responses, ortho_k[None, :, :], axis=0)[0],
                np.float32(0.0),
            )
            ortho_out[r0:r1, :] = np.where(ok_sub, ortho_val, np.float32(np.nan))

    if return_selectivity_and_ortho:
        assert sel_out is not None and ortho_out is not None
        return peak_out, win_idx_out, sel_out, ortho_out
    return peak_out, win_idx_out


def compute_csr_static_features(
    raw_stack: np.ndarray,
    valid_mask: np.ndarray,
    tmi_up150_u8: np.ndarray | None = None,
    out: np.ndarray | None = None,
) -> np.ndarray:
    """Compute all 26 static ``CSR-1`` features into ``out`` (shape ``(26, H, W)``, ``float32``)."""
    if raw_stack.ndim != 3 or raw_stack.shape[0] < 19:
        raise ValueError(f"expected (C>=19, H, W) raw_stack, got {raw_stack.shape}")
    valid = np.asarray(valid_mask, dtype=bool)
    _, h, w = raw_stack.shape
    if valid.shape != (h, w):
        raise ValueError(f"valid_mask shape {valid.shape} != {(h, w)}")
    n_feat = len(CSR_STATIC_FEATURE_NAMES)
    if out is None:
        out = np.empty((n_feat, h, w), dtype=np.float32)
    elif out.shape != (n_feat, h, w) or out.dtype != np.float32:
        raise ValueError(f"out must be float32 of shape {(n_feat, h, w)}")

    # 1. Reconstructed horizontal gravity gradient & Laplace second vertical derivative
    gx_raw, ok_gx = _finite_band(raw_stack[IDX_GRAV_DX], valid)
    gy_raw, ok_gy = _finite_band(raw_stack[IDX_GRAV_DY], valid)
    ok_gvec = ok_gx & ok_gy
    ok_gvec_s15 = _interior_mask(ok_gvec, math.hypot(3, 3))  # 4.24 px
    gx_s = gaussian_filter(gx_raw, sigma=1.5, mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    gy_s = gaussian_filter(gy_raw, sigma=1.5, mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    grav_hgrad = np.hypot(gx_s, gy_s).astype(np.float32)
    out[0] = _apply_mask(grav_hgrad, ok_gvec_s15)

    dgx_dx = gaussian_filter(gx_raw, sigma=1.5, order=(0, 1), mode="constant", cval=0.0, truncate=2.0).astype(
        np.float32
    )
    dgy_dy = gaussian_filter(gy_raw, sigma=1.5, order=(1, 0), mode="constant", cval=0.0, truncate=2.0).astype(
        np.float32
    )
    svd = -(dgx_dx + dgy_dy)
    svd_norm = np.clip(svd / (grav_hgrad + np.float32(0.05)), np.float32(-10.0), np.float32(10.0)).astype(np.float32)
    svd_crest = (
        grav_hgrad / np.sqrt(grav_hgrad * grav_hgrad + (np.float32(0.35) * svd) ** 2 + np.float32(1.0e-4))
    ).astype(np.float32)
    out[1] = _apply_mask(svd_norm, ok_gvec_s15)
    out[2] = _apply_mask(svd_crest, ok_gvec_s15)
    raw_gmag = np.hypot(gx_raw, gy_raw).astype(np.float32)
    del gx_raw, gy_raw, gx_s, gy_s, dgx_dx, dgy_dy, svd, svd_norm, svd_crest

    # 2. Compact planar Poisson upward-continuation gravity vertical derivative & true tilt
    grav, ok_grav = _finite_band(raw_stack[IDX_ISO_GRAV], valid)
    ok_pois = _interior_mask(ok_grav & ok_gvec, 11.5)  # 2.83 + 8.00 = 10.83 px
    grav_s1 = gaussian_filter(grav, sigma=1.0, mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    pkern = _poisson_upward_kernel(height_px=3.0, max_radius_px=8)
    grav_up3 = _convolve_compact_disk(grav_s1, pkern)
    dg_dz = (grav_s1 - grav_up3) / np.float32(0.3)  # mGal / km (3 px = 0.3 km)
    g_tilt = np.arctan2(dg_dz, grav_hgrad + np.float32(0.02)).astype(np.float32)
    g_crest = (grav_hgrad / np.sqrt(grav_hgrad * grav_hgrad + dg_dz * dg_dz + np.float32(4.0e-4))).astype(np.float32)
    out[3] = _apply_mask(g_tilt, ok_pois)
    out[4] = _apply_mask(g_crest, ok_pois)
    del grav, ok_grav, ok_pois, grav_s1, grav_up3, dg_dz, g_tilt, g_crest

    # 3. Unit-consistent (1000x tmi_vg) 3D magnetic tilt, crest, Salem inv-depth, AS3D & up150 persistence
    tmi_hg, ok_mhg = _finite_band(raw_stack[IDX_TMI_HG], valid)
    tmi_vg_raw, ok_mvg = _finite_band(raw_stack[IDX_TMI_VG], valid)
    ok_mag = ok_mhg & ok_mvg
    hg_pos = np.maximum(tmi_hg, np.float32(0.0))
    vg_km = VG_TO_NT_PER_KM * tmi_vg_raw
    m_tilt = np.arctan2(vg_km, hg_pos + np.float32(2.0)).astype(np.float32)
    m_crest = (hg_pos / np.sqrt(hg_pos * hg_pos + vg_km * vg_km + np.float32(4.0))).astype(np.float32)
    m_as3d = np.log1p(np.sqrt(hg_pos * hg_pos + vg_km * vg_km)).astype(np.float32)
    out[5] = _apply_mask(m_tilt, ok_mag)
    out[6] = _apply_mask(m_crest, ok_mag)
    out[8] = _apply_mask(m_as3d, ok_mag)

    ok_mag_s1 = _interior_mask(ok_mag, math.hypot(2, 2))  # 2.83 px
    mtx, mty = _grad2d(np.where(ok_mag, m_tilt, np.float32(0.0)), sigma=1.0, truncate=2.0)
    out[7] = _apply_mask(np.hypot(mtx, mty), ok_mag_s1)
    del tmi_vg_raw, ok_mvg, vg_km, m_tilt, mtx, mty, ok_mag_s1

    if tmi_up150_u8 is not None:
        u8 = np.asarray(tmi_up150_u8)
        ok_up = valid & np.isfinite(u8) & (u8 > 0)
        ok_up_int = _interior_mask(ok_up & ok_mhg, math.hypot(3, 3))
        up_clean = np.where(ok_up, u8.astype(np.float32) / np.float32(255.0), np.float32(0.0))
        ugx, ugy = _grad2d(up_clean, sigma=1.5, truncate=2.0)
        up_grad = np.hypot(ugx, ugy) * np.float32(500.0)
        persist = np.clip(up_grad / (hg_pos + np.float32(10.0)), np.float32(0.0), np.float32(5.0)).astype(np.float32)
        out[9] = _apply_mask(persist, ok_up_int)
        del u8, ok_up, ok_up_int, up_clean, ugx, ugy, up_grad, persist
    else:
        out[9] = np.full((h, w), np.nan, dtype=np.float32)
    del tmi_hg, ok_mhg, hg_pos

    # 4. Cover-attenuation compensation, fractional basement step & demagnetization-claycap coupling
    z_raw, ok_z = _finite_band(raw_stack[IDX_DEPTH_BASE], valid)
    z_clamped = np.clip(z_raw, np.float32(0.0), np.float32(3000.0))
    cover_gain = np.clip(np.float32(1.0) + z_clamped / np.float32(300.0), np.float32(1.0), np.float32(6.0)).astype(
        np.float32
    )
    out[10] = _apply_mask(cover_gain * grav_hgrad, ok_gvec_s15 & ok_z)
    cc_mag = (np.sqrt(cover_gain) * m_as3d * m_crest).astype(np.float32)
    out[11] = _apply_mask(cc_mag, ok_mag & ok_z)

    log_z = np.log(np.clip(z_raw, np.float32(0.0), np.float32(10000.0)) + np.float32(100.0)).astype(np.float32)
    ok_z_s2 = _interior_mask(ok_z, math.hypot(4, 4))  # 5.66 px
    zgx, zgy = _grad2d(np.where(ok_z, log_z, np.float32(0.0)), sigma=2.0, truncate=2.0)
    out[12] = _apply_mask(np.hypot(zgx, zgy), ok_z_s2)
    del z_raw, z_clamped, zgx, zgy, ok_z_s2, grav_hgrad, ok_gvec_s15, m_as3d, m_crest

    cond, ok_cond = _finite_band(raw_stack[IDX_COND_SURF], valid)
    ok_cond_s2 = _interior_mask(ok_cond, math.hypot(4, 4))
    cgx, cgy = _grad2d(cond, sigma=2.0, truncate=2.0)
    cond_grad = np.hypot(cgx, cgy).astype(np.float32)
    out[13] = _apply_mask(cond_grad, ok_cond_s2)
    del cond, cgx, cgy

    rtp, ok_rtp = _finite_band(raw_stack[IDX_RTP], valid)
    ok_rtp_s4 = _interior_mask(ok_rtp & ok_cond_s2, math.hypot(8, 8))  # 11.31 px
    rtp_low = gaussian_filter(rtp, sigma=4.0, mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    demag_trough = np.maximum(-(rtp - rtp_low), np.float32(0.0))
    out[14] = _apply_mask(np.log1p(demag_trough) * cond_grad, ok_rtp_s4)
    del rtp, ok_rtp, ok_rtp_s4, rtp_low, demag_trough, cond_grad, ok_cond, ok_cond_s2

    # 5. 12-azimuth 1.8 km flank-subtracted Radon line-integral ridges (unchained raw sources; <= 14.66 px)
    ok_rad_g = _interior_mask(ok_gvec & ok_z, 15.0)
    src_grav = np.where(ok_gvec & ok_z, cover_gain * raw_gmag, np.float32(0.0)).astype(np.float32)
    g_peak, g_idx, g_sel, g_ortho = _radon_12az_chunked(src_grav, ok_rad_g, return_selectivity_and_ortho=True)
    out[15] = g_peak
    out[16] = g_sel
    out[17] = g_ortho
    del src_grav, raw_gmag, g_peak, g_sel, g_ortho

    ok_rad_m = _interior_mask(ok_mag & ok_z, 15.0)
    src_mag = np.where(ok_mag & ok_z, cc_mag, np.float32(0.0)).astype(np.float32)
    m_peak, m_idx = _radon_12az_chunked(src_mag, ok_rad_m, return_selectivity_and_ortho=False)
    out[18] = m_peak
    del src_mag, cc_mag, m_peak, ok_mag, cover_gain

    base_step_1px, ok_b1 = _central_grad_mag_1px(np.where(ok_z, log_z, np.float32(0.0)), ok_z)
    ok_rad_b = _interior_mask(ok_z, 15.5)  # 1.414 + 2.828 + 9.0 + 1.414 = 14.657 px <= 15.5 px
    b_peak, _ = _radon_12az_chunked(np.where(ok_b1, base_step_1px, np.float32(0.0)), ok_rad_b)
    out[19] = b_peak
    del log_z, ok_z, base_step_1px, ok_b1, ok_rad_b, b_peak, ok_gvec

    dtheta = (g_idx.astype(np.float32) - m_idx.astype(np.float32)) * np.float32(math.pi / 12.0)
    strike_lock = (np.cos(dtheta) ** 2).astype(np.float32)
    out[20] = _apply_mask(strike_lock, ok_rad_g & ok_rad_m)
    del g_idx, m_idx, dtheta, strike_lock, ok_rad_g, ok_rad_m

    # 6. Active Walker Lane / Great Basin dimensionless transtensional strain partitioning
    inv2, ok_i2 = _finite_band(raw_stack[IDX_GEOD_2NDINV], valid)
    shear, ok_sh = _finite_band(raw_stack[IDX_GEOD_SHEAR], valid)
    dilate, ok_di = _finite_band(raw_stack[IDX_GEOD_DILATE], valid)
    ok_geod = ok_i2 & ok_sh & ok_di
    part = (np.maximum(dilate, np.float32(0.0)) * np.maximum(shear, np.float32(0.0))) / (
        np.maximum(inv2, np.float32(0.0)) ** 2 + np.float32(1.0)
    )
    out[21] = _apply_mask(part, ok_geod)
    del inv2, shear, dilate, ok_i2, ok_sh, ok_di, ok_geod, part

    # 7. Local scale-free topographic curvature & coherence (used only in Expert 2; max reach 12.73 px)
    elev, ok_elev = _finite_band(raw_stack[IDX_DET_ELEV], valid)
    ok_e100 = _interior_mask(ok_elev, math.hypot(3, 3))
    ok_e300 = _interior_mask(ok_elev, math.hypot(9, 9))
    tub100, _ = _hessian_invariants(elev, sigma=1.0, truncate=3.0)
    out[22] = _apply_mask(tub100, ok_e100)
    del tub100, ok_e100
    tub300, sad300 = _hessian_invariants(elev, sigma=3.0, truncate=3.0)
    out[23] = _apply_mask(tub300, ok_e300)
    out[24] = _apply_mask(sad300, ok_e300)
    del tub300, sad300
    out[25] = _apply_mask(_structure_tensor_coherence(elev, 1.0, 2.0), ok_e300)
    del elev, ok_elev, ok_e300

    return out


def build_or_load_csr_cache(
    raw_stack: np.ndarray,
    valid_mask: np.ndarray,
    tmi_up150_u8: np.ndarray | None,
    cache_dir: Path,
    dataset_signature: str,
    up150_sha256: str,
) -> np.ndarray:
    """Build or reuse a disk-backed float32 memmap of the 26 static ``CSR-1`` features."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    array_path = cache_dir / "csr_static_features.npy"
    meta_path = cache_dir / "csr_static_manifest.json"
    expected_meta = {
        "transform_version": TRANSFORM_VERSION,
        "dataset_signature": dataset_signature,
        "up150_sha256": up150_sha256,
        "shape": [len(CSR_STATIC_FEATURE_NAMES), int(raw_stack.shape[1]), int(raw_stack.shape[2])],
        "feature_names": list(CSR_STATIC_FEATURE_NAMES),
        "support_px": SUPPORT_PX,
    }
    if array_path.is_file() and meta_path.is_file():
        try:
            recorded = json.loads(meta_path.read_text())
            if recorded == expected_meta:
                arr = np.load(array_path, mmap_mode="r")
                if arr.shape == tuple(expected_meta["shape"]) and arr.dtype == np.float32:
                    return arr
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    target = np.lib.format.open_memmap(
        array_path,
        mode="w+",
        dtype=np.float32,
        shape=(len(CSR_STATIC_FEATURE_NAMES), raw_stack.shape[1], raw_stack.shape[2]),
    )
    compute_csr_static_features(raw_stack, valid_mask, tmi_up150_u8=tmi_up150_u8, out=target)
    target.flush()
    del target
    meta_path.write_text(json.dumps(expected_meta, indent=2) + "\n")
    return np.load(array_path, mmap_mode="r")


def fit_kd_alteration_residual(
    rad_k_u8: np.ndarray,
    rad_th_u8: np.ndarray,
    train_mask: np.ndarray,
    valid_mask: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    """Fit linear K ~ a + b*Th strictly inside ``train_mask`` and return ``K - (a + b*Th)``."""
    valid = np.asarray(valid_mask, dtype=bool)
    train = np.asarray(train_mask, dtype=bool) & valid
    k = np.asarray(rad_k_u8, dtype=np.float32) / np.float32(255.0)
    th = np.asarray(rad_th_u8, dtype=np.float32) / np.float32(255.0)
    present = valid & (rad_k_u8 > 0) & (rad_th_u8 > 0)
    fit_sel = train & present
    if int(fit_sel.sum()) < 32:
        raise ValueError("insufficient training pixels with GeoDAWN K/Th coverage")
    x = th[fit_sel].astype(np.float64)
    y = k[fit_sel].astype(np.float64)
    xm = float(x.mean())
    ym = float(y.mean())
    dx = x - xm
    var = float(np.dot(dx, dx))
    slope = float(np.dot(dx, y - ym) / var) if var > 1.0e-12 else 0.0
    intercept = ym - slope * xm
    resid = np.where(present, k - (np.float32(intercept) + np.float32(slope) * th), np.float32(np.nan)).astype(
        np.float32
    )
    return resid, {"intercept": intercept, "slope": slope, "fit_pixels": int(fit_sel.sum())}


def calibrate_weighted_case_control_probabilities(
    sampled_prob: np.ndarray,
    *,
    population_positives: float,
    population_negatives: float,
    effective_sample_positives: float,
    effective_sample_negatives: float,
) -> np.ndarray:
    """Exact Prentice-Pyke Bayes prior calibration under positive/negative sample weights."""
    if min(population_positives, population_negatives, effective_sample_positives, effective_sample_negatives) <= 0:
        raise ValueError("positive/negative effective counts must all be > 0")
    pop_odds = float(population_positives) / float(population_negatives)
    samp_odds = float(effective_sample_positives) / float(effective_sample_negatives)
    ratio = np.float32(pop_odds / samp_odds)
    p = np.clip(np.asarray(sampled_prob, dtype=np.float32), np.float32(1.0e-6), np.float32(1.0 - 1.0e-6))
    adj_odds = (p / (np.float32(1.0) - p)) * ratio
    return (adj_odds / (np.float32(1.0) + adj_odds)).astype(np.float32, copy=False)


def fit_csr_gate_scales(
    csr_static: np.ndarray,
    train_mask: np.ndarray,
    *,
    quantile: float = 0.85,
    max_samples: int = 250_000,
) -> np.ndarray:
    """Fit Rayleigh curvilinear gate amplitude scales strictly on ``train_mask``."""
    train = np.asarray(train_mask, dtype=bool)
    flat_idx = np.flatnonzero(train)
    if flat_idx.size == 0:
        raise ValueError("empty train_mask for CSR gate calibration")
    if flat_idx.size > max_samples:
        step = max(1, flat_idx.size // max_samples)
        flat_idx = flat_idx[::step][:max_samples]
    rr, cc = np.unravel_index(flat_idx, train.shape)
    scales = np.empty(len(CSR_GATE_AMP_INDICES), dtype=np.float32)
    for j, ch in enumerate(CSR_GATE_AMP_INDICES):
        vals = np.asarray(csr_static[ch][rr, cc], dtype=np.float32)
        vals = vals[np.isfinite(vals) & (vals > 0.0)]
        q = float(np.quantile(vals, quantile)) if vals.size >= 16 else 1.0
        scales[j] = np.float32(max(q, 1.0e-6))
    return scales


def compute_csr_structural_gate(
    csr_static: np.ndarray,
    valid_mask: np.ndarray,
    gate_scales: np.ndarray,
    *,
    floor: float = 0.08,
    block: int = 512,
) -> np.ndarray:
    """Evaluate bounded Rayleigh structural gate with nonzero floor for deeply buried faults."""
    scales = np.asarray(gate_scales, dtype=np.float32)
    valid = np.asarray(valid_mask, dtype=bool)
    h, w = valid.shape
    out = np.zeros((h, w), dtype=np.float32)
    amp_idx = list(CSR_GATE_AMP_INDICES)
    coh_idx = list(CSR_GATE_COH_INDICES)
    fl = np.float32(floor)

    for r0 in range(0, h, block):
        r1 = min(r0 + block, h)
        for c0 in range(0, w, block):
            c1 = min(c0 + block, w)
            sub_v = valid[r0:r1, c0:c1]
            if not sub_v.any():
                continue
            amps = np.asarray(csr_static[amp_idx, r0:r1, c0:c1], dtype=np.float32)
            amps = np.where(np.isfinite(amps), np.maximum(amps, np.float32(0.0)), np.float32(0.0))
            z_max = np.max(np.clip(amps / scales[:, None, None], np.float32(0.0), np.float32(6.0)), axis=0)

            cohs = np.asarray(csr_static[coh_idx, r0:r1, c0:c1], dtype=np.float32)
            cohs = np.where(np.isfinite(cohs), np.clip(cohs, np.float32(0.0), np.float32(1.0)), np.float32(0.0))
            coh_max = np.max(cohs, axis=0)

            score = z_max * (np.float32(0.5) + np.float32(0.5) * coh_max)
            rayleigh = np.float32(1.0) - np.exp(np.float32(-0.5) * score * score)
            gated = fl + (np.float32(1.0) - fl) * rayleigh
            out[r0:r1, c0:c1] = np.where(sub_v, np.clip(gated, np.float32(0.0), np.float32(1.0)), np.float32(0.0))
    return out


def concentrate_ridge_belief(
    belief: np.ndarray,
    eligible_mask: np.ndarray,
    *,
    gamma: float = 1.25,
    normal_step_px: float = 2.0,
) -> np.ndarray:
    """Concentrate cross-strike blurred 2D posterior halos onto 1D curvilinear ridge crests.

    Operates strictly inside ``eligible_mask``: pixels outside ``eligible_mask``
    contribute zero flank value so boundary crests are never penalized and zero
    information crosses fold boundaries.
    """
    elig = np.asarray(eligible_mask, dtype=bool)
    b = np.where(elig & np.isfinite(belief), np.maximum(belief, np.float32(0.0)), np.float32(0.0)).astype(np.float32)
    if gamma <= 0.0:
        return b
    bs = gaussian_filter(b, sigma=1.0, mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    hxx = gaussian_filter(bs, sigma=1.0, order=(0, 2), mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    hyy = gaussian_filter(bs, sigma=1.0, order=(2, 0), mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    hxy = gaussian_filter(bs, sigma=1.0, order=(1, 1), mode="constant", cval=0.0, truncate=2.0).astype(np.float32)
    del bs

    # Eigenvector of most-negative curvature points perpendicular to a bright ridge crest
    diff = hyy - hxx
    disc = np.sqrt(diff * diff + np.float32(4.0) * hxy * hxy)
    lam_neg = np.float32(0.5) * ((hyy + hxx) - disc)
    vy = lam_neg - hxx
    vx = hxy
    norm = np.hypot(vy, vx)
    deg = norm <= np.float32(1.0e-10)
    ny = np.where(deg, np.where(hyy <= hxx, np.float32(1.0), np.float32(0.0)), vy / np.maximum(norm, np.float32(1.0e-10)))
    nx = np.where(deg, np.where(hyy <= hxx, np.float32(0.0), np.float32(1.0)), vx / np.maximum(norm, np.float32(1.0e-10)))
    del hxx, hyy, hxy, diff, disc, lam_neg, vy, vx, norm, deg

    h, w = b.shape
    step = np.float32(normal_step_px)
    out = np.zeros((h, w), dtype=np.float32)
    halo = int(math.ceil(abs(normal_step_px))) + 2
    for r0 in range(0, h, 512):
        r1 = min(r0 + 512, h)
        esub = elig[r0:r1, :]
        if not esub.any():
            continue
        p0 = max(0, r0 - halo)
        p1 = min(h, r1 + halo)
        patch = b[p0:p1, :]
        yy, xx = np.meshgrid(
            np.arange(r0 - p0, r1 - p0, dtype=np.float32),
            np.arange(w, dtype=np.float32),
            indexing="ij",
        )
        nys = ny[r0:r1, :]
        nxs = nx[r0:r1, :]
        b_pos = map_coordinates(
            patch, np.array([yy + step * nys, xx + step * nxs], dtype=np.float32),
            order=1, mode="constant", cval=0.0, prefilter=False,
        )
        b_neg = map_coordinates(
            patch, np.array([yy - step * nys, xx - step * nxs], dtype=np.float32),
            order=1, mode="constant", cval=0.0, prefilter=False,
        )
        b_here = b[r0:r1, :]
        flank_max = np.maximum(b_here, np.maximum(b_pos, b_neg))
        ratio = np.where(flank_max > np.float32(1.0e-12), b_here / np.maximum(flank_max, np.float32(1.0e-12)), np.float32(1.0))
        conc = b_here * np.power(np.clip(ratio, np.float32(0.0), np.float32(1.0)), np.float32(gamma))
        out[r0:r1, :] = np.where(esub, conc, np.float32(0.0))
    return out


def select_csr_dispersed_dots(
    calibrated_belief: np.ndarray,
    active_mask: np.ndarray,
    dot_budget: int,
    *,
    gamma: float = 1.25,
    min_sq_dist_excl: int = 6,
) -> np.ndarray:
    """1D ridge-concentrated submodular EDGE selector with minimum spacing >= sqrt(excl+1) px."""
    from gemsdoe30.emitter_opt import edge_select

    if int(dot_budget) < 1:
        raise ValueError(f"dot_budget must be >= 1, got {dot_budget}")
    active = np.asarray(active_mask, dtype=bool)
    concentrated = concentrate_ridge_belief(calibrated_belief, active, gamma=gamma)
    emitted, diag = edge_select(
        concentrated,
        support=active,
        truth_mass=1.0e9,
        max_dots=int(dot_budget),
        min_sq_dist_excl=int(min_sq_dist_excl),
        return_diagnostics=True,
    )
    if int(diag["accepted"]) != int(dot_budget) or int(np.count_nonzero(emitted)) != int(dot_budget):
        raise ValueError(
            f"CSR dispersed EDGE shortfall: requested {dot_budget}, accepted {diag['accepted']} "
            f"on {int(active.sum())} active pixels"
        )
    return emitted.astype(np.float32)
