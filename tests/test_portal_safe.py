from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HAS_GEOSPATIAL = bool(importlib.util.find_spec("numpy") and importlib.util.find_spec("rasterio"))


@unittest.skipUnless(HAS_GEOSPATIAL, "optional numpy/rasterio dependencies are not installed")
class SubmissionOutsideConventionTests(unittest.TestCase):
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

    def test_default_writer_matches_published_nan_outside_contract(self) -> None:
        import numpy as np
        import rasterio

        from gemsdoe30.submission import validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            output_path = root / "candidate-nan.tif"
            probabilities = np.full(shape, 0.25, dtype=np.float32)

            manifest = write_submission_file(
                probabilities,
                template_path,
                output_path,
                note="GEMSDOE30 test | published-format NaN outside",
                run_name="GEMSDOE30_test_nan",
            )

            self.assertEqual(manifest["schema_version"], 3)
            self.assertTrue(manifest["published_format_compliant"])
            self.assertEqual(manifest["outside_convention"], "NaN outside; matches published GEMS format")
            self.assertFalse(manifest["whole_raster_range_diagnostic_passed"])
            self.assertFalse(manifest["whole_raster_range_diagnostic"]["passed"])
            report = validate_submission_file(output_path, template_path)
            self.assertTrue(report.passed, report.to_dict())
            advisory = next(check for check in report.checks if check.name.endswith("_advisory"))
            self.assertTrue(advisory.passed)
            self.assertIn("advisory only", advisory.detail)
            with rasterio.open(output_path) as src:
                values = src.read(1, masked=False)
                self.assertTrue(np.all(np.isfinite(values[:-1, :])))
                self.assertTrue(np.isnan(values[-1, -1]))
                self.assertTrue(np.isnan(src.nodata))
                self.assertTrue(np.all(values[:-1, :] == 0.25))

    def test_zero_outside_is_only_a_nonstandard_diagnostic(self) -> None:
        import numpy as np
        import rasterio

        from gemsdoe30.submission import validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            output_path = root / "candidate-zeros.tif"
            manifest = write_submission_file(
                np.full(shape, 0.25, dtype=np.float32),
                template_path,
                output_path,
                note="GEMSDOE30 test | nonstandard diagnostic only",
                run_name="GEMSDOE30_test_zeros",
                outside_value=0.0,
            )

            self.assertFalse(manifest["published_format_compliant"])
            self.assertIn("does not match published", manifest["outside_convention"])
            self.assertTrue(manifest["whole_raster_range_diagnostic"]["passed"])
            self.assertTrue(manifest["whole_raster_range_diagnostic_passed"])
            published = validate_submission_file(output_path, template_path)
            self.assertFalse(published.passed)
            failed = {check.name for check in published.checks if not check.passed}
            self.assertEqual(failed, {"null_outside_template_footprint"})
            diagnostic = validate_submission_file(output_path, template_path, require_finite_all_cells=True)
            self.assertTrue(diagnostic.passed, diagnostic.to_dict())
            legacy_alias = validate_submission_file(output_path, template_path, portal_safe=True)
            self.assertTrue(legacy_alias.passed, legacy_alias.to_dict())
            with rasterio.open(output_path) as src:
                values = src.read(1, masked=False)
                self.assertTrue(np.all(np.isfinite(values)))
                self.assertIsNone(src.nodata)
                self.assertEqual(float(values[-1, -1]), 0.0)
                self.assertTrue(np.all(values[:-1, :] == 0.25))

    def test_nan_outside_fails_only_the_stricter_whole_array_diagnostic(self) -> None:
        import numpy as np

        from gemsdoe30.submission import validate_submission_file, write_submission_file

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            output_path = root / "candidate-nan.tif"
            write_submission_file(
                np.full(shape, 0.25, dtype=np.float32),
                template_path,
                output_path,
                note="GEMSDOE30 test | NaN outside",
                run_name="GEMSDOE30_test_nan",
            )
            self.assertTrue(validate_submission_file(output_path, template_path).passed)
            strict = validate_submission_file(output_path, template_path, require_finite_all_cells=True)
            self.assertFalse(strict.passed)
            failed = {check.name for check in strict.checks if not check.passed}
            self.assertEqual(
                failed,
                {"finite_in_range_outside_footprint_diagnostic", "whole_raster_finite_range_diagnostic"},
            )

    def test_legacy_zero_outside_converter_records_both_results(self) -> None:
        import numpy as np
        import rasterio

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
                note="GEMSDOE30 test | diagnostic only",
                run_name="GEMSDOE30_conv",
            )
            self.assertTrue(manifest["in_footprint_identical_to_source"])
            self.assertIn("source_sha256", manifest)
            self.assertFalse(manifest["published_format_compliant"])
            self.assertTrue(manifest["whole_raster_range_diagnostic"]["passed"])
            with rasterio.open(output_path) as dst, rasterio.open(source_path) as src:
                a = src.read(1, masked=False)
                b = dst.read(1, masked=False)
            valid = np.isfinite(a)
            self.assertTrue(np.array_equal(a[valid], b[valid]))
            self.assertTrue(np.all(b[~valid] == 0.0))
            self.assertFalse(validate_submission_file(output_path, template_path).passed)
            self.assertTrue(
                validate_submission_file(output_path, template_path, require_finite_all_cells=True).passed
            )

    def test_whole_array_range_helper_rejects_nan_and_out_of_range_values(self) -> None:
        import numpy as np

        from gemsdoe30.submission import validate_portal_range

        ok = np.array([[0.0, 1.0], [0.5, 0.0]], dtype=np.float32)
        validate_portal_range(ok)  # compatibility helper for a diagnostic, not portal behavior
        bad_nan = ok.copy()
        bad_nan[0, 1] = np.nan
        with self.assertRaisesRegex(ValueError, "not a diagnosis of portal behavior"):
            validate_portal_range(bad_nan)
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

    def test_legacy_conversion_cli_requires_explicit_nonstandard_acknowledgement(self) -> None:
        import numpy as np
        import json
        from gemsdoe30.submission import write_submission_file

        repo_root = Path(__file__).resolve().parents[1]
        converter = repo_root / "scripts" / "make_portal_safe.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            source_path = root / "source-nan.tif"
            output_path = root / "diagnostic-zeros.tif"
            write_submission_file(
                np.full(shape, 0.5, dtype=np.float32),
                template_path,
                source_path,
                note="source",
                run_name="source",
            )
            command = [
                sys.executable,
                str(converter),
                str(source_path),
                "--template", str(template_path),
                "--output", str(output_path),
            ]
            rejected = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertIn("conflicts with the published GEMS format", rejected.stderr)
            self.assertFalse(output_path.exists())

            accepted = subprocess.run(
                command + ["--confirm-nonstandard-outside"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            manifest = json.loads(output_path.with_suffix(".json").read_text())
            self.assertFalse(manifest["published_format_compliant"])
            self.assertTrue(manifest["whole_raster_range_diagnostic"]["passed"])
            self.assertIn("not a submission recommendation", manifest["note"])

    def test_builder_defaults_to_nan_and_requires_explicit_zero_diagnostic(self) -> None:
        import numpy as np
        import rasterio

        repo_root = Path(__file__).resolve().parents[1]
        builder = repo_root / "scripts" / "build_submission.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, _, shape = self._template(root)
            probability_path = root / "probabilities.npy"
            np.save(probability_path, np.full(shape, 0.5, dtype=np.float32))
            output_dir = root / "out"

            rejected = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    "--probabilities", str(probability_path),
                    "--template", str(template_path),
                    "--output-dir", str(output_dir),
                    "--outside", "zeros",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertIn("does not match the published", rejected.stderr)
            self.assertFalse(output_dir.exists())

            accepted = subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    "--probabilities", str(probability_path),
                    "--template", str(template_path),
                    "--output-dir", str(output_dir),
                    "--name", "test-default-nan",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            tiffs = list(output_dir.glob("*.tif"))
            self.assertEqual(len(tiffs), 1)
            self.assertTrue(tiffs[0].name.endswith("-nan.tif"))
            with rasterio.open(tiffs[0]) as src:
                self.assertTrue(np.isnan(src.read(1, masked=False)[-1, -1]))
            sidecar = json.loads(tiffs[0].with_suffix(".json").read_text())
            self.assertTrue(sidecar["published_format_compliant"])
            self.assertIn(sidecar["run_name"], tiffs[0].stem)
            self.assertIn("method label: test-default-nan", sidecar["note"])
            self.assertIn("holdout status: unverified", sidecar["note"])
            self.assertEqual(sidecar["outside_convention"], "NaN outside; matches published GEMS format")


if __name__ == "__main__":
    unittest.main()
