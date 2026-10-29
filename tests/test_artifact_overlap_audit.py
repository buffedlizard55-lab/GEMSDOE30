"""The overlap audit must fail closed (exit 1, no receipt) on missing inputs."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_artifact_overlap.py"


def test_missing_candidate_fails_closed(tmp_path):
    out = tmp_path / "receipt.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--candidate", str(tmp_path / "absent.tif"), "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 1
    assert not out.exists()
    assert "missing required input" in result.stderr
