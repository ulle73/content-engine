"""Probe the golfkuponger experiment theme pages: cookie banner buttons, key texts, page height.
Declines non-essential cookies only (never clicks accept)."""
import json, sys
from playwright.sync_api import sync_playwright

URLS = sys.argv[1:] or [
    "https://golfkuponger.se/pages/friskvard?preview_theme_id=201846882645",
    "https://golfkuponger.se/?preview_theme_id=201846882645",
]
OUT = "work/friskvard-v2/scratch/probe"

DECLINE = ["Avslå", "Avvisa alla", "Avvisa", "Neka alla", "Neka", "Endast nödvändiga", "Bara nödvändiga",
           "Avböj", "Reject all", "Decline", "Only necessary"]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for k, url in enumerate(URLS):
        pg = b.new_page(viewport={"width": 430, "height": 932}, device_scale_factor=2)
        try:
            pg.goto(url, wait_until="networkidle", timeout=20000)
        except Exception:
            pg.wait_for_timeout(2500)
        pg.wait_for_timeout(2500)
        btns = pg.evaluate("""() => [...document.querySelectorAll('button, a[role=button], [role=button]')]
            .filter(b => b.offsetParent).map(b => (b.innerText||'').trim()).filter(Boolean).slice(0,60)""")
        print("URL", url)
        print("buttons:", json.dumps(btns, ensure_ascii=False))
        pg.screenshot(path=f"{OUT}-{k}-banner.png")
        clicked = None
        for label in DECLINE:
            try:
                el = pg.get_by_role("button", name=label, exact=False).first
                if el.is_visible(timeout=500):
                    el.click(timeout=1500); clicked = label; pg.wait_for_timeout(800); break
            except Exception:
                pass
        print("declined via:", clicked)
        h = pg.evaluate("document.documentElement.scrollHeight")
        print("height", h)
        txt = pg.inner_text("body")
        print(txt[:3000].replace("\n\n", "\n"))
        pg.screenshot(path=f"{OUT}-{k}-full.png", full_page=True)
        pg.close()
    b.close()
