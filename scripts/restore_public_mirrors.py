#!/usr/bin/env python3
"""Restore explicitly pinned owner-provided mirrors via GitHub; never logs in to DrivenData."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def restore(row, root):
    dest = root / row['dest']
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and hashlib.file_digest(dest.open('rb'), 'sha256').hexdigest() == row['sha256']:
        return dest
    # Stream large multipart blobs; never hold the complete raster in memory.
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as stream:
        tmp = Path(stream.name)
        try:
            for path in row.get('parts', [row.get('path')]):
                subprocess.run(['gh', 'api', f"repos/{row['repo']}/contents/{path}?ref={row['ref']}",
                                '-H', 'Accept: application/vnd.github.raw+json'], stdout=stream, check=True)
            stream.flush()
            if tmp.stat().st_size != row['bytes']:
                raise ValueError(f"size mismatch for {row['id']}")
            with tmp.open('rb') as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            if digest != row['sha256']:
                raise ValueError(f"SHA-256 mismatch for {row['id']}")
            tmp.replace(dest)
        finally:
            tmp.unlink(missing_ok=True)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pins', type=Path, default=Path('docs/research/mirror-pins.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/raw'))
    args = parser.parse_args()
    pins = json.loads(args.pins.read_text())
    for row in pins['files']:
        print('Restoring', row['id'], flush=True)
        print(restore(row, args.output_dir), flush=True)
    print('Owner mirrors restored. Not organizer-authenticated; run preparation and audit.')


if __name__ == '__main__':
    main()
