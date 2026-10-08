#!/usr/bin/env python3
"""
tp-0925b — STYLE: persa (full bleed), NO GRADE.  "Google just released new AI voices."
Gemini 3.8 Flash TTS (blog.google, 2026-09-23): voice design from one sentence, saved voices,
2,000+ voices, 100+ languages, two speakers, voice replication behind a consent recording.
Opens on a 41s live demo: "Sarah from Phaselink" calls him — an AI voice. CTA keyword NARRATOR.

    python3 build.py            # writes index.html (preview) + layers/mid + layers/fg
    (layers render --format mov, then composite.py lays them on the UNTOUCHED camera)

── SOURCING (SOURCING.html, 2026-09-25) ──
  CALL  our in-call screen (work/call.html, rec-call.py) — waveform = the take's real envelope,
        lit only while Sarah talks. The ONLY built surface.
  P N L W R  Google DeepMind's launch film (YouTube FL6mI_Br-mc), cut by cut-film.sh
  K     blog.google's launch key art          D  his AI Studio: "Voice Design runs on the paid tier"

── FACT-CHECK — he chose: keep the VO, correct in captions + annotations ──
  "came out September 22nd"      ✗ blog.google dated Sept 23      → caption 23RD, pill SEPT 23
  "it's on Google's free tier"   ½ TTS free until Dec 31 (pricing page) BUT Voice Design is
                                   paid-tier in AI Studio            → caption FREE TTS / DESIGN PAID
  "30 studio voices"             ✗ 2,000+ ("from 30 original voices") → caption 2,000+
  "more than 130 languages"      ✗ 100+                              → caption 100+
  "two speakers in one clip"     ✓ native two-speaker staging
  "copy your real voice… consent recording first"  ✓ verbal consent recording required
"""
import json, pathlib, re

D = pathlib.Path(__file__).parent
W, H = 1080, 1920
DUR = 95.80
FPS = 30
NAME = "tp-0925b"

CAP_Y = 1400
GEO = json.loads((D / "assets/geometry.json").read_text(encoding="utf-8"))
CARD = dict(left=GEO["card"]["left"], top=GEO["card"]["top"], w=GEO["card"]["width"],
            h=GEO["card"]["height"], r=GEO["card"]["radius"])
CAMS = GEO["cam"]
ACTS = GEO["acts"]
HEAD = GEO.get("head_on_screen", {})
KISS = 22
CALL0 = 4.60           # src/clips/CALL.mp4 starts at video time 4.60

words = json.loads((D / "assets/transcript.json").read_text(encoding="utf-8"))
for w in words:
    w["text"] = w["text"].strip(" ,.?!").upper()
# ASR + FACT fixes, keyed by the word's own onset (never by string)
FIX = {5.76: "JAD", 51.92: "23RD", 53.52: "GOOGLE'S", 54.00: "FREE TTS", 54.32: "DESIGN PAID",
       74.00: "2,000+", 76.40: "100+", 89.44: "CONSENT"}
for w in words:
    k = round(w["start"], 2)
    if k in FIX:
        w["text"] = FIX[k]
missing = set(FIX) - {round(w["start"], 2) for w in words}
assert not missing, f"FIX keys match no word onset: {missing}"
M = "src/marks/"


def act_of(t):
    for s, e, k in ACTS:
        if s <= t < e:
            return k
    return ACTS[-1][2]


def emph_size(word, cap=190, box=960, adv=0.516):
    """Anton's advance on caps is 0.516 em MEASURED (tp-0921c)."""
    return min(cap, int(box / (adv * len(word))))


def marker_size(txt, cap=84, box=1000, adv=0.700):
    return min(cap, int(box / (adv * len(txt))))


def top_for(size, beat_i, kiss=KISS):
    h = HEAD.get(str(beat_i), 400 if BEATS[beat_i][2] != "ui" else 974)
    return max(24, h + kiss - size)


HOLE = ("-webkit-mask-image:url(&quot;data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
        "width='1080' height='1920'><path fill-rule='evenodd' d='M0 0H1080V1920H0Z "
        f"M{CARD['left']+CARD['r']} {CARD['top']}H{CARD['left']+CARD['w']-CARD['r']}"
        f"A{CARD['r']} {CARD['r']} 0 0 1 {CARD['left']+CARD['w']} {CARD['top']+CARD['r']}"
        f"V{1920-CARD['r']}A{CARD['r']} {CARD['r']} 0 0 1 {CARD['left']+CARD['w']-CARD['r']} 1920"
        f"H{CARD['left']+CARD['r']}A{CARD['r']} {CARD['r']} 0 0 1 {CARD['left']} {1920-CARD['r']}"
        f"V{CARD['top']+CARD['r']}A{CARD['r']} {CARD['r']} 0 0 1 {CARD['left']+CARD['r']} {CARD['top']}Z'/>"
        "</svg>&quot;);-webkit-mask-size:1080px 1920px")

TRK = [900]


def track():
    TRK[0] += 1
    return TRK[0]


def el(cls, at, dur, style, inner="", tag="div", extra=""):
    return (f'  <{tag} class="clip {cls}" data-start="{at:.2f}" data-duration="{max(dur,0.04):.2f}" '
            f'data-track-index="{track()}" data-layout-allow-occlusion {extra} '
            f'style="{style}">{inner}</{tag}>')


def ease(name, dur, delay, fill="both", e="cubic-bezier(.16,1,.3,1)"):
    return f"animation:{name} {dur}s {e} {delay:.2f}s {fill}"


OVER = "cubic-bezier(.34,1.56,.64,1)"


def pill(at, dur, x, y, txt, kind="", center=False):
    style = (f"left:0;width:1080px;text-align:center;top:{y}px;" if center else f"left:{x}px;top:{y}px;")
    return el("pl" + (f" {kind}" if kind else "") + (" ctr" if center else ""), at, dur,
              style + ease("pop" if kind != "stop" else "stamp", .26, 0, e=OVER), f"<span>{txt}</span>")


def lime(at, dur, y, txt, size=60):
    return el("lime", at, dur, f"left:0;width:1080px;text-align:center;top:{y}px;font-size:{size}px;"
              + ease("pop", .22, 0, e=OVER), txt)


# ── per-beat surfaces + annotations ─────────────────────────────────────────────────────────
def anim_call_end(s, e):
    # the dark ground above Sarah's avatar is the call screen's own negative space
    return [lime(43.84, e - 43.84, 40, "30&ndash;45 MIN", 64)]


def anim_key(s, e):
    # blog.google's launch key art, fitted to width over its own sky
    return [el("apic feather", s, e - s, "left:0;top:430px;width:1080px;height:769px;" + ease("tin", .40, 0),
               '<img src="src/blog/hero-crop.png" alt=""/>'),
            pill(51.36, e - 51.36, 0, 1260, "SEPT 23, 2026", "stop", center=True)]


def anim_paid(s, e):
    return [el("apic", s, e - s, "left:20px;top:240px;width:1040px;height:197px;" + ease("tin", .40, 0),
               '<img src="src/aistudio/paid-tier-crop.png" alt=""/>'),
            lime(53.52, e - 53.52, 520, "FREE TTS", 76),
            lime(54.00, e - 54.00, 620, "VOICE DESIGN = PAID", 60)]


def anim_prompt(s, e):
    return [pill(57.60, e - 57.60, 0, 760, "ONE SENTENCE", "ink", center=True)]


def anim_saved(s, e):
    return [pill(63.84, e - 63.84, 0, 1040, "SAVED", "stop", center=True)]


def anim_library(s, e):
    return [pill(74.40, e - 74.40, 0, 60, "2,000+ VOICES", "stop", center=True),
            pill(76.40, e - 76.40, 0, 180, "100+ LANGUAGES", "ink", center=True)]


def anim_speakers(s, e):
    return [pill(78.48, e - 78.48, 0, 1040, "2 SPEAKERS &middot; 1 CLIP", "stop", center=True),
            pill(81.12, e - 81.12, 0, 1160, "PODCAST", "ink", center=True)]


def anim_consent(s, e):
    return [pill(88.72, e - 88.72, 0, 70, "CONSENT FIRST", "stop", center=True)]


def call(s, e, mstart=None, **k):
    """mstart defaults to the live call's own clock; the callback replays a moment of it."""
    ms = s - CALL0 if mstart is None else mstart
    assert 0 <= ms and ms + (e - s) <= 41.6, f"CALL.mp4 has no footage at {ms:.2f}+{e-s:.2f}"
    return (s, e, "ui", dict(plate="#10131b", vid="CALL", mstart=ms, **k))


BEATS = [
    # 00 HOOK — "Google just released new AI voices and you can design your own with a single sentence."
    (0.00, 4.60, "face", dict(
        gmark=(0.16, 0.96, "google.png"),
        emphs=[("AI VOICES", 1.12, 1.48, "c", 190, None), ("ONE SENTENCE", 3.92, 0.68, "c", 190, None)],
        mline=[("DESIGN YOUR OWN", 2.60, 1.28, 80)])),
    # 01-10 THE DEMO — Sarah's lines on the call screen, his on his face
    call(4.60, 6.40),
    (6.40, 8.10, "face", dict()),
    call(8.10, 17.30),
    (17.30, 20.70, "face", dict(emphs=[("2 MINUTES AGO", 19.84, 0.86, "s", 190, None)])),
    call(20.70, 26.40),
    (26.40, 30.00, "face", dict(emphs=[("LEADS", 26.40, 1.48, "c", 190, None),
                                       ("ADS", 27.92, 0.56, "s", 190, None)],
                                mline=[("AND MARKETING", 28.48, 1.52, 80)])),
    call(30.00, 34.90),
    (34.90, 39.90, "face", dict(mline=[("BOOK A CALL?", 38.90, 1.00, 84)])),
    call(39.90, 46.10, callend=True),
    # 10 THE REVEAL — "Alright, so you've seen it. It's called Gemini 3.8 Flash TTS."
    (46.10, 50.50, "face", dict(
        mline=[("YOU'VE SEEN IT", 46.64, 1.24, 84)],
        gmark=(47.92, 1.36, "gemini.png"),
        emphs=[("FLASH TTS", 49.28, 1.22, "c", 190, None)])),
    # 11 K — the launch art, the real date
    (50.50, 52.85, "broll", dict(plate="#c4e1fe", key=True)),
    # 12 D — "free tier": AI Studio's own paid-tier gate
    (52.85, 54.85, "ui", dict(plate="#191919", paid=True)),
    # 13 "Here's why it matters for your business."
    (54.85, 56.90, "face", dict(emphs=[("YOUR BUSINESS", 56.24, 0.66, "c", 190, None)])),
    # 14 P — the Voice Design prompt typed
    (56.90, 62.50, "ui", dict(plate="#cfe6fb", vid="P", prompt=True)),
    # 15 N — "It builds the voice and saves it."
    (62.50, 64.50, "broll", dict(plate="#cee9fa", vid="N", saved=True)),
    # 16 "So you can use this exact same one every time,"
    (64.50, 67.30, "face", dict(emphs=[("SAME ONE", 65.52, 1.04, "s", 190, None),
                                       ("EVERY TIME", 66.56, 0.74, "c", 190, None)])),
    # 17 "like the one that we just saw" — back on the call
    call(67.30, 69.30, mstart=17.40),     # Sarah mid-pitch (video 22.0)
    # 18 "your explainer videos, and your product demos all sound like one brand."
    (69.30, 73.30, "face", dict(mline=[("EXPLAINER VIDEOS", 69.52, 1.44, 80),
                                       ("PRODUCT DEMOS", 70.96, 1.52, 80)],
                                emphs=[("ONE BRAND", 72.48, 0.82, "c", 190, None)])),
    # 19 L — the voice library: 2,000+, 100+ (the VO says 30 and 130)
    (73.30, 78.40, "ui", dict(plate="#6d7a88", vid="L", library=True)),
    # 20 W — two speakers, podcast
    (78.40, 84.40, "broll", dict(plate="#aadffd", vid="W", speakers=True)),
    # 21 R — voice replication behind a consent recording
    (84.40, 90.50, "ui", dict(plate="#eef4fb", vid="R", mstart=0.0, consent=True)),
    # 22 CTA — the old one (BLACKLIST #9), keyword NARRATOR
    (90.50, DUR, "cta", dict()),
]

ANIMS = {"callend": anim_call_end, "key": anim_key, "paid": anim_paid, "prompt": anim_prompt,
         "saved": anim_saved, "library": anim_library, "speakers": anim_speakers, "consent": anim_consent}

for i in range(1, len(BEATS)):
    assert BEATS[i][2] != BEATS[i - 1][2], f"beats {i-1},{i} share a treatment"
    assert abs(BEATS[i][0] - BEATS[i - 1][1]) < 1e-6, f"gap/overlap at beat {i}"

TYPE_KEYS = ("emphs", "mline", "gmark")


def clipify(lines):
    """Animated CHILDREN need their own data-start (css-delay-needs-own-data-start).
    ⚠ The duration is taken from the GROUP OPENER only (clipify-timing-reference)."""
    tr = [100]
    last = [None]
    out = []
    for ln in lines:
        mm0 = re.search(r'class="clip grp[^"]*" data-start="([\d.]+)" data-duration="([\d.]+)"', ln)
        if mm0:
            last[0] = mm0
        m = last[0]

        def fix(mm):
            tag, cls, st = mm.group(1), mm.group(2), mm.group(3)
            tr[0] += 1
            dur = float(m.group(1)) + float(m.group(2)) - float(st) if m else 1.0
            return (f'<{tag} class="clip {cls}" data-start="{st}" data-duration="{dur:.2f}" '
                    f'data-track-index="{tr[0]}"')
        ln = re.sub(r'<(\w+) class="((?!clip)[^"]*)" data-start="([\d.]+)"(?! data-duration)', fix, ln)
        out.append(ln)
    return out


def grp(at, dd):
    return (f'  <div class="clip grp" data-start="{at:.2f}" data-duration="{dd:.2f}" '
            f'data-track-index="{track()}" data-layout-allow-occlusion '
            f'style="left:0;top:0;width:0;height:0"></div>')


def build():
    cam, mid, cut, fg = [], [], [], []

    for i, (s, e, kind, p) in enumerate(BEATS):
        d = e - s
        clip = f'data-start="{s:.2f}" data-duration="{d:.2f}"'

        if kind == "face":
            cam.append(f'  <video class="clip cam" id="cr{i}" src="assets/recording.mp4" {clip} '
                       f'data-media-start="{s:.2f}" data-track-index="1" muted playsinline></video>')

        if kind == "ui":
            mid.append(f'  <div class="clip uifull" id="u{i}" {clip} data-track-index="2" '
                       f'style="background:{p["plate"]};{HOLE}"></div>')
            if p.get("vid"):
                mid.append(f'  <video class="clip uivid" id="v{i}" src="src/clips/{p["vid"]}.mp4" {clip} '
                           f'data-media-start="{p.get("mstart",0):.2f}" data-track-index="3" muted playsinline></video>')
            cam.append(f'  <div class="camcard c-{act_of(s)}" data-layout-allow-overflow>'
                       f'<video class="clip" id="cc{i}" src="assets/recording.mp4" {clip} '
                       f'data-media-start="{s:.2f}" data-track-index="1" muted playsinline></video></div>')
            cut.append(f'  <video class="clip cutout cu-{act_of(s)}" id="cf{i}" '
                       f'src="assets/person.webm" {clip} '
                       f'data-media-start="{s:.2f}" data-track-index="4" muted playsinline></video>')

        elif kind == "broll":
            # B-ROLL FULL — the media owns all 1920 rows, no camera at all
            mid.append(f'  <div class="clip uifull" id="u{i}" {clip} data-track-index="2" '
                       f'style="background:{p["plate"]}"></div>')
            if p.get("vid"):
                mid.append(f'  <video class="clip brvid" id="v{i}" src="src/clips/{p["vid"]}.mp4" {clip} '
                           f'data-media-start="{p.get("mstart",0):.2f}" data-track-index="3" muted playsinline></video>')

        elif kind == "cta":
            mid.append(f'  <div class="clip creamplate" id="cp{i}" {clip} data-track-index="2"></div>')
            cam.append(f'  <div class="cardwrap" data-layout-allow-overflow>'
                       f'<video class="clip" id="ccta" src="assets/recording.mp4" {clip} '
                       f'data-media-start="{s:.2f}" data-track-index="1" muted playsinline></video></div>')
            fg.append(f'  <div class="clip ctapanel" id="cta" data-start="{s + 0.10:.2f}" '
                      f'data-duration="{d - 0.10:.2f}" data-track-index="9">')
            fg.append('    <div class="ctalines"><div class="l1" id="cta_l1">COMMENT</div>'
                      '<div class="l2" id="cta_l2">narrator</div></div>')
            fg.append('    <div class="arrow" id="cta_ar"><i></i></div>')
            fg.append('  </div>')

        if kind in ("ui", "broll"):
            for k, fn in ANIMS.items():
                if p.get(k):
                    mid.append(grp(s, d))
                    mid += fn(s, e)

        # ── the real square mark, on the word, behind his head
        if p.get("gmark"):
            at, dd, png = p["gmark"]
            mid.append(grp(at, dd))
            mt = top_for(250, i)
            mid.append(el("tmark", at, dd, f"left:415px;top:{mt}px;width:250px;height:250px;"
                          + ease("stamp", .30, 0, e=OVER), f'<img src="{M}{png}" alt=""/>'))

        for word, at, dur, col, size, top in p.get("emphs", []):
            size = min(size, emph_size(word)) if size else emph_size(word)
            top = top if top is not None else top_for(size, i)
            mid.append(el(f"emfill ef-{col}", at, dur, f"top:{top}px;font-size:{size}px", word))

        for txt, at, dur, fs in p.get("mline", []):
            fs = marker_size(txt, fs)
            mid.append(el("mline", at, dur, f"top:{top_for(fs, i, -4)}px;font-size:{fs}px", txt))

        if kind == "face" and any(p.get(k) for k in TYPE_KEYS):
            cut.append(f'  <video class="clip cutfull" id="of{i}" src="assets/person.webm" {clip} '
                       f'data-media-start="{s:.2f}" data-track-index="8" muted playsinline></video>')

    # ── CAPTIONS — one style, one word, one line at 1400. Dropped for the CTA.
    cta_in = BEATS[-1][0]
    n = 0
    for wi, w in enumerate(words):
        if w["start"] >= cta_in:
            break
        nxt = words[wi + 1]["start"] if wi + 1 < len(words) else cta_in
        lim = nxt - w["start"]
        dd = max(0.12, min(w["end"] - w["start"], lim - 0.02, cta_in - w["start"]))
        if dd + 0.02 < lim < 0.5:
            dd = lim - 0.02
        dd = max(0.05, min(dd, lim - 0.02))
        fs = f"font-size:{min(96, int(1000 / (0.62 * len(w['text']))))}px;" if len(w["text"]) > 10 else ""
        fg.append(f'  <div class="clip cap c-ws" id="c{n}" data-start="{w["start"]:.2f}" '
                  f'data-duration="{dd:.2f}" data-track-index="{30 + n % 2}" '
                  f'style="top:{CAP_Y}px;{fs}">{w["text"]}</div>')
        n += 1

    def page(body, title, bg, prefix=""):
        b = "\n".join(body)
        out = (TPL.replace("__BODY__", b).replace("__DUR__", f"{DUR:.2f}").replace("__TITLE__", title)
                  .replace("__BG__", bg).replace("__TOK__", prefix + "tokens.css")
                  .replace("__FONT__", prefix + "assets/fonts/InstrumentSerif.ttf")
                  .replace("__CARDL__", str(CARD["left"])).replace("__CARDT__", str(CARD["top"]))
                  .replace("__CARDW__", str(CARD["w"])).replace("__CARDH__", str(CARD["h"]))
                  .replace("__CARDR__", str(CARD["r"]))
                  .replace("__CAMFULL_T__", str(GEO["full_top"])))
        css = []
        for k, c in CAMS.items():
            css.append(f".camcard.c-{k} video{{left:{c['left']-CARD['left']}px;"
                       f"top:{c['top']-CARD['top']}px;width:{c['width']}px;height:{c['height']}px}}")
            css.append(f".cutout.cu-{k}{{left:{c['left']}px;top:{c['top']}px;"
                       f"width:{c['width']}px;height:{c['height']}px}}")
        return out.replace("__ACTCSS__", "\n  ".join(css))

    mid = clipify(mid)
    (D / "index.html").write_text(page(cam + mid + cut + fg, NAME, "#000"), encoding="utf-8")
    for name, body in (("mid", mid), ("fg", fg)):
        lp = D / "layers" / name
        lp.mkdir(parents=True, exist_ok=True)
        for sub in ("assets", "src", "tokens.css"):
            link = lp / sub
            if not link.exists():
                link.symlink_to(D / sub)
        (lp / "index.html").write_text(page(body, f"{NAME} {name}", "transparent"), encoding="utf-8")
        (lp / "hyperframes.json").write_text((D / "hyperframes.json").read_text(encoding="utf-8"), encoding="utf-8")
    json.dump([(s, e, k) for (s, e, k, _) in BEATS], open(D / "beats.json", "w", encoding="utf-8"))
    json.dump([i for i, (s, e, k, p) in enumerate(BEATS)
               if k == "face" and any(p.get(x) for x in TYPE_KEYS)],
              open(D / "assets/face_type.json", "w", encoding="utf-8"))
    print(f"wrote index.html + layers — {len(BEATS)} beats, {n} captions")


TPL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>__TITLE__</title>
<link rel="stylesheet" href="__TOK__"/>
<style>
  @font-face{font-family:"InstrumentSerif";src:url("__FONT__") format("truetype");font-display:block}
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:1080px;height:1920px;overflow:hidden;background:__BG__}
  #root{position:relative;width:1080px;height:1920px;overflow:hidden;background:__BG__}

  /* ── the camera. Here for the PREVIEW only; the render path never sends it through the
     browser (browser-render-tints-camera) — composite.py lays these layers onto the
     untouched recording in ffmpeg. ── */
  .cam{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
  .uifull{position:absolute;left:0;top:0;width:1080px;height:1920px}
  .camcard{position:absolute;left:__CARDL__px;top:__CARDT__px;width:__CARDW__px;
    height:__CARDH__px;border-radius:__CARDR__px;overflow:hidden}
  .camcard video{position:absolute}
  .cutout{position:absolute}
  .cutfull{position:absolute;left:0;top:0;width:1080px;height:1920px}
  __ACTCSS__

  /* ── motion vocabulary ──
     Every SECOND animation on an element is `to`-only ON PURPOSE. A `to`-only keyframe
     synthesises its 0% from the underlying value, which already carries the entrance's
     backwards fill; an explicit from{} OVERRIDES that and paints the element from frame 1
     (entrance-from-state-paints-early / second-animation-paints-early). ── */
  @keyframes tin{from{opacity:0;transform:translateY(26px) scale(.90)}to{opacity:1;transform:none}}
  @keyframes nodein{from{opacity:0;transform:translateY(38px) scale(.86)}to{opacity:1;transform:none}}
  @keyframes slidein{from{opacity:0;transform:translateX(-46px)}to{opacity:1;transform:none}}
  @keyframes pop{from{opacity:0;transform:scale(.70)}to{opacity:1;transform:none}}
  @keyframes stamp{from{opacity:0;transform:scale(1.55) rotate(-4deg)}to{opacity:1;transform:none}}
  @keyframes fadein{from{opacity:0}to{opacity:1}}
  @keyframes growy{from{opacity:0;transform:scaleY(0)}to{opacity:1;transform:scaleY(1)}}
  @keyframes drawflat{from{opacity:0;transform:scaleX(0)}8%{opacity:1}to{opacity:1;transform:scaleX(1)}}
  @keyframes typein{from{width:0}to{width:100%}}
  /* the card turning over. The back arrives edge-on and lands flat — the front is gone by
     then, so no two faces are ever lit at once. */
  @keyframes flipin{from{opacity:0;transform:perspective(1400px) rotateY(-96deg)}
    40%{opacity:1}to{opacity:1;transform:perspective(1400px) rotateY(0)}}

  /* ── Google's footage owns the top of the frame (ui) or all of it (broll) ── */
  .uivid{position:absolute;left:0;top:0;width:1080px;height:1143px;object-fit:cover;object-position:50% 0}
  .brvid{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
  .feather{-webkit-mask-image:linear-gradient(180deg,transparent 0,#000 14%,#000 86%,transparent 100%)}
  .apic{position:absolute}
  .apic img{width:100%;height:100%;display:block}
  .lime{position:absolute;font-family:var(--font-pixel);color:var(--annot-lime);filter:var(--glow-lime);white-space:nowrap;letter-spacing:.02em}

  @keyframes rise{from{opacity:0;transform:translateY(40px);filter:blur(14px)}to{opacity:1;transform:none;filter:blur(0)}}
  @keyframes drop{from{opacity:0;transform:translateY(-160px) scale(.8)}to{opacity:1;transform:none}}

  .tmark{position:absolute}
  .tmark img{width:100%;height:100%;object-fit:contain;display:block;
    filter:drop-shadow(0 10px 30px rgba(0,0,0,.35))}

  /* ── pills on light UI. Ink = pointing at the thing; coral = the claim ── */
  .pl{position:absolute;white-space:nowrap}
  .pl span{display:inline-block;font:800 44px var(--font-ui);letter-spacing:.05em;
    border-radius:999px;padding:16px 34px;color:#fff;background:var(--an-ink);
    box-shadow:0 14px 34px rgba(17,24,39,.18)}
  .pl.step span{font:400 52px var(--font-display-heavy);letter-spacing:.04em;padding:12px 30px;
    background:var(--display-coral);filter:var(--glow-coral);box-shadow:none}
  .pl.stop span{background:var(--display-coral);box-shadow:0 0 44px rgba(225,42,43,.45)}
  .chip{position:absolute;font:800 40px var(--font-ui);color:var(--an-ink);width:330px;text-align:center;
    background:var(--an-block);border-radius:999px;padding:16px 0;letter-spacing:.08em;white-space:nowrap}
  .stampbig{position:absolute;font:400 104px var(--font-display-heavy);color:var(--display-coral);
    letter-spacing:.01em;white-space:nowrap;filter:var(--glow-coral)}

  /* ── the sample review + reply (DESIGNED — no platform chrome) ── */
  .rcard{position:absolute;background:var(--an-paper);border:3px solid var(--an-line);border-radius:34px;
    box-shadow:0 30px 80px rgba(17,24,39,.10)}
  .ravatar{position:absolute;width:92px;height:92px;border-radius:50%;background:var(--an-block);
    font:800 46px/92px var(--font-ui);color:var(--an-mute);text-align:center}
  .rname{position:absolute;font:800 40px var(--font-ui);color:var(--an-ink);white-space:nowrap}
  .rstar{position:absolute;font:400 62px/1 var(--font-ui);color:var(--an-line)}
  .rstar.on{color:var(--display-coral);filter:var(--glow-coral)}
  .rtext{position:absolute;font:400 58px/1.12 "InstrumentSerif",serif;color:var(--an-ink)}
  .arrowdn{position:absolute;width:48px;height:70px}
  .arrowdn i{position:absolute;left:19px;top:0;width:10px;height:52px;background:var(--an-ink);border-radius:5px}
  .arrowdn i::after{content:"";position:absolute;left:-12px;top:30px;width:26px;height:26px;
    border-right:10px solid var(--an-ink);border-bottom:10px solid var(--an-ink);transform:rotate(45deg);border-radius:3px}
  .reply{position:absolute;background:var(--an-ink);border-radius:34px;padding:36px 44px 40px}
  .reply b{display:block;font:800 34px var(--font-ui);color:var(--display-coral);letter-spacing:.14em;margin-bottom:12px}
  .reply span{display:block;font:400 54px/1.14 "InstrumentSerif",serif;color:#fff}

  /* ── TYPE ROLES ──
     BRIGHT TAKE (mean luma 157.9): every emphasis word is FILLED, never the hollow outline —
     the outline needs a dark photographic ground and this room has none
     (persa-needs-the-full-type-pass). ── */
  .mline{position:absolute;left:0;width:1080px;text-align:center;
    font-family:var(--font-marker);font-size:84px;color:#fff;letter-spacing:.02em;
    text-transform:uppercase;white-space:nowrap;
    filter:drop-shadow(0 0 7px rgba(0,0,0,.9)) drop-shadow(0 5px 16px rgba(0,0,0,.7));
    animation:tin .36s cubic-bezier(.16,1,.3,1) both}
  .emfill{position:absolute;left:0;width:1080px;text-align:center;
    font-family:var(--font-display-heavy);line-height:1;letter-spacing:.012em;
    text-transform:uppercase;
    animation:pop .18s cubic-bezier(.34,1.56,.64,1) both}
  .ef-c{color:var(--display-coral);filter:var(--glow-coral)}
  .ef-s{color:#fff;filter:drop-shadow(0 0 7px rgba(0,0,0,.9)) drop-shadow(0 6px 20px rgba(0,0,0,.6))}

  /* ── CAPTIONS — one style, one word, one line at 1400, and it never moves. ── */
  .cap{position:absolute;left:0;width:1080px;text-align:center;will-change:transform,opacity}
  .c-ws{font:900 96px var(--font-heavy);color:#fff;text-transform:uppercase;letter-spacing:-.02em;
    filter:drop-shadow(0 0 7px rgba(0,0,0,.92)) drop-shadow(0 0 18px rgba(0,0,0,.7))
           drop-shadow(0 4px 14px rgba(0,0,0,.6))}

  /* ── CTA — the old one (BLACKLIST #9). Cream top half, HIM in the bottom half.
     `padding-right` on .l2 is the background-clip:text fix, not a redesign
     (background-clip-text-italic): an italic's last glyph leans past its advance box. ── */
  .creamplate{position:absolute;left:0;top:0;width:1080px;height:960px;background:var(--cream)}
  .cardwrap{position:absolute;left:0;top:960px;width:1080px;height:960px;overflow:hidden}
  .cardwrap video{position:absolute;left:0;top:-__CAMFULL_T__px;width:1080px;height:1920px;
    object-fit:none;object-position:0 0}
  .ctapanel{position:absolute;left:0;top:118px;width:1080px;display:flex;
    flex-direction:column;align-items:center;gap:34px}
  .ctalines{text-align:center}
  .l1{font:900 82px var(--font-heavy);color:var(--ink);letter-spacing:.02em}
  .l2{font:400 150px "InstrumentSerif",serif;font-style:italic;line-height:1.05;
    padding-right:.10em;
    background:linear-gradient(90deg,var(--coral-deep),var(--coral));
    -webkit-background-clip:text;background-clip:text;color:transparent}
  .arrow{height:100px;display:flex;justify-content:center}
  .arrow i{display:block;width:10px;height:90px;background:var(--ink);border-radius:6px;
    transform-origin:50% 0%;position:relative}
  .arrow i::after{content:"";position:absolute;left:50%;bottom:-6px;width:34px;height:34px;
    margin-left:-17px;border-right:10px solid var(--ink);border-bottom:10px solid var(--ink);
    transform:rotate(45deg);border-radius:3px}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-no-timeline data-start="0" data-duration="__DUR__"
     data-width="1080" data-height="1920" data-fps="30">
__BODY__
</div>
</body>
</html>
"""

if __name__ == "__main__":
    build()
