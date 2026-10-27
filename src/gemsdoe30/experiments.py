"""Explicit supported experiment contracts; unknown experiment IDs fail closed.

Contracts are code-reviewed, not arbitrary mutable JSON that can redefine a failed
promotion gate. Old TDX-1, TDX-C2, and MSDB-1v2 receipts keep their original schema and expectations.
"""
from __future__ import annotations

CORE_FEATURES = (
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15", "cond_surf",
    "iso_grav_anom_hg", "det_elev_slope",
)
TDX_FEATURES = ("mag_texture", "rtp_texture", "texture_consensus")
CONTROL_FEATURES = ("zero_mag", "zero_rtp", "zero_consensus", "phase_mag", "phase_rtp", "phase_consensus")
MSDB_FEATURES = (
    "msdb_mag_tilt_rad", "msdb_mag_tilt_zero_crest", "msdb_mag_contact_invdepth",
    "msdb_topo_tubularity_100m", "msdb_topo_tubularity_300m", "msdb_topo_saddle_300m",
    "msdb_rtp_tubularity_300m", "msdb_grav_tubularity_300m", "msdb_base_tubularity_300m",
    "msdb_cond_saddle_300m", "msdb_topo_coherence", "msdb_grav_coherence",
    "msdb_align_grav_basement", "msdb_align_rtp_grav", "msdb_align_topo_radtc",
    "msdb_piedmont_ramp_index", "msdb_radtc_grad_300m", "msdb_transtensional_index",
)
PTA_CANDIDATE_FEATURES = (
    "pta_mag_tilt",
    "pta_mag_hd_tdr",
    "pta_mag_as3d_log",
    "pta_grav_tilt",
    "pta_grav_hd_tdr",
    "pta_mg_strike_concord",
    "pta_strike_persist",
    "pta_dip_grav_mig",
    "pta_dip_cover_step",
    "pta_dip_cond_step",
)
PTA_CONTROL_FEATURES = (
    "ctrl_naive_mag_tilt",
    "ctrl_naive_mag_hd_tdr",
    "ctrl_naive_mag_as3d_log",
    "ctrl_naive_mg_concord",
    "ctrl_normal_blur",
    "ctrl_sym_grav_mig",
    "ctrl_sym_cover_step",
    "ctrl_sym_cond_step",
)
LIDAR_FEATURES = (
    "lidar_valid", "step_max", "ex_max", "ex_mean", "lapneg_max", "lappos_max",
    "downface_max", "upface_max", "cross_max", "relief", "coh100",
    "scarp_dipole", "scarp_face", "face_vs_channel", "strike_persistence_5x5",
    "scarp_face_max3", "scarp_dipole_smooth",
)


def contract(card: dict) -> dict:
    name = card.get("experiment_spec", "tdx1")
    if name == "tdx1":
        return {
            "id": name,
            "candidate": "tdx6",
            "arms": ("physics3", "core19", "tdx6"),
            "required_positive_deltas": ("physics3", "core19"),
            "features": CORE_FEATURES + TDX_FEATURES,
            "support_px": 17,
            "guard_px": 17,
            "transform_path": "src/gemsdoe30/texture.py",
            "transform_version": "tdx1-profiles-v2-euclidean-support-20261025",
            "label": "TDX-1",
            "image_name": "tdx1-support.png",
        }
    if name == "tdxc2":
        return {
            "id": name,
            "candidate": "tdx22",
            "arms": ("core19", "tdx22", "zero22", "phase22"),
            "required_positive_deltas": ("core19", "zero22", "phase22"),
            "features": CORE_FEATURES + TDX_FEATURES + CONTROL_FEATURES,
            "support_px": 17,
            "guard_px": 17,
            "transform_path": "src/gemsdoe30/texture_controls.py",
            "parent_transform_path": "src/gemsdoe30/texture.py",
            "parent_transform_version": "tdx1-profiles-v2-euclidean-support-20261025",
            "transform_version": "tdxc2-local-profile-controls-v1-20261025",
            "label": "TDX-C2",
            "image_name": "tdxc2-support.png",
        }
    if name == "msdb1v2":
        return {
            "id": name,
            "candidate": "msdb_edge",
            "arms": ("core19", "msdb_poisson", "msdb_edge"),
            "required_positive_deltas": ("core19",),
            "features": CORE_FEATURES + MSDB_FEATURES,
            "support_px": 13,
            "guard_px": 17,
            "transform_path": "src/gemsdoe30/msdb.py",
            "transform_version": "msdb-piedmont-v2-20261025",
            "label": "MSDB-1v2",
            "image_name": "msdb1-support.png",
        }
    if name == "pta1":
        return {
            "id": name,
            "candidate": "pta1_cand",
            "arms": ("core19", "sub8_raw", "pta_naive_sym", "pta1_cand"),
            "required_positive_deltas": ("core19", "sub8_raw", "pta_naive_sym"),
            "features": CORE_FEATURES + PTA_CANDIDATE_FEATURES + PTA_CONTROL_FEATURES,
            "support_px": 17,
            "guard_px": 17,
            "tight_analytic_support_px": 12,
            "transform_path": "src/gemsdoe30/phase_tilt.py",
            "transform_version": "phase-tilt-dip-asymmetry-v1-support17px-20261025",
            "label": "PTA-1",
            "image_name": "pta1-support.png",
        }
    if name == "gdx1":
        from .geothermal_chemistry import EXTRA_NAMES, GUARD_PX, SUPPORT_PX, VERSION
        return {
            "id": name,
            "candidate": "gdx12",
            "arms": ("core19", "effort6", "gdx12"),
            "required_positive_deltas": ("core19", "effort6"),
            "features": CORE_FEATURES + EXTRA_NAMES,
            "support_px": SUPPORT_PX,
            "guard_px": GUARD_PX,
            "transform_path": "src/gemsdoe30/geothermal_chemistry.py",
            "transform_version": VERSION,
            "label": "GDX-1",
        }
    if name == "qpc1":
        from .quadrature_phase import FEATURE_NAMES, GUARD_PX, SUPPORT_PX, VERSION
        return {
            "id": name,
            "candidate": "qpc23",
            "arms": ("core19", "persistence21", "qpc23", "msdb_edge", "ffl_confirm"),
            "required_positive_deltas": ("persistence21", "msdb_edge", "ffl_confirm"),
            "features": CORE_FEATURES + FEATURE_NAMES,
            "support_px": SUPPORT_PX,
            "guard_px": GUARD_PX,
            "transform_path": "src/gemsdoe30/quadrature_phase.py",
            "transform_version": VERSION,
            "label": "QPC-1",
        }
    if name == "fflidar1":
        return {
            "id": name,
            "candidate": "fusion_ffstrat",
            "arms": ("msdb_edge", "fusion_edge", "fusion_ffstrat"),
            "required_positive_deltas": ("msdb_edge", "fusion_edge"),
            "features": CORE_FEATURES + MSDB_FEATURES + LIDAR_FEATURES,
            "support_px": 13,
            "guard_px": 17,
            "transform_path": "src/gemsdoe30/msdb.py",
            "transform_version": "msdb-piedmont-v2-20261025",
            "label": "FFL-1",
            "image_name": "fflidar-support.png",
        }
    if name == "csr1":
        from .csr_discontinuity import CSR_ALL_DERIVED_NAMES, GUARD_PX, SUPPORT_PX, TRANSFORM_VERSION
        return {
            "id": name,
            "candidate": "csr_dispersed",
            "arms": ("core19_edge", "msdb_edge", "csr_dense_edge", "csr_dispersed"),
            "required_positive_deltas": ("core19_edge", "msdb_edge"),
            "features": CORE_FEATURES + MSDB_FEATURES + CSR_ALL_DERIVED_NAMES + LIDAR_FEATURES,
            "support_px": SUPPORT_PX,
            "guard_px": GUARD_PX,
            "transform_path": "src/gemsdoe30/csr_discontinuity.py",
            "transform_version": TRANSFORM_VERSION,
            "label": "CSR-1",
        }
    if name == "pool1":
        from .csr_discontinuity import CSR_ALL_DERIVED_NAMES, GUARD_PX, SUPPORT_PX, TRANSFORM_VERSION
        return {
            "id": name,
            "candidate": "pool_dispersed",
            "arms": ("msdb_edge", "pool_dense_edge", "pool_dispersed"),
            "required_positive_deltas": ("msdb_edge",),
            "features": CORE_FEATURES + MSDB_FEATURES + CSR_ALL_DERIVED_NAMES + LIDAR_FEATURES,
            "support_px": SUPPORT_PX,
            "guard_px": GUARD_PX,
            "transform_path": "src/gemsdoe30/csr_discontinuity.py",
            "transform_version": TRANSFORM_VERSION,
            "label": "POOL-1",
        }
    raise ValueError(f"unknown research experiment contract: {name!r}")


class LayerStack:
    """A zero-copy channel view over cached arrays for the existing sampler/predictor."""

    def __init__(self, layers):
        self.layers = tuple(layers)
        if not self.layers or len(self.layers[0].shape) != 2:
            raise ValueError("at least one 2D layer required")
        if any(layer.shape != self.layers[0].shape for layer in self.layers):
            raise ValueError("all layer shapes must match")
        self.shape = (len(self.layers), *self.layers[0].shape)

    def __getitem__(self, key):
        import numpy as np
        if not isinstance(key, tuple) or len(key) != 3:
            raise IndexError("channel, row and column selectors required")
        channel, row, col = key
        if isinstance(channel, (int, np.integer)):
            return self.layers[channel][row, col]
        indices = np.arange(len(self.layers))[channel]
        return np.stack([self.layers[int(i)][row, col] for i in indices])
