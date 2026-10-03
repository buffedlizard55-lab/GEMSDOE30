#!/usr/bin/env bash
# Paired regional-vs-metric-geometry loss ablation on the four buffered spatial folds.
# Same seed, patch size, steps, and optimizer in both arms; only the loss differs.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
COMMON=(--epochs 6 --steps-per-epoch 100 --batch-size 4 --patch-size 96 --seed 30)
for FOLD in 0 1 2 3; do
  for ARM in regional combined; do
    echo "=== fold ${FOLD} arm ${ARM} $(date -u +%H:%M:%S) ==="
    python scripts/train_model.py --fold "${FOLD}" --loss "${ARM}" \
      --output "runs/f${FOLD}-${ARM}.pt" "${COMMON[@]}" || echo "FAILED f${FOLD} ${ARM}"
  done
done
echo "=== training batch complete $(date -u +%H:%M:%S) ==="
