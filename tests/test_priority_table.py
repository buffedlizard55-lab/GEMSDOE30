import json
from pathlib import Path

from scripts.render_gdx_review import priority_table


def test_nine_site_table_exposes_relations_and_unknown_estimates():
    fleet = json.loads(Path('docs/research/2026-10-26-gdx/fleet-audit.json').read_text())
    table = priority_table(fleet)
    assert table.count('<tr><th scope="row">') == 9
    assert 'Uniqueness vs listed files' in table
    assert 'Estimated score' in table
    assert table.count('Unknown; no defensible estimate') == 9
    assert 'Same footprint values as GEMSDOE30' in table
    assert 'Same footprint values as GEMSDOE25' in table
    assert 'of GEMSDOE' in table  # reverse-direction overlap is labelled, not inverted
    for row in fleet['rows']:
        assert row['historical_file'] in table
