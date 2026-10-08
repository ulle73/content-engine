"""Capture the REAL golfkuponger.se friskvård page for the product scene.
Declines non-essential cookies ("Avslå"), hides only floating chat/fixed widgets.

Outputs (work/friskvard-v2/assets/ui/):
  friskvard-page.png    top 2 600 CSS px of the page at 430 px width, DPR 3 (1290 px wide)
  card-2000.png         element shot of the "Populärast 2,000 kr" price card
  card-1000.png / card-3000.png  neighbours (for the 3D fan)
  ui.json               rects (CSS px, page coords) of the phrases + card
"""
import json, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path("work/friskvard-v2/assets/ui"); OUT.mkdir(parents=True, exist_ok=True)
URL = "https://golfkuponger.se/pages/friskvard"
W, DPR, CROP_H = 430, 3, 2600

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": W, "height": 932}, device_scale_factor=DPR, locale="sv-SE")
    try:
        pg.goto(URL, wait_until="networkidle", timeout=25000)
    except Exception:
        pg.wait_for_timeout(2500)
    pg.wait_for_timeout(2500)
    btn = pg.get_by_role("button", name="Avslå", exact=True).first
    if btn.is_visible(timeout=3000):
        btn.click(); pg.wait_for_timeout(1200)
    print("cookie banner declined")
    # hide floating chat bubble etc. (fixed elements that are not the header)
    pg.evaluate("""() => {
      document.querySelectorAll('body *').forEach(e => {
        const cs = getComputedStyle(e);
        if (cs.position === 'fixed') e.style.setProperty('display','none','important');
      });
      document.documentElement.style.scrollBehavior='auto';
    }""")
    # make sure lazy images load: scroll through
    for y in range(0, CROP_H + 900, 300):
        pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(120)
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(1500)

    FIND = """(phrase) => {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = w.nextNode())) {
        const i = n.nodeValue.indexOf(phrase);
        if (i === -1) continue;
        const el = n.parentElement; if (!el || !el.offsetParent) continue;
        const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + phrase.length);
        const bs = [...r.getClientRects()]; if (!bs.length) continue;
        return bs.map(b => ({x: b.x, y: b.y + window.scrollY, w: b.width, h: b.height}));
      }
      return null;
    }"""
    meta = {"url": URL, "css_width": W, "dpr": DPR, "crop_h": CROP_H, "phrases": {}}
    for ph in ["friskvårdsbidraget", "300+ anslutna golfklubbar", "greenfee, range, golflektioner",
               "upp till 5 000 kr per år", "Köp via din", "Populärast", "2,000 kr"]:
        meta["phrases"][ph] = pg.evaluate(FIND, ph)
        print(ph, meta["phrases"][ph])

    # the visible popular card (carousel slide containing 'Populärast')
    card = pg.evaluate("""() => {
      const lab = [...document.querySelectorAll('*')].find(e => e.childElementCount===0 && e.textContent.trim()==='Populärast' && e.offsetParent);
      let el = lab;
      // climb until the element is a card-sized box (> 250px tall)
      while (el && el.getBoundingClientRect().height < 380) el = el.parentElement;
      el.setAttribute('data-cap','card');
      const r = el.getBoundingClientRect();
      return {x:r.x, y:r.y+window.scrollY, w:r.width, h:r.height, cls: el.className};
    }""")
    meta["card"] = card
    print("card", card)
    pg.screenshot(path=str(OUT / "friskvard-page.png"), full_page=True,
                  clip={"x": 0, "y": 0, "width": W, "height": CROP_H})
    # isolate the card: hide carousel arrows + sibling slides, make ancestors transparent
    pg.evaluate("""() => {
      const card = document.querySelector('[data-cap=card]');
      document.querySelectorAll('button').forEach(b => { if (!card.contains(b)) b.style.setProperty('visibility','hidden','important'); });
      card.parentElement && [...card.parentElement.children].forEach(s => { if (s !== card && !s.contains(card)) s.style.setProperty('visibility','hidden','important'); });
      let el = card.parentElement;
      while (el) { el.style.setProperty('background','transparent','important'); el.style.setProperty('background-image','none','important'); el = el.parentElement; }
    }""")
    pg.wait_for_timeout(400)
    pg.locator("[data-cap=card]").screenshot(path=str(OUT / "card-2000.png"), omit_background=True)
    (OUT / "ui.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    b.close()
print("done")
