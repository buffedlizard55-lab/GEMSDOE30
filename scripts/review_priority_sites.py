#!/usr/bin/env python3
"""Restore priority historical rasters for education ONLY, pinned to reviewed commits.

Does not generate or approve a submission. GitHub owner mirrors are not official
organizer receipts. All downloaded rasters stay in ignored data/raw/registry.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / 'docs/research/priority-site-pins.json'


def main():
    pins = json.loads(PINS.read_text())
    rows = []
    for row in pins['rasters']:
        path = ROOT / row['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            temp = path.with_suffix('.partial')
            try:
                with temp.open('wb') as stream:
                    subprocess.run(['gh', 'api', f"repos/{row['repo']}/contents/{row['source_path']}?ref={row['ref']}",
                                    '-H', 'Accept: application/vnd.github.raw+json'], stdout=stream, check=True)
                with temp.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest != row['sha256']:
                    raise ValueError(f'hash mismatch: {path}')
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != row['sha256']:
                raise ValueError(f'hash mismatch: {path}')
        rows.append(row)
        print(path.relative_to(ROOT))
    print(f'{len(rows)} educational rasters restored; registry coverage remains partial.')


if __name__ == '__main__':
    main()
