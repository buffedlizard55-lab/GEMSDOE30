#!/usr/bin/env python3
"""Serve only public research assets for an Arena/static-site preview, never .git/data.

No API, training trigger, upload, or competition authentication is exposed.
"""
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {"data", "outputs", "runs", "checkpoints", "node_modules", "tests"}


class PublicHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        parts = Path(unquote(urlsplit(self.path).path)).parts
        if any(part.startswith(".") or part in BLOCKED for part in parts if part not in ("/", "")):
            self.send_error(403, "Private workspace files are not public site assets")
            return None
        path = Path(self.translate_path(self.path)).resolve()
        if not path.is_relative_to(ROOT):
            self.send_error(403, "Outside public site")
            return None
        # Apply the same denylist after resolving symlinks: a public-looking
        # filename must not expose .git, raw inputs, caches or model outputs.
        if any(part.startswith(".") or part in BLOCKED for part in path.relative_to(ROOT).parts):
            self.send_error(403, "Resolved path is private")
            return None
        if path.is_dir() and not (path / "index.html").is_file():
            self.send_error(403, "Directory listings disabled")
            return None
        return super().send_head()

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        # No frame-blocking headers: this static preview must embed in Arena.
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), PublicHandler)
    print(f"Research website on 0.0.0.0:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
