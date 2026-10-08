#!/usr/bin/env python3
"""
THE CAPTION BOOK — every text treatment in the two reference reels, rebuilt.

Thirteen of them. Jad asked to see "all the captions", so this is all of them, not
just the four that made it into TYPE-ROLES.md on the first pass.

    python build.py && npx hyperframes render . -o out/captions.mp4
"""
import pathlib

W, H = 1080, 1920
OUT = pathlib.Path(__file__).parent / "index.html"

# Anton advance is ~0.46em per uppercase char; stamp every size, never leave it implicit.
def fit(word, cap=290, box=940, adv=0.46):
    return min(cap, int(box / (adv * len(word))))


def arc(sentence):
    """A whole line bent into the room's perspective, the way reel A does at 9.3s.

    Built as ONE SVG <textPath>, not per-character spans: the glyphs rotate smoothly
    along the curve instead of stepping, and it stays a single text node so the layout
    checker does not read every adjacent letter as an overlapping block.
    """
    return (
        '<svg class="arcsvg" viewBox="0 0 1080 1000" aria-label="%s">'
        '<defs><path id="arcp" d="M 10 360 A 1200 1200 0 0 1 1070 660" fill="none"/></defs>'
        '<text><textPath href="#arcp" startOffset="50%%" text-anchor="middle">%s</textPath></text>'
        '</svg>' % (sentence, sentence)
    )


# ── the thirteen treatments ────────────────────────────────────────────────────────────
# (label, seconds, html) — html is emitted inside the root, timed by the caller
BEATS = []


def beat(label, dur, html, ground="face"):
    BEATS.append({"label": label, "dur": dur, "html": html, "ground": ground})


# 1 · the word caption — the constant, the only one that is always on
beat("1 · WORD CAPTION · white caps at 72.9%, one word, word-synced", 3.0, """
  <div class="clip cap c-ws" data-start="{s0:.2f}" data-duration="0.9" data-track-index="30" style="top:1400px">EVERY</div>
  <div class="clip cap c-ws" data-start="{s1:.2f}" data-duration="0.9" data-track-index="31" style="top:1400px">SINGLE</div>
  <div class="clip cap c-ws" data-start="{s2:.2f}" data-duration="1.1" data-track-index="30" style="top:1400px">WORD</div>
""")

# 2 · emphasis outline, white
beat("2 · EMPHASIS OUTLINE · white — the neutral word", 2.3, """
  <div class="clip emph e-w" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="top:300px;font-size:{sz}px">THEM</div>
""".replace("{sz}", str(fit("THEM"))))

# 3 · emphasis outline, amber
beat("3 · EMPHASIS OUTLINE · amber — the pain word", 2.3, """
  <div class="clip emph e-a" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="top:340px;font-size:%dpx">MANUALLY</div>
""" % fit("MANUALLY"))

# 4 · name tag — the cast roll-call.
#     The UI owns the WHOLE FRAME and he is the cutout in the card. The text goes in the
#     shot's real negative space, found with scripts/find-empty-space.py, never a guessed y.
beat("4 · NAME TAG · the cast roll-call — the UI owns the FRAME, he is the cutout", 2.9, """
  <img class="clip uifull" src="assets/fork.png" data-start="{t:.2f}" data-duration="{d:.2f}"
       data-track-index="12" style="left:0px;top:0px;width:1080px;height:1920px" alt=""/>
  <div class="camcard"><video class="clip" id="c4" src="assets/recording.mp4" data-start="{t:.2f}"
       data-duration="{d:.2f}" data-media-start="23.33" data-track-index="13" muted playsinline></video></div>
  <video class="clip cutout" src="assets/person-alpha.webm" id="p4" data-start="{t:.2f}"
         data-duration="{d:.2f}" data-media-start="0" data-track-index="14" muted playsinline></video>
  <div class="clip emph e-w" data-start="{t2:.2f}" data-duration="{d2:.2f}" data-track-index="15"
       style="top:130px;font-size:150px">YURI</div>
""", ground="ui")

# 5 · payoff word — coral, FILLED
beat("5 · PAYOFF WORD · coral, FILLED — hook and CTA only, never an outline", 2.3, """
  <div class="clip payoff" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="top:300px;font-size:%dpx">FREE</div>
""" % fit("FREE"))

# 6 · the full title stack
beat("6 · TITLE STACK · pill + real square mark + marker line + payoff", 3.2, """
  <div class="clip tstack" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="10">
    <div class="tpill">Claude Code v2.0.0</div>
    <img class="tmark" src="assets/brand/claude-coral.svg" alt=""/>
    <div class="tline">the agent that actually</div>
    <div class="tword" style="font-size:208px">SHIPS</div>
  </div>
""")

# 7 · the handwritten marker line on its own
beat("7 · MARKER LINE · handwritten, white, all caps, never wraps", 2.2, """
  <div class="clip mline" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="top:430px">actually free</div>
""")

# 8 · the pill label on its own
beat("8 · PILL LABEL · the real product name, dark capsule, small", 2.2, """
  <div class="clip pillrow" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="top:300px"><span class="tpill">Adobe Premiere Pro 2026</span></div>
""")

# 9 · lime annotation — a claim, typed into the UI's own gutter
beat("9 · LIME CLAIM · typed INTO the UI's empty space — UI owns the FRAME", 3.0, """
  <img class="clip uifull" src="assets/fork.png" data-start="{t:.2f}" data-duration="{d:.2f}"
       data-track-index="12" style="left:0px;top:0px;width:1080px;height:1920px" alt=""/>
  <div class="camcard"><video class="clip" id="c9" src="assets/recording.mp4" data-start="{t:.2f}"
       data-duration="{d:.2f}" data-media-start="26.4" data-track-index="13" muted playsinline></video></div>
  <video class="clip cutout" src="assets/person-alpha.webm" id="p9" data-start="{t:.2f}"
         data-duration="{d:.2f}" data-media-start="3.07" data-track-index="14" muted playsinline></video>
  <div class="clip annot" data-start="{t2:.2f}" data-duration="{d2:.2f}" data-track-index="15"
       style="left:60px;top:52px;font-size:62px">FREE! +
OPEN SOURCE
NO SUBSCRIPTION</div>
""", ground="ui")

# 10 · lime reaction — one word. His pairs an emoji with it; ours does not (BLACKLIST #4).
beat("10 · LIME REACTION · one word — his has an emoji here, ours never does", 2.3, """
  <div class="clip annot areact" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="left:0px;top:560px;width:1080px;text-align:center;font-size:78px">RESPECT!</div>
""")

# 11 · pixel speech bubble — a word spoken BY an actor, in the actor's own resolution
beat("11 · PIXEL SPEECH BUBBLE · a word spoken by an actor, at the actor's resolution", 2.6, """
  <div class="clip bub" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="left:300px;top:380px">
    <svg class="bubsvg" viewBox="0 0 44 30" shape-rendering="crispEdges" aria-hidden="true">
      <path d="M2 0 H42 V2 H44 V18 H42 V20 H14 V22 H12 V24 H10 V26 H8 V24 H6 V22 H4 V20 H2 V18 H0 V2 H2 Z"
            fill="#ffffff" stroke="#111111" stroke-width="2"/>
    </svg>
    <span class="bubtx">VIDEOS</span>
  </div>
""")

# 12 · stacked repetition — the same word cascading, outline then solid, running off frame
beat("12 · STACKED REPETITION · the same word cascading — outline, then solid", 2.8, """
  <div class="clip emph e-w" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11"
       style="top:330px;font-size:230px">AGAIN</div>
  <div class="clip rep2" data-start="{t2:.2f}" data-duration="{d2:.2f}" data-track-index="12"
       style="top:560px;left:250px;font-size:230px">AGAIN</div>
  <div class="clip rep2" data-start="{t3:.2f}" data-duration="{d3:.2f}" data-track-index="13"
       style="top:790px;left:520px;font-size:230px">AGAIN</div>
""")

# 13 · the arced sentence — a whole line bent into the room's own perspective
beat("13 · ARCED SENTENCE · a line bent into the room's perspective (his runs off both edges)", 3.4, """
  <div class="clip arcwrap" data-start="{t:.2f}" data-duration="{d:.2f}" data-track-index="11">%s</div>
""" % arc("hours creating something,"))


# ── emit ───────────────────────────────────────────────────────────────────────────────
def render():
    body, labels, t = [], [], 0.0
    for b in BEATS:
        d = b["dur"]
        h = (b["html"]
             .replace("{t:.2f}", f"{t:.2f}").replace("{d:.2f}", f"{d:.2f}")
             .replace("{t2:.2f}", f"{t + 0.35:.2f}").replace("{d2:.2f}", f"{d - 0.35:.2f}")
             .replace("{t3:.2f}", f"{t + 0.70:.2f}").replace("{d3:.2f}", f"{d - 0.70:.2f}")
             .replace("{s0:.2f}", f"{t:.2f}").replace("{s1:.2f}", f"{t + 0.95:.2f}")
             .replace("{s2:.2f}", f"{t + 1.90:.2f}"))
        body.append(h)
        labels.append(f'  <div class="clip lbl" data-start="{t:.2f}" data-duration="{d:.2f}" '
                      f'data-track-index="40">{b["label"]}</div>')
        # the vignette only where a graphic needs a dark photographic ground
        if b["ground"] == "face":
            labels.append(f'  <div class="clip vig" data-start="{t:.2f}" data-duration="{d:.2f}" '
                          f'data-track-index="2"></div>')
        t += d

    total = round(t + 0.4, 2)
    cam = (f'  <video class="clip cam" id="cam0" src="assets/recording.mp4" data-start="0" '
           f'data-duration="{total}" data-media-start="4.2" data-track-index="1" muted playsinline></video>')

    html = TEMPLATE.replace("__TOTAL__", str(total)) \
                   .replace("__CAM__", cam) \
                   .replace("__BODY__", "\n".join(body)) \
                   .replace("__LABELS__", "\n".join(labels))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}  {len(BEATS)} treatments  {total}s")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>captions</title>
<link rel="stylesheet" href="tokens.css"/>
<style>
  html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}
  #root{position:relative;width:1080px;height:1920px;overflow:hidden}
  .cam{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
  /* ── WHEN A REAL UI IS THE BEAT, IT OWNS THE WHOLE FRAME ───────────────────────────
     1080x1920, object-fit:COVER, corner to corner. Our page shots are ALREADY shot at
     1080x1920 by shoot-page-9x16.py — putting one in a shorter box with object-fit:contain
     letterboxes it to ~664px wide and produces the "small screenshot floating in the frame"
     look, with a hard edge across his face. That is the bug this class exists to prevent. */
  .uifull{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;
    display:block}
  /* and HE goes on top of it in the CARD at the bottom — not full height over the UI,
     which just hides the thing the beat is about. Card measured off reel B:
     left 10.6% · width 79.7% · top 59.5% · radius 3.6%. Two layers from one source:
     the raw take clipped by the card, and the matte over it UNCLIPPED so the head
     breaks the card's top edge. Camera scale 0.80 — it must FILL the 861px card. */
  .camcard{position:absolute;left:114px;top:1143px;width:861px;height:777px;
    overflow:hidden;border-radius:39px}
  .camcard video{position:absolute;left:-6px;top:-692px;width:864px;height:1536px;
    object-fit:cover}
  .cutout{position:absolute;left:108px;top:451px;width:864px;height:1536px;
    object-fit:contain;display:block}
  .med{position:absolute;display:block;object-fit:contain}

  /* darkening on the MEDIA — BLACKLIST #3 allows this and bans a band behind the text */
  .vig{position:absolute;left:0;top:0;width:1080px;height:1080px;
    background:linear-gradient(180deg,rgba(12,9,8,.60) 0%,rgba(12,9,8,.40) 46%,rgba(12,9,8,0) 100%)}

  /* 1 · WORD CAPTION — the only text that is always on */
  .cap{position:absolute;left:0;width:1080px;text-align:center}
  .c-ws{font:900 96px var(--font-heavy);color:#fff;text-transform:uppercase;letter-spacing:-.02em;
    filter:drop-shadow(0 4px 14px rgba(0,0,0,.55))}

  /* 2-4 · EMPHASIS OUTLINE — hollow, bloomed, screened. White and amber only. */
  .emph{position:absolute;left:0;width:1080px;text-align:center;
    font-family:var(--font-display-heavy);line-height:1;letter-spacing:.012em;
    text-transform:uppercase;
    color:var(--emph-fill);-webkit-text-fill-color:var(--emph-fill);
    -webkit-text-stroke-width:var(--emph-stroke);mix-blend-mode:screen}
  .e-w{-webkit-text-stroke-color:var(--emph-white);filter:var(--glow-white)}
  .e-a{-webkit-text-stroke-color:var(--emph-amber);filter:var(--glow-amber)}

  /* 5 · PAYOFF WORD — coral, filled */
  .tword,.payoff{font-family:var(--font-display-heavy);line-height:.9;text-transform:uppercase;
    color:var(--display-coral);letter-spacing:.008em;
    filter:drop-shadow(0 8px 30px rgba(0,0,0,.55))}
  .payoff{position:absolute;left:0;width:1080px;text-align:center}

  /* 6 · TITLE STACK */
  .tstack{position:absolute;left:0;top:86px;width:1080px;
    display:flex;flex-direction:column;align-items:center;gap:16px}
  .tpill{font:400 38px var(--font-ui);color:#fff;background:rgba(15,12,10,.5);
    padding:11px 32px;border-radius:var(--r-pill);letter-spacing:.01em}
  .tmark{width:212px;height:212px;object-fit:contain;
    filter:drop-shadow(0 10px 26px rgba(0,0,0,.5))}
  .tline{font-family:var(--font-marker);font-size:64px;color:#fff;letter-spacing:.02em;
    text-transform:uppercase;white-space:nowrap;
    filter:drop-shadow(0 5px 16px rgba(0,0,0,.6))}

  /* 7 · MARKER LINE on its own */
  .mline{position:absolute;left:0;width:1080px;text-align:center;
    font-family:var(--font-marker);font-size:78px;color:#fff;letter-spacing:.02em;
    text-transform:uppercase;white-space:nowrap;
    filter:drop-shadow(0 5px 16px rgba(0,0,0,.6))}

  /* 8 · PILL LABEL on its own */
  .pillrow{position:absolute;left:0;width:1080px;text-align:center}

  /* 9-10 · LIME ANNOTATION */
  .annot{position:absolute;font-family:var(--font-pixel);font-weight:700;
    color:var(--annot-lime);filter:var(--glow-lime);line-height:1.45;letter-spacing:.02em;
    white-space:pre}
  .areact{color:var(--annot-lime-soft)}

  /* 11 · PIXEL SPEECH BUBBLE — drawn at the actor's resolution, stepped edges and all */
  .bub{position:absolute;width:480px;height:328px}
  .bubsvg{position:absolute;left:0;top:0;width:480px;height:328px;
    filter:drop-shadow(0 8px 22px rgba(0,0,0,.45))}
  .bubtx{position:absolute;left:0;top:74px;width:480px;text-align:center;
    font-family:var(--font-pixel);font-weight:700;font-size:64px;color:#111;
    letter-spacing:.02em}

  /* 12 · STACKED REPETITION — the solid pass under the outline */
  .rep2{position:absolute;width:1080px;
    font-family:var(--font-display-heavy);line-height:1;letter-spacing:.012em;
    text-transform:uppercase;color:#fff;
    filter:drop-shadow(0 6px 20px rgba(0,0,0,.5))}

  /* 13 · ARCED SENTENCE — each glyph rotated onto a circle, stamped at build time */
  .arcwrap{position:absolute;left:0;top:260px;width:1080px;height:1000px}
  .arcsvg{width:1080px;height:1000px;overflow:visible;
    filter:drop-shadow(0 4px 16px rgba(0,0,0,.55))}
  .arcsvg text{font:600 80px var(--font-ui);fill:#fff;letter-spacing:.005em}

  .lbl{position:absolute;left:40px;top:1810px;width:1000px;text-align:center;
    font:500 30px var(--font-mono);color:#fff;letter-spacing:.05em;line-height:1.4;
    filter:drop-shadow(0 3px 10px rgba(0,0,0,.95))}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-no-timeline data-start="0" data-duration="__TOTAL__"
     data-width="1080" data-height="1920" data-fps="30">
__CAM__
__LABELS__
__BODY__
</div>
</body>
</html>
"""

if __name__ == "__main__":
    render()
