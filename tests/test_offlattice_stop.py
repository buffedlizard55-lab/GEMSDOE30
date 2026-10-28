"""The archived hole-filling experiment must not be regenerated or misinterpreted."""
import subprocess
import sys
from pathlib import Path

import numpy as np

from scripts.build_offlattice_submission import select_dots

ROOT = Path(__file__).resolve().parents[1]


def test_emission_does_not_depend_on_geological_rank_or_seed():
    uncovered = np.array([[True, False, True], [False, True, True]])
    a, _ = select_dots(uncovered, np.zeros((2, 3)), 1)
    b, _ = select_dots(uncovered, np.arange(6).reshape(2, 3), 99)
    np.testing.assert_array_equal(a, uncovered)
    np.testing.assert_array_equal(a, b)


def test_archived_cli_fails_closed_without_writing(tmp_path):
    target = tmp_path / 'candidate.tif'
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/build_offlattice_submission.py'),
         '--output', str(target), '--run-name', 'x', '--note', 'x'],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    assert result.returncode == 2
    assert 'STOP:' in result.stderr
    assert not target.exists()
