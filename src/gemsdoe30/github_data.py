"""Shared exact-byte GitHub API transport for pinned data, never a competition login.

Source loaders retain their own mandatory byte-count, Git-blob and SHA-256 gates.
This transport fixes a runner gh binary-stream defect without bypassing auth errors.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
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
    result = subprocess.run(command, stdout=stream, stderr=subprocess.PIPE, text=True, timeout=120)
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


