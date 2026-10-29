"""The geothermal coverage-hole generator is retired and must stay fail-closed."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/build_unique_geothermal_submission.py"


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--help"],
        ["--force"],
        [
            "--template", "template.tif",
            "--lattice", "lattice.tif",
            "--external-dir", "external",
            "--output", "candidate.tif",
            "--sidecar", "receipt.json",
            "--run-name", "retry",
            "--note", "test",
            "--dot-budget", "1000",
            "--seed", "99",
        ],
    ],
)
def test_cli_refuses_old_generation_and_writes_nothing(tmp_path, arguments):
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *arguments],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "STOP: geothermal candidate generation is disabled" in result.stderr
    assert "no-evasion protocol" in result.stderr
    assert "NOT OK TO SUBMIT" in result.stderr
    assert not result.stdout
    assert list(tmp_path.iterdir()) == []


def test_imported_entrypoint_is_also_stopped(capsys):
    spec = importlib.util.spec_from_file_location("stopped_geothermal", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    assert module.main() == 2
    assert "STOP:" in capsys.readouterr().err
    assert not hasattr(module, "build_concealed_geothermal_score")
    assert not hasattr(module, "load_external_layer")
