from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HAS_GEOSPATIAL = bool(
    importlib.util.find_spec("numpy")
    and importlib.util.find_spec("rasterio")
)


@unittest.skipUnless(HAS_GEOSPATIAL, "optional numpy/rasterio dependencies are not installed")
class GeoTiffTests(unittest.TestCase):
    def _write_raster(self, path, array, *, transform, crs="EPSG:32611", nodata=float("nan")):
        import numpy as np
        import rasterio

        array = np.asarray(array)
        if array.ndim == 2:
            array = array[None, ...]
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=array.shape[1],
            width=array.shape[2],
            count=array.shape[0],
            dtype=array.dtype,
            crs=crs,
            transform=transform,
            nodata=nodata,
        ) as dst:
            dst.write(array)

    def test_writer_and_validator_match_template_and_nan_footprint(self) -> None:
        import numpy as np
        from affine import Affine

        from gemsdoe30.submission import validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path = root / "template.tif"
            output_path = root / "candidate.tif"
            transform = Affine.translation(243350.0, 4508550.0) @ Affine.scale(100.0, -100.0)
            template = np.zeros((6, 7), dtype=np.float32)
            template[-1, -1] = np.nan
            self._write_raster(template_path, template, transform=transform)
            probabilities = np.full(template.shape, 0.25, dtype=np.float32)
            probabilities[-1, -1] = np.nan

            manifest = write_submission_file(
                probabilities,
                template_path,
                output_path,
                note="GEMSDOE30 test | local synthetic only",
                run_name="GEMSDOE30_test",
            )
            report = validate_submission_file(output_path, template_path)
            self.assertTrue(report.passed, report.to_dict())
            self.assertEqual(manifest["format_validation"]["passed"], True)
            with __import__("rasterio").open(output_path) as src:
                self.assertEqual(src.count, 1)
                self.assertEqual(src.dtypes, ("float32",))
                self.assertEqual(src.crs.to_epsg(), 32611)
                values = src.read(1)
                self.assertTrue(np.isnan(values[-1, -1]))
                self.assertTrue(np.all(values[:-1, :] == 0.25))

    def test_writer_rejects_nan_or_out_of_range_inside(self) -> None:
        import numpy as np
        from affine import Affine

        from gemsdoe30.submission import write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path = root / "template.tif"
            transform = Affine.translation(243350.0, 4508550.0) @ Affine.scale(100.0, -100.0)
            template = np.zeros((4, 4), dtype=np.float32)
            self._write_raster(template_path, template, transform=transform)
            for bad in (float("nan"), float("inf"), -0.01, 1.01):
                probability = np.full((4, 4), 0.5, dtype=np.float32)
                probability[1, 1] = bad
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    write_submission_file(
                        probability,
                        template_path,
                        root / f"bad-{str(bad).replace('.', '_')}.tif",
                        note="bad",
                        run_name="bad",
                    )
            # This float64 value rounds to 1.0 in float32, but is invalid input.
            almost_one = np.full((4, 4), 0.5, dtype=np.float64)
            almost_one[1, 1] = 1.00000001
            with self.assertRaises(ValueError):
                write_submission_file(
                    almost_one,
                    template_path,
                    root / "rounding-must-not-hide-range-error.tif",
                    note="bad",
                    run_name="bad",
                )

    def test_prepare_data_handles_masked_integer_labels(self) -> None:
        import numpy as np
        from affine import Affine

        from scripts.prepare_data import prepare

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path = root / "sample_submission.tif"
            features_path = root / "training_features.tif"
            labels_path = root / "labels.tif"
            transform = Affine.translation(243350.0, 4508550.0) @ Affine.scale(100.0, -100.0)
            template = np.zeros((8, 9), dtype=np.float32)
            template[-1, -1] = np.nan
            self._write_raster(template_path, template, transform=transform)
            features = np.stack(
                [np.arange(72, dtype=np.float32).reshape(8, 9), np.ones((8, 9), dtype=np.float32)]
            )
            features[:, -1, -1] = np.nan
            self._write_raster(features_path, features, transform=transform)
            labels = np.zeros((8, 9), dtype=np.uint8)
            labels[2, 3] = 1
            # Integer label source with no nodata sentinel; the sample footprint masks outside.
            self._write_raster(labels_path, labels, transform=transform, nodata=None)
            output_dir = root / "processed"
            manifest = prepare(features_path, labels_path, template_path, output_dir)
            processed_labels = np.load(output_dir / "labels.npy")
            processed_valid = np.load(output_dir / "valid.npy")
            self.assertEqual(manifest["feature_channels"], 2)
            self.assertEqual(manifest["transform_gdal"], [float(value) for value in transform.to_gdal()])
            self.assertEqual(len(manifest["valid_mask_sha256"]), 64)
            self.assertEqual(int(processed_labels.sum()), 1)
            self.assertEqual(int(processed_valid.sum()), 71)
            raw_features = np.load(output_dir / "features_raw.npy")
            self.assertTrue(np.isnan(raw_features[:, -1, -1]).all())
            self.assertEqual(float(raw_features[0, 2, 3]), 21.0)
            self.assertIn("training-fold", manifest["normalization"]["fit_scope"])


if __name__ == "__main__":
    unittest.main()
