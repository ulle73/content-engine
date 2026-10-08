#!/usr/bin/env python3
"""Real claude.com/marketplace pages, recorded frame by frame at 380 CSS wide (dsf 2.842 -> 1080 px).
Only the top ~1060 px shows above his head on a ui beat, so every state is lifted into that band.
B  connectors-plugins grid scrolling (the 2,000+ beat)
C  plugins hub: 'Add new capabilities to Claude' + Submit a plugin
F  Superpowers detail: Install in Claude Code -> Made by / Installs
H  marketplace hero: the live search typing + 'add, buy, scale'
"""
import pathlib, sys
from playwright.sync_api import sync_playwright
D=pathlib.Path(__file__).parent; OUT=D/"src/pages"; OUT.mkdir(parents=True,exist_ok=True)
VW,VH=380,676; DPR=1080/380; FPS=30
KILL="""()=>{for(const e of document.querySelectorAll('[class*=cookie],[id*=cookie],[class*=consent],[id*=onetrust],[class*=Cookie]'))e.remove();
 document.documentElement.style.scrollBehavior='auto';}"""
def ease(u): return u*u*(3-2*u)
def shoot(pg,name,n,step):
    d=OUT/name; d.mkdir(exist_ok=True)
    for i in range(n):
        step(i); pg.screenshot(path=str(d/f"{i:04d}.png"))
def y_of(pg,sel_text):
    return pg.evaluate("""t=>{const e=[...document.querySelectorAll('h1,h2,h3,a,button,span,div,p')].filter(x=>x.children.length===0&&x.textContent.trim()===t)[0];return e?e.getBoundingClientRect().top+scrollY:null}""",sel_text)
def _launch(p):
    try:
        return p.chromium.launch()
    except Exception:  # content-engine: no bundled Chromium -> the installed Chrome
        return p.chromium.launch(channel="chrome")
def run(w):
    with sync_playwright() as p:
        b=_launch(p); pg=b.new_page(viewport={"width":VW,"height":VH},device_scale_factor=DPR)
        if w=="H":
            pg.clock.install()
            pg.goto("https://claude.com/marketplace",wait_until="load",timeout=90000); pg.clock.run_for(6000); pg.evaluate(KILL)
            pg.evaluate("()=>scrollTo(0,110)")
            shoot(pg,"H",180,lambda i: pg.clock.run_for(33 if i%3 else 34))
        if w=="B":
            pg.goto("https://claude.com/marketplace/connectors-plugins",wait_until="load",timeout=90000); pg.wait_for_timeout(4000); pg.evaluate(KILL)
            y0=y_of(pg,"Top connectors") or 600; y0-=20
            n=int(4.6*FPS)
            shoot(pg,"B",n,lambda i:(pg.evaluate(f"()=>scrollTo(0,{y0+ease(i/(n-1))*1500})"),pg.wait_for_timeout(60)))
        if w=="C":
            pg.goto("https://claude.com/marketplace/plugins",wait_until="load",timeout=90000); pg.wait_for_timeout(4000); pg.evaluate(KILL)
            n=int(5.6*FPS)
            shoot(pg,"C",n,lambda i:(pg.evaluate(f"()=>scrollTo(0,{60+ease(min(1,i/(n*0.5)))*290})"),pg.wait_for_timeout(40)))
        if w=="F":
            pg.goto("https://claude.com/marketplace/plugins/superpowers",wait_until="load",timeout=90000); pg.wait_for_timeout(4000); pg.evaluate(KILL)
            n=int(6.0*FPS)
            shoot(pg,"F",n,lambda i:(pg.evaluate(f"()=>scrollTo(0,{40+ease(min(1,max(0,(i-50)/50)))*320})"),pg.wait_for_timeout(40)))
        b.close()
for w in (sys.argv[1:] or ["H","B","C","F"]): run(w); print(w,"done")
