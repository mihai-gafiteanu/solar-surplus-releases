#!/usr/bin/env python3
"""
The one reading of index.html's section structure, imported by
make-section-editor.py and apply-sections.py.

A document is a run of sections; a section is an <h2 id="sNN"> and the top-level
blocks after it; a block is either EDITABLE prose or HELD. Tables, code blocks,
figures, key-value grids and inline SVG are held: summarised in one line, never
editable. Nothing carrying a base64 image is passed to the browser.
"""

import re

VOID = {"br", "hr", "img", "input", "meta", "link", "source",
        "col", "area", "base", "wbr", "path", "rect", "circle",
        "line", "polyline", "polygon", "use", "stop", "ellipse"}

EDITABLE_TAGS = {"p", "h3", "h4", "ul", "ol", "blockquote"}
EDITABLE_DIV_CLASSES = ("note", "pass")

# Containers that are scaffolding rather than content: their children are the
# real blocks. The argument is folded into <details class="why"> in section 01,
# so without this the whole of it is one held chip carrying a table and an SVG,
# and none of it can be edited. The technical depth is folded the
# same way — a <details class="more"> per run of deep blocks, its content in
# <div class="morebody"> — and descends for the same reason.
DESCEND = (("details", "why"), ("div", "whybody"), ("summary", None),
           ("details", "more"), ("div", "morebody"))

# Spans carrying the argument's own prose, inside <summary>. Reached only from a
# descended container, and only ever spliced by inner range, so the wrapper span
# and its class survive an edit untouched.
EDITABLE_SPAN_CLASSES = ("sn", "whytitle", "whyhint")


# --------------------------------------------------------------- scanning
def _end_of_start_tag(s, i):
    """Index just past the '>' of the start tag beginning at i, quotes respected."""
    q = None
    j = i
    while j < len(s):
        c = s[j]
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == ">":
            return j + 1
        j += 1
    raise ValueError("unterminated start tag at %d" % i)


def _match_close(s, after_start, tag):
    """Index just past the matching </tag>, counting nested same-name tags."""
    depth = 1
    pat = re.compile(r"<(/?)%s\b" % re.escape(tag), re.I)
    i = after_start
    while True:
        m = pat.search(s, i)
        if not m:
            raise ValueError("unclosed <%s>" % tag)
        if m.group(1):
            depth -= 1
            if depth == 0:
                return _end_of_start_tag(s, m.start())
            i = m.end()
        else:
            e = _end_of_start_tag(s, m.start())
            if s[e - 2] != "/":
                depth += 1
            i = e


def top_blocks(s, base=0):
    """[(start, end, tag)] for every top-level element in s, offsets + base."""
    out, i, n = [], 0, len(s)
    while i < n:
        j = s.find("<", i)
        if j < 0:
            break
        if s.startswith("<!--", j):
            k = s.find("-->", j)
            k = n if k < 0 else k + 3
            out.append((base + j, base + k, "#comment"))
            i = k
            continue
        m = re.match(r"<([a-zA-Z][\w:-]*)", s[j:])
        if not m:
            i = j + 1
            continue
        tag = m.group(1).lower()
        e = _end_of_start_tag(s, j)
        if tag in VOID or s[e - 2] == "/":
            out.append((base + j, base + e, tag))
            i = e
            continue
        k = _match_close(s, e, tag)
        out.append((base + j, base + k, tag))
        i = k
    return out


def _attr(start_tag, name):
    m = re.search(r'\b%s="([^"]*)"' % name, start_tag)
    return m.group(1) if m else ""


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


# --------------------------------------------------------------- summaries
def summarise(tag, cls, html):
    """One line describing a held block, for the editor's grey chip."""
    if tag == "figure":
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", html, re.S)
        what = "chart" if "<svg" in html else ("photo" if "data:image" in html else "figure")
        return "%s — %s" % (what, _text(cap.group(1))[:110] if cap else "no caption")
    if tag == "div" and "tw" in cls:
        cap = re.search(r"<caption[^>]*>(.*?)</caption>", html, re.S)
        rows = html.count("<tr")
        return "table, %d rows — %s" % (rows - 1, _text(cap.group(1))[:110] if cap else "no caption")
    if tag == "div" and "cmd" in cls:
        lbl = re.search(r'<div class="lbl">(.*?)</div>', html, re.S)
        path = _text(lbl.group(1))[:90] if lbl else "shell"
        return "code block — %s" % path
    if tag == "div" and "kv" in cls:
        return "key–value grid, %d cells" % html.count('<div class="k">')
    if tag == "div" and "volt" in cls:
        return "253 V rule"
    if tag == "span" and "whytoggle" in cls:
        return "the argument's open/close chevron"
    if tag == "span" and ("more-ask" in cls or "more-close" in cls):
        return "the fold's Want-to-know-more / Close label"
    if tag == "div" and ("figrow" in cls or "gallery" in cls):
        return "%s, %d figures" % ("figure row" if "figrow" in cls else "gallery", html.count("<figure"))
    if tag == "svg":
        t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        return "inline SVG — %s" % (_text(t.group(1))[:110] if t else "diagram")
    if tag == "hr":
        return "rule"
    if tag == "#comment":
        return "comment"
    body = _text(html)
    return ("%s — %s" % (tag, body[:110])) if body else tag


def is_editable(tag, cls, inner, nested=False):
    if "data:" in inner or "<pre" in inner or "<table" in inner or "<svg" in inner:
        return False
    if tag in EDITABLE_TAGS:
        return True
    if tag == "div" and any(c in cls.split() for c in EDITABLE_DIV_CLASSES):
        return True
    if nested and tag == "span" and any(c in cls.split() for c in EDITABLE_SPAN_CLASSES):
        return True
    return False


def _descends(tag, cls):
    return any(tag == t and (c is None or c in cls.split()) for t, c in DESCEND)


def fingerprint(secs):
    """A short hash of the block structure a plan's numbers are indexes into.

    `index_sha` says which document a plan was cut from. It does not say how
    that document was cut up, and a change here renumbers blocks without moving
    a byte of index.html - so a plan from the older editor would still pass the
    sha check and then edit the wrong paragraph. This is the second half of
    that guard, and it is why apply-sections.py refuses a plan that carries a
    different one.
    """
    import hashlib
    spine = "|".join("%s:%d:%s.%s.%d" % (s["id"], b["i"], b["tag"], b["cls"], b["editable"])
                     for s in secs for b in s["blocks"])
    return hashlib.sha256(spine.encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------- the model
def parse(html):
    """
    -> (columns, sections)

    columns  [(inner_start, inner_end)] for each <div class="col">, in order
    sections [dict] with, for each:
        id     's01'
        n      1
        title  the h2's text with the 'Section 01' marker removed
        col    index into columns
        h2     (start, end)          the whole <h2> element
        span   (start, end)          h2 through the last block before the next h2
        blocks [ {i, tag, cls, span, inner, editable, summary, html} ]
    """
    ms, me = html.index("<main>") + len("<main>"), html.index("</main>")
    main = html[ms:me]

    columns = []
    for a, b, tag in top_blocks(main, ms):
        if tag != "div" or _attr(html[a:_end_of_start_tag(html, a)], "class").split() != ["col"]:
            continue
        columns.append((_end_of_start_tag(html, a), b - len("</div>")))

    sections = []
    for ci, (ia, ib) in enumerate(columns):
        blocks = top_blocks(html[ia:ib], ia)
        heads = [k for k, (a, b, t) in enumerate(blocks)
                 if t == "h2" and re.search(r'id="s\d\d"', html[a:_end_of_start_tag(html, a)])]
        for hi, k in enumerate(heads):
            a, b, _ = blocks[k]
            start_tag = html[a:_end_of_start_tag(html, a)]
            sid = _attr(start_tag, "id")
            inner = html[_end_of_start_tag(html, a):b - len("</h2>")]
            title = _text(re.sub(r'<span class="sn">.*?</span>', "", inner, flags=re.S))
            last = blocks[heads[hi + 1]][0] if hi + 1 < len(heads) else ib
            body = []

            def emit(ba, bb, btag, within=None):
                bstart = html[ba:_end_of_start_tag(html, ba)]
                cls = _attr(bstart, "class")
                bhtml = html[ba:bb]
                if btag in VOID or bhtml.endswith("/>") or btag == "#comment":
                    binner = (bb, bb)
                else:
                    binner = (_end_of_start_tag(html, ba), bb - (len(btag) + 3))
                # Scaffolding: step through it and take its children instead. A
                # descended container is never itself a block, so no two blocks
                # can ever nest and a splice by inner range stays unambiguous.
                if _descends(btag, cls):
                    inside = within or (cls.split()[0] if cls.split() else btag)
                    for ca, cb, ctag in top_blocks(html[binner[0]:binner[1]], binner[0]):
                        emit(ca, cb, ctag, within=inside)
                    return
                ih = html[binner[0]:binner[1]]
                ed = is_editable(btag, cls, ih, nested=within is not None)
                body.append({
                    "i": len(body), "tag": btag, "cls": cls,
                    # The container this came out of, or None for a block that
                    # is a section's own child. The argument is prose to edit
                    # but it is not a step to install, so the review desk reads
                    # this and the section editor ignores it.
                    "within": within,
                    "span": (ba, bb), "inner": binner,
                    "editable": ed,
                    "summary": "" if ed else summarise(btag, cls, bhtml),
                    "html": ih if ed else "",
                })

            for ba, bb, btag in blocks[k + 1:]:
                if ba >= last:
                    break
                emit(ba, bb, btag)
            sections.append({
                "id": sid, "n": int(sid[1:]), "title": title, "col": ci,
                "h2": (a, b), "span": (a, last), "blocks": body,
            })
    return columns, sections


def toc_groups(html):
    """The [{at, label}] the inline script builds its contents headings from.

    `at` is a section id — 's01' — because the contents is keyed by id rather
    than by position: the first entry no longer has a number. A bare number is
    still read, and returned as the id it stands for, so an older document does
    not silently produce an empty contents.
    """
    m = re.search(r"var groups = \[(.*?)\];", html, re.S)
    if not m:
        return []
    out = []
    for a, l in re.findall(r"\{at:\s*'?(s?\d+)'?,\s*label:\s*'([^']*)'\}", m.group(1)):
        out.append({"at": a if a.startswith("s") else "s%02d" % int(a), "label": l})
    return out


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "site/app/index.html"
    h = open(src, encoding="utf-8").read()
    cols, secs = parse(h)
    print("%d columns, %d sections" % (len(cols), len(secs)))
    for g in toc_groups(h):
        print("  group at %s  %s" % (g["at"], g["label"]))
    total = held = 0
    for s in secs:
        e = sum(1 for b in s["blocks"] if b["editable"])
        total += len(s["blocks"])
        held += len(s["blocks"]) - e
        print("  %s  %-38s %2d blocks  %2d editable" % (s["id"], s["title"][:38], len(s["blocks"]), e))
    print("  %d blocks: %d held, %d prose" % (total, held, total - held))
