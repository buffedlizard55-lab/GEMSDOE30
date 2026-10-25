import hashlib
import io
import subprocess
from types import SimpleNamespace
import pytest
from scripts import restore_public_mirrors as mirrors
from gemsdoe30 import github_data as client


def pin(content, *, parts=None):
    row = {'id':'synthetic', 'repo':'test/synthetic', 'ref':'a'*40, 'path':'source.tif',
           'dest':'restored.tif', 'bytes':len(content), 'sha256':hashlib.sha256(content).hexdigest()}
    if parts: row['parts'] = parts
    return row


def test_binary_cli_fallback_removes_partial_bytes_and_preserves_multipart_order(tmp_path, monkeypatch):
    a, b = b'II\x00\x80\xfffirst', b'MM\x00\x81\xfesecond'
    bodies = iter([a, b]); requests = []
    def fail(command, *, stdout, **kwargs):
        stdout.write(b'corrupt partial prefix')
        return SimpleNamespace(returncode=1, stderr='transform: short source buffer\n')
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            assert request.full_url.startswith('https://api.github.com/') and timeout == 120
            return io.BytesIO(next(bodies))
    monkeypatch.setattr(client.subprocess, 'run', fail)
    monkeypatch.setattr(client, 'build_opener', lambda *args: Opener())
    row = pin(a+b, parts=['part-0','part-1'])
    dest = mirrors.restore(row, tmp_path)
    assert dest.read_bytes() == a+b and len(requests) == 2
    assert list(tmp_path.iterdir()) == [dest]


def test_fallback_never_publishes_wrong_pinned_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(client.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1, stderr='transform: short source buffer'))
    class Opener:
        def open(self, request, timeout): return io.BytesIO(b'wrong')
    monkeypatch.setattr(client, 'build_opener', lambda *a: Opener())
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        mirrors.restore(pin(b'right'), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_http_auth_failures_are_not_masked_by_a_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(client.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1, stderr='HTTP 401 Unauthorized'))
    monkeypatch.setattr(client, 'build_opener', lambda *a: pytest.fail('auth failures must remain failures'))
    with pytest.raises(subprocess.CalledProcessError):
        mirrors.restore(pin(b'right'), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_api_credentials_never_follow_a_cross_host_redirect():
    handler = mirrors.ApiOnlyRedirect()
    with pytest.raises(ValueError, match='outside api.github.com'):
        handler.redirect_request(None,None,302,'',{},'https://elsewhere.invalid/blob')
