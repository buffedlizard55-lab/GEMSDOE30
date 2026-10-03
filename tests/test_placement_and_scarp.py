"""Unit tests for spacing-matched holdout helpers and external layer CRS/encoding helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point

from scripts.fetch_external_layers import (
    project_geometries_to_grid_crs,
    read_csv_with_fallback,
)
from scripts.placement_and_scarp_holdout import (
    median_nn_spacing_px,
    poisson_disk_top_n,
    poisson_distance_matched_draw,
)
from scripts.run_verification_checks import build_scarp_score_from_dict


class SpacingAndScarpTests(unittest.TestCase):
    def test_poisson_disk_top_n_enforces_spacing(self) -> None:
        rng = np.random.default_rng(19)
        score = rng.uniform(0.0, 1.0, size=(60, 60))
        # Create a dense high-score patch that would clump under un-thinned top-N
        score[20:30, 20:30] += 5.0
        support = np.ones((60, 60), dtype=bool)

        emitted = poisson_disk_top_n(score, support, count=80, radius_px=3.0)
        self.assertEqual(int(emitted.sum()), 80)

        spacing = median_nn_spacing_px(emitted)
        self.assertGreaterEqual(spacing["median_nn_px"], 3.0 - 1e-6)

    def test_poisson_distance_matched_draw_matches_histogram_and_spacing(self) -> None:
        dist = np.broadcast_to(
            np.linspace(0.0, 15000.0, 80, dtype=np.float32)[None, :], (80, 80)
        ).copy()
        support = dist >= 300.0
        target = np.zeros((80, 80), dtype=bool)
        target[10:70:4, 15:35:4] = True  # 15 * 5 = 75 dots in near-splay/stepover bands

        rng = np.random.default_rng(23)
        ctrl = poisson_distance_matched_draw(
            support,
            target,
            dist,
            count=int(target.sum()),
            rng=rng,
            radius_px=3.0,
        )
        self.assertEqual(int(ctrl.sum()), int(target.sum()))
        spacing = median_nn_spacing_px(ctrl)
        self.assertGreaterEqual(spacing["median_nn_px"], 3.0 - 1e-6)

    def test_build_scarp_score_from_dict_handles_lidar_and_fallback(self) -> None:
        shape = (32, 32)
        valid = np.ones(shape, dtype=bool)
        lidar_valid = np.zeros(shape, dtype=bool)
        lidar_valid[:16, :] = True

        step_max = np.zeros(shape, dtype=np.float64)
        lapneg_max = np.zeros(shape, dtype=np.float64)
        lappos_max = np.zeros(shape, dtype=np.float64)
        coh100 = np.zeros(shape, dtype=np.float64)
        strike = np.zeros(shape, dtype=np.float64)
        det_elev_slope = np.full(shape, 5.0, dtype=np.float64)

        # Put a strong horizontal scarp line along row 8 in the LiDAR region
        step_max[8, 4:28] = 200.0
        lapneg_max[8, 4:28] = 200.0
        lappos_max[8, 4:28] = 200.0
        coh100[8, 4:28] = 0.90
        strike[8, 4:28] = 0.0  # East-West strike (0 deg)

        # Put a strong slope anomaly in the non-LiDAR fallback region
        det_elev_slope[24, 4:28] = 35.0

        dipole = build_scarp_score_from_dict(
            {
                "step_max": step_max,
                "lapneg_max": lapneg_max,
                "lappos_max": lappos_max,
                "coh100": coh100,
                "strike": strike,
                "lidar_valid": lidar_valid,
                "det_elev_slope": det_elev_slope,
            },
            valid,
        )
        self.assertEqual(dipole.shape, shape)
        self.assertTrue(np.all((dipole >= 0.0) & (dipole <= 1.0)))
        # Scarp line should score much higher than background LiDAR pixels
        self.assertGreater(float(dipole[8, 16]), float(dipole[4, 16]) + 0.3)
        # Fallback region anomaly should also outscore fallback background
        self.assertGreater(float(dipole[24, 16]), float(dipole[20, 16]) + 0.15)


class ExternalLayerHelperTests(unittest.TestCase):
    def test_project_geometries_to_grid_crs_preserves_utm_and_reprojects_albers(self) -> None:
        # 1. Geometry already in EPSG:32611 (e.g. Faults_24k.shp)
        utm_line = LineString([(350000.0, 4300000.0), (351000.0, 4301000.0)])
        proj_utm = project_geometries_to_grid_crs([utm_line], source_crs="EPSG:32611")
        self.assertEqual(len(proj_utm), 1)
        x0, y0 = proj_utm[0].coords[0]
        self.assertAlmostEqual(x0, 350000.0, places=3)
        self.assertAlmostEqual(y0, 4300000.0, places=3)

        # 2. Geometry in EPSG:4326 (lon/lat inside Nevada)
        wgs_pt = Point(-118.0, 39.0)
        proj_wgs = project_geometries_to_grid_crs([wgs_pt], source_crs=None)
        self.assertEqual(len(proj_wgs), 1)
        px, py = proj_wgs[0].coords[0]
        self.assertTrue(200000.0 < px < 650000.0)
        self.assertTrue(4100000.0 < py < 4600000.0)

    def test_read_csv_with_fallback_handles_latin1_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "latin1.csv"
            # Write Latin-1 byte 0xb0 (degree symbol) that fails strict UTF-8
            raw = "Site,Temp_C,Notes\n Dixie,120\xb0C, Sinter\n".encode("latin-1")
            csv_path.write_bytes(raw)
            rows = read_csv_with_fallback(csv_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Site"].strip(), "Dixie")


if __name__ == "__main__":
    unittest.main()
