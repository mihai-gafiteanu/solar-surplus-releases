#!/usr/bin/env python3
"""
serve.py — serve this folder on localhost so the review desk can autosave

    python3 serve.py            # http://localhost:8765/install-review.html
    python3 serve.py 9000       # pick another port

Served from localhost (not file://) the page can link files and autosave; binds 127.0.0.1 only.
"""

import http.server, socketserver, sys, webbrowser, functools, pathlib

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
ROOT = pathlib.Path(__file__).resolve().parent
PAGE = 'install-review.html'


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *a):
        pass  # quiet


def main():
    handler = functools.partial(Handler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    except OSError as e:
        sys.exit('could not bind port %d (%s) — try:  python3 serve.py %d' % (PORT, e, PORT + 1))

    url = 'http://localhost:%d/%s' % (PORT, PAGE)
    print('serving %s\n  %s' % (ROOT, url))
    if not (ROOT / PAGE).exists():
        print('  (note: %s is not in this folder — directory listing at http://localhost:%d/)' % (PAGE, PORT))
    print('\nCtrl-C to stop')
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')


if __name__ == '__main__':
    main()
