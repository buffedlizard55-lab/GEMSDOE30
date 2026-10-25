from types import SimpleNamespace
from scripts import ci_check


def test_ci_diagnostics_preserve_failure_exit_and_escape_annotations(monkeypatch, capsys):
    monkeypatch.setattr(ci_check.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=7, stdout='bad 50%\r\nnext\n'))
    assert ci_check.main(['synthetic']) == 7
    out = capsys.readouterr().out
    assert '::error title=CI command failed::bad 50%25%0D%0Anext%0A' in out


def test_success_has_no_error_annotation_and_missing_command_fails(monkeypatch, capsys):
    monkeypatch.setattr(ci_check.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=0, stdout='passed\n'))
    assert ci_check.main(['synthetic']) == 0
    assert '::error' not in capsys.readouterr().out
    assert ci_check.main([]) == 2
