from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HAS_GEOSPATIAL = bool(importlib.util.find_spec("numpy") and importlib.util.find_spec("rasterio"))


@unittest.skipUnless(HAS_GEOSPATIAL, "optional numpy/rasterio dependencies are not installed")
class PortalSafeTests(unittest.TestCase):
    def _write_raster(self, path, array, *, transform, nodata=float("nan")):
        import numpy as np
        import rasterio

        array = np.asarray(array)
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=array.shape[0],
            width=array.shape[1],
            count=1,
            dtype=array.dtype,
            crs="EPSG:32611",
            transform=transform,
            nodata=nodata,
        ) as dst:
            dst.write(array, 1)

    def _template(self, root: Path):
        import numpy as np
        from affine import Affine

        transform = Affine.translation(243350.0, 4508550.0) @ Affine.scale(100.0, -100.0)
        template_path = root / "template.tif"
        template = np.zeros((6, 7), dtype=np.float32)
        template[-1, -1] = np.nan
        self._write_raster(template_path, template, transform=transform)
        return template_path, transform, template.shape

    def test_portal_safe_writer_emits_finite_zeros_outside(self) -> None:
        import numpy as np

        from gemsdoe30.submission import validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            output_path = root / "candidate-zeros.tif"
            probabilities = np.full(shape, 0.25, dtype=np.float32)

            manifest = write_submission_file(
                probabilities,
                template_path,
                output_path,
                note="GEMSDOE30 test | portal-safe synthetic",
                run_name="GEMSDOE30_test_zeros",
                outside_value=0.0,
            )
            self.assertEqual(manifest["outside_convention"], "0.0 portal-safe (finite everywhere)")
            report = validate_submission_file(output_path, template_path, portal_safe=True)
            self.assertTrue(report.passed, report.to_dict())
            with __import__("rasterio").open(output_path) as src:
                values = src.read(1)
                self.assertTrue(np.all(np.isfinite(values)))
                self.assertIsNone(src.nodata)
                self.assertEqual(float(values[-1, -1]), 0.0)
                self.assertTrue(np.all(values[:-1, :] == 0.25))

    def test_default_mode_still_requires_nan_outside(self) -> None:
        import numpy as np

        from gemsdoe30.submission import validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            output_path = root / "candidate-nan.tif"
            probabilities = np.full(shape, 0.25, dtype=np.float32)
            write_submission_file(
                probabilities,
                template_path,
                output_path,
                note="GEMSDOE30 test | nan synthetic",
                run_name="GEMSDOE30_test_nan",
            )
            default_report = validate_submission_file(output_path, template_path)
            self.assertTrue(default_report.passed, default_report.to_dict())
            # The NaN-outside file must fail the strict portal-safe check.
            strict = validate_submission_file(output_path, template_path, portal_safe=True)
            self.assertFalse(strict.passed)
            failed = {c.name for c in strict.checks if not c.passed}
            self.assertIn("finite_in_range_outside_footprint", failed)
            self.assertIn("portal_range_all_pixels", failed)

    def test_portal_safe_file_passes_both_modes_report_for_upload(self) -> None:
        import numpy as np

        from gemsdoe30.submission import validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            output_path = root / "candidate-zeros.tif"
            write_submission_file(
                np.full(shape, 1.0, dtype=np.float32),
                template_path,
                output_path,
                note="GEMSDOE30 test | portal-safe synthetic",
                run_name="GEMSDOE30_test_zeros",
                outside_value=0.0,
            )
            strict = validate_submission_file(output_path, template_path, portal_safe=True)
            self.assertTrue(strict.passed, strict.to_dict())

    def test_convert_to_portal_safe_preserves_footprint_bytes(self) -> None:
        import numpy as np

        from gemsdoe30.submission import convert_to_portal_safe, validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            source_path = root / "source-nan.tif"
            output_path = root / "converted-zeros.tif"
            probs = np.zeros(shape, dtype=np.float32)
            probs[0, 0] = 1.0
            probs[2, 3] = 0.5
            write_submission_file(
                probs,
                template_path,
                source_path,
                note="GEMSDOE30 test | source",
                run_name="GEMSDOE30_src",
            )
            manifest = convert_to_portal_safe(
                source_path,
                template_path,
                output_path,
                note="GEMSDOE30 test | converted",
                run_name="GEMSDOE30_conv",
            )
            self.assertTrue(manifest["in_footprint_identical_to_source"])
            self.assertIn("source_sha256", manifest)
            with __import__("rasterio").open(output_path) as dst, __import__("rasterio").open(source_path) as src:
                a = src.read(1, masked=False)
                b = dst.read(1, masked=False)
            valid = np.isfinite(a)
            self.assertTrue(np.array_equal(a[valid], b[valid]))
            self.assertTrue(np.all(b[~valid] == 0.0))
            self.assertTrue(validate_submission_file(output_path, template_path, portal_safe=True).passed)

    def test_portal_range_rejects_nan_anywhere(self) -> None:
        import numpy as np

        from gemsdoe30.submission import validate_portal_range

        ok = np.array([[0.0, 1.0], [0.5, 0.0]], dtype=np.float32)
        validate_portal_range(ok)  # must not raise
        bad = ok.copy()
        bad[0, 1] = np.nan
        with self.assertRaises(ValueError):
            validate_portal_range(bad)
        with self.assertRaises(ValueError):
            validate_portal_range(np.array([[1.5]], dtype=np.float32))

    def test_writer_rejects_outside_value_other_than_nan_or_zero(self) -> None:
        import numpy as np

        from gemsdoe30.submission import write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            with self.assertRaises(ValueError):
                write_submission_file(
                    np.zeros(shape, dtype=np.float32),
                    template_path,
                    root / "nope.tif",
                    note="x",
                    run_name="x",
                    outside_value=-1.0,
                )


if __name__ == "__main__":
    unittest.main()
