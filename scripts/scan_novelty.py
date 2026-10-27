#!/usr/bin/env python3
"""Compatibility wrapper around the shared, fail-closed registry auditor.

A local downloads directory alone is not a complete parallel registry, a
candidate cannot define its own valid footprint, and an omitted reference is
not a novelty pass. Supply a hash-pinned manifest and the actual template.
For the full interface use ``scripts/check_novelty.py`` directly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from check_novelty import audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('stage', choices=('surface', 'dots'))
    parser.add_argument('--registry', type=Path, help='hash-pinned explicit registry manifest')
    parser.add_argument('--template', type=Path, default=Path('data/raw/sample_submission.tif'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.registry is None:
        result = {'decision': 'blocked-incomplete-registry', 'submission_approved': False,
                  'errors': ['a hash-pinned registry is required; local downloads are not a complete inventory']}
    else:
        try:
            result = audit(args.candidate, args.template, args.registry, args.stage)
        except (ValueError, OSError, KeyError) as exc:
            result = {'decision': 'blocked-invalid-input', 'submission_approved': False, 'errors': [str(exc)]}
    encoded = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end='')
    return 0 if result['decision'] == 'novelty-check-passed-not-submission-approval' else 2


if __name__ == '__main__':
    raise SystemExit(main())
