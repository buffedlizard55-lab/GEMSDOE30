#!/usr/bin/env python3
"""Archived policy-violating off-lattice generator: generation is disabled.

The original implementation is preserved in Git history at commit
3344c38758a1379f9f7d69b4ef86cb4d7176935a. Historical receipts and TIFFs
are research evidence only, not approval. See docs/research/2026-10-28-
offlattice-safety-review.md. This entrypoint deliberately needs no scientific
packages, data, network access, or output arguments to fail closed.
"""
from __future__ import annotations

import sys

STOP_REASON = (
    "STOP: off-lattice generation is disabled. The archived generator used "
    "registry coverage holes as its placement target, contrary to the existing "
    "no-evasion decision; it selected every uncovered cell regardless of the "
    "geological score. No assigned lane, leakage-safe HOLDOUT-DTI, complete "
    "two-stage registry clearance, or selector approval is available. "
    "No file written; NOT OK TO SUBMIT. See "
    "docs/research/2026-10-28-offlattice-safety-review.md."
)


def main() -> int:
    """Refuse all invocations, including former generation/override arguments."""
    print(STOP_REASON, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
