#!/usr/bin/env bash
# Out-of-fold inference for every ablation checkpoint, then stitch per arm.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p runs/oof
for FOLD in 0 1 2 3; do
  for ARM in regional combined; do
    OUT="runs/oof/${ARM}-f${FOLD}.npy"
    if [[ -s "${OUT}" ]]; then
      echo "=== skip ${OUT} (already present) ==="
      continue
    fi
    echo "=== oof ${ARM} fold ${FOLD} $(date -u +%H:%M:%S) ==="
    python scripts/infer_model.py \
      --checkpoint "runs/f${FOLD}-${ARM}.pt" \
      --fold "${FOLD}" \
      --predictions-only \
      --output "${OUT}"
  done
done
for ARM in regional combined; do
  echo "=== stitch ${ARM} $(date -u +%H:%M:%S) ==="
  python scripts/stitch_oof_predictions.py \
    --fold0 "runs/oof/${ARM}-f0.npy" \
    --fold1 "runs/oof/${ARM}-f1.npy" \
    --fold2 "runs/oof/${ARM}-f2.npy" \
    --fold3 "runs/oof/${ARM}-f3.npy" \
    --output "runs/oof/${ARM}-oof.npy"
done
echo "=== oof inference complete $(date -u +%H:%M:%S) ==="
