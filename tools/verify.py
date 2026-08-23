#!/usr/bin/env python3
"""
Serve the repo root the way GitHub Pages does — plain files, no custom
headers, the CSP riding index.html's own meta tag — load the page in a
real browser and report anything the policy blocked.

    python3 tools/verify.py            expect zero violations and a built contents list
    python3 tools/verify.py --break    corrupt the script hash; proves the check notices
"""
import json
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
BREAK = "--break" in sys.argv

PAGE = (ROOT / "index.html").read_bytes()
if BREAK:
    # Corrupt the meta CSP's script hash: the browser must then refuse the
    # inline script, and this check must notice that it did.
    PAGE = re.sub(rb"script-src 'sha256-.", rb"script-src 'sha256-X", PAGE)


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def do_GET(self):
        if BREAK and self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
            return
        super().do_GET()

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 8099), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

chrome = next((str(p) for p in Path("/opt/pw-browsers").glob("chromium*/chrome-linux/chrome")), None)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=chrome) if chrome else p.chromium.launch()
    pg = b.new_page()
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.add_init_script("window.__v=[];document.addEventListener('securitypolicyviolation',"
                       "function(e){window.__v.push(e.violatedDirective+' '+e.blockedURI)})")
    pg.goto("http://127.0.0.1:8099/index.html", wait_until="load")
    pg.wait_for_timeout(1500)
    result = pg.evaluate("""() => ({
        title: document.title,
        metaCsp: !!document.querySelector('meta[http-equiv="Content-Security-Policy"]'),
        sections: document.querySelectorAll('main h2[id]').length,
        toc: document.querySelectorAll('#toclist a').length,
        groups: Array.from(document.querySelectorAll('#toclist .grp')).map(e=>e.textContent),
        imagesLoaded: Array.from(document.images).filter(i=>i.naturalWidth>0).length,
        imagesTotal: document.images.length,
        tables: document.querySelectorAll('main table').length,
        styledCells: document.querySelectorAll('[style*="width"]').length,
        deadAnchors: Array.from(document.querySelectorAll('a[href^="#"]'))
                          .map(a=>a.getAttribute('href'))
                          .filter(h=>!document.querySelector(h)),
        violations: window.__v,
        activeTocAfterLoad: !!document.querySelector('#toclist a.active')
    })""")
    result["consoleErrors"] = errs[:5]

    # every download link points at this repo's releases — whether each
    # linked name is really shipped belongs to whoever edits the document,
    # since the release/document seam was deliberately released in v2.42
    DL = "https://github.com/mihai-gafiteanu/solar-surplus-releases/releases/latest/download/"
    hrefs = pg.eval_on_selector_all("a[href^='https://']", "els => els.map(e => e.getAttribute('href'))")
    result["fileLinks"] = len({h for h in hrefs if h.startswith(DL)})
    b.close()

srv.shutdown()
print(json.dumps(result, indent=1, ensure_ascii=False))

bad = (result["violations"] or not result["metaCsp"] or result["deadAnchors"]
       or result["toc"] != result["sections"]
       or result["imagesLoaded"] != result["imagesTotal"])
if BREAK:
    print("\nnegative control:", "noticed" if bad else "DID NOT NOTICE — the check is broken")
    sys.exit(0 if bad else 1)
print("\n" + ("FAILED" if bad else "all checks passed"))
sys.exit(1 if bad else 0)
