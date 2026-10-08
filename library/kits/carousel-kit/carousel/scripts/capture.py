"""Capture a web screenshot for use inside a carousel slide.

Plain headless Chromium (Playwright) — no user-agent spoofing, no hiding of the automation
flag (removed in the content-engine import). Sites that block headless browsers: take the
screenshot by hand instead. Best effort: declines cookie banners (privacy-preserving labels
only), triggers lazy-loaded content by scrolling, then screenshots the whole page, a CSS
element, or an explicit clip box. Saves a PNG you can drop into a slide's `content` block
as {"type":"image", ...}.

Examples (from the repo root, default output folder is work/<kit>/shots/):
  library/.venv/Scripts/python library/kits/<kit>/carousel/scripts/capture.py "https://example.com/post" work/<kit>/shots/probe.png --full
  ... capture.py "<url>" work/<kit>/shots/chart.png --clip 120,2400,900,560
  ... capture.py "<url>" work/<kit>/shots/chart.png --selector "figure.benchmark"

Always credit the source in the slide caption (e.g. "via scb.se").
"""
import argparse
from pathlib import Path

import carousel_config as cfg

# privacy-preserving choices only — never auto-accept tracking cookies
COOKIE_LABELS = ["Reject all", "Reject non-essential", "Reject", "Decline", "Only necessary",
                 "Necessary only", "Avvisa alla", "Neka alla", "Endast nödvändiga",
                 "Bara nödvändiga", "Avböj"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--selector", help="CSS selector of the element to capture")
    ap.add_argument("--clip", help="x,y,width,height in CSS px (at --width)")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1600)
    ap.add_argument("--scale", type=int, default=2, help="device scale (2 = retina/crisp)")
    ap.add_argument("--full", action="store_true", help="full-page screenshot")
    ap.add_argument("--wait", type=int, default=1800, help="ms to wait after load/scroll")
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("library/.venv/Scripts/python -m pip install playwright && "
                         "library/.venv/Scripts/python -m playwright install chromium")

    out = Path(a.out)
    if not out.is_absolute() and len(out.parts) == 1:
        out = cfg.SHOTS_DIR / out          # bare file name -> work/<kit>/shots/
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = cfg.launch_browser(p)
        ctx = browser.new_context(viewport={"width": a.width, "height": a.height},
                                  device_scale_factor=a.scale)
        page = ctx.new_page()
        try:
            page.goto(a.url, wait_until="networkidle", timeout=45000)
        except Exception:
            page.goto(a.url, wait_until="domcontentloaded", timeout=45000)

        # Decline cookie/consent banners (best effort).
        for label in COOKIE_LABELS:
            try:
                btn = page.get_by_role("button", name=label, exact=False)
                if btn.count():
                    btn.first.click(timeout=1200)
                    page.wait_for_timeout(400)
                    break
            except Exception:
                pass

        # Trigger lazy-loaded / scroll-animated content, then return to top.
        page.evaluate("""async () => {
            const h = document.body.scrollHeight;
            for (let y = 0; y < h; y += 500) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); }
            window.scrollTo(0, 0);
        }""")
        page.wait_for_timeout(a.wait)

        if a.selector:
            el = page.locator(a.selector).first
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(600)
            el.screenshot(path=str(out))
        elif a.clip:
            x, y, w, h = (float(v) for v in a.clip.split(","))
            page.screenshot(path=str(out), clip={"x": x, "y": y, "width": w, "height": h})
        else:
            page.screenshot(path=str(out), full_page=a.full)
        browser.close()
    print("saved:", out)


if __name__ == "__main__":
    main()
