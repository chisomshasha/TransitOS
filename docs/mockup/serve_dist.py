"""
Static server for the Expo web export, with SPA fallback.

Serves ``frontend/dist`` so that:
  /trips            -> dist/trips/index.html   (if present) else dist/trips.html
  /settlements/s1   -> dist/settlements/s1.html (if present) else dist/index.html

The fallback to index.html lets expo-router resolve dynamic client-side
routes such as /settlements/s1.
"""

from __future__ import annotations

import functools
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "dist")
PORT = int(sys.argv[2] if len(sys.argv) > 2 else 8080)


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        rel = clean.lstrip("/")
        for candidate in (
            os.path.join(ROOT, rel),
            os.path.join(ROOT, rel + ".html"),
            os.path.join(ROOT, rel, "index.html"),
        ):
            if os.path.isfile(candidate):
                return candidate
        return os.path.join(ROOT, "index.html")

    def end_headers(self):
        # Never cache during a capture run.
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    # Pass directory= instead of os.chdir(): SimpleHTTPRequestHandler reads
    # os.getcwd() on every request, which explodes if the process cwd is
    # deleted (e.g. an Expo export that clears and recreates dist/).
    handler = functools.partial(Handler, directory=ROOT)
    print(f"serving {ROOT} on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), handler).serve_forever()
