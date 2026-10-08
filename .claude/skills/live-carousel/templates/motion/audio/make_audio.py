"""Sound design for this live carousel: one loop-exact mix per slide, written to audio/out/<slide>.wav.

Run:  <skill>/scripts/py audio/make_audio.py      (from the project folder)
Every slide is a whole number of 120 BPM bars and effect tails wrap round to the start, so the
Instagram loop is seamless in sound as well as picture. The instruments live in lc_audio.py.
Retime every event to the visual moment it belongs to: read the slide's render(t) for the times.
"""
from pathlib import Path

import numpy as np

from lc_audio import *  # noqa: F401,F403  (Bus, groove, boop, whoosh, place_sample, master, write_wav ...)
import lc_audio

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
lc_audio.set_cache(HERE / ".sfx-cache")


# ================================================================ SLIDE 1: HOOK (6 s)
def slide1():
    sec = 6.0
    bus = Bus(sec + 3)
    # 0.26-0.5: the ball falls in (whistle + whoosh), then IMPACT on the downbeat
    bus.add(whistle_fall(0.26, 0.25, 1900, 900), 0.24, 1.0, pan=-0.2)
    bus.add(whoosh(0.3, 0.6, 800, 6000, "in"), 0.2, 1.0)
    place_sample(bus, "impact-bass-1", 0.5, 0.95)
    bus.add(stereo(kick(1.0)), 0.5, 0.9)
    bus.add(crash(0.35), 0.5, 1.0)
    # rising xylophone run across S T A T I C .
    run = ["A4", "C5", "D5", "E5", "G5", "A5", "C6"]
    for i, (n, t) in enumerate(zip(run, [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0])):
        bus.add(boop(NOTE[n], 0.75 + i * 0.03), t, 1.0, pan=-0.6 + i * 0.2)
        if i:
            bus.add(stereo(thump(0.35)), t, 1.0)
    # light pulse under the run: hats on 8ths, building
    for k in range(8):
        bus.add(hat(0.4 + k * 0.08), 0.5 + k * 0.25, 0.4, pan=0.3)
    # riser into the drop, cut 80 ms before the slam
    rise, ron = load("riser")
    seg = rise[int(7.4 * SR): int(7.4 * SR) + int(1.42 * SR)]
    seg = seg * np.linspace(0.2, 1, len(seg))[:, None]
    bus.add(seg, 1.0, 0.55)
    # flips STATIC -> ALIVE (clacks), whoosh up for the launch
    for i in range(7):
        place_sample(bus, "click", 2.0 + i * 0.028, 0.35, pan=-0.5 + i * 0.15, rate=1.2 + i * 0.05)
    for j in range(6):
        place_sample(bus, "click", 2.13 + j * 0.04 + 0.2, 0.3, pan=-0.4 + j * 0.16, rate=0.9 + j * 0.05)
    bus.add(whoosh(0.45, 0.8, 600, 7000, "swell"), 2.02, 1.0)
    # 2.5 THE DROP
    place_sample(bus, "impact-bass-2", 2.5, 1.0)
    bus.add(crash(0.6), 2.5, 1.0)
    bus.add(boing(260, 0.55, 0.6), 2.5, 1.0)
    # groove from the slam: one bar + a beat ... then tape stop at 4.5
    g, gsec = groove(2, 1.0, fill=False)
    live = g[: int(2.0 * SR)]
    stop = tape_stop(g, 2.0, 0.6)
    bus.add(np.concatenate([live, stop]), 2.5, 0.95)
    # ball landings on V E . (on the kick) + exit whoosh
    for n, t in (("E5", 3.0), ("G5", 3.5), ("A5", 4.0)):
        bus.add(boop(NOTE[n], 0.6), t, 1.0, pan=0.3)
    bus.add(whoosh(0.5, 0.7, 500, 5000, "swell"), 4.05, 1.0, pan=0.7)
    # life drains: flips back + fps countdown blips + selection box redraw ticks
    for j in range(6):
        place_sample(bus, "click-soft", 4.72 + j * 0.045, 0.3, rate=0.8)
    for k in range(6):
        bus.add(tick(0.25, 1800 - k * 180), 4.62 + k * 0.1, 1.0)
    for k in range(8):
        bus.add(tick(0.18, 3200), 5.15 + k * 0.03, 1.0, pan=-0.5 + k * 0.14)
    bus.add(boop(NOTE["A3"], 0.3, 0.5), 5.0, 1.0)
    return master(bus, sec, wrap=True) * 0.74


# ================================================================ SLIDE 2: EASING (8 s)
def slide2():
    sec = 8.0
    bus = Bus(sec + 3)
    g, _ = groove(4, 0.78)
    bus.add(g, 0.0, 1.0)
    bus.add(whoosh(0.34, 0.55, 600, 5000, "in"), 0.0, 1.0, pan=-0.6)
    bus.add(boop(NOTE["A4"], 0.6), 0.34, 1.0, pan=-0.5)
    bus.add(stereo(thump(0.4), -0.5), 0.34, 1.0)
    bus.add(boop(NOTE["E5"], 0.3), 0.62, 1.0, pan=-0.5)
    for (t0, d) in ((1.0, 1), (2.5, -1), (4.5, 1)):
        # robot: ticks at perfectly even spacing (every 2 frames) + hard clunk stop
        for k in range(16):
            bus.add(tick(0.32, 2600), t0 + k / 15, 1.0, pan=-0.2)
        bus.add(clunk(0.6), t0 + 1.0, 1.0, pan=-0.2)
        # eased ball: whoosh that follows its velocity curve (sonified ease in-out)
        tt = np.arange(int(1.0 * SR)) / SR
        vel = np.where(tt < 0.5, 12 * tt**2, 3 * (2 - 2 * tt) ** 2)
        bus.add(speed_whoosh(vel, 0.5), t0, 1.0, pan=0.2 * d)
        bus.add(boop(NOTE["C5" if d > 0 else "A4"], 0.45), t0 + 1.0, 1.0, pan=0.4 * d)
    place_sample(bus, "pop", 2.0, 0.45, pan=0.4)
    place_sample(bus, "pop", 2.08, 0.5, pan=0.5, rate=1.15)
    bus.add(scribble(0.3, 0.75), 3.5, 1.0, pan=0.1)
    place_sample(bus, "impact-bass-1", 3.62, 0.45)
    for k in range(16):
        bus.add(tick(0.25, 2300), 6.4 + k / 15, 1.0, pan=-0.2)
    bus.add(clunk(0.5), 7.4, 1.0)
    bus.add(boing(380, 0.6, 0.5, up=True), 6.5, 1.0, pan=0.5)
    bus.add(whoosh(0.6, 0.6, 500, 6000, "swell"), 6.55, 1.0, pan=0.8)
    bus.add(scribble(0.22, 0.4), 7.3, 1.0)
    return master(bus, sec, wrap=True)


# ================================================================ SLIDE 3: WEIGHT (8 s)
def slide3():
    sec = 8.0
    bus = Bus(sec + 3)
    g, _ = groove(4, 0.75)
    bus.add(g, 0.0, 1.0)
    bus.add(whoosh(0.5, 0.45, 500, 4000, "swell"), 0.0, 1.0, pan=-0.6)
    bus.add(whistle_fall(0.42, 0.3, 1700, 380), 0.56, 1.0, pan=-0.3)
    lands = [(1.0, 1.0, 300), (2.0, 0.8, 330), (2.5, 0.6, 360), (2.75, 0.42, 390), (2.875, 0.28, 420)]
    for t, lvl, f in lands:
        bus.add(boing(f, 0.75 * lvl, 0.5), t, 1.0)
        bus.add(stereo(thump(0.9 * lvl)), t, 1.0)
    place_sample(bus, "impact-bass-1", 1.0, 0.5)
    for t in (3.1, 3.6):
        bus.add(scribble(0.33, 0.25), t, 1.0, pan=0.3)
        place_sample(bus, "pop", t + 0.12, 0.5, pan=0.3 if t < 3.5 else -0.3)
    # crouch: tension creak rising, then the trampoline launch
    t = T(0.45)
    creak = np.sin(2 * np.pi * np.cumsum(120 + 260 * (t / 0.45) ** 2) / SR) * (t / 0.45) * 0.35
    bus.add(creak, 6.0, 1.0)
    bus.add(boing(240, 0.9, 0.7, up=True), 6.45, 1.0)
    place_sample(bus, "impact-bass-2", 6.45, 0.55)
    bus.add(whoosh(0.7, 0.7, 600, 7000, "swell"), 6.5, 1.0, pan=0.7)
    return master(bus, sec, wrap=True)


# ================================================================ SLIDE 4: CTA (8 s)
def slide4():
    sec = 8.0
    bus = Bus(sec + 3)
    g, _ = groove(4, 0.75)
    bus.add(g, 0.0, 1.0)
    bus.add(whistle_fall(0.45, 0.22, 1500, 700), 0.05, 1.0, pan=-0.5)
    bus.add(boop(NOTE["A4"], 0.6), 0.5, 1.0, pan=-0.4)
    bus.add(stereo(thump(0.4)), 0.5, 1.0)
    # snap into the O
    place_sample(bus, "pop", 1.0, 0.85)
    place_sample(bus, "chime", 1.02, 0.4)
    place_sample(bus, "impact-bass-1", 1.0, 0.45)
    bus.add(boop(NOTE["E5"], 0.5), 1.0, 1.0)
    # typing M O T I O N
    for i in range(6):
        place_sample(bus, "key-press", 1.45 + i * 0.14, 0.55, pan=0.1 * (i - 3), rate=1.0 + 0.03 * (i % 3))
    bus.add(whoosh(0.5, 0.2, 1500, 6000, "swell"), 2.4, 1.0, pan=0.5)
    # press POST, comment appears, reply ping, heart
    place_sample(bus, "click", 3.0, 0.8, pan=0.5)
    bus.add(whoosh(0.3, 0.4, 900, 6000, "in"), 2.78, 1.0)
    place_sample(bus, "pop", 3.06, 0.55, pan=-0.3)
    bus.add(boop(NOTE["G5"], 0.45), 3.1, 1.0)
    place_sample(bus, "ping", 3.62, 0.5)
    bus.add(boop(NOTE["A5"], 0.4), 3.65, 1.0)
    place_sample(bus, "sparkle", 4.05, 0.55, pan=0.6)
    place_sample(bus, "pop", 4.05, 0.45, pan=0.6, rate=1.2)
    for i, (t, n) in enumerate(((4.5, "C5"), (5.0, "D5"), (5.5, "E5"))):
        place_sample(bus, "click-soft", t, 0.5, pan=-0.4 + 0.4 * i)
        bus.add(boop(NOTE[n], 0.3), t, 1.0, pan=-0.4 + 0.4 * i)
    # reset + ball pops out and leaves
    bus.add(whoosh(0.35, 0.25, 800, 4000, "out"), 6.85, 1.0)
    place_sample(bus, "pop", 7.1, 0.6, rate=0.9)
    bus.add(boing(330, 0.5, 0.5, up=True), 7.12, 1.0)
    bus.add(whoosh(0.6, 0.55, 600, 6000, "swell"), 7.15, 1.0, pan=0.7)
    return master(bus, sec, wrap=True)


if __name__ == "__main__":
    for name, fn in (("01-hook", slide1), ("02-easing", slide2), ("03-weight", slide3), ("04-cta", slide4)):
        x = fn()
        write_wav(OUT / f"{name}.wav", x)
        report(name, x)
