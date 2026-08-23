#!/usr/bin/env python3
"""
Fold sections 01-06 into one collapsed 'Why' at the top of the page, prepend the
two Word documents to it, and renumber the build half from 07-23 down to 01-17.

Run once, from the project root:  python3 apply-why.py

Every edit is anchored on a string that must be found; a missing anchor stops the
script before anything is written.
"""
import io
import re
import sys

sys.path.insert(0, "/tmp/build")
from why_prose import PERSONAL

INDEX = "site/app/index.html"
src = io.open(INDEX, encoding="utf-8").read()
orig_len = len(src)


def must(old, new, s, count=1):
    """Replace, or say which anchor went missing."""
    n = s.count(old)
    if n != count:
        sys.exit("anchor found %d times, expected %d:\n  %r" % (n, count, old[:120]))
    return s.replace(old, new, count)


# ---------------------------------------------------------------- 1. cut out
START = '<div class="col">\n\n<h2 id="s01">'
END = '</div><!-- /col, the argument -->'
i = src.find(START)
j = src.find(END)
if i < 0 or j < 0 or j < i:
    sys.exit("could not locate the argument block")
argument = src[i + len('<div class="col">'):j]
before, after = src[:i], src[j + len(END):]

# --------------------------------------------------- 2. demote its headings
# <h2 id="sNN"><span class="sn">Section NN</span>Title</h2>  ->  <h3 class="argh">Title</h3>
argument, n = re.subn(
    r'<h2 id="s0[1-6]"><span class="sn">Section 0[1-6]</span>(.*?)</h2>',
    lambda m: '<h3 class="argh">%s</h3>' % m.group(1),
    argument)
if n != 6:
    sys.exit("expected 6 argument headings, demoted %d" % n)

# no trailing rule where the argument meets the build's cover
argument = argument.rstrip()

# ------------------------------------------------------------ 3. the wrapper
why = (
    '<details class="why" id="why">\n'
    '<summary>\n'
    '  <h2 id="why-h" data-toc="Why">'
    '<span class="sn">The argument</span>'
    'Why<span class="whyhint">Why one household built this, why 2026 rhymes with 1979, '
    'and the case for fixing the wires rather than the rooftops.</span>'
    '<span class="whytoggle" aria-hidden="true"></span>'
    '</h2>\n'
    '</summary>\n'
    '<div class="col whybody">\n'
    + PERSONAL.strip() + "\n"
    + argument + "\n"
    '</div><!-- /col, the argument -->\n'
    '</details>\n'
)

src = before + why + after

# ------------------------------------------------------------- 4. renumber
# Only the build half, which begins at the mid-page cover; the argument links
# forward into it, so anchors are rewritten across the whole file.
# One pass, one alternation - a second pass would renumber the same occurrence
# twice.
N = r'(?:0[7-9]|1[0-9]|2[0-3])'
FORMS = re.compile(
    r'(?P<id>\bs(?P<idn>%s)\b)'                                   # id / #anchor
    r'|(?P<rng>\b(?P<rw>[Ss]ections)\s+(?P<a>%s)\s+to\s+(?P<b>%s)\b)'  # 'Sections 07 to 23'
    r'|(?P<one>\b(?P<ow>[Ss]ection)\s+(?P<on>%s)\b)'              # 'section 12'
    % (N, N, N, N))

counts = {"id": 0, "rng": 0, "one": 0}


def shift(m):
    if m.group("id"):
        counts["id"] += 1
        return "s%02d" % (int(m.group("idn")) - 6)
    if m.group("rng"):
        counts["rng"] += 1
        return "%s %02d to %02d" % (m.group("rw"),
                                    int(m.group("a")) - 6, int(m.group("b")) - 6)
    counts["one"] += 1
    return "%s %02d" % (m.group("ow"), int(m.group("on")) - 6)


src = FORMS.sub(shift, src)
if counts["id"] != 42:
    sys.exit("expected 42 ids and anchors, shifted %d" % counts["id"])
heads = len(re.findall(r'<span class="sn">Section \d\d</span>', src))
if heads != 17:
    sys.exit("expected 17 numbered headings after the shift, found %d" % heads)
print("renumbered: %(id)d ids/anchors, %(rng)d ranges, %(one)d prose mentions" % counts)

# ------------------------------------------------------- 5. the cover's promise
src = must(
    'The first six sections are the case for fixing the wires rather than the '
    'rooftops. The seventeen after them are one house doing it for itself.',
    'The case for fixing the wires rather than the rooftops is folded into '
    '<a href="#why">Why</a>, closed at the top of this page. The seventeen '
    'sections after it are one house doing it for itself.',
    src)

# -------------------------------------------------------------- 6. the CSS
src = must(
    '/* ---- the argument, sections 01-06 ---',
    '/* ---- the argument, now folded into Why ---', src)

src = must('.volt + h2{margin-top:40px}',
           '.volt + h2,.volt + h3.argh{margin-top:40px}', src)

src = must('h2 + .lede{', 'h2 + .lede,h3.argh + .lede{', src)

WHY_CSS = """
/* ---- Why: the argument, folded shut ------------------------------------
   Six sections of argument and two prefatory pieces are a lot of page to put
   in front of someone who came for the build, and deleting them is not the
   answer either. So they are one <details>, closed on load. The disclosure is
   pure CSS - no script runs to open it, which also means it survives the CSP
   with nothing added to the hash. */
details.why{max-width:790px}
details.why > summary{
  list-style:none; display:block; cursor:pointer; background:var(--panel);
  padding:40px 56px 40px; position:relative; transition:background .12s ease;
}
details.why > summary::-webkit-details-marker{display:none}
details.why > summary::marker{content:""}
details.why > summary:hover{background:var(--accent-soft)}
details.why > summary:focus-visible{outline:2px solid var(--accent); outline-offset:-4px}
details.why > summary h2{
  margin:0; font-size:30px; padding-right:34px; scroll-margin-top:24px;
}
details.why > summary .whyhint{
  display:block; margin-top:12px; max-width:610px;
  font:400 16px/1.55 var(--sans); color:var(--muted); letter-spacing:0;
}
/* The chevron, and the word beside it. Both are content: rules, so the open
   and closed states are one declaration each and cannot disagree. */
details.why > summary .whytoggle{
  position:absolute; right:56px; top:44px;
  font:600 11px/1 var(--sans); letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); display:flex; align-items:center; gap:9px;
}
details.why > summary .whytoggle::before{content:"Read"}
details.why[open] > summary .whytoggle::before{content:"Close"}
details.why > summary .whytoggle::after{
  content:""; width:7px; height:7px; border-right:1.8px solid var(--accent);
  border-bottom:1.8px solid var(--accent); transform:rotate(45deg);
  margin-top:-4px; transition:transform .16s ease;
}
details.why[open] > summary .whytoggle::after{transform:rotate(-135deg); margin-top:2px}
details.why .whybody{
  background:var(--bg); padding-top:8px; padding-bottom:56px;
  border-top:1px solid var(--rule);
}
details.why .whybody > h3.argh:first-child{margin-top:44px}
/* Inside Why the six former sections are subheads, not sections. They keep the
   serif and the size relationship to the body, and lose the number. */
h3.argh{
  font-family:var(--serif); font-weight:600; font-size:24px; line-height:1.2;
  letter-spacing:-.012em; color:var(--ink); margin:62px 0 6px; scroll-margin-top:24px;
}
@media (max-width:1000px){
  details.why > summary{padding-left:26px; padding-right:26px}
  details.why > summary .whytoggle{right:26px}
}
@media (max-width:560px){
  details.why > summary{padding:30px 18px}
  details.why > summary h2{font-size:25px; padding-right:0}
  details.why > summary .whytoggle{position:static; margin-top:16px; display:inline-flex}
  h3.argh{font-size:21px; margin-top:46px}
}
@media print{
  details.why > summary .whytoggle{display:none}
}
"""
src = must("figure.chart{margin:30px 0}", WHY_CSS.strip() + "\nfigure.chart{margin:30px 0}", src)

# ---------------------------------------------------------------- 7. the TOC
src = must(
    """  var groups = [{at:1,  label:'The argument'},
                {at:7,  label:'The installation'},
                {at:12, label:'Building it'},
                {at:18, label:'Running it'}];""",
    """  // Keyed by id rather than by number, because the first entry no longer
  // has a number: Why sits above the numbered document rather than inside it.
  var groups = [{at:'why-h', label:'The argument'},
                {at:'s01',   label:'The installation'},
                {at:'s06',   label:'Building it'},
                {at:'s12',   label:'Running it'}];""",
    src)

src = must(
    """  heads.forEach(function(h){
    var num = parseInt(h.id.replace('s',''), 10);
    groups.forEach(function(g){
      if(num === g.at){""",
    """  heads.forEach(function(h){
    var mm = /^s(\\d+)$/.exec(h.id);
    var num = mm ? parseInt(mm[1], 10) : null;
    groups.forEach(function(g){
      if(h.id === g.at){""",
    src)

src = must(
    """    var sn = h.querySelector('.sn');
    var title = h.textContent.replace(sn ? sn.textContent : '', '').trim();""",
    """    var sn = h.querySelector('.sn');
    // Why's heading carries its own standfirst inside the <summary>, so the
    // contents take the label from data-toc where a heading offers one.
    var title = h.getAttribute('data-toc')
              || h.textContent.replace(sn ? sn.textContent : '', '').trim();""",
    src)

src = must(
    """    var n = document.createElement('span');
    n.className = 'n'; n.textContent = String(num).length < 2 ? '0' + num : String(num);""",
    """    var n = document.createElement('span');
    n.className = 'n';
    n.textContent = num === null ? '' : (String(num).length < 2 ? '0' + num : String(num));""",
    src)

io.open(INDEX, "w", encoding="utf-8").write(src)
print("index.html: %d -> %d bytes" % (orig_len, len(src)))
