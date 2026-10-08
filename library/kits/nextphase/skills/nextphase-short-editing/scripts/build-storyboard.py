#!/usr/bin/env python3
"""
Build a beat-by-beat STORYBOARD.html for a video folder: one real frame per beat, with the
role it plays in the arc, the line being spoken over it, the layout, the caption style and
the sound cues that fire inside it.

    python scripts/build-storyboard.py videos/tp-0809

Reads BEATS out of the folder's build.py, the words out of assets/transcript.json, the cues
out of sfx-cues.txt, and the frames out of storyboard/ (make them with
`hyperframes snapshot --at <mid-beat times> -o storyboard`).
"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _win_utf8  # noqa: E402,F401  content-engine import: UTF-8 text I/O on Windows
import ast, html, json, pathlib, re, sys

VID = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "videos/tp-0809").resolve()

# ── the arc role of each beat, in order. This is the editorial layer the beat map can't hold.
ROLES = [
    ("HOOK",            "Transparent. He delivers the hook; the wordmark wipes on, the mascot "
                        "walks in, riser building underneath."),
    ("HOOK PAYOFF",     "Cut to his full face, frame-filling, slow push. The line lands with "
                        "nothing else on screen."),
    ("THE PROBLEM",     "Split, coral. FOUR REAL SESSION WINDOWS — one running, three stuck on "
                        "'waiting' — and one mascot running between them. That is what "
                        "babysitting sessions looks like. (Was a sleeping mascot.)"),
    ("THE QUEUE",       "Transparent. One session works at a terminal, two sit asleep behind it "
                        "— 'before starting the next'."),
    ("THE TURN",        "Full face, short. 'Now they do that themselves' is the pivot of the "
                        "whole video."),
    ("B-ROLL TAKEOVER", "The page owns the frame. Two sessions, a wire, a message riding across, "
                        "a check when it lands. The mechanism, explained."),
    ("CROSS-MACHINE",   "Split, coral. One session conducting mac mini / laptop / desktop — each "
                        "on its own computer."),
    ("THE OLD LIMIT",   "Transparent. Mascot juggling — helpers are actors, so a mascot is right "
                        "here (see the concept catalog)."),
    ("LIMIT GONE",      "Split, coral. Six helpers pop in one after another. 'That's gone' lands "
                        "on a magic-reveal."),
    ("THEY RUN THEMSELVES","B-roll full. All four session windows green and running with nobody "
                        "tending them — the payoff of beat 03's pain."),
    ("THE WARNING",     "Full face, punch. The safety line, eye contact, no graphics competing."),
    ("THE GUARD",       "B-roll full. The real permission prompt inside a session: a message "
                        "arrives, Allow / Deny, Allow lights up. This is the UI you asked for on "
                        "the word 'session'."),
    ("PLATFORMS",       "Split, coral. Cream chips for macOS and Linux, Windows outlined and "
                        "dimmed. Designed marks only."),
    ("CTA",             "The old CTA — logo chip, COMMENT, \"RELAY\", ink arrow. Captions off."),
]

LAYOUT_LABEL = {
    "trans": ("TRANSPARENT",   "pop-out on cream, media above his head"),
    "face":  ("FULL FACE",     "the raw take fills the whole frame"),
    "split": ("SPLIT SCREEN",  "media owns the top half, camera card the bottom"),
    "bfull": ("B-ROLL FULL",   "the media owns the frame — no camera at all"),
    "cta":   ("CTA",           "cream panel over the camera card"),
}
CAP_LABEL = {
    "trans": "Parallax · Instrument Serif · y840",
    "face":  "Chrome gradient · y1470",
    "split": "Highlighted · coral marker · on the seam y900",
    "bfull": "Parallax · y1500 · straight on the page, no band (BLACKLIST #3)",
    "cta":   "none — the pill is the message",
}

# ── read the beat map straight out of build.py so this can never drift ───────
src = (VID / "build.py").read_text()
m = re.search(r"BEATS = (\[.*?\n\])", src, re.S)
BEATS = ast.literal_eval(re.sub(r"#.*", "", m.group(1)))

# ROLES and the caption map are per-VIDEO editorial, not a property of the format: a cut with
# its own arc must not be described with another cut's roles. If the video's build.py declares
# them, they win; the lists above are only the fallback.
_m = re.search(r"^ROLES = (\[.*?\n\])", src, re.S | re.M)
if _m:
    ROLES = ast.literal_eval(re.sub(r"#.*", "", _m.group(1)))
_m = re.search(r"^CAP = (\{.*?\})\n", src, re.S | re.M)
if _m:
    _cap = ast.literal_eval(re.sub(r"#.*", "", _m.group(1)))
    _STYLE_NAME = {"par": "Parallax · Instrument Serif · --red",
                   "grad": "Parallax × gradient",
                   "hl": "Highlighted · white on a coral marker",
                   "hidden": "none — the pill is the message"}
    CAP_LABEL = {k: (_STYLE_NAME.get(v[0], v[0]) + (f" · y{v[1]}" if v[1] else ""))
                 for k, v in _cap.items()}
_m = re.search(r"^CAP_AT_BEAT = (\{.*?\})\n", src, re.S | re.M)
CAP_AT_BEAT = ast.literal_eval(re.sub(r"#.*", "", _m.group(1))) if _m else {}

W = json.loads((VID / "assets/transcript.json").read_text())

def line_for(a, b):
    return " ".join(w["text"].strip() for w in W if a <= w["start"] < b).strip()

# ── cues ─────────────────────────────────────────────────────────────────────
cues = []
cp = VID / "sfx-cues.txt"
if cp.exists():
    for ln in cp.read_text().splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        parts = ln.split()
        note = ln.split("#", 1)[1].strip() if "#" in ln else ""
        cues.append((float(parts[0]), parts[1], note))

frames = sorted((VID / "storyboard").glob("frame-*.png"))

cards = []
for i, (a, b, lay) in enumerate(BEATS):
    role, why = ROLES[i] if i < len(ROLES) else ("BEAT", "")
    lname, ldesc = LAYOUT_LABEL[lay]
    shot = f"storyboard/{frames[i].name}" if i < len(frames) else ""
    inbeat = [c for c in cues if a <= c[0] < b]
    cue_html = "".join(
        f'<li><b>{c[0]:.2f}</b> <code>{html.escape(c[1])}</code>'
        f'<span>{html.escape(c[2])}</span></li>' for c in inbeat) or "<li class='none'>—</li>"
    line = line_for(a, b) or "—"
    cards.append(f"""
<article class="beat lay-{lay}">
  <div class="shot"><img src="{shot}" loading="lazy" alt="">
    <span class="tc">{a:05.2f} – {b:05.2f}s · {b-a:.1f}s</span></div>
  <div class="meta">
    <div class="rolerow"><span class="role">{i+1:02d} · {html.escape(role)}</span>
      <span class="lay">{html.escape(lname)}</span></div>
    <p class="script">“{html.escape(line)}”</p>
    <p class="why">{why}</p>
    <dl>
      <dt>Frame</dt><dd>{html.escape(ldesc)}</dd>
      <dt>Captions</dt><dd>{html.escape(
        (lambda o: _STYLE_NAME.get(o[0], o[0]) + (f" · y{o[1]}" if o[1] else "")
         )(CAP_AT_BEAT[i]) + "  (per-beat override)" if i in CAP_AT_BEAT
        else CAP_LABEL[lay])}</dd>
    </dl>
    <div class="cues"><h4>Sound</h4><ul>{cue_html}</ul></div>
  </div>
</article>""")

seq = "".join(f'<span class="s s-{l}" style="flex:{b-a:.2f}"><i>{L}</i></span>'
              for (a, b, l), L in ((x, LAYOUT_LABEL[x[2]][0].split()[0]) for x in BEATS))

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>tp-0809 — storyboard</title>
<style>
:root{{--coral:#D97757;--coral-deep:#BD5D3A;--red:#E03A2F;--cream:#F0EDE4;--cream-card:#EAE6DA;
  --ink:#191817;--ink-soft:#6B6660;--dark:#201512;--on:#F7F3EF;
  --shadow:0 20px 60px rgba(0,0,0,.10),0 4px 14px rgba(0,0,0,.05)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--cream);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Inter",sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1240px;margin:0 auto;padding:0 26px 100px}}
header{{padding:56px 0 30px;border-bottom:3px solid var(--ink)}}
.eyebrow{{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--coral-deep);font-weight:700}}
h1{{font-size:clamp(34px,5vw,58px);line-height:1.03;margin:12px 0 14px;letter-spacing:-.03em;font-weight:800}}
.lede{{font-size:18px;max-width:74ch;color:var(--ink-soft)}} .lede strong{{color:var(--ink)}}
code{{font-family:ui-monospace,Menlo,monospace;font-size:.86em;background:var(--cream-card);
  padding:1px 6px;border-radius:5px}}

/* the rotation strip */
.seq{{display:flex;margin:26px 0 6px;border:2px solid var(--ink);border-radius:12px;overflow:hidden;height:52px}}
.seq .s{{display:flex;align-items:center;justify-content:center;border-right:2px solid var(--ink);
  font-size:9.5px;font-weight:800;letter-spacing:.06em;text-align:center;padding:0 2px}}
.seq .s:last-child{{border-right:0}}
.s-trans{{background:#E4DFD1}} .s-face{{background:var(--dark);color:var(--on)}}
.s-split{{background:var(--coral);color:#fff}} .s-bfull{{background:var(--ink);color:var(--on)}}
.s-cta{{background:#E8A38A}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--ink-soft);margin-bottom:8px}}
.legend b{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;
  vertical-align:-1px}}

/* beats */
.beat{{display:grid;grid-template-columns:300px 1fr;gap:26px;background:#fff;border-radius:20px;
  padding:20px;margin-top:22px;box-shadow:var(--shadow);align-items:start}}
@media(max-width:820px){{.beat{{grid-template-columns:1fr}}}}
.shot{{position:relative;border-radius:14px;overflow:hidden;background:var(--cream);
  border:1px solid rgba(0,0,0,.08)}}
.shot img{{width:100%;display:block;aspect-ratio:9/16;object-fit:cover}}
.tc{{position:absolute;left:8px;bottom:8px;background:rgba(25,24,23,.82);color:#fff;
  font:600 11px ui-monospace,Menlo,monospace;padding:4px 8px;border-radius:6px}}
.rolerow{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}}
.role{{font:800 13px/1 -apple-system,sans-serif;letter-spacing:.1em;text-transform:uppercase;
  background:var(--ink);color:var(--on);padding:7px 12px;border-radius:999px}}
.lay{{font:800 11px/1 -apple-system,sans-serif;letter-spacing:.1em;text-transform:uppercase;
  padding:6px 11px;border-radius:999px;background:var(--cream-card);color:var(--ink-soft)}}
.lay-face .lay{{background:var(--dark);color:var(--on)}}
.lay-split .lay{{background:var(--coral);color:#fff}}
.lay-bfull .lay{{background:var(--ink);color:var(--on)}}
.script{{font-family:Georgia,"Times New Roman",serif;font-size:21px;line-height:1.4;margin:0 0 10px;
  color:var(--ink)}}
.why{{margin:0 0 14px;font-size:14px;color:var(--ink-soft);max-width:72ch}}
dl{{display:grid;grid-template-columns:92px 1fr;gap:4px 14px;margin:0 0 14px;font-size:13px}}
dt{{color:var(--ink-soft);font-weight:700}} dd{{margin:0}}
.cues h4{{margin:0 0 6px;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--coral-deep)}}
.cues ul{{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px}}
.cues li{{font-size:12px;background:var(--cream);border-radius:8px;padding:5px 9px;
  display:flex;gap:7px;align-items:baseline}}
.cues li b{{font-family:ui-monospace,Menlo,monospace;color:var(--ink-soft)}}
.cues li span{{color:var(--ink-soft)}}
.cues li.none{{opacity:.5}}
.warn{{background:#FFF6F2;border-left:5px solid var(--red);border-radius:12px;padding:18px 22px;
  margin-top:26px}}
.black{{background:#fff;border-left:5px solid var(--ink);border-radius:12px;padding:20px 24px;
  margin-top:26px;box-shadow:var(--shadow)}}
.black h3{{margin:0 0 6px;font-size:17px}}
.black p{{margin:0 0 10px;font-size:14px;color:var(--ink-soft)}}
.black ol{{margin:0;padding-left:20px;font-size:14px;color:var(--ink-soft);line-height:1.55}}
.black li{{margin-bottom:7px}} .black b{{color:var(--ink)}}
.warn h3{{margin:0 0 6px;font-size:16px}} .warn p{{margin:0;font-size:14px;color:var(--ink-soft)}}
</style></head><body><div class="wrap">

<header>
  <div class="eyebrow">tp-0809 · storyboard · not rendered yet</div>
  <h1>Every frame, and the line it carries.</h1>
  <p class="lede">Rebuilt after your note. The first version rotated the <em>graphic</em> but not
  the <strong>frame</strong> — transparent and b-roll are the same camera treatment, so 14
  seconds read as one screen. Now the camera treatment itself changes every beat:
  <strong>transparent → full face → split → …</strong> and no two neighbours share one.
  Every image below is a real frame from the composition.</p>
  <div class="seq">{seq}</div>
  <div class="legend">
    <span><b style="background:#E4DFD1"></b>Transparent</span>
    <span><b style="background:#201512"></b>Full face</span>
    <span><b style="background:#D97757"></b>Split screen</span>
    <span><b style="background:#191817"></b>B-roll full</span>
    <span><b style="background:#E8A38A"></b>CTA</span>
    <span>· width = time on screen</span>
  </div>
</header>

{"".join(cards)}

<div class="black" id="cat">
  <h3>The concept catalog — what to show for what he says</h3>
  <p>New: <a href="/CONCEPTS.html"><b>CONCEPTS.html</b></a> — 13 concepts mined from all 22
  shipped scripts, each with the words that trigger it, what to show, what never to show, and
  live animating previews. The rule that drives it: <b>a product is shown as its real UI; a
  mascot is only ever the actor tending it, never the thing itself.</b> That is why beat 03 is
  now four real session windows instead of a sleeping mascot.</p>
</div>

<div class="black">
  <h3>Blacklist — applied to this cut</h3>
  <p>Written to <code>reference/BLACKLIST.md</code> so it survives the session. Four beats changed
  because of it.</p>
  <ol>
    <li><b>No small text, in any form.</b> No docs-page crops, no headline cards, no tables of
      body type — on screen or sourced from the web. If the only way to make the point is a wall
      of text, it belongs in the VO and the caption. Beats 04, 07, 10 and 12 were rebuilt as
      designed mascot scenes.</li>
    <li><b>No caption gets its own background band.</b> A caption sits on the frame, never on a
      strip pasted over it. Fixed on beat 06.</li>
    <li><b>The rotation is a change of CAMERA TREATMENT, not of graphic.</b> Transparent and
      b-roll-on-cream are the same frame; swapping the graphic inside it is not a change.</li>
    <li>No typeset text cards · no emojis · no people who aren't the subject · no stills of
      animated blocks · no silent layout changes · no new CTA · no grid plate · never shrink
      him · no captions on his body or over the media · never publish without approval.</li>
  </ol>
</div>

<div class="warn">
  <h3>⚠ Beat 10 — the script is factually wrong here</h3>
  <p>He says “you actually need to turn on the incoming messaging setting before you switch this
  on.” The docs say the opposite, verbatim: <strong>“When a session meets the requirements,
  messaging is on with nothing to enable.”</strong> <code>crossSessionInbound</code> is an
  override (accept / hold / refuse), not a prerequisite. Also: “across every computer you have”
  overstates it — across machines Claude can only <em>reply</em>, never start an exchange, and the
  real table on beat 7 says “Replies only” on screen while he says otherwise. And “there used to
  be a limit on how many helpers” isn’t supported anywhere in the docs. Mac/Linux/not-Windows and
  the “can’t run actions you never approved” line both check out exactly.</p>
</div>

</div></body></html>"""

(VID / "STORYBOARD.html").write_text(page)
print(f"wrote {VID/'STORYBOARD.html'} — {len(BEATS)} beats, {len(frames)} frames, {len(cues)} cues")
