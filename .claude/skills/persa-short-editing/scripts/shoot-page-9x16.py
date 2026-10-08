#!/usr/bin/env python3
"""
Screenshot a REAL page as a full-bleed 9:16 frame with big type, and locate the phrases the
highlighter will sweep — measured from the live DOM, never nudged by eye.

    python scripts/shoot-page-9x16.py <url> <out.png> \
        --hl "messaging is on with nothing to enable" \
        --hl "macOS and Linux"

Why a narrow viewport: a 1400px-wide desktop page squeezed into a 1080 frame scales type to
0.7x and is unreadable — the thing Jad blacklisted. Shot at ~560 CSS px the same page reflows
to one readable column, and filling 1080 scales it ~1.9x UP.

Writes <out.png> (1080x1920) and <out>.json — the phrase rects as PERCENT of the image, which
is what broll-library/ui-blocks/page-highlight.html consumes.
"""
import argparse, json, pathlib, sys
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("out")
ap.add_argument("--w",   type=int, default=560, help="CSS width; smaller = bigger type in frame")
ap.add_argument("--dpr", type=int, default=3,   help="device scale factor")
ap.add_argument("--hl",  action="append", default=[], help="phrase to locate (repeatable)")
ap.add_argument("--anchor", default=None, help="scroll this text to the top before shooting")
ap.add_argument("--no-center", dest="center", action="store_false",
                help="do not vertically centre the first --hl phrase in the frame")
ap.add_argument("--pad",  type=int, default=150,
                help="px above the anchor — must clear the site's sticky header")
ap.add_argument("--css",  action="append", default=[],
                help="extra CSS to inject (repeatable). Use it to force-wrap a non-wrapping "
                     "viewer — a raw .txt/LICENSE renders as one <pre> whose lines run off the "
                     "right edge and clip the sentence you came to mark: "
                     "--css 'pre{white-space:pre-wrap;word-break:break-word}'")
a = ap.parse_args()

# A phrase can repeat on a page, and the FIRST match is often the wrong one — on the Artificial
# Analysis leaderboard "MiniMax H3" appears in a small grey "added this month" note ABOVE the
# table, so the marker landed there instead of on the #1 row and the push zoomed away from the
# thing being claimed. Append ::n to mark the nth occurrence instead:
#     --hl "MiniMax H3::2"
PHRASE, NTH = [], []
for _p in a.hl:
    _t, _sep, _n = _p.rpartition("::")
    if _sep and _n.isdigit():
        PHRASE.append(_t); NTH.append(int(_n))
    else:
        PHRASE.append(_p); NTH.append(1)

H = round(a.w * 16 / 9)                       # a true 9:16 viewport, so the shot IS the frame
out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    try:
        b = p.chromium.launch()
    except Exception:                     # content-engine: no bundled Chromium -> use the installed Chrome
        b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": a.w, "height": H},
                    device_scale_factor=a.dpr, color_scheme="light")
    # networkidle is the ideal wait, but sites that hold a long-poll / websocket open (Hugging
    # Face is one) NEVER reach it and the shot hangs forever with no error. Try it briefly,
    # then fall back to domcontentloaded + a settle pause. Verified 2026-08-11 on
    # huggingface.co/MiniMaxAI/MiniMax-H3, which hung past 180s on networkidle and loads in 3s.
    try:
        pg.goto(a.url, wait_until="networkidle", timeout=15000)
    except Exception:
        pg.goto(a.url, wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_timeout(1800)
    pg.wait_for_timeout(2200)
    # Consent/cookie overlays dim the page and land in the shot. They also load LATE, so this
    # has to run again right before the screenshot, not just once after load.
    def dekill():
        pg.evaluate("""() => {
          for (const s of ['[class*=cookie]','[class*=consent]','[id*=cookie]','[class*=Cookie]',
                           '[class*=banner]','[class*=Banner]','[role=dialog]']) {
            document.querySelectorAll(s).forEach(e => e.remove());
          }
        }""")
    # Hiding loses to a widget that re-injects itself in a shadow root — DISMISS it instead.
    for label in ["Reject all", "Reject All", "Accept all", "Accept All", "Accept", "Agree", "Got it"]:
        try:
            btn = pg.get_by_role("button", name=label, exact=False).first
            if btn.is_visible(timeout=800):
                btn.click(timeout=1500); pg.wait_for_timeout(500); break
        except Exception:
            continue
    dekill()

    # pg.add_style_tag() HANGS FOREVER on a text/plain URL (a raw LICENSE, a .txt, a robots.txt).
    # Chrome wraps those in a synthetic document with no real <head>, so the <style> never fires
    # the load event Playwright waits on — no error, no timeout, just a dead process. Inject by
    # hand instead; it needs no load event. Measured 2026-08-11: everything up to this call
    # finished in 3.2s, then it sat past 180s. Applies to EVERY style injection below too.
    def style(css):
        pg.evaluate("""(css) => {
          const s = document.createElement('style');
          s.textContent = css;
          (document.head || document.documentElement).appendChild(s);
        }""", css)

    # Deleting nodes loses to a consent widget that re-injects itself. A style rule does not.
    style("""
      [class*=cookie],[class*=Cookie],[id*=cookie],[class*=consent],[class*=Consent],
      [role=dialog],[class*=onetrust],[id*=onetrust],[class*=banner]{display:none !important}
    """)
    # A site's own sticky header/nav/breadcrumb rides down the page and lands in the shot as
    # chrome. The frame should be the CONTENT only.
    pg.evaluate("""() => {
      document.querySelectorAll('body *').forEach(e => {
        const p = getComputedStyle(e).position;
        if (p === 'fixed' || p === 'sticky') e.style.setProperty('display','none','important');
      });
    }""")
    # Caller CSS goes on LAST so it can beat the rules above, and before any measuring — a
    # wrap rule changes every rect on the page, so locating phrases first would measure a
    # layout that no longer exists at screenshot time.
    for css in a.css:
        style(css)
    pg.wait_for_timeout(300)

    # dekill() REMOVES nodes, so it reflows the document. It used to run only after the phrases
    # were located, which left every rect stale by the height of whatever came out — on the
    # prime-agent README that was ~37% of the frame, and the marker drew across the security
    # warning instead of the sentence it was aimed at. Nothing may mutate layout between the
    # measurement and the screenshot, so all removal happens HERE, before scrolling/measuring.
    # (Found 2026-08-13 on tp-0813 by sampling the rendered block, not the shot.)
    dekill(); pg.wait_for_timeout(250); dekill()
    pg.wait_for_timeout(250)

    # GitHub (and any site setting scroll-behavior:smooth) ANIMATES window.scrollTo. The rects
    # were being read mid-flight, so every one was short of where it landed — on the prime-agent
    # README by a uniform 10.2% of the frame, which put the marker on the security warning
    # instead of the sentence above it. Force instant scrolling before anything scrolls.
    style("html,body,*{scroll-behavior:auto !important}")

    top = 0
    if a.anchor:
        el = pg.get_by_text(a.anchor, exact=False).locator("visible=true").first
        el.scroll_into_view_if_needed(timeout=10000)
        pg.wait_for_timeout(400)
        # bounding_box() is VIEWPORT-relative; add scrollY to get the absolute offset, or
        # scrollTo() jumps back to the top with a tiny number.
        abs_y = pg.evaluate("window.scrollY") + el.bounding_box()["y"]
        pg.evaluate(f"window.scrollTo(0,{max(0, abs_y - a.pad)})")
        pg.wait_for_timeout(500)


    # Centre the FIRST highlight phrase in the frame. Without this the marker can land near the
    # top of the shot, and then a split/transparent slot cannot centre on it without exposing
    # blank page — the framing has to be solved at capture, not at layout time.
    if a.hl and a.center:
        first = pg.evaluate("""([phrase, nth]) => {
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let n, seen = 0;
          while ((n = w.nextNode())) {
            const i = n.nodeValue.indexOf(phrase);
            if (i === -1) continue;
            if (!n.parentElement || !n.parentElement.offsetParent) continue;
            const r = document.createRange();
            r.setStart(n, i); r.setEnd(n, i + phrase.length);
            const bs = [...r.getClientRects()];
            if (!bs.length) continue;
            if (++seen < nth) continue;
            const top = Math.min(...bs.map(b => b.y));
            const bot = Math.max(...bs.map(b => b.y + b.height));
            return window.scrollY + (top + bot) / 2;
          }
          return null;
        }""", [PHRASE[0], NTH[0]])
        if first is not None:
            pg.evaluate(f"window.scrollTo({{top:{max(0, first - H / 2)},behavior:'instant'}})")
            # Belt and braces: block until scrollY actually stops moving. A rect measured while
            # the viewport is still travelling is silently wrong and only shows up as a marker
            # on the wrong sentence, three steps later, in the rendered mp4.
            last, stable = None, 0
            for _ in range(40):
                y = pg.evaluate("window.scrollY")
                stable = stable + 1 if y == last else 0
                last = y
                if stable >= 3:
                    break
                pg.wait_for_timeout(100)
            else:
                print("  ! scroll never settled — rects may be off", file=sys.stderr)
            pg.wait_for_timeout(200)

    # Locate each phrase with a DOM Range over the exact substring, then take
    # getClientRects() — one rect PER LINE, so a phrase that wraps gets a marker bar per line
    # exactly like a real highlighter. get_by_text() only ever returns the whole element box.
    FIND = """([phrase, nth]) => {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n, seen = 0;
      while ((n = w.nextNode())) {
        const i = n.nodeValue.indexOf(phrase);
        if (i === -1) continue;
        const el = n.parentElement;
        if (!el || !el.offsetParent) continue;               // skip hidden
        const r = document.createRange();
        r.setStart(n, i); r.setEnd(n, i + phrase.length);
        const bs = [...r.getClientRects()];
        if (!bs.length) continue;
        if (++seen < nth) continue;                          // ← see --hl "phrase::2"
        return bs.map(b => ({x: b.x, y: b.y, w: b.width, h: b.height}));
      }
      return null;
    }"""
    rects = []
    for phrase, nth in zip(PHRASE, NTH):
        boxes = pg.evaluate(FIND, [phrase, nth])
        if not boxes:
            print(f"  ! phrase not found on screen, skipped: {phrase[:46]}", file=sys.stderr)
            continue
        kept = 0
        for bx in boxes:                       # not `b` — that is the browser handle
            if not (-4 <= bx["y"] <= H) or bx["w"] < 4:
                continue
            rects.append({
                "phrase": phrase,
                "left":   round(bx["x"] / a.w * 100, 2),
                "top":    round(bx["y"] / H * 100, 2),
                "width":  round(bx["w"] / a.w * 100, 2),
                "height": round(bx["h"] / H * 100, 2),
            })
            kept += 1
        if kept:
            r = rects[-kept]
            print(f"  ✓ {phrase[:42]:<44} {kept} line(s)  @ {r['left']:5.1f}% {r['top']:5.1f}%")
        else:
            print(f"  ! phrase off-frame, skipped: {phrase[:46]}", file=sys.stderr)

    # NOTHING may mutate layout from here to pg.screenshot() — the rects above are already
    # measured. Consent widgets were dismissed before the measurement instead.

    # REFUSE to write a bot-wall or an empty page. Reddit, Cloudflare and login walls all return
    # 200 and render a perfectly valid screenshot of nothing useful — which then ships as a blank
    # panel. Fail loudly here instead.
    body_text = (pg.inner_text("body") or "").strip()
    WALLS = ["blocked by network security", "verify you are human", "just a moment",
             "enable javascript", "are you a robot", "unusual traffic", "log in to continue",
             "sign in to continue", "access denied", "attention required"]
    low = body_text.lower()
    hit = next((w for w in WALLS if w in low), None)
    if hit or len(body_text) < 220:
        pg.screenshot(path=str(out.with_suffix(".REJECTED.png")))
        b.close()
        why = f"bot/login wall — page says “{hit}”" if hit else \
              f"page has only {len(body_text)} chars of text"
        sys.exit(f"\nREFUSED to write {out.name}: {why}.\n"
                 f"  Wrote {out.with_suffix('.REJECTED.png').name} so you can see what came back.\n"
                 f"  Reddit and X block headless Chromium. Use old.reddit.com, an official\n"
                 f"  embed, or drive a real logged-in browser — see reference/SOURCING.md.")

    pg.screenshot(path=str(out))          # viewport shot — clip= would ignore the scroll
    b.close()

# normalise to exactly 1080x1920 whatever the DPR produced
import subprocess
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out),
                "-vf", "scale=1080:1920:flags=lanczos", str(out.with_suffix(".tmp.png"))], check=True)
out.with_suffix(".tmp.png").replace(out)

meta = {"url": a.url, "css_width": a.w, "scale_into_frame": round(1080 / a.w, 2), "rects": rects}
out.with_suffix(".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
print(f"\n{out}  1080x1920   type scales {meta['scale_into_frame']}x UP   {len(rects)} phrase(s)")
