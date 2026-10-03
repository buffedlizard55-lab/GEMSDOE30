#!/usr/bin/env python3
"""Preregistered follow-up to the regional-vs-boundary ablation: fold-0 boundary-weight sweep.

The seed-30 screen (+0.0019) did not replicate at seed 31 (+0.0001). The recorded
next step was: "use a larger training budget and a boundary-weight sweep before
any fresh-seed test, and score emitted masks rather than dense probability
surfaces." This script executes exactly that screen on fold 0 (the same buffered
spatial quadrant design as the ablation), at a 2.5x larger step budget than the
original 2 x 20-step screen:

    arm regional       soft-Tversky only
    arm combined-025   regional + 0.25 x metric-geometry term
    arm combined-050   regional + 0.50 x term (the ablation's untuned setting)
    arm combined-100   regional + 1.00 x term

Each arm trains with an identical recipe and seed, predicts its held-out
quadrant, and is scored both densely and as a uniform Poisson-disk emitted mask
(default emission family). Fold-isolated values are diagnostics: a weight is
only *selected* here if it is best on both scorings; the promotion decision
still requires the full four-fold paired design plus fresh-seed confirmation.

Output: ``docs/research/loss-weight-sweep.json`` + printed summary.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ARMS = (
    ("regional", "regional", 0.0),
    ("combined-025", "combined", 0.25),
    ("combined-050", "combined", 0.5),
    ("combined-100", "combined", 1.0),
)


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--steps-per-epoch", type=int, default=50)
    parser.add_argument("--runs-dir", type=Path, default=Path("runs/loss-weight-sweep"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/loss-weight-sweep.json"))
    args = parser.parse_args()

    runs = ROOT / args.runs_dir
    runs.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    report: dict = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "design": "fold-0 boundary-weight screen; larger budget than the 2x20-step ablation screen; "
                  "identical recipes across arms; scored densely and as uniform Poisson-disk emitted masks",
        "params": {"fold": args.fold, "seed": args.seed, "epochs": args.epochs,
                   "steps_per_epoch": args.steps_per_epoch},
        "note": "fold-isolated diagnostics only; selection is not promotion; "
                "promotion still needs the 4-fold paired design + fresh-seed confirmation",
        "arms": {},
    }
    for name, loss, weight in ARMS:
        ckpt = runs / f"fold{args.fold}-{name}.pt"
        pred = runs / f"fold{args.fold}-{name}.npy"
        score = runs / f"fold{args.fold}-{name}-score.json"
        run([py, "scripts/train_model.py", "--fold", str(args.fold), "--loss", loss,
             "--boundary-weight", str(weight), "--seed", str(args.seed),
             "--epochs", str(args.epochs), "--steps-per-epoch", str(args.steps_per_epoch),
             "--output", str(ckpt)])
        run([py, "scripts/infer_model.py", "--checkpoint", str(ckpt), "--fold", str(args.fold),
             "--predictions-only", "--output", str(pred)])
        run([py, "scripts/score_sweep_arm.py", "--predictions", str(pred),
             "--output", str(score)])
        report["arms"][name] = {
            "loss": loss,
            "boundary_weight": weight,
            "checkpoint": str(ckpt),
            "predictions": str(pred),
            "scores": json.loads(score.read_text()),
        }

    summary = {}
    for name, entry in report["arms"].items():
        s = entry["scores"]
        summary[name] = {
            "dense_dti": s["dense"]["dti"],
            "emitted_dti": s["emitted_uniform_dots"]["dti"],
            "dots": s["emitted_uniform_dots"]["dots"],
        }
    report["summary"] = summary
    best_dense = max(summary, key=lambda k: summary[k]["dense_dti"])
    best_emitted = max(summary, key=lambda k: summary[k]["emitted_dti"])
    report["screen_selection"] = {
        "best_dense": best_dense,
        "best_emitted": best_emitted,
        "agrees": best_dense == best_emitted,
        "selected_for_confirmation": best_emitted if best_dense == best_emitted else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "screen_selection": report["screen_selection"]}, indent=2))
    print(f"full record: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
