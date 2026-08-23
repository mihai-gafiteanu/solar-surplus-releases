#!/usr/bin/env python3
"""
Regenerate the Content-Security-Policy META TAG in index.html from the
hashes of its own inline blocks. Run from the repo root after any edit:

    python3 tools/refresh-csp.py

  script-src      'sha256-...'     the one inline <script>, pinned exactly
  style-src-elem  'sha256-...' x2  the two inline <style> blocks, pinned
  style-src-attr  'unsafe-inline'  the static style="width:..%" attributes
  style-src       'unsafe-inline'  fallback for browsers predating CSP3

The policy rides a <meta http-equiv> tag because GitHub Pages sends no
custom response headers — that is the one thing the move from Azure
changed. A meta CSP is enforced by browsers with two known limits, both
priced in: frame-ancestors is ignored there (so it is not declared), and
the policy only guards what loads after the tag is parsed (so the tag
sits in <head> before every style and script block).

Hashing the style attributes instead would blank them and wreck the table
column widths; CSP3 browsers use -elem/-attr and ignore the style-src
fallback.
"""
import base64
import hashlib
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent
page = root / "index.html"
html = page.read_text(encoding="utf-8")


def hashes(tag):
    out = []
    for m in re.finditer(rf"<{tag}\b([^>]*)>(.*?)</{tag}>", html, re.S):
        if "src=" in m.group(1):
            continue
        digest = hashlib.sha256(m.group(2).encode("utf-8")).digest()
        out.append("'sha256-" + base64.b64encode(digest).decode() + "'")
    return out


scripts, styles = hashes("script"), hashes("style")
if not scripts or not styles:
    sys.exit(f"expected inline script and style blocks; found {len(scripts)} / {len(styles)}")

for pattern, what in ((r"\son[a-z]+\s*=\s*[\"']", "inline event handler"),
                      (r"javascript:", "javascript: URL"),
                      (r"<script[^>]+src=", "external script")):
    if re.search(pattern, html):
        sys.exit(f"refusing to write a CSP: {what} found in index.html")

csp = "; ".join([
    "default-src 'none'",
    "img-src 'self' data:",
    # section 14 carries the board as an inline <video>, under the same data:
    # rule as the images. Without this the element is blocked and the page
    # shows its poster frame and nothing else.
    "media-src 'self' data:",
    "script-src " + " ".join(scripts),
    "style-src-elem " + " ".join(styles),
    "style-src-attr 'unsafe-inline'",
    "style-src 'unsafe-inline'",
    "base-uri 'none'",
    "form-action 'none'",
    # no frame-ancestors: a meta CSP cannot carry it, and declaring a
    # directive the browser will announce it ignored is noise, not safety.
])

meta = re.compile(
    r'(<meta http-equiv="Content-Security-Policy" content=")[^"]*(">)')
if not meta.search(html):
    sys.exit("index.html carries no Content-Security-Policy meta tag to fill")
old = meta.search(html).group(0)
new_html = meta.sub(lambda m: m.group(1) + csp + m.group(2), html, count=1)
# newline="\n": on Windows write_text would otherwise turn every "\n" into
# CRLF and the whole 4 MB page would land in the diff as line-ending churn.
page.write_text(new_html, encoding="utf-8", newline="\n")

print(f"{len(scripts)} script hash, {len(styles)} style hashes")
for h in scripts + styles:
    print("   ", h)
print("unchanged" if old == meta.search(new_html).group(0)
      else "index.html's CSP meta updated")
