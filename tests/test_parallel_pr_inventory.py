import json

import pytest

from scripts import sync_priority_registry as sync


def row(number):
    return {'number': number, 'html_url': f'https://github.com/o/r/pull/{number}',
            'updated_at': '2026-10-26T00:00:00Z',
            'head': {'sha': f'{number:040x}', 'ref': f'parallel-{number}', 'repo': {'full_name': 'o/r'}}}


def test_open_pr_heads_are_paginated_and_explicitly_unscanned(monkeypatch):
    calls = []
    def api(endpoint):
        calls.append(endpoint)
        page = int(endpoint.split('page=')[-1])
        return json.dumps([row(i) for i in range(1, 101)] if page == 1 else [row(101)]).encode()
    monkeypatch.setattr(sync, 'api', api)
    heads = sync.discover_open_pull_request_heads('o/r', 'SITE')
    assert len(heads) == 101 and len(calls) == 2
    assert heads[-1]['number'] == 101 and heads[-1]['head_sha'] == f'{101:040x}'
    assert all('not scanned or compared' in h['comparison_status'] for h in heads)


def test_missing_or_malformed_pr_metadata_fails_closed(monkeypatch):
    monkeypatch.setattr(sync, 'api', lambda endpoint: b'{"message":"forbidden"}')
    with pytest.raises(ValueError, match='unexpected open-PR response'):
        sync.discover_open_pull_request_heads('o/r', 'SITE')
    bad = row(2)
    bad['head']['sha'] = None
    monkeypatch.setattr(sync, 'api', lambda endpoint: json.dumps([bad]).encode())
    with pytest.raises(ValueError, match='without a pinned head'):
        sync.discover_open_pull_request_heads('o/r', 'SITE')
