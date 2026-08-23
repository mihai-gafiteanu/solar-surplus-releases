#!/usr/bin/env python3
"""
Write a section editor plan back into index.html.

    python3 tools/apply-sections.py section-plan.json
    python3 tools/apply-sections.py section-plan.json --check     # say, write nothing

The plan carries an order, a title per section, an include flag and only the
prose blocks that changed. A plan only applies to the index.html it was cut from.

Renumbering runs in a single pass over the reassembled document: heading
`id="sNN"`, the `Section NN` marker and every `href="#sNN"` move together under
one old->new map. A section switched off has its incoming anchors unwrapped to
plain text.

Then run:  python3 check.py
"""

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sections as S  # noqa: E402


def esc_title(t):
    return t.replace("<", "&lt;").replace(">", "&gt;")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--index", default="site/app/index.html")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="apply a plan cut from a different index.html anyway")
    a = ap.parse_args()

    html = open(a.index, encoding="utf-8").read()
    plan = json.load(open(a.plan, encoding="utf-8"))
    sha = hashlib.sha256(html.encode("utf-8")).hexdigest()[:12]
    if plan.get("index_sha") and plan["index_sha"] != sha and not a.force:
        sys.exit("this plan was cut from index.html %s; the file on disk is %s.\n"
                 "Block positions are per-document, so applying it would edit the wrong text.\n"
                 "Regenerate the editor (tools/make-section-editor.py) and redo the plan,\n"
                 "or pass --force if you are certain." % (plan["index_sha"], sha))

    cols, secs = S.parse(html)
    if len(cols) not in (1, 2):
        sys.exit("expected one or two <div class=\"col\"> blocks, found %d" % len(cols))

    # index_sha says which document; this says how it was cut into blocks. A
    # change in sections.py renumbers them without moving a byte, so the sha
    # above would pass and every number in the plan would mean something else.
    spine = S.fingerprint(secs)
    if plan.get("blocks_sha") and plan["blocks_sha"] != spine and not a.force:
        sys.exit("this plan was cut against block structure %s; this tree reads %s.\n"
                 "The document is unchanged but sections.py numbers its blocks differently,\n"
                 "so every block number in the plan now points at another paragraph.\n"
                 "Regenerate the editor (tools/make-section-editor.py) and redo the plan,\n"
                 "or pass --force if you are certain." % (plan["blocks_sha"], spine))

    by_id = {s["id"]: s for s in secs}

    order = [i for i in plan["order"]]
    # The marker only means something when there are two columns to tell apart.
    # Since the argument was folded into section 01 this document has one, and a
    # plan cut from it carries no boundary to place.
    if len(cols) == 2 and "--part--" not in order:
        sys.exit("the plan has no --part-- marker, so the two columns cannot be told apart")
    known = set(by_id)
    listed = {i for i in order if i != "--part--"}
    if listed != known:
        sys.exit("plan lists %s; the document has %s"
                 % (sorted(listed - known) or "nothing extra", sorted(known - listed) or "nothing missing"))

    # ------------------------------------------------------------ what changes
    kept, dropped = [], []
    for sid in order:
        if sid == "--part--":
            kept.append(sid)
            continue
        (dropped if plan["sections"].get(sid, {}).get("include") is False else kept).append(sid)

    live = [s for s in kept if s != "--part--"]
    remap = {sid: "s%02d" % (n + 1) for n, sid in enumerate(live)}
    if len(cols) == 2:
        part = kept.index("--part--")
        news = [[s for s in kept[:part] if s != "--part--"],
                [s for s in kept[part:] if s != "--part--"]]
    else:
        news = [[s for s in kept if s != "--part--"]]

    moved = [s for s in live if [x for x in order if x != "--part--"].index(s)
             != [x["id"] for x in secs].index(s)]
    retitled = [s for s in live
                if plan["sections"].get(s, {}).get("title", by_id[s]["title"]) != by_id[s]["title"]]
    edited = {s: sorted(plan["sections"][s]["blocks"], key=int)
              for s in live if plan["sections"].get(s, {}).get("blocks")}
    renumbered = [s for s in live if remap[s] != s]

    print("plan: %d sections kept, %d switched off" % (len(live), len(dropped)))
    for s in dropped:
        print("  OFF       %s  %s" % (s, by_id[s]["title"]))
    for s in retitled:
        print("  RETITLE   %s  %r -> %r" % (s, by_id[s]["title"], plan["sections"][s]["title"]))
    for s, ks in edited.items():
        print("  EDIT      %s  blocks %s" % (s, ", ".join(ks)))
    if renumbered:
        print("  RENUMBER  " + ", ".join("%s->%s" % (s, remap[s]) for s in renumbered))
    if len(cols) == 2:
        was0 = [s["id"] for s in secs if s["col"] == 0 and s["id"] in live]
        if set(news[0]) != set(was0):     # order inside a column is not the seam moving
            print("  PART      the boundary moved: %d section(s) before it, %d after"
                  % (len(news[0]), len(news[1])))

    # ------------------------------------------------------ rebuild a section
    def render(sid):
        s = by_id[sid]
        a0, a1 = s["span"]
        text = html[a0:a1]
        edits = []
        for k in plan["sections"].get(sid, {}).get("blocks", {}):
            b = s["blocks"][int(k)]
            if not b["editable"]:
                sys.exit("plan edits block %s of %s, which is held (%s)" % (k, sid, b["tag"]))
            edits.append((b["inner"][0] - a0, b["inner"][1] - a0,
                          plan["sections"][sid]["blocks"][k]))
        newtitle = plan["sections"].get(sid, {}).get("title", s["title"])
        if newtitle != s["title"]:
            h0, h1 = s["h2"][0] - a0, s["h2"][1] - a0
            m = re.search(r'(<span class="sn">.*?</span>)', text[h0:h1], re.S)
            if not m:
                sys.exit("%s has no Section marker to write beside" % sid)
            inner_a = h0 + m.end()
            inner_b = h1 - len("</h2>")
            edits.append((inner_a, inner_b, esc_title(newtitle)))
        for x, y, rep in sorted(edits, reverse=True):
            text = text[:x] + rep + text[y:]
        return text

    # the blank line a column opens with belongs to the column, not its first section
    lead = []
    for ci, (ia, _ib) in enumerate(cols):
        first = [x for x in secs if x["col"] == ci]
        lead.append(html[ia:first[0]["span"][0]] if first else "\n")

    body = [lead[i] + "".join(render(s) for s in news[i]) for i in range(len(cols))]
    out = html[:cols[0][0]]
    for i in range(len(cols)):
        out += body[i]
        if i + 1 < len(cols):
            out += html[cols[i][1]:cols[i + 1][0]]
    out += html[cols[-1][1]:]

    # ------------------------------------------- references to dropped sections
    orphans = []

    def unwrap(m):
        orphans.append((m.group(1), S._text(m.group(2))))
        return m.group(2)

    if dropped:
        pat = r'<a href="#(%s)">(.*?)</a>' % "|".join(re.escape(d) for d in dropped)
        out = re.sub(pat, unwrap, out, flags=re.S)
        for sid, txt in orphans:
            print("  ORPHAN    link to %s unwrapped: %r" % (sid, txt[:60]))
        left = re.findall(r'#(%s)\b' % "|".join(re.escape(d) for d in dropped), out)
        if left:
            sys.exit("still %d reference(s) to dropped sections: %s" % (len(left), sorted(set(left))))

    # ------------------------------------------------------ one renumbering pass
    # id="sNN", href="#sNN", 'Section NN' and 'Sections NN to NN', all under
    # `remap` in one sweep so nothing is mapped twice.
    num = {sid: int(new[1:]) for sid, new in remap.items()}
    hits = {"id": 0, "href": 0, "word": 0}

    def nn(old_two):
        sid = "s" + old_two
        return remap.get(sid), num.get(sid)

    def fix(m):
        if m.group("rng"):
            a_new, a_n = nn(m.group("ra"))
            b_new, b_n = nn(m.group("rb"))
            if not a_new or not b_new:
                return m.group(0)
            hits["word"] += 2
            return "%s%02d to %02d" % (m.group("rw"), a_n, b_n)
        if m.group("id"):
            new, _ = nn(m.group("id"))
            if not new:
                return m.group(0)
            hits["id"] += 1
            return 'id="%s"' % new
        if m.group("href"):
            new, _ = nn(m.group("href"))
            if not new:
                return m.group(0)
            hits["href"] += 1
            return 'href="#%s"' % new
        new, n = nn(m.group("wn"))
        if not new:
            return m.group(0)
        hits["word"] += 1
        return "%s%02d" % (m.group("ww"), n)

    pattern = re.compile(
        r'(?P<rng>(?P<rw>\b[Ss]ections\s)(?P<ra>\d\d)\sto\s(?P<rb>\d\d)\b)'
        r'|id="s(?P<id>\d\d)"'
        r'|href="#s(?P<href>\d\d)"'
        r'|(?P<ww>\b[Ss]ections?\s)(?P<wn>\d\d)\b')
    out = pattern.sub(fix, out)
    print("  rewrote %d ids, %d cross-reference hrefs, %d written numbers"
          % (hits["id"], hits["href"], hits["word"]))

    # --------------------------------------------------------- contents groups
    # Each heading hangs off a section id, and that id has just been renumbered,
    # so it is written out under the same map as everything else.
    groups = []
    for g in (plan.get("groups") or []):
        at = g["at"] if str(g["at"]).startswith("s") else "s%02d" % int(g["at"])
        if at in remap:
            groups.append({"at": remap[at], "label": g["label"]})
        else:
            print("  GROUP     heading %r dropped: %s is not in the document"
                  % (g["label"], at))
    arr = ",\n                ".join("{%slabel:'%s'}" % (("at:'%s'," % g["at"]).ljust(10),
                                                          g["label"].replace("'", "\\'"))
                                     for g in groups)
    out2, k = re.subn(r"var groups = \[.*?\];", "var groups = [" + arr + "];", out, count=1, flags=re.S)
    if k != 1:
        sys.exit("could not find the contents groups array")
    out = out2
    print("  contents groups: " + (", ".join("%s %s" % (g["at"], g["label"]) for g in groups) or "none"))

    # ------------------------------------------------------------------- write
    _, after = S.parse(out)
    ids = [s["id"] for s in after]
    if ids != ["s%02d" % (i + 1) for i in range(len(ids))]:
        sys.exit("the rebuilt document is not numbered 01..%02d: %s" % (len(ids), ids))
    dead = sorted({h for h in re.findall(r'href="#(s\d\d)"', out)} - set(ids))
    if dead:
        sys.exit("rebuilt document has dead anchors: %s" % dead)

    if a.check:
        print("\n--check: nothing written. %d sections would be renumbered 01..%02d."
              % (len(ids), len(ids)))
        return
    open(a.index, "w", encoding="utf-8").write(out)
    print("\n%s rewritten (%d sections, %.2f MB)" % (a.index, len(ids), len(out) / 1048576))
    print("now run:  python3 check.py        # refresh-csp is step 3 of it, and this needs it")


if __name__ == "__main__":
    main()
