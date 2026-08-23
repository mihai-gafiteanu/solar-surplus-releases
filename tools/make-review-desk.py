#!/usr/bin/env python3
# evcc solar-surplus charging · review desk generator
#
#   python3 tools/make-review-desk.py \
#       --index    site/app/index.html \
#       --template site/install-review.html \
#       --out      site/install-review.html
#
# The desk is the document again, one step at a time, with a verdict and a notes
# box beside each step and a tick-list of every shell command it contains.
# Everything in the file except the JSON in <script id="data"> is generic, so a
# release regenerates rather than hand-edits it. The template is the previous
# release's desk; each generated desk is the template for the next.
#
# The document is read through tools/sections.py, the same parser the section
# editor uses.
#
# What the transform does, and what it must keep doing:
#   · a section splits into steps at every <h3>; the blocks before the first one
#     are "Overview", and a section with no <h3> is a single step
#   · <figure> and <div class="figwide"> are carried as their caption alone.
#     Inlining 2.4 MB of base64 would defeat the purpose of the file
#   · <details class="why"> is dropped: it holds no shell command and nothing to
#     check against a Pi
#   · <details class="more"> — the technical depth, folded in place — is
#     transparent: its blocks are steps and commands like any others, and
#     only its Want-to-know-more / Close labels are dropped
#   · the footer is appended to the last step, because its version line and its
#     placeholder note are both claims a review can find wrong
#   · every <pre> becomes tick-list entries, one per command, except a block
#     labelled Response — that is output to read, not a command to run

import argparse
import html as H
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sections as S  # noqa: E402

DATA = re.compile(r'(<script id="data" type="application/json">)(.*?)(</script>)',
                  re.S)


def text(fragment):
    """Tags out, entities resolved, whitespace flattened."""
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", H.unescape(t)).strip()


def caption(fragment):
    m = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", fragment, re.S)
    return text(m.group(1)) if m else ""


def carry(block, index_html):
    """One document block as the desk should hold it, or None to drop it.

    The block is taken from the document by span rather than from its "html"
    field, which sections.py leaves empty for held blocks — the desk needs the
    table, the code block and the key-value grid, not just their summaries.
    """
    a, z = block["span"]
    tag, cls, frag = block["tag"], block["cls"], index_html[a:z]
    if tag == "details":
        return None
    # The fold's own chrome: the Want-to-know-more / Close labels on a
    # <details class="more"> summary are how the document folds, not a step.
    if tag == "span" and ("more-ask" in cls or "more-close" in cls):
        return None
    # Anything carrying an image is reduced to its captions, however it is
    # wrapped — figure, figwide, figrow, gallery. The test is the image itself
    # rather than the class, because a new wrapper class must not be able to
    # smuggle 2.4 MB of base64 into this file.
    if tag == "figure" or "data:image" in frag or "<figure" in frag:
        caps = [text(c) for c in
                re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", frag, re.S)]
        caps = [c for c in caps if c]
        if not caps:
            return None
        return "\n".join(
            '<div class="imgstub"><span class="k">figure</span> %s</div>'
            % H.escape(c, quote=False) for c in caps)
    return frag


def commands(step_html):
    """The shell commands of one step, in order, one tick per command.

    Every <pre> is read, labelled or not. A block whose label reads Response
    is output to check against rather than a command to run, and is skipped.
    """
    out = []
    for m in re.finditer(r"<pre>(.*?)</pre>", step_html, re.S):
        before = step_html[:m.start()]
        lbl = re.findall(r'<div class="lbl">(.*?)</div>', before, re.S)
        near = before.rfind('<div class="lbl">')
        if lbl and near >= 0 and "<pre>" not in before[near:]:
            if text(lbl[-1]).lower().startswith("response"):
                continue
        out += _lines(m.group(1))
    return out


def _lines(body):
    raw = H.unescape(re.sub(r"<[^>]+>", "", body))
    # Join continuations before anything else: one command, one tick.
    raw = re.sub(r"\\\n\s*", " ", raw)
    lines = [l.strip() for l in raw.split("\n")]
    lines = [l for l in lines if l and not l.startswith("#")]
    # A comment column is annotation and is dropped; a lone inline comment is
    # part of the line and stays.
    columned = [l for l in lines if re.search(r"\S {2,}#", l)]
    if lines and len(columned) * 2 >= len(lines):
        lines = [re.sub(r"\s{2,}#.*$", "", l).strip() for l in lines]
    return [re.sub(r"\s{2,}", " ", l) for l in lines]


def build(index_html):
    cols, secs = S.parse(index_html)
    footer = ""
    m = re.search(r"<footer class=\"end\">.*?</footer>", index_html, re.S)
    if m:
        footer = m.group(0)

    out, n = [], 0
    for sec in secs:
        steps, cur, title = [], [], None
        def close():
            if cur or title:
                steps.append((title, "\n\n".join(x for x in cur if x)))
        for b in sec["blocks"]:
            # The argument folded into section 01 is prose the section editor
            # opens, but it is not a step anyone installs: its eight headings
            # would otherwise split section 01 into eight more steps. The
            # technical folds are the opposite case — their blocks ARE the
            # steps — so only the argument is skipped.
            if b.get("within") == "why":
                continue
            if b["tag"] == "h3":
                close()
                cur, title = [], text(b["html"])
                continue
            kept = carry(b, index_html)
            if kept:
                cur.append(kept)
        close()

        if len(steps) == 1 and steps[0][0] is None:
            steps = [(sec["title"], steps[0][1])]
        else:
            steps = [(t if t is not None else "Overview", h) for t, h in steps]
        steps = [(t, h) for t, h in steps if h.strip()]

        entries = []
        for t, h in steps:
            n += 1
            entries.append({"id": "s%d" % n, "title": t, "html": h,
                            "cmds": commands(h)})
        out.append({"num": "%02d" % sec["n"], "title": sec["title"],
                    "steps": entries})

    if footer and out and out[-1]["steps"]:
        last = out[-1]["steps"][-1]
        last["html"] = last["html"] + "\n\n" + footer
    return {"sections": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    index_html = open(a.index, encoding="utf-8").read()
    shell = open(a.template, encoding="utf-8").read()
    if not DATA.search(shell):
        sys.exit("%s carries no <script id=\"data\"> block to replace" % a.template)

    # The shell rides the template from desk to desk, so anything in it that
    # names a revision would otherwise never move again — the chrome is
    # re-stamped from the document each build, off the dated footer
    # sentence. Loud when it cannot: a desk that does not know its
    # revision would state a stale one. (The document stopped carrying a
    # release version when the site separated from the release train in
    # v2.42 — its date is its identity now.)
    revs = set(re.findall(r"last revised (\d{4}-\d{2}-\d{2})", index_html))
    if len(revs) != 1:
        sys.exit("the desk needs exactly one 'last revised YYYY-MM-DD' "
                 "reading in the document to stamp its chrome from; found %s"
                 % (sorted(revs) or "none"))
    rev = revs.pop()
    shell = re.sub(r"Solar Surplus (?:v\d+\.\d+|rev\. \d{4}-\d{2}-\d{2})",
                   "Solar Surplus rev. " + rev, shell)
    shell = re.sub(r'class="v">(?:v\d+\.\d+|rev\. \d{4}-\d{2}-\d{2})<',
                   'class="v">rev. %s<' % rev, shell)
    # The snapshot() metadata too: a review saved from this desk must
    # record the revision it reviewed, not the one the template last saw.
    shell = re.sub(r"(doc: 'solar-surplus install review', version: ')[^']*(',)",
                   r"\g<1>%s\g<2>" % rev, shell)

    data = build(index_html)
    steps = sum(len(s["steps"]) for s in data["sections"])
    cmds = sum(len(t["cmds"]) for s in data["sections"] for t in s["steps"])
    if not steps:
        sys.exit("no steps built — is %s the document?" % a.index)

    payload = json.dumps(data, ensure_ascii=False)
    if "</script>" in payload:
        sys.exit("the document contains </script> — it cannot be inlined as JSON")
    if "data:image" in payload:
        where = [(s["num"], t["title"]) for s in data["sections"]
                 for t in s["steps"] if "data:image" in t["html"]]
        sys.exit("an image reached the desk, which is what keeps it small: %s"
                 % where)
    built = DATA.sub(lambda m: m.group(1) + payload + m.group(3), shell, count=1)

    # newline="\n": on Windows the default text mode rewrites the whole desk
    # with CRLF, so a regeneration that changed three sentences arrives as a
    # 750-line diff. Same fix make-dashboard.py carries.
    open(a.out, "w", encoding="utf-8", newline="\n").write(built)
    print(a.out)
    print("  %d sections · %d steps · %d commands · %d KB"
          % (len(data["sections"]), steps, cmds,
             round(os.path.getsize(a.out) / 1024)))


if __name__ == "__main__":
    main()
