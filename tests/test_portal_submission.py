from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HAS_GEOSPATIAL = bool(importlib.util.find_spec("numpy") and importlib.util.find_spec("rasterio"))

FLOAT32_SENTINEL = -3.4028234663852886e38


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_portal_submission",
        Path(__file__).resolve().parents[1] / "scripts" / "build_portal_submission.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAS_GEOSPATIAL, "optional numpy/rasterio dependencies are not installed")
class PortalSubmissionBuilderTests(unittest.TestCase):
    """The builder must make the portal's [0, 1] range rejection impossible."""

    def _write(self, path: Path, array, *, nodata=float("nan")) -> None:
        import numpy as np
        import rasterio
        from affine import Affine

        transform = Affine.translation(243350.0, 4508550.0) @ Affine.scale(100.0, -100.0)
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

        template = np.zeros((8, 9), dtype=np.float32)
        template[0, :2] = np.nan          # outside footprint: top-left corner
        template[-1, -3:] = np.nan        # outside footprint: bottom-right corner
        template[3, 4] = 1.0
        path = root / "template.tif"
        self._write(path, template)
        return path, template

    def _dirty_source(self, root: Path, shape):
        """A source carrying both documented range-error mechanisms."""
        import numpy as np

        source = np.full(shape, 0.5, dtype=np.float32)
        source[5, 5] = 1.0
        source[3, 4] = 0.0
        # mechanism 1: raw float32 nodata sentinel inside the footprint
        source[6, 1] = np.float32(FLOAT32_SENTINEL)
        # mechanism 2: NaN inside the footprint (feature-mask mismatch)
        source[2, 7] = np.nan
        # out-of-range finite values
        source[4, 2] = 3.0
        source[4, 3] = -2.0
        path = root / "dirty_source.tif"
        self._write(path, source, nodata=None)
        return path, source

    def test_zeros_mode_is_range_error_immune(self) -> None:
        import numpy as np
        import rasterio

        builder = _load_builder()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, template = self._template(root)
            source_path, _ = self._dirty_source(root, template.shape)
            out = root / "candidate.tif"
            sidecar = root / "candidate.json"

            report = builder.build(
                source_path,
                template_path,
                out,
                run_name="test-zeros",
                note="unit test note",
                outside="zeros",
                sidecar=sidecar,
            )

            with rasterio.open(out) as ds:
                array = ds.read(1, masked=False)
                self.assertIsNone(ds.nodatavals[0])
                self.assertEqual(ds.count, 1)
                self.assertEqual(ds.dtypes, ("float32",))

            # The guarantee that matters: no NaN anywhere, nothing outside [0, 1].
            self.assertTrue(np.all(np.isfinite(array)))
            self.assertGreaterEqual(float(array.min()), 0.0)
            self.assertLessEqual(float(array.max()), 1.0)
            self.assertEqual(report["value_guarantees"]["nan_cells_anywhere"], 0)
            self.assertTrue(report["value_guarantees"]["all_cells_in_0_1"])
            self.assertTrue(report["range_error_immunity"]["immune_to_whole_raster_range_check"])
            self.assertTrue(report["validation_all_cells_finite"]["passed"])

            # Both documented mechanisms were actually present and were neutralised.
            self.assertEqual(report["sanitisation"]["float32_sentinel_hits_inside_footprint"], 1)
            self.assertEqual(report["sanitisation"]["nonfinite_inside_footprint_before"], 1)
            self.assertEqual(report["sanitisation"]["policy"], "nan->0.0, +inf->1.0, -inf->0.0, then clip to [0, 1]")

            # The ONLY published-format clause a zero-outside file may fail is the
            # null/NaN-outside encoding; anything else is a real defect.
            self.assertEqual(
                report["validation_published_format_failures"],
                ["null_outside_template_footprint"],
            )
            self.assertIn("outside_encoding_tradeoff", report)

            # Out-of-range finite values were clipped, in-range values preserved.
            footprint = np.isfinite(template)
            self.assertEqual(float(array[5, 5]), 1.0)
            self.assertEqual(float(array[3, 4]), 0.0)
            self.assertEqual(float(array[4, 2]), 1.0)   # 3.0 -> clipped to 1.0
            self.assertEqual(float(array[4, 3]), 0.0)   # -2.0 -> clipped to 0.0
            self.assertEqual(float(array[6, 1]), 0.0)   # sentinel -> 0.0
            self.assertEqual(float(array[2, 7]), 0.0)   # NaN -> 0.0
            self.assertTrue(np.all(array[~footprint] == 0.0))

            # Sidecar is real and self-consistent.
            receipt = json.loads(sidecar.read_text())
            self.assertEqual(receipt["output_sha256"], report["output_sha256"])
            self.assertEqual(receipt["drivendata_note"], "unit test note")

    def test_nan_mode_satisfies_published_format(self) -> None:
        import numpy as np
        import rasterio

        builder = _load_builder()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, template = self._template(root)
            source_path, _ = self._dirty_source(root, template.shape)
            out = root / "candidate_nan.tif"

            report = builder.build(
                source_path,
                template_path,
                out,
                run_name="test-nan",
                note="unit test note",
                outside="nan",
            )

            with rasterio.open(out) as ds:
                array = ds.read(1, masked=False)
            footprint = np.isfinite(template)
            self.assertTrue(np.all(np.isnan(array[~footprint])))
            self.assertTrue(np.all(np.isfinite(array[footprint])))
            self.assertTrue(report["validation_published_format"]["passed"])
            self.assertEqual(report["validation_published_format_failures"], [])
            self.assertFalse(report["range_error_immunity"]["immune_to_whole_raster_range_check"])

    def test_clean_source_in_footprint_is_preserved_bit_for_bit(self) -> None:
        import numpy as np
        import rasterio

        builder = _load_builder()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, template = self._template(root)
            clean = np.zeros(template.shape, dtype=np.float32)
            clean[1, 1] = 0.75
            clean[6, 6] = 1.0
            source_path = root / "clean.tif"
            self._write(source_path, clean, nodata=None)
            out = root / "clean_out.tif"

            builder.build(
                source_path,
                template_path,
                out,
                run_name="test-clean",
                note="n",
                outside="zeros",
            )
            with rasterio.open(out) as ds:
                array = ds.read(1, masked=False)
            footprint = np.isfinite(template)
            self.assertTrue(np.array_equal(array[footprint], clean[footprint]))

    def test_grid_mismatch_fails_closed(self) -> None:
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, template = self._template(root)
            wrong = root / "wrong.tif"
            import numpy as np

            self._write(wrong, np.zeros((template.shape[0] + 1, template.shape[1]), dtype=np.float32), nodata=None)
            with self.assertRaises(ValueError):
                builder.build(
                    wrong,
                    template_path,
                    root / "never.tif",
                    run_name="test-bad-grid",
                    note="n",
                    outside="zeros",
                )
            self.assertFalse((root / "never.tif").exists())

    def test_rejected_build_leaves_no_raster_on_disk(self) -> None:
        """A failed gate must not leave a raster in the published directory."""
        import gemsdoe30.submission as submission_module

        builder = _load_builder()
        original = submission_module.validate_submission_file

        def always_fail(*args, **kwargs):
            report = original(*args, **kwargs)
            checks = tuple(report.checks) + (
                submission_module.SubmissionCheck(
                    "injected_failure", False, "forced for the fail-closed test"
                ),
            )
            return submission_module.SubmissionReport(report.path, checks)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, template = self._template(root)
            source_path, _ = self._dirty_source(root, template.shape)
            out = root / "should_not_appear.tif"
            sidecar = root / "should_not_appear.json"

            submission_module.validate_submission_file = always_fail
            try:
                with self.assertRaises(AssertionError):
                    builder.build(
                        source_path,
                        template_path,
                        out,
                        run_name="test-rejected",
                        note="n",
                        outside="zeros",
                        sidecar=sidecar,
                    )
            finally:
                submission_module.validate_submission_file = original

            self.assertFalse(out.exists(), "rejected raster was published anyway")
            self.assertFalse(
                out.with_name(out.name + ".partial").exists(),
                "staging raster was left behind after a rejected build",
            )
            self.assertFalse(sidecar.exists(), "a sidecar was written for a rejected build")
            self.assertEqual([p.name for p in root.iterdir() if p.suffix == ".tif"], ["template.tif", "dirty_source.tif"])

    def test_successful_build_leaves_no_staging_file(self) -> None:
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, template = self._template(root)
            source_path, _ = self._dirty_source(root, template.shape)
            out = root / "published.tif"
            builder.build(source_path, template_path, out, run_name="test-ok", note="n", outside="zeros")
            self.assertTrue(out.exists())
            self.assertFalse(out.with_name(out.name + ".partial").exists())

    def test_rejects_unknown_outside_mode(self) -> None:
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template_path, template = self._template(root)
            source_path, _ = self._dirty_source(root, template.shape)
            with self.assertRaises(ValueError):
                builder.build(
                    source_path,
                    template_path,
                    root / "x.tif",
                    run_name="test-bad-mode",
                    note="n",
                    outside="maybe",
                )


if __name__ == "__main__":
    unittest.main()
