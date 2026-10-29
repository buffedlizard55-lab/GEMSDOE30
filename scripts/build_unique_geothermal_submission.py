#!/usr/bin/env python3
"""Retired candidate generator: do not create or promote off-lattice outputs.

The historical implementation used a prior prediction's coverage holes as a
placement constraint, which makes registry geometry part of the model and
violates the project's no-evasion policy. Its output is not evidence of a
leakage-safe HOLDOUT-DTI or independent novelty. The old tracked candidate is
preserved byte-for-byte for audit only. See
``docs/research/2026-10-29-repository-review.md`` and
``docs/research/2026-10-29-candidate-audit.json``.

This entrypoint intentionally has no feature-loading, placement, writer, or
network code. It refuses every invocation and never writes an artifact.
"""
from __future__ import annotations

import sys

STOP_REASON = (
    "STOP: geothermal candidate generation is disabled. The archived method "
    "constrained placement to a previous raster's coverage holes, contrary to "
    "the no-evasion protocol. No assigned lane, pre-placement surface receipt, "
    "leakage-safe HOLDOUT-DTI promotion, or complete registry clearance exists. "
    "No file written; NOT OK TO SUBMIT. See "
    "docs/research/2026-10-29-repository-review.md."
)


def main() -> int:
    """Fail closed for CLI calls, including former generation/override arguments."""
    print(STOP_REASON, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
