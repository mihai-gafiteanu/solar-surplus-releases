#!/usr/bin/env python3
# evcc solar-surplus charging · section editor generator
#
#   python3 tools/make-section-editor.py \
#       --index site/app/index.html \
#       --out   site/section-editor.html
#
# Writes one self-contained HTML editor: every section as a card that can be
# dragged, retitled, rewritten or switched off, plus the part boundary as a card
# of its own. It exports a JSON; tools/apply-sections.py writes that back.
#
# Every prose block is shown three times, side by side. The left pane is the
# document as it shipped and carries contenteditable="false" — it always reads
# from DATA and never from the saved state, so a reload after an edit still
# shows what the block started as. The middle pane is the STORY: the owner
# tells it in Romanian, and that telling is the truth the document must match.
# The right pane is the English translation of that truth, and the plan is cut
# from the right pane alone — the story rides the exported JSON beside it
# (per-block "ro" maps that apply-sections.py deliberately ignores), so the
# record of what the document means survives with the plan that shipped it.
# Import closes the loop: a plan JSON written elsewhere (a translation pass)
# loads back into the editor for correction.
#
# Prose only. Figures, tables, code blocks and inline SVG are held: shown as a
# one-line summary spanning the panes, never editable. tools/sections.py
# decides which is which.

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sections as S  # noqa: E402


def build_data(html):
    cols, secs = S.parse(html)
    order, out = [], {}
    for s in secs:
        if s["col"] == 1 and "--part--" not in order:
            order.append("--part--")
        order.append(s["id"])
        out[s["id"]] = {
            "n": s["n"], "title": s["title"], "col": s["col"],
            "blocks": [{"i": b["i"], "tag": b["tag"], "cls": b["cls"],
                        "editable": b["editable"],
                        "html": b["html"], "summary": b["summary"]}
                       for b in s["blocks"]],
        }
    # The part card exists only where there are two columns for it to sit
    # between. This document folded its argument into section 01 and has one,
    # so there is no seam to drag and the editor does not offer one.
    groups = S.toc_groups(html)
    # The document dates itself; it stopped carrying a release version
    # when the site separated from the release train in v2.42.
    rel = re.search(r"last revised (\d{4}-\d{2}-\d{2})", html)
    return {"release": rel.group(1) if rel else "?",
            # the document this editor was cut from; a plan only applies to the
            # index.html whose fingerprint it carries
            "index_sha": hashlib.sha256(html.encode("utf-8")).hexdigest()[:12],
            # and how that index.html was cut into blocks, because a change in
            # sections.py renumbers them without changing a byte of the file
            "blocks_sha": S.fingerprint(secs),
            "order": order, "groups": groups, "sections": out}


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Section editor rev. __REL__ — charging on solar surplus</title>
<style>
:root{
  --ink:#15181c; --body:#2c333c; --muted:#69727e; --faint:#8b95a1;
  --rule:#e2e6ea; --rule-soft:#eef1f4; --bg:#ffffff; --panel:#f7f8fa;
  --accent:#b45309; --accent-soft:#fdf6ec; --accent-line:#e8c99a;
  --green:#15803d; --green-soft:#f0f8f2; --green-line:#bfdfc9;
  --blue:#1d4ed8; --blue-soft:#f2f5fd; --blue-line:#c4d2f4;
  --red:#b91c1c; --red-soft:#fdf3f2; --red-line:#eec7c4;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--panel);color:var(--body);font-family:var(--sans);font-size:15px;line-height:1.6}

/* ---------------------------------------------------------------- top bar */
.top{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  padding:11px 20px;background:var(--bg);border-bottom:1px solid var(--rule)}
.brand{font-weight:650;color:var(--ink);font-size:15px;letter-spacing:-.01em}
.brand .v{display:inline-block;margin-left:9px;padding:3px 9px;border-radius:5px;background:var(--accent);
  color:#fff;font:700 11.5px/1 var(--sans);letter-spacing:.05em;vertical-align:1px}
.count{font:500 12.5px/1 var(--mono);color:var(--muted)}
.spacer{flex:1}
.btn{font:600 12.5px/1 var(--sans);padding:8px 12px;border:1px solid var(--rule);background:var(--bg);
  color:var(--body);border-radius:6px;cursor:pointer}
.btn:hover{border-color:var(--faint);color:var(--ink)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{filter:brightness(1.07)}
.btn:disabled{opacity:.4;cursor:default}
.chip{font:600 11.5px/1 var(--sans);padding:6px 11px;border:1px solid var(--rule);background:var(--bg);
  color:var(--muted);border-radius:20px;cursor:pointer}
.chip.on{background:var(--ink);border-color:var(--ink);color:#fff}
.savest{font:500 11.5px/1 var(--mono);color:var(--faint);min-width:118px}
.savest.live{color:var(--green)} .savest.err{color:var(--red)}

/* ------------------------------------------------------------------ frame */
.cols{display:grid;grid-template-columns:250px minmax(0,1fr);align-items:start}
aside{position:sticky;top:53px;max-height:calc(100vh - 53px);overflow:auto;padding:20px 14px 60px 20px;
  border-right:1px solid var(--rule);background:var(--bg)}
aside .g{font:600 10px/1 var(--sans);letter-spacing:.15em;text-transform:uppercase;color:var(--faint);margin:18px 0 7px}
aside a{display:flex;gap:8px;padding:3.5px 0 3.5px 8px;font-size:12.8px;color:var(--muted);
  text-decoration:none;border-left:2px solid transparent;cursor:pointer}
aside a:hover{color:var(--ink)}
aside a.off{opacity:.42;text-decoration:line-through}
aside a.dirty{border-left-color:var(--accent);color:var(--ink)}
aside a .n{font:600 10.5px/1.5 var(--mono);color:var(--faint);min-width:18px}
main{padding:22px 26px 200px;max-width:1380px}

/* ------------------------------------------------------------------ cards */
.grp{display:flex;align-items:center;gap:11px;margin:26px 0 12px}
.grp::after{content:"";flex:1;height:1px;background:var(--rule)}
.grp input{font:600 10.5px/1 var(--sans);letter-spacing:.15em;text-transform:uppercase;color:var(--accent);
  border:1px dashed transparent;background:none;padding:4px 6px;border-radius:4px;width:230px}
.grp input:hover{border-color:var(--accent-line)}
.grp input:focus{outline:0;border-color:var(--accent);border-style:solid;background:var(--accent-soft)}

.card{background:var(--bg);border:1px solid var(--rule);border-radius:9px;margin:0 0 10px}
.card.drag{opacity:.35}
.card.over{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.card.off{background:var(--panel)}
.card.off .hd .t{color:var(--faint);text-decoration:line-through}
.card.part{background:var(--blue-soft);border-color:var(--blue-line);border-style:dashed}

.hd{display:flex;align-items:center;gap:10px;padding:11px 13px}
.hd .grab{cursor:grab;color:var(--faint);font-size:15px;line-height:1;padding:2px 3px;user-select:none}
.hd .grab:active{cursor:grabbing}
.hd .n{font:700 11.5px/1 var(--mono);color:#fff;background:var(--faint);border-radius:5px;padding:5px 7px;min-width:28px;text-align:center}
.card:not(.off) .hd .n{background:var(--accent)}
.hd .t{flex:1;min-width:0;font:650 15.5px/1.35 var(--serif);color:var(--ink);border:1px solid transparent;
  background:none;padding:5px 7px;border-radius:5px}
.hd .t:hover{border-color:var(--rule)}
.hd .t:focus{outline:0;border-color:var(--accent);background:var(--accent-soft)}
.hd .part-label{flex:1;font:600 11px/1 var(--sans);letter-spacing:.13em;text-transform:uppercase;color:var(--blue)}
.tags{display:flex;gap:5px}
.tag{font:600 9.5px/1.7 var(--sans);letter-spacing:.07em;text-transform:uppercase;padding:1px 7px;border-radius:20px;white-space:nowrap}
.tag.e{background:var(--accent-soft);color:var(--accent);border:1px solid var(--accent-line)}
.tag.m{background:var(--blue-soft);color:var(--blue);border:1px solid var(--blue-line)}
.tag.r{background:var(--green-soft);color:var(--green);border:1px solid var(--green-line)}
.tag.o{background:var(--red-soft);color:var(--red);border:1px solid var(--red-line)}
.tag.s{background:var(--blue-soft);color:var(--blue);border:1px solid var(--blue-line)}
.ico{border:1px solid var(--rule);background:var(--bg);border-radius:5px;width:26px;height:26px;
  font:600 12px/1 var(--sans);color:var(--muted);cursor:pointer;padding:0}
.ico:hover{border-color:var(--faint);color:var(--ink)}
.ico:disabled{opacity:.3;cursor:default}
.sw{position:relative;width:36px;height:20px;border-radius:20px;background:var(--rule);border:0;cursor:pointer;padding:0}
.sw::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;
  box-shadow:0 1px 2px rgba(0,0,0,.2);transition:left .13s}
.sw.on{background:var(--green)}
.sw.on::after{left:18px}

.body{border-top:1px solid var(--rule-soft);padding:6px 13px 13px}
.card.closed .body{display:none}

/* Three panes, one grid, so the key column and the raw button stay put
   whatever is showing. Left is the document as it shipped and is never
   editable; the middle is the story, told in Romanian, and is the truth;
   the right is its English translation and is what the plan is cut from.
   Either of the first two can be hidden for room. */
.blkrow{display:grid;grid-template-columns:44px minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) 30px;gap:9px;
  align-items:start;padding:7px 0;border-bottom:1px solid var(--rule-soft)}
.blkrow:last-child{border-bottom:0}
.blkrow .k{font:600 9.5px/1.9 var(--mono);color:var(--faint);text-align:right;padding-top:3px}
.blkrow .w{min-width:0}
.blkrow .w.spanfill{grid-column:2 / span 3}
.panehd{display:grid;grid-template-columns:44px minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) 30px;gap:9px;
  font:600 9.5px/1.7 var(--sans);letter-spacing:.13em;text-transform:uppercase;color:var(--faint);
  padding:3px 0 5px;border-bottom:1px solid var(--rule-soft)}
.panehd .r2{color:var(--blue)}
.panehd .r3{color:var(--accent)}
body.no-orig .blkrow,body.no-orig .panehd{grid-template-columns:44px minmax(0,1fr) minmax(0,1fr) 30px}
body.no-ro .blkrow,body.no-ro .panehd{grid-template-columns:44px minmax(0,1fr) minmax(0,1fr) 30px}
body.no-orig.no-ro .blkrow,body.no-orig.no-ro .panehd{grid-template-columns:44px minmax(0,1fr) 30px}
body.no-orig .orig,body.no-orig .panehd .r1{display:none}
body.no-ro .blk.ro,body.no-ro .panehd .r2{display:none}
body.no-orig .blkrow .w.spanfill,body.no-ro .blkrow .w.spanfill{grid-column:2 / span 2}
body.no-orig.no-ro .blkrow .w.spanfill{grid-column:2}
.blkrow .raw{border:1px solid var(--rule);background:var(--bg);border-radius:4px;font:600 10px/1 var(--mono);
  color:var(--faint);cursor:pointer;padding:4px 6px;margin-top:3px}
.blkrow .raw.on{background:var(--ink);border-color:var(--ink);color:#fff}

.blk{border:1px solid transparent;border-radius:5px;padding:5px 8px}
.blk:hover{border-color:var(--rule-soft);background:#fcfdfe}
.blk:focus{outline:0;border-color:var(--accent);background:var(--accent-soft)}
.blk.dirty{border-left:2px solid var(--accent)}
.blk.orig{background:#fbfcfd;border-color:var(--rule-soft);color:var(--muted);cursor:default}
.blk.orig:hover{background:#fbfcfd;border-color:var(--rule-soft)}
.blk.orig.was{border-left:2px solid var(--faint)}
.blk.ro{background:#fcfdff;border-color:var(--rule-soft)}
.blk.ro:hover{border-color:var(--blue-line)}
.blk.ro:focus{border-color:var(--blue);background:var(--blue-soft)}
.blk.ro.has{border-left:2px solid var(--blue)}
.blk.ro:empty::before{content:"\2014 povestea \2014";color:var(--faint);font-style:italic}
.blk p,.blk ul,.blk ol{margin:0 0 9px}
.blk p:last-child,.blk ul:last-child,.blk ol:last-child{margin-bottom:0}
.blk.t-p{font-size:15px}
.blk.t-lede{font-size:15.5px;color:var(--muted)}
.blk.t-h3{font-size:16px;font-weight:650;color:var(--ink)}
.blk.t-h4{font-size:14px;font-weight:650;color:var(--ink)}
.blk.t-note{background:var(--accent-soft);border:1px solid var(--accent-line);border-left:3px solid var(--accent);
  border-radius:0 6px 6px 0;font-size:14.4px}
.blk.t-note.blue{background:var(--blue-soft);border-color:var(--blue-line);border-left-color:var(--blue)}
.blk.t-note.green{background:var(--green-soft);border-color:var(--green-line);border-left-color:var(--green)}
.blk.t-note.red{background:var(--red-soft);border-color:var(--red-line);border-left-color:var(--red)}
.blk .h{display:block;font-size:12.5px;font-weight:700;color:var(--ink);margin-bottom:4px}
.blk a{color:var(--accent)}
.blk code{font:400 .87em/1.4 var(--mono);background:var(--panel);border:1px solid var(--rule);
  border-radius:4px;padding:1px 4px;color:#3b444f}
.blk .small{font-size:.88em;color:var(--muted)}
.blk ul,.blk ol{padding-left:20px}
.held{font:500 12.3px/1.5 var(--mono);color:var(--muted);background:var(--panel);border:1px solid var(--rule);
  border-radius:5px;padding:7px 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.held b{color:var(--body);font-weight:600}
textarea.rawbox{width:100%;min-height:96px;font:400 12px/1.6 var(--mono);color:var(--ink);
  border:1px solid var(--accent);border-radius:5px;padding:8px 9px;resize:vertical;background:#fffdf8}
textarea.rawbox:focus{outline:0}

.help{background:var(--bg);border:1px solid var(--rule);border-radius:9px;padding:15px 18px;margin:0 0 20px;
  font-size:13.6px;color:var(--muted);line-height:1.62}
.help b{color:var(--ink)}
.help kbd{font:600 11px/1 var(--mono);border:1px solid var(--rule);border-bottom-width:2px;border-radius:4px;
  padding:3px 5px;background:var(--panel);color:var(--body)}
.toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);background:var(--ink);color:#fff;
  font:600 13px/1 var(--sans);padding:12px 18px;border-radius:7px;opacity:0;pointer-events:none;transition:opacity .18s;z-index:60}
.toast.on{opacity:1}
@media (max-width:900px){ .cols{grid-template-columns:minmax(0,1fr)} aside{display:none} main{padding:18px 14px 200px} }
</style>
</head>
<body>

<div class="top">
  <div class="brand">Section editor<span class="v">rev. __REL__</span></div>
  <div class="count" id="count"></div>
  <button class="chip on" data-f="all">All</button>
  <button class="chip" data-f="changed">Changed</button>
  <button class="chip" data-f="off">Off</button>
  <button class="chip on" id="btnorig" title="show or hide the frozen original">Shipped</button>
  <button class="chip on" id="btnro" title="show or hide the story pane">Story</button>
  <div class="spacer"></div>
  <button class="btn" id="btnlink" title="Autosave straight into site/">&#9955; Link file</button>
  <span class="savest" id="savest"></span>
  <button class="btn" id="btnreset">Reset</button>
  <button class="btn" id="btnimp" title="load a plan JSON back into the editor">Import .json</button>
  <button class="btn" id="btndl">Download .json</button>
  <button class="btn primary" id="btncopy">Copy JSON</button>
  <input type="file" id="impfile" accept=".json,application/json" style="display:none">
</div>

<div class="cols">
  <aside id="rail"></aside>
  <main>
    <div class="help">
      <p style="margin:0 0 8px"><b>Drag a card by its &#10303; handle</b> to move a section, or use <kbd>&#9650;</kbd> <kbd>&#9660;</kbd>.
      Numbers renumber themselves as you go, and <code>apply-sections.py</code> repoints every cross-reference
      in the document to match &mdash; you never edit an anchor by hand.</p>
      <p style="margin:0 0 8px"><b>The dashed blue card is the part boundary.</b> Sections above it are the argument,
      in the first column of the page; sections below it are the build documentation, after the mid-page title
      block and the credits. Drag it to move the seam.</p>
      <p style="margin:0 0 8px"><b>Three panes.</b> The left is the document as v__REL__ shipped and
      cannot be typed into. The middle is <b>the story, in Romanian &mdash; the truth</b>: what the
      document must mean, told plainly; it starts empty. The right is the English translation of that
      truth, starts as the shipped text, and is <b>what the plan is cut from</b> &mdash; the document
      ships the right pane, and the story rides beside it in the export as the record of what it means.
      <b>Shipped</b> and <b>Story</b> in the bar hide their panes when you want the room.</p>
      <p style="margin:0 0 8px"><b>The translation loop.</b> Tell the story in the middle pane (or in
      chat) and export; the translation pass fills the right panes and hands back a JSON;
      <b>Import .json</b> loads it here for correction. Import replaces the editor's state with the
      file's &mdash; export first if you have unexported work.</p>
      <p style="margin:0 0 8px"><b>Prose is editable in place.</b> <kbd>Enter</kbd> is suppressed inside a paragraph
      or heading, because one block is one element &mdash; use <kbd>Shift</kbd>+<kbd>Enter</kbd> for a line break, or
      <b>&lt;/&gt;</b> to edit that block's raw HTML. Tables, code blocks, figures and inline SVG are
      <i>held</i>: shown as a grey line, moved with their section, never altered here.</p>
      <p style="margin:0"><b>Nothing here writes the site.</b> The export is a JSON;
      <code>python3 tools/apply-sections.py &lt;file&gt;.json</code> is what edits <code>index.html</code>,
      and it prints what it changed before it does.</p>
    </div>
    <div id="list"></div>
  </main>
</div>
<div class="toast" id="toast"></div>

<script>
var DATA = __DATA__;

/* ------------------------------------------------------------------ state
   state is only ever the DIFFERENCE from DATA: an order, and per section the
   fields the user has actually touched. A file that records nothing but the
   changes is a file that can be read. */
var KEY = 'ssr-sections-' + DATA.release;
var ORIG = JSON.parse(JSON.stringify(DATA.order));
var state = {order: DATA.order.slice(), sec: {}};
var fileHandle = null, saveTimer = null, filter = 'all';

function rec(id){ if(!state.sec[id]) state.sec[id] = {}; return state.sec[id]; }
function title(id){ var r = state.sec[id]; return (r && r.title !== undefined) ? r.title : DATA.sections[id].title; }
function on(id){ var r = state.sec[id]; return (r && r.include !== undefined) ? r.include : true; }
function blk(id, i){
  var r = state.sec[id];
  if(r && r.blocks && r.blocks[i] !== undefined) return r.blocks[i];
  return DATA.sections[id].blocks[i].html;
}
/* The story pane. There is no default to fall back to — the document ships
   no Romanian — so an untold block reads as the empty string. */
function ro(id, i){
  var r = state.sec[id];
  if(r && r.ro && r.ro[i] !== undefined) return r.ro[i];
  return '';
}
/* Contents headings hang off a section id rather than a position, so moving a
   section carries its heading with it and apply-sections.py renumbers both
   under the same map. */
function groupAt(id){
  var r = state.groups && state.groups[id];
  if(r !== undefined) return r;
  var g = DATA.groups.filter(function(x){ return x.at === id; })[0];
  return g ? g.label : '';
}
function setGroup(id, label){
  if(!state.groups) state.groups = {};
  state.groups[id] = label;
}

function live(){ return state.order.filter(function(id){ return id === '--part--' || on(id); }); }
function numberOf(id){
  var n = 0, l = live();
  for(var i = 0; i < l.length; i++){
    if(l[i] === '--part--') continue;
    n++;
    if(l[i] === id) return n;
  }
  return 0;
}
function dirty(id){
  var r = state.sec[id]; if(!r) return {};
  var d = {};
  if(r.title !== undefined && r.title !== DATA.sections[id].title) d.renamed = 1;
  if(r.include === false) d.off = 1;
  if(r.blocks) for(var k in r.blocks){ if(r.blocks[k] !== DATA.sections[id].blocks[k].html){ d.edited = 1; break; } }
  if(r.ro) for(var k2 in r.ro){ if(r.ro[k2] !== ''){ d.storied = 1; break; } }
  if(state.order.indexOf(id) !== ORIG.indexOf(id)) d.moved = 1;
  return d;
}
function anyDirty(id){ var d = dirty(id); return !!(d.renamed || d.off || d.edited || d.moved || d.storied); }

/* ---------------------------------------------------------------- cleaning
   contenteditable leaves the browser's fingerprints behind: style attributes
   on everything it touched, bare spans, and a <div> per line break. None of
   that belongs in a document whose whole styling comes from twelve classes,
   so it is stripped on the way out rather than argued with on the way in. */
function clean(html){
  var d = document.createElement('div');
  d.innerHTML = html;
  Array.prototype.forEach.call(d.querySelectorAll('[style]'), function(e){ e.removeAttribute('style'); });
  Array.prototype.forEach.call(d.querySelectorAll('font,b>b,i>i'), unwrap);
  Array.prototype.forEach.call(d.querySelectorAll('span:not([class])'), unwrap);
  Array.prototype.forEach.call(d.querySelectorAll('div'), unwrap);
  function unwrap(e){ while(e.firstChild) e.parentNode.insertBefore(e.firstChild, e); e.parentNode.removeChild(e); }
  return d.innerHTML.replace(/ /g, '&nbsp;').replace(/\s+$/, '');
}

/* ------------------------------------------------------------------ render */
function render(){
  var list = document.getElementById('list');
  list.innerHTML = '';
  var pos = 0, seenPart = false;
  state.order.forEach(function(id, idx){
    if(id === '--part--'){
      seenPart = true;
      list.appendChild(partCard(idx));
      return;
    }
    var visible = on(id);
    if(visible) pos++;
    if(filter === 'changed' && !anyDirty(id)) return;
    if(filter === 'off' && visible) return;
    if(visible){
      var g = groupAt(id);
      if(g !== '' || (state.groups && state.groups[id] === '')){
        var row = document.createElement('div');
        row.className = 'grp';
        var inp = document.createElement('input');
        inp.value = g; inp.placeholder = 'contents heading'; inp.dataset.sid = id;
        inp.oninput = function(){ setGroup(this.dataset.sid, this.value); save(); buildRail(); };
        row.appendChild(inp);
        list.appendChild(row);
      }
    }
    list.appendChild(card(id, idx, pos));
  });
  updateCount();
  buildRail();
}

/* Typing in a title or a paragraph must not re-render — that would take the
   caret with it — so the counter is updated on its own instead. */
function updateCount(){
  document.getElementById('count').textContent =
    live().filter(function(i){ return i !== '--part--'; }).length + ' sections \u00b7 ' +
    state.order.filter(function(i){ return i !== '--part--' && !on(i); }).length + ' off \u00b7 ' +
    state.order.filter(function(i){ return i !== '--part--' && anyDirty(i); }).length + ' changed \u00b7 ' +
    state.order.filter(function(i){ return i !== '--part--' && dirty(i).storied; }).length + ' storied';
}

function partCard(idx){
  var c = document.createElement('div');
  c.className = 'card part';
  c.draggable = true; c.dataset.idx = idx; c.dataset.id = '--part--';
  c.innerHTML = '<div class="hd"><span class="grab">&#10303;</span>' +
    '<span class="part-label">&#8595; below here: the build documentation ' +
    '(mid-page title block, credits, then the technical sections)</span></div>';
  wire(c);
  return c;
}

function card(id, idx, pos){
  var s = DATA.sections[id], d = dirty(id), vis = on(id);
  var c = document.createElement('div');
  c.className = 'card' + (vis ? '' : ' off') + (window.__closed && window.__closed[id] ? ' closed' : '');
  c.draggable = true; c.dataset.idx = idx; c.dataset.id = id; c.id = 'card-' + id;

  var hd = document.createElement('div');
  hd.className = 'hd';
  hd.innerHTML = '<span class="grab">&#10303;</span>' +
    '<span class="n">' + (vis ? String(pos).padStart(2, '0') : '--') + '</span>';

  var t = document.createElement('div');
  t.className = 't'; t.contentEditable = 'true'; t.spellcheck = false;
  t.textContent = title(id);
  t.oninput = function(){ rec(id).title = this.textContent.trim(); save(); tags(); updateCount(); buildRail(); };
  t.onkeydown = function(e){ if(e.key === 'Enter'){ e.preventDefault(); this.blur(); } };
  hd.appendChild(t);

  var tg = document.createElement('div'); tg.className = 'tags';
  hd.appendChild(tg);
  function tags(){
    var d2 = dirty(id);
    tg.innerHTML = (d2.edited ? '<span class="tag e">edited</span>' : '') +
                   (d2.storied ? '<span class="tag s">storied</span>' : '') +
                   (d2.renamed ? '<span class="tag r">renamed</span>' : '') +
                   (d2.moved ? '<span class="tag m">moved</span>' : '') +
                   (d2.off ? '<span class="tag o">off</span>' : '');
  }
  tags();

  var up = mk('ico', '&#9650;', function(){ move(idx, -1); });
  var dn = mk('ico', '&#9660;', function(){ move(idx, 1); });
  up.disabled = idx === 0; dn.disabled = idx === state.order.length - 1;
  var sw = mk('sw' + (vis ? ' on' : ''), '', function(){ rec(id).include = !on(id); save(); render(); });
  sw.title = 'include this section in the document';
  var cl = mk('ico', window.__closed && window.__closed[id] ? '+' : '&minus;', function(){
    window.__closed = window.__closed || {};
    window.__closed[id] = !window.__closed[id];
    c.classList.toggle('closed');
    this.innerHTML = window.__closed[id] ? '+' : '&minus;';
  });
  [up, dn, sw, cl].forEach(function(b){ hd.appendChild(b); });
  c.appendChild(hd);

  var body = document.createElement('div');
  body.className = 'body';
  if(s.blocks.length){
    var ph = document.createElement('div');
    ph.className = 'panehd';
    ph.innerHTML = '<div></div><div class="r1">as shipped &middot; v' + DATA.release +
                   '</div><div class="r2">povestea &middot; Romanian &mdash; the truth</div>' +
                   '<div class="r3">the translation &middot; what the document ships</div><div></div>';
    body.appendChild(ph);
  }
  s.blocks.forEach(function(b){
    var row = document.createElement('div'); row.className = 'blkrow';
    var k = document.createElement('div'); k.className = 'k';
    k.textContent = String(b.i).padStart(2, '0') + ' ' + (b.cls ? '.' + b.cls.split(' ')[0] : b.tag);
    row.appendChild(k);
    var w = document.createElement('div'); w.className = 'w';
    if(!b.editable){
      /* Held: one line, spanning the panes. There is nothing to compare and
         nothing to edit — a command is not prose. */
      w.className = 'w spanfill';
      w.innerHTML = '<div class="held"><b>' + b.tag + '</b> &middot; ' + esc(b.summary) + '</div>';
      row.appendChild(w);
      row.appendChild(document.createTextNode(''));
    } else {
      var o = document.createElement('div');
      o.className = 'blk orig ' + klass(b);
      o.innerHTML = b.html;                 /* frozen: always DATA, never state */
      o.setAttribute('contenteditable', 'false');
      o.title = 'the document as it shipped — read only';
      row.appendChild(o);

      var s2 = document.createElement('div');
      s2.className = 'blk ro ' + klass(b);
      s2.contentEditable = 'true'; s2.spellcheck = false;
      s2.innerHTML = ro(id, b.i);
      if(ro(id, b.i) !== '') s2.classList.add('has');
      s2.title = 'povestea, in Romanian — the truth this block must say';
      s2.oninput = function(){
        var r = rec(id); r.ro = r.ro || {};
        var v = clean(this.innerHTML);
        if(v === '') delete r.ro[b.i]; else r.ro[b.i] = v;
        this.classList.toggle('has', v !== '');
        save(); tags(); updateCount(); buildRail();
      };
      s2.onkeydown = function(ev){
        if(ev.key !== 'Enter' || b.tag === 'ul' || b.tag === 'ol' || b.tag === 'div') return;
        ev.preventDefault();
        if(ev.shiftKey) document.execCommand('insertHTML', false, '<br>');
      };
      s2.onpaste = function(ev){
        ev.preventDefault();
        document.execCommand('insertText', false, (ev.clipboardData || window.clipboardData).getData('text'));
      };
      row.appendChild(s2);

      var e = document.createElement('div');
      e.className = 'blk ' + klass(b);
      e.contentEditable = 'true'; e.spellcheck = false;
      e.innerHTML = blk(id, b.i);
      if(blk(id, b.i) !== b.html){ e.classList.add('dirty'); o.classList.add('was'); }
      e.oninput = function(){
        var r = rec(id); r.blocks = r.blocks || {};
        r.blocks[b.i] = clean(this.innerHTML);
        var changed = r.blocks[b.i] !== b.html;
        this.classList.toggle('dirty', changed);
        o.classList.toggle('was', changed);
        save(); tags(); updateCount(); buildRail();
      };
      e.onkeydown = function(ev){
        if(ev.key !== 'Enter' || b.tag === 'ul' || b.tag === 'ol' || b.tag === 'div') return;
        ev.preventDefault();
        if(ev.shiftKey) document.execCommand('insertHTML', false, '<br>');
      };
      e.onpaste = function(ev){
        ev.preventDefault();
        document.execCommand('insertText', false, (ev.clipboardData || window.clipboardData).getData('text'));
      };
      w.appendChild(e);
      row.appendChild(w);
      var raw = mk('raw', '&lt;/&gt;', function(){ toggleRaw(this, w, e, id, b); });
      raw.title = 'edit this block as raw HTML';
      row.appendChild(raw);
    }
    body.appendChild(row);
  });
  if(!s.blocks.length){
    body.innerHTML = '<div class="blkrow"><div class="k"></div><div class="w spanfill"><div class="held">empty section</div></div></div>';
  }
  c.appendChild(body);
  wire(c);
  return c;
}

function toggleRaw(btn, w, e, id, b){
  if(btn.classList.contains('on')){
    var ta = w.querySelector('textarea');
    var r = rec(id); r.blocks = r.blocks || {};
    r.blocks[b.i] = ta.value.trim();
    e.innerHTML = r.blocks[b.i];
    e.classList.toggle('dirty', r.blocks[b.i] !== b.html);
    var o2 = w.parentNode.querySelector('.blk.orig');
    if(o2) o2.classList.toggle('was', r.blocks[b.i] !== b.html);
    ta.remove(); e.style.display = '';
    btn.classList.remove('on');
    save(); updateCount(); buildRail();
  } else {
    var t = document.createElement('textarea');
    t.className = 'rawbox'; t.value = blk(id, b.i); t.spellcheck = false;
    e.style.display = 'none';
    w.appendChild(t); t.focus();
    btn.classList.add('on');
  }
}

function klass(b){
  var c = b.cls || '';
  if(b.tag === 'h3') return 't-h3';
  if(b.tag === 'h4') return 't-h4';
  if(c.indexOf('note') >= 0) return 't-note' + (c.indexOf('blue') >= 0 ? ' blue' : c.indexOf('green') >= 0 ? ' green' : c.indexOf('red') >= 0 ? ' red' : '');
  if(c.indexOf('lede') >= 0) return 't-lede';
  return 't-p';
}
function mk(cls, html, fn){
  var b = document.createElement('button');
  b.className = cls; b.innerHTML = html; b.onclick = fn; b.type = 'button';
  return b;
}
function esc(s){ return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

function buildRail(){
  var rail = document.getElementById('rail'); rail.innerHTML = '';
  var pos = 0;
  state.order.forEach(function(id){
    if(id === '--part--'){
      var p = document.createElement('div'); p.className = 'g'; p.style.color = 'var(--blue)';
      p.textContent = '— part boundary —'; rail.appendChild(p); return;
    }
    var vis = on(id);
    if(vis){ pos++; var g = groupAt(id);
      if(g){ var h = document.createElement('div'); h.className = 'g'; h.textContent = g; rail.appendChild(h); } }
    var a = document.createElement('a');
    a.className = (vis ? '' : 'off ') + (anyDirty(id) ? 'dirty' : '');
    a.innerHTML = '<span class="n">' + (vis ? String(pos).padStart(2, '0') : '--') + '</span><span>' + esc(title(id)) + '</span>';
    a.onclick = function(){
      var el = document.getElementById('card-' + id);
      if(el) el.scrollIntoView({block: 'center', behavior: 'smooth'});
    };
    rail.appendChild(a);
  });
}

/* --------------------------------------------------------------- reordering */
function move(idx, by){
  var to = idx + by;
  if(to < 0 || to >= state.order.length) return;
  var o = state.order;
  var x = o.splice(idx, 1)[0];
  o.splice(to, 0, x);
  save(); render();
  var el = document.getElementById('card-' + x);
  if(el) el.scrollIntoView({block: 'center'});
}
var dragIdx = null;
function wire(c){
  c.addEventListener('dragstart', function(e){
    if(!e.target.closest || !e.target.closest('.card')) return;
    dragIdx = +c.dataset.idx; c.classList.add('drag');
    e.dataTransfer.effectAllowed = 'move';
    try{ e.dataTransfer.setData('text/plain', c.dataset.id); }catch(err){}
  });
  c.addEventListener('dragend', function(){ c.classList.remove('drag'); dragIdx = null; clearOver(); });
  c.addEventListener('dragover', function(e){ e.preventDefault(); e.dataTransfer.dropEffect = 'move'; clearOver(); c.classList.add('over'); });
  c.addEventListener('dragleave', function(){ c.classList.remove('over'); });
  c.addEventListener('drop', function(e){
    e.preventDefault(); clearOver();
    if(dragIdx === null) return;
    var to = +c.dataset.idx;
    if(to === dragIdx) return;
    // after the splice-out the target has shifted, so inserting at `to`
    // drops below the target going down and above it going up — the usual
    // reading of where the card was let go
    var o = state.order, x = o.splice(dragIdx, 1)[0];
    o.splice(to, 0, x);
    dragIdx = null; save(); render();
  });
}
function clearOver(){ Array.prototype.forEach.call(document.querySelectorAll('.card.over'), function(e){ e.classList.remove('over'); }); }

/* ------------------------------------------------------------------ export */
function snapshot(){
  var out = {tool: 'section-editor', release: DATA.release, index_sha: DATA.index_sha,
             blocks_sha: DATA.blocks_sha,
             order: state.order.slice(), groups: [], sections: {}};
  var pos = 0;
  state.order.forEach(function(id){
    if(id === '--part--') return;
    var r = state.sec[id], roMap = null;
    if(r && r.ro){
      var m = {};
      for(var k0 in r.ro){ if(r.ro[k0] !== '') m[k0] = r.ro[k0]; }
      if(Object.keys(m).length) roMap = m;
    }
    if(!on(id)){
      /* The story survives a switched-off section: the plan is also the
         record of what was told, and apply-sections.py ignores ro anyway. */
      var off = {include: false};
      if(roMap) off.ro = roMap;
      out.sections[id] = off;
      return;
    }
    pos++;
    var g = groupAt(id);
    if(g) out.groups.push({at: id, label: g});
    var e = {title: title(id), include: true};
    if(r && r.blocks){
      var b = {};
      for(var k in r.blocks){ if(r.blocks[k] !== DATA.sections[id].blocks[k].html) b[k] = r.blocks[k]; }
      if(Object.keys(b).length) e.blocks = b;
    }
    if(roMap) e.ro = roMap;
    out.sections[id] = e;
  });
  return out;
}

/* --------------------------------------------------------- saving the file */
function save(){
  try{ localStorage.setItem(KEY, JSON.stringify(state)); }catch(e){}
  if(!fileHandle) return;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(writeFile, 700);
}
function writeFile(){
  if(!fileHandle) return;
  fileHandle.createWritable().then(function(w){
    return w.write(JSON.stringify(snapshot(), null, 2)).then(function(){ return w.close(); });
  }).then(function(){
    status('live', 'saved ' + new Date().toTimeString().slice(0, 5));
  }).catch(function(err){ status('err', 'save failed — ' + (err && err.name || 'error')); });
}
function status(cls, msg){
  var el = document.getElementById('savest');
  el.className = 'savest ' + (cls || ''); el.textContent = msg || '';
}
function idb(fn){
  try{
    var rq = indexedDB.open('ssr-sections-handle', 1);
    rq.onupgradeneeded = function(){ rq.result.createObjectStore('h'); };
    rq.onsuccess = function(){ fn(rq.result); };
    rq.onerror = function(){};
  }catch(e){}
}
function recallHandle(){
  if(!window.showSaveFilePicker) return status('', 'autosave unavailable here');
  idb(function(db){
    var g;
    try{ g = db.transaction('h', 'readonly').objectStore('h').get('file'); }catch(e){ return; }
    g.onsuccess = function(){
      var h = g.result;
      if(!h) return status('', 'not linked — click ⛁ Link file');
      h.queryPermission({mode: 'readwrite'}).then(function(p){
        if(p === 'granted'){ fileHandle = h; status('live', 'linked'); }
        else status('', 'click ⛁ Link file to resume autosave');
      }).catch(function(){});
    };
  });
}
document.getElementById('btnlink').onclick = function(){
  if(!window.showSaveFilePicker){
    alert('This browser has no File System Access API, so the page cannot write the JSON itself.\n\n' +
          'Use Chrome or Edge, or keep using "Download .json".');
    return;
  }
  window.showSaveFilePicker({
    suggestedName: 'section-plan.json',
    types: [{description: 'Section plan', accept: {'application/json': ['.json']}}]
  }).then(function(h){
    idb(function(db){ try{ db.transaction('h', 'readwrite').objectStore('h').put(h, 'file'); }catch(e){} });
    fileHandle = h; writeFile();
  }).catch(function(err){
    if(err && err.name === 'AbortError') return;
    status('err', 'could not link — ' + (err && err.name || 'error'));
    alert('The browser refused the file picker.\n\n' +
          'A page opened straight from disk (file://) is an opaque origin and is usually blocked from ' +
          'writing files. Run  python3 site/serve.py  and open the editor over localhost instead.');
  });
};
document.getElementById('btndl').onclick = function(){
  var b = new Blob([JSON.stringify(snapshot(), null, 2)], {type: 'application/json'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(b); a.download = 'section-plan.json';
  document.body.appendChild(a); a.click(); a.remove();
  toast('section-plan.json downloaded');
};
document.getElementById('btncopy').onclick = function(){
  var txt = JSON.stringify(snapshot(), null, 2);
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(function(){ toast('JSON copied'); }).catch(fallback);
  } else fallback();
  function fallback(){
    var ta = document.createElement('textarea');
    ta.value = txt; document.body.appendChild(ta); ta.select();
    try{ document.execCommand('copy'); toast('JSON copied'); }catch(e){ toast('Select and copy manually'); }
    ta.remove();
  }
};
document.getElementById('btnreset').onclick = function(){
  if(!confirm('Throw away every reorder, retitle, story and edit?')) return;
  state = {order: DATA.order.slice(), sec: {}};
  try{ localStorage.removeItem(KEY); }catch(e){}
  save(); render();
};

/* Import: a plan JSON written elsewhere — the translation pass — becomes the
   editor's state, replacing it whole. The same two fingerprints apply-
   sections.py refuses on are confirmed here, softly: block numbers are
   per-document, so a plan from another index.html may edit other text. */
function importPlan(o){
  if(!o || o.tool !== 'section-editor' || !o.order || !o.sections){ toast('Not a section plan'); return; }
  if((o.index_sha && o.index_sha !== DATA.index_sha) ||
     (o.blocks_sha && o.blocks_sha !== DATA.blocks_sha)){
    if(!confirm('This plan was cut from a different index.html or block structure.\n' +
                'Its block numbers may point at other paragraphs here. Import anyway?')) return;
  }
  var known = {};
  DATA.order.forEach(function(i){ known[i] = 1; });
  var st = {order: [], sec: {}, groups: {}};
  o.order.forEach(function(i){ if(known[i]){ st.order.push(i); delete known[i]; } });
  DATA.order.forEach(function(i){ if(known[i]) st.order.push(i); });  /* nothing is lost */
  DATA.order.forEach(function(id){
    if(id === '--part--') return;
    var p = o.sections[id];
    if(!p) return;
    var r = {};
    if(p.include === false) r.include = false;
    if(p.title !== undefined) r.title = p.title;
    if(p.blocks) r.blocks = p.blocks;
    if(p.ro) r.ro = p.ro;
    if(Object.keys(r).length) st.sec[id] = r;
  });
  var listed = {};
  (o.groups || []).forEach(function(g){ listed[g.at] = g.label; });
  DATA.groups.forEach(function(g){ if(listed[g.at] === undefined) st.groups[g.at] = ''; });
  for(var at in listed) st.groups[at] = listed[at];
  state = st;
  save(); render();
  toast('Plan imported');
}
document.getElementById('btnimp').onclick = function(){ document.getElementById('impfile').click(); };
document.getElementById('impfile').onchange = function(){
  var f = this.files && this.files[0];
  this.value = '';
  if(!f) return;
  var rd = new FileReader();
  rd.onload = function(){
    var o = null;
    try{ o = JSON.parse(rd.result); }catch(err){ toast('That file is not JSON'); return; }
    importPlan(o);
  };
  rd.readAsText(f);
};

function paneChip(btn, cls, key){
  btn.onclick = function(){
    var off = document.body.classList.toggle(cls);
    btn.classList.toggle('on', !off);
    try{ localStorage.setItem(KEY + key, off ? '1' : ''); }catch(e){}
  };
  try{
    if(localStorage.getItem(KEY + key)){
      document.body.classList.add(cls);
      btn.classList.remove('on');
    }
  }catch(e){}
}
paneChip(document.getElementById('btnorig'), 'no-orig', '-noorig');
paneChip(document.getElementById('btnro'), 'no-ro', '-noro');

Array.prototype.forEach.call(document.querySelectorAll('.chip:not(#btnorig):not(#btnro)'), function(ch){
  ch.onclick = function(){
    Array.prototype.forEach.call(document.querySelectorAll('.chip[data-f]'), function(o){ o.classList.remove('on'); });
    ch.classList.add('on'); filter = ch.dataset.f; render();
  };
});
var toastT = null;
function toast(m){
  var t = document.getElementById('toast');
  t.textContent = m; t.classList.add('on');
  clearTimeout(toastT); toastT = setTimeout(function(){ t.classList.remove('on'); }, 1900);
}

/* ------------------------------------------------------------------- start */
try{
  var raw = localStorage.getItem(KEY);
  if(raw){
    var o = JSON.parse(raw);
    if(o && o.order && o.order.length === DATA.order.length){ state = o; state.sec = state.sec || {}; }
  }
}catch(e){}
render();
recallHandle();
window.addEventListener('beforeunload', function(e){
  if(!fileHandle && state.order.some(function(i){ return i !== '--part--' && anyDirty(i); })){
    e.preventDefault(); e.returnValue = '';
  }
});
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="site/app/index.html")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    html = open(a.index, encoding="utf-8").read()
    data = build_data(html)
    # Unversioned, like every other artifact: git carries the
    # version, the page states it inside. A versioned default outlives
    # that rule by writing a stray file BESIDE the one it regenerates.
    out = a.out or os.path.join("site", "section-editor.html")

    page = (TEMPLATE
            .replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            .replace("__REL__", data["release"]))
    # newline="\n": on Windows the default text mode writes CRLF into a file
    # the repo reads as LF, and a regeneration that changed one sentence then
    # arrives as a whole-file diff. Every generator in the tree carries
    # this — make-dashboard.py, refresh-csp.py, make-review-desk.py too.
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)

    ed = sum(1 for s in data["sections"].values() for b in s["blocks"] if b["editable"])
    held = sum(1 for s in data["sections"].values() for b in s["blocks"] if not b["editable"])
    print("%s\n  %d sections · %d editable blocks · %d held · %.0f KB"
          % (out, len(data["sections"]), ed, held, os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()
