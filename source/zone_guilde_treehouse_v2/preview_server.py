#!/usr/bin/env python3
"""Serve the interactive ZGT2 preview at the preview root."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/renders/zone_guilde_treehouse_v3/index.html"
        return super().do_GET()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 4174), PreviewHandler).serve_forever()
