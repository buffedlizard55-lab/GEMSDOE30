"""Multi-Scale Steerable Discontinuity & Piedmont Cover-Breach (`MSDB-1`) transforms.

Every operator in this module is strictly label-free, catalogue-free, and
bounded in Euclidean spatial support:

* Maximum axial Gaussian filter half-width: ``MAX_AXIAL_HALFWIDTH_PX = 9`` pixels
  (``sigma = 3.0`` with ``truncate = 3.0`` gives ``int(3.0 * 3.0 + 0.5) = 9``,
  and the structure tensor chains ``sigma_inner = 1.0`` [half-width 3] with
  ``sigma_outer = 2.0`` [half-width 6] for combined axial half-width ``3 + 6 = 9``).
* Exact Euclidean influence radius: ``hypot(9, 9) = 12.727922... <= 13`` pixels
  (``SUPPORT_PX = 13``), strictly inside the 17-pixel holdout regional guard.
* Any target pixel within ``hypot(9, 9)`` pixels of a non-finite source pixel in
  the contributing bands is set to ``NaN`` so sentinel values and footprint
  boundaries never bleed into finite geophysical features.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

TRANSFORM_VERSION = "msdb-piedmont-v2-20261025"
TRUNCATE = 3.0
MAX_AXIAL_HALFWIDTH_PX = 9
EUCLIDEAN_SUPPORT_EXACT_PX = math.hypot(MAX_AXIAL_HALFWIDTH_PX, MAX_AXIAL_HALFWIDTH_PX)
SUPPORT_PX = int(math.ceil(EUCLIDEAN_SUPPORT_EXACT_PX))  # 13 px <= 17 px guard

# Stationary local/tectonic raw bands retained in MSDB-1 v2 (excludes the 6
# non-stationary regional DC-level / 100-km coordinate-proxy bands: 0 mag_anom,
# 1 rtp DC level, 9 deq_n100a15, 12 iso_grav_anom DC level, 13 tmi DC level,
# 15 ieq_n100a15, whose local derivatives/curvatures are captured in MSDB).
MSDB_RAW_KEEP_INDICES: tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 10, 11, 14, 16, 17, 18)

# Discontinuity amplitude and dimensionless coherence indices inside MSDB_FEATURE_NAMES
GATE_AMPLITUDE_INDICES: tuple[int, ...] = (3, 4, 6, 7, 15, 16)
GATE_COHERENCE_INDICES: tuple[int, ...] = (1, 10, 11, 12, 13, 14)

# Zero-based indices in features_raw.npy verified against both GDAL metadata and
# Organizer Reference Notebook Cell 5 (plus GeoDAWN TC & finite-difference audits).
IDX_RTP = 1                 # Band 2: Reduced-to-pole magnetic anomaly
IDX_TMI_HG = 2              # Band 3: Total magnetic intensity horizontal gradient (>= 0)
IDX_GEOD_2NDINV = 3         # Band 4: Geodetic strain second invariant
IDX_TC = 5                  # Band 6: GeoDAWN Radiometric Total Count (verified Spearman=0.999957)
IDX_GEOD_SHEAR = 6          # Band 7: Geodetic shear strain rate
IDX_GEOD_DILATE = 7         # Band 8: Geodetic dilatation strain rate
IDX_TMI_VG = 8              # Band 9: Total magnetic intensity vertical derivative
IDX_GRAV_DY = 10            # Band 11: Signed image-y gravity derivative (+dg/dy)
IDX_DET_ELEV = 11           # Band 12: Detrended elevation
IDX_ISO_GRAV = 12           # Band 13: Isostatic gravity anomaly
IDX_DEPTH_BASE = 14         # Band 15: Depth to basement surface
IDX_COND_SURF = 16          # Band 17: Surface electrical conductivity
IDX_GRAV_DX = 17            # Band 18: Signed image-x gravity derivative (+dg/dx)

MSDB_FEATURE_NAMES: tuple[str, ...] = (
    "msdb_mag_tilt_rad",
    "msdb_mag_tilt_zero_crest",
    "msdb_mag_contact_invdepth",
    "msdb_topo_tubularity_100m",
    "msdb_topo_tubularity_300m",
    "msdb_topo_saddle_300m",
    "msdb_rtp_tubularity_300m",
    "msdb_grav_tubularity_300m",
    "msdb_base_tubularity_300m",
    "msdb_cond_saddle_300m",
    "msdb_topo_coherence",
    "msdb_grav_coherence",
    "msdb_align_grav_basement",
    "msdb_align_rtp_grav",
    "msdb_align_topo_radtc",
    "msdb_piedmont_ramp_index",
    "msdb_radtc_grad_300m",
    "msdb_transtensional_index",
)


def _finite_band(arr: np.ndarray, valid_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return float32 zero-filled copy and exact finite in-footprint mask."""
    raw = np.asarray(arr, dtype=np.float32)
    ok = np.asarray(valid_mask, dtype=bool) & np.isfinite(raw) & (raw > -1.0e30)
    clean = np.where(ok, raw, np.float32(0.0))
    return clean, ok


def _interior_mask(ok: np.ndarray, axial_halfwidth_px: int) -> np.ndarray:
    """True only where every pixel in the [-w..w]^2 box is finite in ``ok``."""
    if axial_halfwidth_px <= 0:
        return ok.copy()
    if bool(ok.all()):
        return ok.copy()
    reach = math.hypot(axial_halfwidth_px, axial_halfwidth_px)
    # Any non-finite pixel at offset (dr, dc) with |dr| <= w and |dc| <= w has
    # Euclidean distance <= hypot(w, w). Requiring strictly greater distance
    # guarantees 100% finite support inside the [-w..w]^2 filter box.
    return ok & (distance_transform_edt(ok) > reach + 1.0e-6)


def _apply_mask(values: np.ndarray, support_ok: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=np.float32)
    out = np.where(support_ok, out, np.float32(np.nan))
    return out


def _grad2d(clean: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    """Gaussian smoothed (gx, gy) = (du/dx, du/dy) with exact axial half-width."""
    gy = gaussian_filter(clean, sigma=sigma, order=(1, 0), mode="constant", cval=0.0, truncate=TRUNCATE)
    gx = gaussian_filter(clean, sigma=sigma, order=(0, 1), mode="constant", cval=0.0, truncate=TRUNCATE)
    return gx.astype(np.float32, copy=False), gy.astype(np.float32, copy=False)


def _hessian_invariants(clean: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    """Return scale-normalized (tubularity, saddle_index) at Gaussian scale ``sigma``.

    * ``tubularity = |lambda_1| - |lambda_2| >= 0`` isolates 1-D curvilinear
      fault scarps/edges while vanishing on isotropic domes and basins.
    * ``saddle_index = sqrt(max(-lambda_1 * lambda_2, 0))`` isolates hyperbolic
      structural saddles (relay-ramp breaches and cross-strike transfer zones).
    """
    s2 = np.float32(sigma * sigma)
    hyy = s2 * gaussian_filter(clean, sigma=sigma, order=(2, 0), mode="constant", cval=0.0, truncate=TRUNCATE)
    hxx = s2 * gaussian_filter(clean, sigma=sigma, order=(0, 2), mode="constant", cval=0.0, truncate=TRUNCATE)
    hxy = s2 * gaussian_filter(clean, sigma=sigma, order=(1, 1), mode="constant", cval=0.0, truncate=TRUNCATE)
    trace = np.float32(0.5) * (hxx + hyy)
    disc = np.sqrt(np.maximum(np.float32(0.25) * (hxx - hyy) ** 2 + hxy * hxy, np.float32(0.0)))
    lam_a = trace + disc
    lam_b = trace - disc
    abs_a = np.abs(lam_a)
    abs_b = np.abs(lam_b)
    tubularity = np.abs(abs_a - abs_b).astype(np.float32, copy=False)
    saddle = np.sqrt(np.maximum(-(lam_a * lam_b), np.float32(0.0))).astype(np.float32, copy=False)
    return tubularity, saddle


def _structure_tensor_coherence(clean: np.ndarray, sigma_inner: float = 1.0, sigma_outer: float = 2.0) -> np.ndarray:
    """1-D linear strike coherence in [0, 1] with axial half-width 3 + 6 = 9 px."""
    gx, gy = _grad2d(clean, sigma=sigma_inner)
    jxx = gaussian_filter(gx * gx, sigma=sigma_outer, order=0, mode="constant", cval=0.0, truncate=TRUNCATE)
    jyy = gaussian_filter(gy * gy, sigma=sigma_outer, order=0, mode="constant", cval=0.0, truncate=TRUNCATE)
    jxy = gaussian_filter(gx * gy, sigma=sigma_outer, order=0, mode="constant", cval=0.0, truncate=TRUNCATE)
    aniso = np.sqrt(np.maximum((jxx - jyy) ** 2 + np.float32(4.0) * jxy * jxy, np.float32(0.0)))
    denom = jxx + jyy + np.float32(1.0e-8)
    return np.clip(aniso / denom, np.float32(0.0), np.float32(1.0)).astype(np.float32, copy=False)


def _strike_concordance(
    ux: np.ndarray,
    uy: np.ndarray,
    vx: np.ndarray,
    vy: np.ndarray,
) -> np.ndarray:
    """Polarity-invariant strike-normal concordance cos^2(Delta theta) in [0, 1]."""
    dot = ux * vx + uy * vy
    nu2 = ux * ux + uy * uy
    nv2 = vx * vx + vy * vy
    denom = (nu2 + np.float32(1.0e-8)) * (nv2 + np.float32(1.0e-8))
    return np.clip((dot * dot) / denom, np.float32(0.0), np.float32(1.0)).astype(np.float32, copy=False)


def compute_msdb_features(
    raw_stack: np.ndarray,
    valid_mask: np.ndarray,
    out: np.ndarray | None = None,
) -> np.ndarray:
    """Compute all 18 ``MSDB-1`` features into ``out`` (shape ``(18, H, W)``, ``float32``).

    Operates band-by-band in ``float32`` so peak temporary memory remains well
    below 300 MB even on the full ``3730 x 3292`` competition grid.
    """
    if raw_stack.ndim != 3 or raw_stack.shape[0] < 18:
        raise ValueError(f"Expected (C>=18, H, W) raw feature stack, got {raw_stack.shape}")
    valid = np.asarray(valid_mask, dtype=bool)
    _, h, w = raw_stack.shape
    if valid.shape != (h, w):
        raise ValueError(f"valid_mask shape {valid.shape} != {(h, w)}")
    if out is None:
        out = np.empty((len(MSDB_FEATURE_NAMES), h, w), dtype=np.float32)
    elif out.shape != (len(MSDB_FEATURE_NAMES), h, w) or out.dtype != np.float32:
        raise ValueError(f"out must be float32 of shape {(len(MSDB_FEATURE_NAMES), h, w)}")

    w_100 = int(TRUNCATE * 1.0 + 0.5)  # 3 px
    w_300 = int(TRUNCATE * 3.0 + 0.5)  # 9 px
    if max(w_100, w_300) > MAX_AXIAL_HALFWIDTH_PX:
        raise AssertionError("Filter half-width exceeds preregistered bound")

    # --- Group A: True Potential-Field Magnetic Tilt & Contact Inverse Depth ---
    tmi_hg, ok_hg = _finite_band(raw_stack[IDX_TMI_HG], valid)
    tmi_vg, ok_vg = _finite_band(raw_stack[IDX_TMI_VG], valid)
    ok_mag = ok_hg & ok_vg
    hg_pos = np.maximum(tmi_hg, np.float32(0.0))
    tilt = np.arctan2(tmi_vg, np.maximum(hg_pos, np.float32(1.0e-4))).astype(np.float32)
    crest = (hg_pos / np.sqrt(hg_pos * hg_pos + tmi_vg * tmi_vg + np.float32(1.0e-6))).astype(np.float32)
    out[0] = _apply_mask(tilt, ok_mag)
    out[1] = _apply_mask(crest, ok_mag)
    tilt_clean = np.where(ok_mag, tilt, np.float32(0.0))
    ok_mag_100 = _interior_mask(ok_mag, w_100)
    tx, ty = _grad2d(tilt_clean, sigma=1.0)
    out[2] = _apply_mask(np.hypot(tx, ty), ok_mag_100)
    del tmi_hg, tmi_vg, ok_hg, ok_vg, ok_mag, hg_pos, tilt, crest, tilt_clean, ok_mag_100, tx, ty

    # --- Group B & C (Topography): Multi-scale Tubularity, Saddle, Coherence ---
    elev, ok_elev = _finite_band(raw_stack[IDX_DET_ELEV], valid)
    ok_elev_100 = _interior_mask(ok_elev, w_100)
    ok_elev_300 = _interior_mask(ok_elev, w_300)
    tub100, _ = _hessian_invariants(elev, sigma=1.0)
    out[3] = _apply_mask(tub100, ok_elev_100)
    del tub100, ok_elev_100
    tub300, sad300 = _hessian_invariants(elev, sigma=3.0)
    out[4] = _apply_mask(tub300, ok_elev_300)
    out[5] = _apply_mask(sad300, ok_elev_300)
    del tub300, sad300
    out[10] = _apply_mask(_structure_tensor_coherence(elev, 1.0, 2.0), ok_elev_300)
    elev_gx, elev_gy = _grad2d(elev, sigma=3.0)
    del elev, ok_elev

    # --- RTP Magnetic Tubularity & 300 m Gradient ---
    rtp, ok_rtp = _finite_band(raw_stack[IDX_RTP], valid)
    ok_rtp_300 = _interior_mask(ok_rtp, w_300)
    rtp_tub, _ = _hessian_invariants(rtp, sigma=3.0)
    out[6] = _apply_mask(rtp_tub, ok_rtp_300)
    del rtp_tub
    rtp_gx, rtp_gy = _grad2d(rtp, sigma=3.0)
    del rtp, ok_rtp

    # --- Isostatic Gravity Tubularity & Coherence ---
    grav, ok_grav = _finite_band(raw_stack[IDX_ISO_GRAV], valid)
    ok_grav_300 = _interior_mask(ok_grav, w_300)
    grav_tub, _ = _hessian_invariants(grav, sigma=3.0)
    out[7] = _apply_mask(grav_tub, ok_grav_300)
    del grav_tub
    out[11] = _apply_mask(_structure_tensor_coherence(grav, 1.0, 2.0), ok_grav_300)
    del grav, ok_grav, ok_grav_300

    # --- Depth to Basement Tubularity & Piedmont Thin-Cover Ramp Index ---
    base_d, ok_base = _finite_band(raw_stack[IDX_DEPTH_BASE], valid)
    ok_base_300 = _interior_mask(ok_base, w_300)
    base_tub, _ = _hessian_invariants(base_d, sigma=3.0)
    out[8] = _apply_mask(base_tub, ok_base_300)
    del base_tub
    base_gx, base_gy = _grad2d(base_d, sigma=3.0)
    base_grad = np.hypot(base_gx, base_gy)
    shallow_weight = np.exp(-np.clip(base_d, np.float32(0.0), np.float32(10000.0)) / np.float32(500.0))
    out[15] = _apply_mask(shallow_weight * base_grad, ok_base_300)
    del base_d, ok_base, base_grad, shallow_weight

    # --- Surface Conductivity Saddle Breach ---
    cond, ok_cond = _finite_band(raw_stack[IDX_COND_SURF], valid)
    ok_cond_300 = _interior_mask(ok_cond, w_300)
    _, cond_sad = _hessian_invariants(cond, sigma=3.0)
    out[9] = _apply_mask(cond_sad, ok_cond_300)
    del cond, ok_cond, ok_cond_300, cond_sad

    # --- Reconstructed Signed 2-D Gravity Gradient Vector (Band 18, Band 11) ---
    gdx_raw, ok_gdx = _finite_band(raw_stack[IDX_GRAV_DX], valid)
    gdy_raw, ok_gdy = _finite_band(raw_stack[IDX_GRAV_DY], valid)
    ok_gvec_300 = _interior_mask(ok_gdx & ok_gdy, w_300)
    gdx = gaussian_filter(gdx_raw, sigma=3.0, order=0, mode="constant", cval=0.0, truncate=TRUNCATE).astype(np.float32)
    gdy = gaussian_filter(gdy_raw, sigma=3.0, order=0, mode="constant", cval=0.0, truncate=TRUNCATE).astype(np.float32)
    del gdx_raw, gdy_raw, ok_gdx, ok_gdy

    out[12] = _apply_mask(_strike_concordance(gdx, gdy, base_gx, base_gy), ok_gvec_300 & ok_base_300)
    out[13] = _apply_mask(_strike_concordance(rtp_gx, rtp_gy, gdx, gdy), ok_rtp_300 & ok_gvec_300)
    del gdx, gdy, base_gx, base_gy, rtp_gx, rtp_gy, ok_gvec_300, ok_base_300, ok_rtp_300

    # --- GeoDAWN Radiometric Total Count (Band 6 tc) Gradient & Topo Concordance ---
    radtc, ok_tc = _finite_band(raw_stack[IDX_TC], valid)
    ok_tc_300 = _interior_mask(ok_tc, w_300)
    tc_gx, tc_gy = _grad2d(radtc, sigma=3.0)
    out[14] = _apply_mask(_strike_concordance(elev_gx, elev_gy, tc_gx, tc_gy), ok_elev_300 & ok_tc_300)
    out[16] = _apply_mask(np.hypot(tc_gx, tc_gy), ok_tc_300)
    del radtc, ok_tc, ok_tc_300, tc_gx, tc_gy, elev_gx, elev_gy, ok_elev_300

    # --- Active Walker Lane / Great Basin Transtensional Strain Partitioning ---
    inv2, ok_i2 = _finite_band(raw_stack[IDX_GEOD_2NDINV], valid)
    shear, ok_sh = _finite_band(raw_stack[IDX_GEOD_SHEAR], valid)
    dilate, ok_di = _finite_band(raw_stack[IDX_GEOD_DILATE], valid)
    ok_geod = ok_i2 & ok_sh & ok_di
    transtens = (np.maximum(dilate, np.float32(0.0)) * np.maximum(shear, np.float32(0.0))) / (
        np.maximum(inv2, np.float32(0.0)) + np.float32(1.0e-3)
    )
    out[17] = _apply_mask(transtens, ok_geod)
    del inv2, shear, dilate, ok_i2, ok_sh, ok_di, ok_geod, transtens

    return out


def build_or_load_msdb_cache(
    raw_stack: np.ndarray,
    valid_mask: np.ndarray,
    cache_dir: Path,
    dataset_signature: str,
) -> np.ndarray:
    """Build or reuse a disk-backed float32 memmap of the 18 ``MSDB-1`` features."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    array_path = cache_dir / "msdb_features.npy"
    meta_path = cache_dir / "msdb_manifest.json"
    expected_meta = {
        "transform_version": TRANSFORM_VERSION,
        "dataset_signature": dataset_signature,
        "shape": [len(MSDB_FEATURE_NAMES), int(raw_stack.shape[1]), int(raw_stack.shape[2])],
        "feature_names": list(MSDB_FEATURE_NAMES),
        "max_axial_halfwidth_px": MAX_AXIAL_HALFWIDTH_PX,
        "euclidean_support_px_exact": EUCLIDEAN_SUPPORT_EXACT_PX,
        "physical_support_px": SUPPORT_PX,
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
        shape=(len(MSDB_FEATURE_NAMES), raw_stack.shape[1], raw_stack.shape[2]),
    )
    compute_msdb_features(raw_stack, valid_mask, out=target)
    target.flush()
    del target
    meta_path.write_text(json.dumps(expected_meta, indent=2) + "\n")
    return np.load(array_path, mmap_mode="r")


def calibrate_case_control_probabilities(
    sampled_prob: np.ndarray,
    *,
    population_positives: int,
    population_negatives: int,
    sample_positives: int,
    sample_negatives: int,
) -> np.ndarray:
    """Prentice-Pyke (1979) exact Bayes odds recalibration for case-control sampling.

    Under case-control subsampling with sample odds ``n_+ / n_-`` drawn from a
    training domain with true prevalence odds ``N_+ / N_-``, a calibrated sample
    posterior ``q(x)`` maps to spatial prevalence posterior ``pi(x)`` via::

        odds_ratio = (N_+ / N_-) / (n_+ / n_-)
        pi(x) = (odds_ratio * q(x)) / (odds_ratio * q(x) + 1 - q(x))

    All four counts must come strictly from ``train_mask`` (zero test leakage).
    """
    if min(population_positives, population_negatives, sample_positives, sample_negatives) <= 0:
        raise ValueError("All population and sample class counts must be strictly positive")
    pop_odds = float(population_positives) / float(population_negatives)
    samp_odds = float(sample_positives) / float(sample_negatives)
    rho = np.float32(pop_odds / samp_odds)
    q = np.clip(np.asarray(sampled_prob, dtype=np.float32), np.float32(0.0), np.float32(1.0))
    num = rho * q
    denom = num + (np.float32(1.0) - q)
    out = np.where(denom > np.float32(0.0), num / np.maximum(denom, np.float32(1.0e-12)), np.float32(0.0))
    return np.clip(out, np.float32(0.0), np.float32(1.0)).astype(np.float32, copy=False)


def fit_curvilinear_gate_scales(msdb_train_samples: np.ndarray) -> np.ndarray:
    """Estimate robust scale factors for the 6 discontinuity amplitude channels on training pixels."""
    if msdb_train_samples.ndim != 2 or msdb_train_samples.shape[1] != len(MSDB_FEATURE_NAMES):
        raise ValueError(f"Expected (N, {len(MSDB_FEATURE_NAMES)}) training sample matrix")
    scales = np.ones(len(GATE_AMPLITUDE_INDICES), dtype=np.float32)
    for out_idx, col_idx in enumerate(GATE_AMPLITUDE_INDICES):
        col = msdb_train_samples[:, col_idx]
        finite = col[np.isfinite(col)]
        if finite.size == 0:
            scales[out_idx] = np.float32(1.0)
            continue
        q25, q75 = np.percentile(finite, [25.0, 75.0])
        iqr_scale = (q75 - q25) / 1.349
        if not math.isfinite(iqr_scale) or iqr_scale <= 1.0e-8:
            med = float(np.median(np.abs(finite)))
            iqr_scale = med if (math.isfinite(med) and med > 1.0e-8) else 1.0
        scales[out_idx] = np.float32(iqr_scale)
    return scales


def compute_curvilinear_discontinuity_gate(
    msdb_stack: np.ndarray,
    gate_scales: np.ndarray,
    valid_mask: np.ndarray,
    *,
    block: int = 256,
) -> np.ndarray:
    """Compute Rayleigh curvilinear discontinuity gate ``Psi_curv in [0, 1]`` in tiles.

    Suppresses diffuse 2-D regional habitat interiors where no physical modality
    (topographic, magnetic, gravitational, basement-ramp, or radiometric) exhibits
    a 100-300 m curvilinear discontinuity, while transmitting near 1.0 along both
    exposed scarps and concealed subsurface fault ramps.
    """
    if msdb_stack.shape[0] != len(MSDB_FEATURE_NAMES):
        raise ValueError("Unexpected MSDB channel count")
    scales = np.asarray(gate_scales, dtype=np.float32)
    if scales.shape != (len(GATE_AMPLITUDE_INDICES),) or np.any(~np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError("Invalid gate_scales vector")
    valid = np.asarray(valid_mask, dtype=bool)
    height, width = valid.shape
    out = np.zeros((height, width), dtype=np.float32)
    amp_idx = list(GATE_AMPLITUDE_INDICES)
    coh_idx = list(GATE_COHERENCE_INDICES)

    for row in range(0, height, block):
        r1 = min(row + block, height)
        for col in range(0, width, block):
            c1 = min(col + block, width)
            sub_valid = valid[row:r1, col:c1]
            if not sub_valid.any():
                continue
            amps = np.asarray(msdb_stack[amp_idx, row:r1, col:c1], dtype=np.float32)
            amps = np.where(np.isfinite(amps), np.maximum(amps, np.float32(0.0)), np.float32(0.0))
            z_max = np.max(np.clip(amps / scales[:, None, None], np.float32(0.0), np.float32(6.0)), axis=0)

            cohs = np.asarray(msdb_stack[coh_idx, row:r1, col:c1], dtype=np.float32)
            cohs = np.where(np.isfinite(cohs), np.clip(cohs, np.float32(0.0), np.float32(1.0)), np.float32(0.0))
            coh_max = np.max(cohs, axis=0)

            score = z_max * (np.float32(0.5) + np.float32(0.5) * coh_max)
            psi = np.float32(1.0) - np.exp(np.float32(-0.5) * score * score)
            out[row:r1, col:c1] = np.where(sub_valid, np.clip(psi, np.float32(0.0), np.float32(1.0)), np.float32(0.0))
    return out


def select_msdb_edge_dots(
    calibrated_belief: np.ndarray,
    active_mask: np.ndarray,
    dot_budget: int,
) -> np.ndarray:
    """Exact count-matched 300 m submodular marginal-coverage dot selector.

    Uses ``gemsdoe30.emitter_opt.edge_select`` over the full ``active_mask``
    domain with ``truth_mass = 1e9`` (since ``edge_select``'s greedy acceptance
    order is scale-invariant in ``truth_mass``, a large ``truth_mass`` disables
    heuristic early stopping so every count-matched arm emits the exact predeclared
    ``dot_budget``).
    """
    from gemsdoe30.emitter_opt import edge_select

    if int(dot_budget) < 1:
        raise ValueError(f"dot_budget must be >= 1, got {dot_budget}")
    active = np.asarray(active_mask, dtype=bool)
    clean_belief = np.where(active & np.isfinite(calibrated_belief), np.maximum(calibrated_belief, 0.0), 0.0).astype(
        np.float32, copy=False
    )
    emitted, diag = edge_select(
        clean_belief,
        support=active,
        truth_mass=1.0e9,
        max_dots=int(dot_budget),
        return_diagnostics=True,
    )
    if int(diag["accepted"]) != int(dot_budget) or int(np.count_nonzero(emitted)) != int(dot_budget):
        raise ValueError(
            f"Submodular EDGE shortfall: requested {dot_budget}, accepted {diag['accepted']} "
            f"on {int(active.sum())} active pixels"
        )
    return emitted.astype(np.float32)
