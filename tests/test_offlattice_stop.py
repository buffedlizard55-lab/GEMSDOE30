"""A stopped generator must not need data/dependencies or write any files."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/build_offlattice_submission.py'


@pytest.mark.parametrize('arguments', [[], ['--help'], ['--force'], [
    '--output', 'candidate.tif', '--sidecar', 'receipt.json',
    '--run-name', 'retry', '--note', 'test', '--seed', '99',
]])
def test_cli_fails_closed_without_side_effects(tmp_path, arguments):
    # -I excludes PYTHONPATH and the working directory from imports.
    result = subprocess.run([sys.executable, '-I', str(SCRIPT), *arguments],
                            cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert 'NOT OK TO SUBMIT' in result.stderr
    assert 'No file written' in result.stderr
    assert not result.stdout
    assert list(tmp_path.iterdir()) == []


def test_imported_entrypoint_is_also_stopped(capsys):
    spec = importlib.util.spec_from_file_location('stopped_offlattice', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 2
    assert 'STOP:' in capsys.readouterr().err
    assert not hasattr(module, 'select_dots')
    assert not hasattr(module, 'fetch_lattice')
