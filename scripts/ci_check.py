#!/usr/bin/env python3
"""Run a finite CI command, preserving its exit status and API-readable diagnostics.

GitHub's log downloads can redirect to hosts unavailable to this worktree.
Check annotations expose a bounded, escaped copy of failing command output instead;
this never converts a failed validation into success and never prints environment variables.
"""
from __future__ import annotations

import subprocess
import sys


def main(argv=None):
    command = sys.argv[1:] if argv is None else argv
    if not command:
        print("usage: ci_check.py COMMAND [ARGS...]", file=sys.stderr)
        return 2
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output, code = result.stdout, result.returncode
    except OSError as exc:
        output, code = str(exc), 127
    print(output, end="" if output.endswith("\n") else "\n")
    if code:
        output = output[-24000:]
        for start in range(0, len(output), 4000):
            chunk = output[start:start + 4000]
            chunk = chunk.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print("::error title=CI command failed::" + chunk)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
