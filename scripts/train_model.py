#!/usr/bin/env python3
"""Train one loss arm on a buffered spatial fold.

Run twice with the same fold, seed, and optimization settings (once ``regional``
and once ``combined``) for a paired holdout experiment. This script produces a
checkpoint, not a submission and not a leaderboard score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Run from an uninstalled checkout exactly as documented (`python scripts/<name>.py`):
# make the in-repo package importable without `pip install -e .`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--fold", choices=("0", "1", "2", "3", "all"), required=True)
    parser.add_argument("--loss", choices=("regional", "combined"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--steps-per-epoch", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--patch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--boundary-weight", type=float, default=0.5)
    parser.add_argument("--device", default=None, help="e.g. cuda or cpu; defaults to CUDA when available")
    args = parser.parse_args()

    try:
        import numpy as np

        from gemsdoe30.cv import spatial_quadrant_masks
        from gemsdoe30.training import train_one_arm

        feature_path = args.data_dir / "features_raw.npy"
        label_path = args.data_dir / "labels.npy"
        valid_path = args.data_dir / "valid.npy"
        label_valid_path = args.data_dir / "label_valid.npy"
        prepared_manifest_path = args.data_dir / "manifest.json"
        required = (feature_path, label_path, valid_path, label_valid_path, prepared_manifest_path)
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"prepared arrays missing: {', '.join(missing)}; run scripts/prepare_data.py")

        features = np.load(feature_path, mmap_mode="r")
        labels = np.load(label_path, mmap_mode="r")
        valid = np.load(valid_path, mmap_mode="r").astype(bool, copy=False)
        label_valid = np.load(label_valid_path, mmap_mode="r").astype(bool, copy=False)
        prepared_manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))
        if prepared_manifest.get("schema_version") != 3:
            raise ValueError("prepared manifest lacks source-file provenance; rerun scripts/prepare_data.py")
        if prepared_manifest.get("shape_hw") != list(valid.shape):
            raise ValueError("prepared manifest shape does not match valid.npy")
        mask_sha256 = hashlib.sha256(np.packbits(valid).tobytes()).hexdigest()
        if prepared_manifest.get("valid_mask_sha256") != mask_sha256:
            raise ValueError("valid.npy does not match the prepared manifest checksum")
        dataset_signature = prepared_manifest.get("dataset_signature")
        if not isinstance(dataset_signature, str) or len(dataset_signature) != 64:
            raise ValueError("prepared manifest is missing the source-bound dataset signature")
        try:
            int(dataset_signature, 16)
        except ValueError as exc:
            raise ValueError("prepared dataset signature is not a hexadecimal SHA-256") from exc
        if args.fold == "all":
            train_mask = valid & label_valid
            validation_note = "full-label fit; no holdout claim"
        else:
            train_mask, _ = spatial_quadrant_masks(valid, int(args.fold), buffer_m=300.0)
            train_mask &= label_valid
            validation_note = f"fold {args.fold} held out with 300 m training exclusion buffer"

        checkpoint = train_one_arm(
            features,
            labels,
            label_valid,
            train_mask,
            loss_mode=args.loss,
            output_path=args.output,
            dataset_signature=dataset_signature,
            fold=None if args.fold == "all" else int(args.fold),
            seed=args.seed,
            epochs=args.epochs,
            steps_per_epoch=args.steps_per_epoch,
            batch_size=args.batch_size,
            patch_size=args.patch_size,
            learning_rate=args.learning_rate,
            boundary_weight=args.boundary_weight,
            device=args.device,
        )
        run = {
            "checkpoint": str(args.output),
            "dataset_signature": dataset_signature,
            "fold": args.fold,
            "loss": args.loss,
            "seed": args.seed,
            "epochs": args.epochs,
            "steps_per_epoch": args.steps_per_epoch,
            "batch_size": args.batch_size,
            "patch_size": args.patch_size,
            "boundary_weight": args.boundary_weight if args.loss == "combined" else 0.0,
            "validation_note": validation_note,
            "history": checkpoint["history"],
            "status": "trained; holdout scoring is a separate step",
        }
        run_path = args.output.with_suffix(".run.json")
        run_path.parent.mkdir(parents=True, exist_ok=True)
        run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(run, indent=2))
        return 0
    except (ImportError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"TRAINING BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
