#!/usr/bin/env python3
"""Restore explicitly pinned owner-provided mirrors via GitHub; never logs in to DrivenData."""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ApiOnlyRedirect(HTTPRedirectHandler):
    """Never forward an API credential or source request to a different host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https" or urlsplit(newurl).netloc != "api.github.com":
            raise ValueError("pinned-source redirect outside api.github.com rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def stream_raw(endpoint, stream):
    """Keep authenticated gh streaming, with a byte-safe fallback for a known CLI bug.

    Some Actions runner gh versions fail on binary content with Go's
    'transform: short source buffer'. Rewind any partial bytes and fetch that SAME
    pinned public API URL through Python. All final byte-count/SHA checks remain.
    HTTP/authentication failures are not silently converted into another request.
    """
    stream.flush()
    offset = stream.tell()
    command = ['gh', 'api', endpoint, '-H', 'Accept: application/vnd.github.raw+json']
    result = subprocess.run(command, stdout=stream, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return
    error = result.stderr or ''
    if 'transform: short source buffer' not in error:
        print(error, file=sys.stderr, end='')
        raise subprocess.CalledProcessError(result.returncode, command, stderr=error)
    stream.seek(offset)
    stream.truncate()
    print('gh binary transform failed; retrying the same pinned API bytes with Python; size/SHA gates unchanged', flush=True)
    headers = {'Accept': 'application/vnd.github.raw+json',
               'User-Agent': 'GEMSDOE30-pinned-source-restorer',
               'X-GitHub-Api-Version': '2022-11-28'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request('https://api.github.com/' + endpoint, headers=headers)
    with build_opener(ApiOnlyRedirect()).open(request, timeout=120) as response:
        shutil.copyfileobj(response, stream, length=1024 * 1024)
    # A subsequent multipart gh process must append after buffered Python writes.
    stream.flush()


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
