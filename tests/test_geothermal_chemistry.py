"""GDX-1 geological proxy and provenance guard regression tests."""
import csv
from pathlib import Path

import numpy as np
import pytest

from gemsdoe30.experiments import contract
from gemsdoe30.geothermal_chemistry import (
    CANDIDATE_COLUMNS, EFFORT_COLUMNS, EXTRA_NAMES, GUARD_PX, SUPPORT_PX,
    build_features, local_gradient, site_marks, smooth_marks,
)


FIELDS = ["row", "col", "temp_c", "geothermquartz_c", "geothermcat_c", "dist_known_fault_px"]


def csv_file(tmp_path, rows):
    path = tmp_path / "chemistry.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(zip(FIELDS, row)))
    return path


def test_contrasts_are_site_deduplicated_paired_and_label_free(tmp_path):
    valid = np.ones((101, 101), dtype=bool)
    rows = [[50, 50, 20, 120, 140, 0], [50, 50, 40, 160, 180, 999]]
    path = csv_file(tmp_path, rows * 3)
    effort, marks, receipt = site_marks(path, valid)
    assert effort.sum() == 1
    assert marks[0][0][50, 50] == pytest.approx(1.1)
    assert marks[1][0][50, 50] == pytest.approx(0.2)
    assert receipt["forbidden_fields_read"] == []
    rows[0][-1] = "this column must never be parsed"
    path = csv_file(tmp_path, rows)
    e2, m2, _ = site_marks(path, valid)
    assert np.array_equal(effort, e2)
    for a, b in zip(marks, m2):
        assert np.array_equal(a[0], b[0])


def test_unpaired_samples_do_not_invent_reservoir_cooling(tmp_path):
    valid = np.ones((101, 101), dtype=bool)
    path = csv_file(tmp_path, [[50, 50, 20, 120, 140, 1],
                               [40, 40, 30, "", "", 2],
                               [40, 40, "", 300, "", 3]])
    _, marks, _ = site_marks(path, valid)
    assert marks[0][1][40, 40] == 0
    assert marks[1][1][40, 40] == 0
    assert marks[2][1][40, 40] == 0


def test_each_mark_normalized_by_its_own_observation_effort(tmp_path):
    valid = np.ones((101, 101), dtype=bool)
    path = csv_file(tmp_path, [[50, 50, 20, 120, 140, 0], [51, 50, 0, "", "", 0]])
    effort, marks, _ = site_marks(path, valid)
    fields = smooth_marks(effort, marks, valid)
    assert fields["gdx_quartz_cooling"][50, 50] == pytest.approx(1.0)
    assert fields["gdx_quartz_cooling_observed"][50, 50] == 1
    assert fields["gdx_sampling_effort"][50, 50] > np.log(2)
    assert fields["gdx_quartz_cooling"][0, 0] == 0
    assert fields["gdx_quartz_cooling_observed"][0, 0] == 0
    valid[0, 0] = False
    assert np.isnan(smooth_marks(effort, marks, valid)["gdx_sampling_effort"][0, 0])


def test_invalid_rows_and_nonfinite_measurements_fail_safely(tmp_path):
    valid = np.ones((101, 101), dtype=bool)
    path = csv_file(tmp_path, [[50, 50, 0, 100, 120, 0],
                               [-1, 50, 10, 100, 120, 0],
                               [999, 50, 10, 100, 120, 0],
                               [51, 50, "NaN", "Inf", "-9999", 0]])
    effort, marks, receipt = site_marks(path, valid)
    assert effort.sum() == 1
    assert marks[0][0][50, 50] == 1  # zero C is accepted, not treated as missing
    assert receipt["invalid_grid_records"] == 2
    path.write_text("row,col\n0,0\n")
    with pytest.raises(ValueError, match="missing required"):
        site_marks(path, valid)


def test_missing_required_contrast_stops_before_model(tmp_path):
    path = csv_file(tmp_path, [[50, 50, 20, "", "", 0]])
    with pytest.raises(ValueError, match="each chemical contrast"):
        site_marks(path, np.ones((101, 101), dtype=bool))


def test_feature_support_and_gradient_sentinel_protection(tmp_path):
    assert SUPPORT_PX + 3 <= GUARD_PX
    n = 111
    valid = np.ones((n, n), dtype=bool)
    x = np.broadcast_to(np.arange(n, dtype=np.float32), (n, n)).copy()
    assert local_gradient(x, valid)[55, 55] == pytest.approx(.01)
    x[55, 55] = -3.4028235e38
    gradient = local_gradient(x, valid)
    assert np.isnan(gradient[55, 55])
    assert gradient[55, 65] == pytest.approx(.01)
    path = csv_file(tmp_path, [[55, 55, 20, 120, 140, 0]])
    b = np.ones((19, n, n), dtype=np.float32)
    out, _ = build_features(b, valid, path)
    assert set(out) == set(EXTRA_NAMES)
    assert len(CANDIDATE_COLUMNS) == 12
    assert len(EFFORT_COLUMNS) == 6
    assert len(contract({"experiment_spec": "gdx1"})["features"]) == 28
    assert out["gdx_sampling_effort"][55, 86] == 0  # beyond compact Gaussian support
