"""POOL-1 release invariants: confirmed science, duplicate-stop, nothing published."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/research/2026-10-27-pool"
sys.path.insert(0, str(ROOT / "src"))


def load(name: str) -> dict:
    return json.loads((REPORT / name).read_text())


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def test_pool1_contract_registered():
    from gemsdoe30.experiments import contract

    spec = contract({"experiment_spec": "pool1"})
    assert spec["candidate"] == "pool_dispersed"
    assert spec["arms"] == ("msdb_edge", "pool_dense_edge", "pool_dispersed")
    assert spec["required_positive_deltas"] == ("msdb_edge",)
    assert len(spec["features"]) == 81


def test_pool1_science_passed_but_duplicate_stopped():
    card = load("run-card.json")
    results = load("results.json")
    assert card["verdict"] == "negative"
    assert card["published_tiff"] is None
    assert card["download_ok"] is False and card["ok_to_submit"] is False
    assert card["organizer_score"] is None
    assert card["experiments_run"] == 3
    assert len(card["note"]) <= 140
    for summary in (results["summary"], results["confirmation_seed4219"]):
        delta = summary["candidate_minus"]["msdb_edge"]
        assert delta["value"] > 0 and delta["ci95"][0] > 0
    assert results["canary_alarms"] == []
    assert results["max_feature_symmetric_auc"] <= 0.90
    dots = load("novelty-dots.json")
    breaches = {r["reference"] for r in dots["comparisons"]
                if float(r["candidate_fraction_within_3px_of_reference"] or 0.0) > 0.70}
    assert len(breaches) == 3 and dots["decision"] == "duplicate-stop"
    assert not list((ROOT / "docs/downloads").glob("*POOL1*"))


def test_pool1_hash_binding():
    prereg = load("preregistration.json")
    started = load("started.json")
    assert sha(REPORT / "registry.json") == prereg["registry_sha256"]
    assert sha(REPORT / "preregistration.md") == started["preregistration_md_sha256"]


def test_pool1_verifier_cli():
    ok = subprocess.run([sys.executable, "scripts/verify_pool_run.py"],
                        cwd=ROOT, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    promo = subprocess.run([sys.executable, "scripts/verify_pool_run.py", "--require-promote"],
                           cwd=ROOT, capture_output=True, text=True)
    assert promo.returncode == 2
