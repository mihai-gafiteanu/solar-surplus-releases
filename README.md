# solar-surplus-releases

The public half of the solar-surplus build: **the releases a Raspberry Pi
installs from, and the document that explains the whole build** — served
straight from this repo by GitHub Pages.

- **The document**: [index.html](index.html), one self-contained page —
  the prosumer's case and the full build and operations documentation.
  Served at the repo's Pages URL; every image, style and script is
  inlined, and the Content-Security-Policy rides a `<meta>` tag in its
  head because Pages sends no custom headers.
- **The releases**: every `vX.Y` tag of the (private) software repo
  publishes a GitHub Release here — the deb a Pi installs, its sha256,
  and every payload file as a loose asset, so the document's
  `releases/latest/download/<name>` links always serve the newest
  release without this page changing at all.

The document is **dated, not versioned**: it names the day it was last
revised and the release it described that day, while its download links
follow `latest` on their own. It moved here whole in the software repo's
v2.42 ("the site separation") — before that it lived in the private repo
and was stamped on every release.

## Deploying is: push

`.github/workflows/pages.yml` runs on every push to `main`: it loads the
page in a real Chromium under the meta CSP (`tools/verify.py`) and fails
the deploy on any CSP violation, dead anchor, undecoded image or
contents-list mismatch — then publishes the repo root through Pages.

## Editing the document

```bash
python3 tools/refresh-csp.py     # ALWAYS after editing index.html — re-pins
                                 # the inline script/style hashes in the meta
                                 # tag; skip it and the browser silently
                                 # refuses the blocks it no longer recognises
python3 tools/verify.py          # the page in a real browser (needs
                                 # playwright + its chromium)
python3 serve.py                 # serves this folder on localhost
```

The toolchain came along with the document:

```
tools/
  refresh-csp.py           re-pin the meta CSP after any index.html edit
  verify.py                the page under a real browser and its own CSP
  make-review-desk.py      rebuild install-review.html from the document
  make-section-editor.py   rebuild section-editor.html from the document
  sections.py              the document's block model, shared by the two above
  apply-sections.py        apply a section-editor plan back onto index.html
  apply-levels.py          the record of how every block got its depth level
  apply-why.py  why_prose.py   the record of how section 01's argument landed
serve.py                   python3 serve.py — localhost for the desks
install-review.html        the document as a step-by-step review desk
section-editor.html        the document's sections as a reorderable plan
```

Both desks are generated from `index.html` and stamp their chrome from
its "last revised" date — regenerate them after any document edit:

```bash
python3 tools/make-review-desk.py --index index.html --template install-review.html --out install-review.html
python3 tools/make-section-editor.py --index index.html --out section-editor.html
```

The software — the installer, the selftest, the units, the scripts the
document describes — lives in the private `solar-surplus` repo and
arrives here only as release assets, built and published by its CI on
every tag.
