"""Writes audio/sfx_cues.json from the SAME beat constants the scenes use (120 BPM, beat 0.5 s).
Every visual event of the film gets its sound here; build_sfx.py (motion-studio sfx_lib) renders it.
    python audio/make_cues.py && python <motion-studio>/scripts/sfx/build_sfx.py . && powershell -File mix-soundtrack.ps1
"""
import json
from pathlib import Path

C = []
def cue(t, fx, g, label, **kw):
    c = {"t": round(t, 4), "fx": fx, "gain_db": g, "label": label}
    if "args" in kw: c["args"] = kw["args"]
    if kw.get("end"): c["align"] = "end"
    if kw.get("peak"): c["peak"] = True
    C.append(c)

# 1 hook — three slams
for t, w in [(0.0, "DIN CHEF"), (1.0, "BETALAR"), (2.0, "DIN GOLF.")]:
    cue(t, "impact", -9 if t < 2 else -6, f"slam {w}", args={"dur": 1.0})
    if t > 0: cue(t, "whoosh", -16, f"slam air {w}", peak=True, args={"dur": 0.3, "f_lo": 500, "f_hi": 6000})
cue(2.2, "shimmer", -20, "gold glint DIN GOLF.", args={"dur": 0.7, "base": 1320})
cue(3.0, "swell", -10, "into the flash", end=True, args={"dur": 0.9, "freq": 140})
cue(3.0, "whoosh", -12, "flash-through", peak=True, args={"dur": 0.7})
# 2 turn
cue(3.06, "pop", -22, "Med", args={"f0": 380, "f1": 760})
cue(3.31, "pop", -22, "friskvårdsbidraget", args={"f0": 420, "f1": 880})
cue(4.0, "pop", -14, "orb born", args={"f0": 180, "f1": 520, "dur": 0.25})
cue(6.0, "riser", -12, "riser into the 5 000 landing", end=True, args={"dur": 2.0, "f0": 220, "f1": 2600})
for k in range(16):  # counter ticks accelerate into the landing (on 16ths, louder as it nears)
    t = 4.0 + 2.0 * (1 - (1 - k / 16) ** 0.6)
    cue(t, "tick", -26 + k * 0.5, "count tick", args={"freq": 2400 + k * 60})
cue(6.0, "boom", -3, "5 000 kr LANDS (sub)")
cue(6.0, "impact", -8, "5 000 kr LANDS", args={"dur": 1.4})
cue(6.05, "shimmer", -16, "orb sheen", args={"dur": 1.2, "base": 990})
cue(7.0, "whoosh", -11, "dive into gold", peak=True, args={"dur": 0.6})
# 3 product
cue(7.1, "whoosh", -17, "page rises", args={"dur": 0.8, "f_lo": 150, "f_hi": 2500})
cue(8.0, "paper", -12, "marker sweep", args={"dur": 0.35})
cue(9.0, "whoosh", -16, "tilt down to cards", args={"dur": 0.7, "f_lo": 200, "f_hi": 3000})
cue(10.45, "key", -10, "click on 2 000 kr", args={"heavy": True})
cue(10.5, "pop", -18, "click ring", args={"f0": 700, "f1": 1400})
cue(11.0, "whoosh", -13, "card lifts out", args={"dur": 0.5, "f_lo": 300, "f_hi": 5000})
cue(11.05, "snap", -14, "card lift settle")
cue(11.25, "shimmer", -18, "card glint", args={"dur": 0.8, "base": 1180})
for t, n in [(11.5, "Greenfee"), (12.0, "Range"), (12.5, "Lektioner")]:
    cue(t, "pop", -13, f"chip {n}", args={"f0": 520, "f1": 1250})
cue(13.0, "whoosh", -10, "card at the lens / cut", peak=True, args={"dur": 0.45})
# 4 portals
for i in range(12):
    cue(13.25 + i * 0.0625, "key", -18, "type Golfkuponger")
for i, n in enumerate(["Benifex", "ePassi", "Söderberg & Partners", "Edenred"]):
    cue(14.0 + i * 0.25, "snap", -12, f"tile {n}")
    cue(13.9 + i * 0.25, "whoosh", -20, f"tile flight {n}", args={"dur": 0.25, "f_lo": 600, "f_hi": 7000})
cue(14.9, "pop", -20, "alt line", args={"f0": 600, "f1": 900})
cue(15.0, "whoosh", -17, "grid tips", args={"dur": 0.8, "f_lo": 150, "f_hi": 2000})
cue(16.0, "riser", -10, "dive riser", end=True, args={"dur": 1.4, "f0": 300, "f1": 4000})
# 5 proof (the drop)
cue(16.0, "boom", -2, "DROP: 300+")
cue(16.0, "impact", -6, "300+ slam", args={"dur": 1.6})
for t in (17.0, 18.0, 19.0):
    cue(t, "whoosh", -14, "photo whip", peak=True, args={"dur": 0.35, "f_lo": 400, "f_hi": 6000})
    cue(t, "shutter", -18, "photo swap")
cue(16.5, "pop", -20, "name tag in", args={"f0": 500, "f1": 800})
cue(20.0, "impact", -7, "flare shockwave", args={"dur": 1.6})
cue(20.0, "shimmer", -14, "flare sparkle", args={"dur": 1.4, "base": 880})
cue(21.0, "whoosh", -10, "whip to CTA", peak=True, args={"dur": 0.55})
# 6 CTA
cue(22.0, "swell", -12, "into emblem reveal", end=True, args={"dur": 1.0, "freq": 110})
cue(22.0, "chime", -8, "EMBLEM resolves", args={"freqs": [880, 1318.5]})
cue(22.5, "paper", -20, "wordmark wipe", args={"dur": 0.3})
cue(23.0, "pop", -21, "Låt chefen bjuda", args={"f0": 400, "f1": 700})
cue(23.5, "pop", -16, "url pill", args={"f0": 600, "f1": 1200})
cue(24.0, "shimmer", -11, "FINAL CHORD shimmer on the url", args={"dur": 1.2, "base": 1320})

Path(__file__).with_name("sfx_cues.json").write_text(json.dumps({"duration": 25.0, "cues": C}, indent=1, ensure_ascii=False), encoding="utf-8")
print(len(C), "cues")
