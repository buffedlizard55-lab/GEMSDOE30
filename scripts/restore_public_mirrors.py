#!/usr/bin/env python3
"""Restore explicitly pinned owner-provided mirrors via GitHub; never logs in to DrivenData."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe30.github_data import ApiOnlyRedirect, stream_raw


def restore(row, root):
    dest = root / row['dest']
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        with dest.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() == row['sha256']:
                return dest
    # Stream large multipart blobs; never hold the complete raster in memory.
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as stream:
        tmp = Path(stream.name)
        try:
            for path in row.get('parts', [row.get('path')]):
                stream_raw(f"repos/{row['repo']}/contents/{path}?ref={row['ref']}", stream)
            stream.flush()
            if tmp.stat().st_size != row['bytes']:
                raise ValueError(f"size mismatch for {row['id']}: got {tmp.stat().st_size}, expected {row['bytes']}")
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
    parser.add_argument('--ids', nargs='+', help='restore only named pinned IDs, e.g. sample_submission for CI')
    args = parser.parse_args()
    pins = json.loads(args.pins.read_text())
    if args.ids and not set(args.ids) <= {row['id'] for row in pins['files']}:
        parser.error('unknown mirror ID')
    for row in pins['files']:
        if args.ids and row['id'] not in args.ids:
            continue
        print('Restoring', row['id'], flush=True)
        print(restore(row, args.output_dir), flush=True)
    print('Owner mirrors restored. Not organizer-authenticated; run preparation and audit.')


if __name__ == '__main__':
    main()
