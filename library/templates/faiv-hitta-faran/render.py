"""FAIV – "Hitta faran" 9:16. Renderar bildrutor med numpy/PIL och kodar med ffmpeg.

  ../../.venv/Scripts/python.exe -I render.py              # hela filmen -> out/video.mp4 (utan ljud)
  ../../.venv/Scripts/python.exe -I render.py --stills 1.0 8.2 9.8   # enstaka bilder -> build/still_*.png
Kör prep.py först.
"""
import argparse
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.exists(os.path.join(ROOT, "manage.py")):       # repots rot (för typsnitten), var mappen än ligger
    parent = os.path.dirname(ROOT)
    if parent == ROOT:
        raise SystemExit("Hittar inte content-engine-repots rot (manage.py) ovanför " + HERE)
    ROOT = parent
W, H, FPS = 1080, 1920, 30

F_HEAD = os.path.join(ROOT, ".claude/skills/live-carousel/templates/common/fonts/Anybody-Var.woff2")
F_INTER = {w: os.path.join(ROOT, f"edit-renderer/fonts/inter-{w}.woff2") for w in (400, 500, 600, 700)}

# ---------------------------------------------------------------- läsregel
# Samma regel som engine/edit/spec.py: varje textbit får max(5/6 s, tecken/12) + 0,9 s (entré + ren sorti),
# och text som läses i följd i en scen får lästiden för all text tillsammans räknat från första biten.
READ_CPS, READ_MIN_S, READ_OVERHEAD_S = 12.0, 5 / 6, 0.9


def read_s(text):
    return max(READ_MIN_S, len(text) / READ_CPS) + READ_OVERHEAD_S


# ---------------------------------------------------------------- tidslinje (sekunder)
T_S1 = 0.00                  # mörk bild + "HITTA FARAN." + timer
T_S2 = 2.40                  # svart "SÅG DU DET?"
T_S3 = T_S2 + 1.90           # mörk bild "En gång till." + timer
T_S4 = T_S3 + 2.20           # svart "SVÅRT, VA?" / "Då tänder vi."
T_S5 = T_S4 + 2.90           # mörk bild, förväntan, klick
T_CLICK = T_S5 + 0.42
T_S6 = T_S5 + 1.25           # ljus bild, "DÄR."
T_DAR = T_S6 + 0.567       # 0,567: klick → SE MER. blir exakt 8 takter i låten (100 BPM)
T_S7 = T_DAR + 2.25          # slider
T_S8 = T_S7 + 5.75           # svart, fakta
T_S9 = T_S8 + 5.55           # mörk bild, "Det du inte ser …"
T_S10 = T_S9 + 4.25          # ljus bild, "SE MER. TIDIGARE."
T_S11 = T_S10 + 2.40         # slutbild
DUR = round(T_S11 + 7.25, 2)

TIMER1 = (0.30, 2.30)
TIMER2 = (T_S3 + 0.20, T_S3 + 2.15)

# entréer (sekunder efter scenstart)
S4_LINE2 = 0.60
SLIDER_LINES = (0.45, 1.75, 3.25)                       # SAMMA VÄG. / SAMMA RÅDJUR. / HELT ANNAN SIKT.
SLIDER_MOVES = ((0.0, 0.75, 540.0), (1.60, 2.25, 1000.0), (3.05, 3.75, 470.0))
FACT_L1, FACT_L2, FACT_NUM, FACT_UNIT = 0.15, 1.75, 3.35, 3.90
QUOTE_L1, QUOTE_L2 = 0.12, 1.35
SEE_L1, SEE_L2 = 0.04, 0.60
END_CIRCLE, END_WORD, END_L1, END_L2 = 0.60, 0.95, 1.30, 1.75
END_STROKE = END_L2 + 0.30            # understrykningen ritas

# (grupp, text, syns från, syns till) – "till" = när texten börjar tona ut eller klipps bort
TEXTS = [
    ("s1", "HITTA FARAN.", T_S1 + 0.08, T_S2),
    ("s2", "SÅG DU DET?", T_S2 + 0.03, T_S3),
    ("s3", "En gång till.", T_S3 + 0.08, T_S4),
    ("s4", "SVÅRT, VA?", T_S4 + 0.03, T_S5),
    ("s4", "Då tänder vi.", T_S4 + S4_LINE2, T_S5),
    ("s6", "DÄR.", T_DAR, T_S7 - 0.35),
    ("s6", "RÅDJUR", T_DAR + 0.12, T_S7 - 0.35),
    ("s7", "SAMMA VÄG.", T_S7 + SLIDER_LINES[0], T_S8 - 0.25),
    ("s7", "SAMMA RÅDJUR.", T_S7 + SLIDER_LINES[1], T_S8 - 0.25),
    ("s7", "HELT ANNAN SIKT.", T_S7 + SLIDER_LINES[2], T_S8 - 0.25),
    ("s8", "Du letade i 2 sekunder.", T_S8 + FACT_L1, T_S9),
    ("s8", "I 90 km/h hinner bilen", T_S8 + FACT_L2, T_S9),
    ("s8", "50 METER", T_S8 + FACT_NUM, T_S9),
    ("s9", "Det du inte ser", T_S9 + QUOTE_L1, T_S10),
    ("s9", "kan du inte reagera på.", T_S9 + QUOTE_L2, T_S10),
    ("s10", "SE MER.", T_S10 + SEE_L1, T_S11),
    ("s10", "TIDIGARE.", T_S10 + SEE_L2, T_S11),
    ("s11", "Extraljus för svenska vägar.", T_S11 + END_L1, DUR - 0.5),
    ("s11", "Hitta rätt ljus på FAIV.se", T_S11 + END_L2, DUR - 0.5),
]


def check_reading():
    """Kontrollera läsregeln; returnerar lista med brott (tom = ok)."""
    bad = []
    for g, txt, t0, t1 in TEXTS:
        need = read_s(txt)
        if t1 - t0 < need - 1e-6:
            bad.append(f"{txt!r}: syns {t1 - t0:.2f} s, behöver {need:.2f} s")
    groups = {}
    for g, txt, t0, t1 in TEXTS:
        groups.setdefault(g, []).append((txt, t0, t1))
    for g, items in groups.items():
        if len(items) < 2:
            continue
        chars = sum(len(t) for t, _, _ in items)
        need = max(READ_MIN_S, chars / READ_CPS) + READ_OVERHEAD_S
        span = max(e for _, _, e in items) - min(s for _, s, _ in items)
        if span < need - 1e-6:
            bad.append(f"scen {g} ({chars} tecken): {span:.2f} s, behöver {need:.2f} s")
    return bad


# ---------------------------------------------------------------- textplacering
# All text utom slutkortet har sin första rad på samma höjd (versalernas mitt), följande rader under.
TEXT_Y = 300

# ---------------------------------------------------------------- geometri (2x-plåtens koordinater)
PW, PH = 1882, 3344
ANCHOR = np.array([1100.0, 1300.0])          # push-in mot vägen/rådjuret
BASE = max(W / PW, H / PH)
VP = np.array([930.0, 1262.0])               # vägens flyktpunkt
DEER_BOX = (1596, 1286, 1744, 1474)
EYES = [(1619, 1328), (1633, 1327)]

WHITE = np.array([255, 255, 255], np.float32)
RED = np.array([250, 12, 24], np.float32)    # sätts om från loggan


# ---------------------------------------------------------------- easing
def clamp01(x):
    return min(1.0, max(0.0, x))


def prog(t, t0, d):
    return clamp01((t - t0) / d)


def e_out3(x):
    return 1 - (1 - x) ** 3


def e_inout3(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def e_out_expo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def e_out_back(x, s=1.4):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def smoothstep(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- resurser (laddas en gång per process)
R = {}


def load():
    if R:
        return
    R["dark"] = Image.open(os.path.join(HERE, "build/dark.png")).convert("RGB")
    R["lit"] = Image.open(os.path.join(HERE, "build/lit.png")).convert("RGB")
    R["T"] = Image.open(os.path.join(HERE, "build/reveal_T.png"))
    logo = Image.open(os.path.join(HERE, "src/logo.png")).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
    # dela i cirkel och ordbild vid första tomma kolumnen efter cirkeln
    a = np.asarray(logo.getchannel("A"))
    cols = a.max(0)
    split = next(i for i in range(int(a.shape[1] * 0.2), a.shape[1]) if cols[i] < 8)
    R["logo_circle"] = logo.crop((0, 0, split, logo.height))
    rest = logo.crop((split, 0, logo.width, logo.height))
    R["logo_word"] = rest.crop(rest.getchannel("A").getbbox())
    R["logo_word_dx"] = split + rest.getchannel("A").getbbox()[0]
    R["logo_word_dy"] = rest.getchannel("A").getbbox()[1]
    la = np.asarray(R["logo_circle"]).astype(np.float32)
    m = la[..., 3] > 200
    red = la[..., :3][m & (la[..., 0] > 180) & (la[..., 1] < 80)]
    if len(red):
        RED[:] = np.median(red, 0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r2 = ((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.47) / (H * 0.6)) ** 2
    R["vignette"] = np.clip(1 - 0.12 * r2, 0.85, 1)[..., None].astype(np.float32)


def build_reveal_map():
    """Tidskarta för ljusets utbredning: 0 = tänds först (nära bilen/kanterna), 1 = sist (flyktpunkten)."""
    dark = np.asarray(Image.open(os.path.join(HERE, "build/dark.png")).convert("L"), np.float32)
    lit = np.asarray(Image.open(os.path.join(HERE, "build/lit.png")).convert("L"), np.float32)
    yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
    dx, dy = xx - VP[0], yy - VP[1]
    car_front = 1500.0                       # vägytan precis framför bilen (2x)
    # A) strålen: asfalten tänds från bilen mot flyktpunkten
    road = (dy > 0) & (np.abs(dx) < 1.9 * dy + 10)
    road = ndi.gaussian_filter(road.astype(np.float32), 10)
    far = 1 - np.clip(dy / (car_front - VP[1]), 0, 1)
    T_road = 0.30 * far ** 0.7
    # B) solfjädern: resten tänds utåt från vägens axel (vinkel runt flyktpunkten)
    theta = np.arctan2(np.sqrt(dx ** 2 + 90.0 ** 2), dy) / np.pi        # 0 = rakt ner längs vägen, 1 = rakt upp
    near = np.clip(np.sqrt(dx ** 2 + (2.5 * dy) ** 2) / 1100.0, 0, 1)
    T_fan = 0.22 + 0.78 * np.clip(theta, 0, 1) ** 1.25 - 0.12 * near
    T = road * np.minimum(T_road, T_fan) + (1 - road) * T_fan
    gain = ndi.gaussian_filter(np.clip(lit - dark, 0, None), 6)
    gain /= np.percentile(gain, 99) + 1e-6
    T -= 0.06 * np.clip(gain, 0, 1)
    T = ndi.gaussian_filter(T, 8)
    T = (T - T.min()) / (T.max() - T.min())
    Image.fromarray((T * 255).astype(np.uint8)).save(os.path.join(HERE, "build/reveal_T.png"))


@lru_cache(maxsize=64)
def font(key, size):
    if key == "head":
        f = ImageFont.truetype(F_HEAD, size)
        f.set_variation_by_axes([115, 800])
    elif key == "sent":
        f = ImageFont.truetype(F_HEAD, size)
        f.set_variation_by_axes([100, 700])
    else:
        f = ImageFont.truetype(F_INTER[int(key[5:])], size)
    return f


@lru_cache(maxsize=512)
def text_mask(text, key, size, tracking):
    """Alfamask + skuggmask för en textrad (kerning bevaras, tracking läggs ovanpå)."""
    f = font(key, size)
    asc, desc = f.getmetrics()
    pad = int(size * 0.5)
    adv = [f.getlength(text[: i + 1]) - f.getlength(text[:i]) for i in range(len(text))]
    total = sum(adv) + tracking * (len(text) - 1)
    im = Image.new("L", (int(math.ceil(total)) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    x = pad
    for c, a in zip(text, adv):
        d.text((x, pad), c, font=f, fill=255)
        x += a + tracking
    sh = im.filter(ImageFilter.GaussianBlur(size * 0.22))
    # optiskt centrum: versalhöjd
    cap = f.getbbox("H")
    cy = pad + (cap[1] + cap[3]) / 2
    return np.asarray(im, np.float32) / 255, np.asarray(sh, np.float32) / 255, pad + total / 2, cy, total


def fit_size(text, key, size, tracking, maxw):
    while size > 10:
        if text_mask(text, key, size, tracking)[4] <= maxw:
            return size
        size -= 2
    return size


def paste(canvas, mask, x0, y0, color, alpha):
    """Lägg mask (HxW 0..1) med färg på canvas vid heltalsposition."""
    h, w = mask.shape
    x0, y0 = int(round(x0)), int(round(y0))
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(W, x0 + w), min(H, y0 + h)
    if cx1 <= cx0 or cy1 <= cy0 or alpha <= 0:
        return
    m = mask[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0, None] * alpha
    reg = canvas[cy0:cy1, cx0:cx1]
    reg *= 1 - m
    reg += m * np.asarray(color, np.float32)


def draw_text(canvas, text, key, size, cx, cy, alpha=1.0, scale=1.0, tracking=0.0, color=WHITE,
              shadow=0.55, align="center", maxw=980):
    if alpha <= 0.002:
        return
    size = fit_size(text, key, size, round(tracking * 2) / 2, maxw)
    m, sh, mx, my, total = text_mask(text, key, size, round(tracking * 2) / 2)
    if abs(scale - 1) > 1e-3:
        hh, ww = m.shape
        nw, nh = max(1, int(ww * scale)), max(1, int(hh * scale))
        m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((nw, nh), Image.BICUBIC), np.float32) / 255
        sh = np.asarray(Image.fromarray((sh * 255).astype(np.uint8)).resize((nw, nh), Image.BICUBIC), np.float32) / 255
        mx, my, total = mx * scale, my * scale, total * scale
    if align == "left":
        mx -= total / 2
    elif align == "right":
        mx += total / 2
    if shadow:
        paste(canvas, sh, cx - mx, cy - my + size * 0.04, (0, 0, 0), alpha * shadow)
    paste(canvas, m, cx - mx, cy - my, color, alpha)


def enter(t, t0, dur=0.38, rise=14, track_from=7.0):
    """Standardentré: fade + lätt scale-in + tracking som dras ihop. Returnerar (alpha, scale, dy, dtrack)."""
    p = prog(t, t0, dur)
    e = e_out3(p)
    return e, 1.035 - 0.035 * e, rise * (1 - e), track_from * (1 - e_out3(prog(t, t0, dur * 1.6)))


# ---------------------------------------------------------------- kamera
def camera(t):
    """Skala och förskjutning för plåten. Push-in 1,5 % över hela filmen + skak vid klicket."""
    z = 1.0 + 0.015 * clamp01(t / DUR)
    s = BASE * z
    sx = sy = 0.0
    if T_CLICK <= t < T_CLICK + 0.32:
        k = t - T_CLICK
        amp = 7.0 * math.exp(-k * 11)
        sx = amp * math.sin(k * 2 * math.pi * 17.0)
        sy = amp * 0.7 * math.sin(k * 2 * math.pi * 23.0 + 1.3)
    P = ANCHOR * BASE + np.array([sx, sy])
    return s, P


def plate_affine(t):
    s, P = camera(t)
    a = 1 / s
    return (a, 0, ANCHOR[0] - P[0] * a, 0, a, ANCHOR[1] - P[1] * a), s, P


def to_screen(t, x, y):
    _, s, P = plate_affine(t)
    return (x - ANCHOR[0]) * s + P[0], (y - ANCHOR[1]) * s + P[1]


def plate(name, t):
    aff, _, _ = plate_affine(t)
    im = R[name].transform((W, H), Image.AFFINE, aff, resample=Image.BICUBIC)
    return np.asarray(im, np.float32) if name != "T" else np.asarray(im, np.float32) / 255


# ---------------------------------------------------------------- effekter
def bloom(img, strength, thresh=150.0):
    if strength <= 0:
        return img
    small = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W // 6, H // 6), Image.BILINEAR), np.float32)
    hi = np.clip(small - thresh, 0, None) * (255 / (255 - thresh))
    b1 = ndi.gaussian_filter(hi, (3, 3, 0))
    b2 = ndi.gaussian_filter(hi, (10, 10, 0))
    b = 0.6 * b1 + 0.4 * b2
    big = np.asarray(Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
    return img + big * strength


def timer_bar(canvas, t, t0, t1, cy, width=300):
    if t < t0 - 0.2:
        return
    a = prog(t, t0 - 0.2, 0.2)
    p = 1 - prog(t, t0, t1 - t0)
    w = width * p
    x0 = W / 2 - width / 2
    # spår
    canvas[cy - 1:cy + 2, int(x0):int(x0 + width)] *= 1 - 0.25 * a
    canvas[cy - 1:cy + 2, int(x0):int(x0 + width)] += 255 * 0.12 * a
    if w > 1:
        xa, xb = int(W / 2 - w / 2), int(W / 2 + w / 2)
        canvas[cy - 1:cy + 2, xa:xb] = canvas[cy - 1:cy + 2, xa:xb] * (1 - 0.9 * a) + 255 * 0.9 * a


def brackets(canvas, t, t0):
    p = prog(t, t0, 0.30)
    if p <= 0:
        return
    e = e_out_back(p, 1.2)
    x0, y0 = to_screen(t, DEER_BOX[0], DEER_BOX[1])
    x1, y1 = to_screen(t, DEER_BOX[2], DEER_BOX[3])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    k = 1.45 - 0.45 * e
    hw, hh = (x1 - x0) / 2 * k + 10, (y1 - y0) / 2 * k + 10
    L = 22
    alpha = min(1.0, p * 2.2) * (1 - 0.35 * prog(t, t0 + 1.0, 0.4))
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = cx + sx * hw, cy + sy * hh
            d.line([(px, py), (px - sx * L, py)], fill=255, width=3)
            d.line([(px, py), (px, py - sy * L)], fill=255, width=3)
    m = np.asarray(img, np.float32) / 255
    paste(canvas, ndi.gaussian_filter(m, 4) * 0.8, 0, 0, (0, 0, 0), alpha * 0.6)
    paste(canvas, m, 0, 0, WHITE, alpha)
    # etikett
    if p > 0.4:
        la = clamp01((p - 0.4) / 0.6) * alpha
        draw_text(canvas, "RÅDJUR", "inter700", 22, cx - hw, cy - hh - 26, la, tracking=4, align="left", shadow=0.8)


def eye_glint(canvas, t, t0):
    p = prog(t, t0, 0.55)
    if p <= 0 or p >= 1:
        return
    k = math.sin(math.pi * p) ** 1.5
    for ex, ey in EYES:
        x, y = to_screen(t, ex, ey)
        r = 26
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
        core = np.exp(-(xx ** 2 + yy ** 2) / (2 * 1.6 ** 2))
        halo = np.exp(-(xx ** 2 + yy ** 2) / (2 * 6.0 ** 2)) * 0.35
        star = (np.exp(-(yy ** 2) / 0.9) * np.exp(-np.abs(xx) / 7) + np.exp(-(xx ** 2) / 0.9) * np.exp(-np.abs(yy) / 7)) * 0.7
        m = np.clip(core + halo + star, 0, 1) * k
        x0, y0 = int(x) - r, int(y) - r
        reg = canvas[y0:y0 + 2 * r + 1, x0:x0 + 2 * r + 1]
        reg += m[..., None] * np.array([215, 255, 225], np.float32) * 0.9


def grain(img, fi, amount=3.2):
    rng = np.random.default_rng(1000 + fi)
    n = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, 0), 2, 1)
    return img + n[..., None] * amount


# ---------------------------------------------------------------- scener
def scene_dark_hunt(t, t0, label, small, timer):
    img = plate("dark", t)
    # första bildrutan: bilden finns redan, lyfter snabbt från 60 %
    if t0 == T_S1:
        img *= 0.6 + 0.4 * e_out3(prog(t, 0, 0.35))
    img = bloom(img, 0.35)
    a, sc, dy, dtr = enter(t, t0 + 0.08)
    if small:
        draw_text(img, label, "inter600", 46, W / 2, TEXT_Y + dy, a, sc, 1.0 + dtr * 0.5)
    else:
        draw_text(img, label, "head", 74, W / 2, TEXT_Y + dy, a, sc, 2.0 + dtr)
    timer_bar(img, t, timer[0], timer[1], TEXT_Y + 72)
    return img


def scene_black_card(t, t0, line1, line2=None, t2=None):
    img = np.zeros((H, W, 3), np.float32)
    a, sc, dy, dtr = enter(t, t0 + 0.03, dur=0.3, rise=0)
    sc = 1.06 - 0.06 * e_out_expo(prog(t, t0, 0.45))
    draw_text(img, line1, "head", 104, W / 2, TEXT_Y, a, sc, 1.0 + dtr * 0.6, shadow=0)
    if line2:
        a2, sc2, dy2, dtr2 = enter(t, t2)
        draw_text(img, line2, "inter500", 48, W / 2, TEXT_Y + 110 + dy2, a2 * 0.82, sc2, dtr2 * 0.4, shadow=0)
    return img


def scene_reveal(t):
    D = plate("dark", t)
    if t < T_CLICK:
        # förväntan: bilden andas ut lite
        D *= 1 - 0.14 * e_inout3(prog(t, T_S5 + 0.1, T_CLICK - T_S5 - 0.1))
        return bloom(D, 0.35)
    L = plate("lit", t)
    T = plate("T", t)[..., None]
    k = t - T_CLICK
    p = -0.18 + 1.40 * e_out3(clamp01(k / 0.62))
    f = 0.16
    M = smoothstep(0, 1, (p - T) / f)
    rim = np.exp(-(((p - T) - 0.05) / 0.06) ** 2) * (1 - clamp01((k - 0.45) / 0.3))
    bump = math.exp(-((k - 0.14) / 0.22) ** 2) if k < 1.2 else 0.0
    expo = 1.0 + 0.14 * bump
    img = D * (1 - M) + L * M * expo
    img += L * rim * 0.35 + rim * 10
    if k < 2 / FPS:                       # tändningsögonblicket
        img += 18
    return bloom(img, 0.30 + 0.6 * bump, thresh=140)


def scene_lit(t):
    img = plate("lit", t)
    img = bloom(img, 0.30)
    if t >= T_DAR:
        # fokus: allt utom rådjuret dimmas, släpps innan slidern
        d_in = e_out3(prog(t, T_DAR, 0.35))
        d_out = e_inout3(prog(t, T_S7 - 0.45, 0.45))
        k = 0.34 * d_in * (1 - d_out)
        if k > 0:
            x0, y0 = to_screen(t, DEER_BOX[0], DEER_BOX[1])
            x1, y1 = to_screen(t, DEER_BOX[2], DEER_BOX[3])
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            yy, xx = np.ogrid[0:H, 0:W]
            d = np.sqrt(((xx - cx) / 150.0) ** 2 + ((yy - cy) / 170.0) ** 2)
            focus = np.clip((d - 0.7) / 0.9, 0, 1).astype(np.float32)
            img *= 1 - k * focus[..., None]
        brackets(img, t, T_DAR)
        eye_glint(img, t, T_DAR + 0.10)
        a, sc, dy, dtr = enter(t, T_DAR, dur=0.3)
        a *= 1 - prog(t, T_S7 - 0.35, 0.3)
        draw_text(img, "DÄR.", "head", 112, W / 2, TEXT_Y + dy, a, sc, 2.0 + dtr)
    return img


def slider_x(t):
    keys = [(T_S7, 0.0)]
    for a, b, x in SLIDER_MOVES:
        keys += [(T_S7 + a, keys[-1][1]), (T_S7 + b, x)]
    keys = keys[1:]
    if t <= keys[0][0]:
        return keys[0][1]
    for (ta, xa), (tb, xb) in zip(keys, keys[1:]):
        if t <= tb:
            return xa + (xb - xa) * e_inout3((t - ta) / (tb - ta))
    return keys[-1][1]


def scene_slider(t):
    D = bloom(plate("dark", t), 0.35)
    L = bloom(plate("lit", t), 0.30)
    x = slider_x(t)
    xs = np.arange(W, dtype=np.float32)
    m = np.clip((xs - x + 1.0) / 2.0, 0, 1)[None, :, None]       # 0 = mörk (vänster), 1 = ljus (höger)
    img = D * (1 - m) + L * m
    # ljusstråle: tunn linje + glöd
    g = np.exp(-((xs - x) / 16.0) ** 2) * 0.38 + np.exp(-((xs - x) / 2.0) ** 2) * 0.9
    ys = np.arange(H, dtype=np.float32)
    vfade = 1 - 0.88 * smoothstep(TEXT_Y - 100, TEXT_Y - 50, ys) * (1 - smoothstep(TEXT_Y + 240, TEXT_Y + 290, ys))  # bakom raderna
    img += vfade[:, None, None] * g[None, :, None] * np.array([255, 250, 238], np.float32)
    enter_a = e_out3(prog(t, T_S7, 0.3))
    # handtag
    if 30 < x < W - 30:
        hy = TEXT_Y + 370
        r = 26
        yy, xx = np.ogrid[-r - 3:r + 4, -r - 3:r + 4]
        dist = np.sqrt(xx ** 2 + yy ** 2)
        ring = np.clip(1.6 - np.abs(dist - r), 0, 1).astype(np.float32)
        fill = (dist < r).astype(np.float32)
        paste(img, fill, x - r - 3, hy - r - 3, (10, 10, 12), 0.55 * enter_a)
        paste(img, ring, x - r - 3, hy - r - 3, WHITE, 0.95 * enter_a)
        tri = Image.new("L", (2 * r + 7, 2 * r + 7), 0)
        d = ImageDraw.Draw(tri)
        c = r + 3
        d.polygon([(c - 6, c - 7), (c - 6, c + 7), (c - 14, c)], fill=255)
        d.polygon([(c + 6, c - 7), (c + 6, c + 7), (c + 14, c)], fill=255)
        paste(img, np.asarray(tri, np.float32) / 255, x - r - 3, hy - r - 3, WHITE, 0.95 * enter_a)
    # etiketter som följer strålen
    la = e_out3(prog(t, T_S7 + 0.4, 0.4)) * (1 - prog(t, T_S8 - 0.3, 0.25))
    left_room = clamp01((x - 230) / 80)
    right_room = clamp01((W - x - 280) / 80)
    draw_text(img, "HELLJUS", "inter700", 28, x - 26, TEXT_Y + 370, la * left_room, tracking=4, align="right", shadow=0.8)
    draw_text(img, "EXTRALJUS", "inter700", 28, x + 26, TEXT_Y + 370, la * right_room, tracking=4, align="left", shadow=0.8)
    # rader
    lines = [("SAMMA VÄG.", T_S7 + SLIDER_LINES[0], TEXT_Y, 62), ("SAMMA RÅDJUR.", T_S7 + SLIDER_LINES[1], TEXT_Y + 86, 62),
             ("HELT ANNAN SIKT.", T_S7 + SLIDER_LINES[2], TEXT_Y + 186, 78)]
    out = 1 - prog(t, T_S8 - 0.25, 0.25)
    for txt, t0, y, size in lines:
        a, sc, dy, dtr = enter(t, t0)
        draw_text(img, txt, "head", size, W / 2, y + dy, a * out, sc, 1.5 + dtr, shadow=0.75)
    return img


def scene_fact(t):
    img = np.zeros((H, W, 3), np.float32)
    a1, s1, d1, r1 = enter(t, T_S8 + FACT_L1)
    a2, s2, d2, r2 = enter(t, T_S8 + FACT_L2)
    draw_text(img, "Du letade i 2 sekunder.", "inter500", 52, W / 2, TEXT_Y + d1, a1 * 0.85, s1, r1 * 0.3, shadow=0)
    draw_text(img, "I 90 km/h hinner bilen", "inter500", 52, W / 2, TEXT_Y + 78 + d2, a2 * 0.85, s2, r2 * 0.3, shadow=0)
    t0 = T_S8 + FACT_NUM
    p = prog(t, t0, 0.75)
    if t >= t0 - 0.05:
        n = int(round(50 * e_out3(p)))
        a3 = e_out3(prog(t, t0 - 0.05, 0.2))
        # högerjustera mot bredden av "50" så siffrorna inte hoppar
        w50 = text_mask("50", "head", 330, 0.0)[4]
        draw_text(img, str(n), "head", 330, W / 2 + w50 / 2, TEXT_Y + 300, a3, 1.0, 0.0, align="right", shadow=0)
        a4, s4, d4, r4 = enter(t, T_S8 + FACT_UNIT)
        draw_text(img, "METER", "head", 72, W / 2, TEXT_Y + 495 + d4, a4, s4, 22 + r4, color=RED, shadow=0)
    return img


def scene_dark_quote(t):
    img = plate("dark", t)
    img = bloom(img, 0.35)
    img *= 0.62
    a1, s1, d1, r1 = enter(t, T_S9 + QUOTE_L1)
    a2, s2, d2, r2 = enter(t, T_S9 + QUOTE_L2)
    draw_text(img, "Det du inte ser", "sent", 66, W / 2, TEXT_Y + d1, a1, s1, r1 * 0.5, shadow=0.8)
    draw_text(img, "kan du inte reagera på.", "sent", 66, W / 2, TEXT_Y + 92 + d2, a2, s2, r2 * 0.5, shadow=0.8)
    return img


def scene_see_more(t):
    img = plate("lit", t)
    k = t - T_S10
    flash = math.exp(-k / 0.12) * 0.35
    img = bloom(img * (1 + flash), 0.30 + flash * 2)
    a1, s1, d1, r1 = enter(t, T_S10 + SEE_L1, dur=0.3)
    a2, s2, d2, r2 = enter(t, T_S10 + SEE_L2, dur=0.3)
    draw_text(img, "SE MER.", "head", 124, W / 2, TEXT_Y + d1, a1, s1, 2.0 + r1, shadow=0.7)
    draw_text(img, "TIDIGARE.", "head", 124, W / 2, TEXT_Y + 140 + d2, a2, s2, 2.0 + r2, color=RED, shadow=0.7)
    return img


@lru_cache(maxsize=4)
def brush_stroke(length):
    """Tunt rent drag med en liten, mjuk kulle på mitten och avsmalnande ändar (ritat med penna, inte slarvigt)."""
    ss = 4                                     # supersampling
    L = length * ss
    h = 20 * ss
    u = np.linspace(0, 1, L)
    mid = h / 2 + (1.2 - 2.4 * np.sin(np.pi * u)) * ss          # kulle: mitten ~2,4 px högre än ändarna
    width = (1.7 + 1.1 * np.sin(np.pi * u)) * ss                 # tjockast på mitten
    width *= np.clip(u / 0.06, 0, 1) ** 0.5 * np.clip((1 - u) / 0.10, 0, 1) ** 0.6
    yy = np.arange(h, dtype=np.float32)[:, None]
    m = np.clip(width[None, :] / 2 - np.abs(yy - mid[None, :]) + 0.5 * ss, 0, ss) / ss
    small = Image.fromarray((m * 255).astype(np.uint8)).resize((length, h // ss), Image.LANCZOS)
    return np.asarray(small, np.float32) / 255


def taillight_layer(t):
    L = plate("lit", t)
    r, g, b = L[..., 0], L[..., 1], L[..., 2]
    m = np.clip((r - np.maximum(g, b) * 1.5 - 25) / 60, 0, 1) * np.clip((r - 70) / 60, 0, 1)
    return L * m[..., None]


def scene_end(t):
    k = t - T_S11
    # 1) allt utom bakljusen tonar till svart, bakljusen glöder upp
    fade = e_inout3(prog(t, T_S11, 0.5))
    tl_out = e_inout3(prog(t, T_S11 + 0.5, 0.55))
    img = np.zeros((H, W, 3), np.float32)
    if tl_out < 1:
        L = plate("lit", t)
        tl = taillight_layer(t)
        base = L * (1 - fade) + tl * fade
        base = bloom(base, 0.30 + 1.6 * fade, thresh=90)
        if tl_out > 0:
            # bakljusen sugs mot loggans cirkel: zoom + oskärpa + fade
            z = 1 + 0.5 * tl_out
            im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
            cx, cy = W / 2, 1030
            aff = (1 / z, 0, cx - cx / z, 0, 1 / z, cy - cy / z)
            im = im.transform((W, H), Image.AFFINE, aff, resample=Image.BILINEAR)
            im = im.filter(ImageFilter.GaussianBlur(2 + 26 * tl_out))
            base = np.asarray(im, np.float32)
        img += base * (1 - tl_out)
    # 2) loggan
    lockup_w = 720
    circ, word = R["logo_circle"], R["logo_word"]
    total_w = R["logo_word_dx"] + word.width
    sc = lockup_w / total_w
    lx0 = W / 2 - lockup_w / 2
    ly0 = 860 - circ.height * sc / 2
    pc = prog(t, T_S11 + END_CIRCLE, 0.55)
    if pc > 0:
        e = e_out3(pc)
        s2 = sc * (1.14 - 0.14 * e)
        cw, ch = int(circ.width * s2), int(circ.height * s2)
        ci = circ.resize((cw, ch), Image.LANCZOS)
        blur = 22 * (1 - e)
        if blur > 0.3:
            ci = ci.filter(ImageFilter.GaussianBlur(blur))
        arr = np.asarray(ci, np.float32)
        ccx = lx0 + circ.width * sc / 2
        ccy = ly0 + circ.height * sc / 2
        # glöd bakom cirkeln som ärver bakljusens rött
        glow = ndi.gaussian_filter(arr[..., 3] / 255, 18) * 0.55 * (1 - 0.6 * e)
        paste(img, glow, ccx - cw / 2, ccy - ch / 2, RED, min(1, pc * 3))
        a = arr[..., 3] / 255
        x0, y0 = int(round(ccx - cw / 2)), int(round(ccy - ch / 2))
        reg = img[y0:y0 + ch, x0:x0 + cw]
        al = (a * min(1.0, e * 1.4))[..., None]
        reg *= 1 - al
        reg += al * arr[..., :3]
    pw = prog(t, T_S11 + END_WORD, 0.5)
    if pw > 0:
        e = e_inout3(pw)
        ww, wh = int(word.width * sc), int(word.height * sc)
        wi = np.asarray(word.resize((ww, wh), Image.LANCZOS), np.float32)
        a = wi[..., 3] / 255
        xs = np.arange(ww, dtype=np.float32)
        edge = e * (ww + 60) - 30
        wipe = np.clip((edge - xs) / 30 + 0.5, 0, 1)[None, :]
        a = a * wipe
        # glans som sveper över ordbilden
        ps = prog(t, T_S11 + 2.0, 0.7)
        col = wi[..., :3].copy()
        if 0 < ps < 1:
            yy, xx = np.mgrid[0:wh, 0:ww].astype(np.float32)
            band = np.exp(-(((xx + yy * 0.5) - (ps * (ww + wh) - wh * 0.25)) / 26) ** 2)
            col = col * (1 - 0.0) + band[..., None] * 60
        x0 = int(round(lx0 + R["logo_word_dx"] * sc - 16 * (1 - e)))
        y0 = int(round(ly0 + R["logo_word_dy"] * sc))
        reg = img[y0:y0 + wh, x0:x0 + ww]
        reg *= 1 - a[..., None]
        reg += a[..., None] * col
    # 3) rader
    a1, s1, d1, r1 = enter(t, T_S11 + END_L1)
    a2, s2, d2, r2 = enter(t, T_S11 + END_L2)
    y1 = 860 + circ.height * sc / 2 + 120
    draw_text(img, "Extraljus för svenska vägar.", "inter600", 50, W / 2, y1 + d1, a1, s1, r1 * 0.3, shadow=0)
    pre, url = "Hitta rätt ljus på ", "FAIV.se"
    f = font("inter500", 44)
    wpre, wurl = f.getlength(pre), font("inter700", 44).getlength(url)
    x0 = W / 2 - (wpre + wurl) / 2
    y2 = y1 + 80 + d2
    draw_text(img, pre, "inter500", 44, x0, y2, a2 * 0.72, 1.0, 0, align="left", shadow=0)
    draw_text(img, url, "inter700", 44, x0 + wpre, y2, a2, 1.0, 0, align="left", shadow=0)
    # röd handritad understrykning som ritas fram från vänster
    pu = prog(t, T_S11 + END_STROKE, 0.42)
    if pu > 0:
        sx0, sy = int(round(x0 + wpre)) - 8, int(round(y2 + 30))
        m = brush_stroke(int(round(wurl)) + 16)
        hh, ww = m.shape
        edge = e_inout3(pu) * (ww + 24) - 12
        reveal = np.clip((edge - np.arange(ww, dtype=np.float32)) / 10 + 0.5, 0, 1)[None, :]
        paste(img, m * reveal, sx0, sy - hh // 2, RED, a2)
    return img


def frame(t, fi=0):
    if t < T_S2:
        img = scene_dark_hunt(t, T_S1, "HITTA FARAN.", False, TIMER1)
    elif t < T_S3:
        img = scene_black_card(t, T_S2, "SÅG DU DET?")
    elif t < T_S4:
        img = scene_dark_hunt(t, T_S3, "En gång till.", True, TIMER2)
    elif t < T_S5:
        img = scene_black_card(t, T_S4, "SVÅRT, VA?", "Då tänder vi.", T_S4 + S4_LINE2)
    elif t < T_S6:
        img = scene_reveal(t)
    elif t < T_S7:
        img = scene_lit(t)
    elif t < T_S8:
        img = scene_slider(t)
    elif t < T_S9:
        img = scene_fact(t)
    elif t < T_S10:
        img = scene_dark_quote(t)
    elif t < T_S11:
        img = scene_see_more(t)
    else:
        img = scene_end(t)
    img = img * R["vignette"]
    img = grain(img, fi)
    return np.clip(img, 0, 255).astype(np.uint8)


def _work(fi):
    load()
    return frame(fi / FPS, fi).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float)
    ap.add_argument("--range", nargs=2, type=float)
    ap.add_argument("--out", default=os.path.join(HERE, "out/video_noaudio.mp4"))
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()
    bad = check_reading()
    if bad:
        sys.exit("Läsregeln bryts:\n  " + "\n  ".join(bad))
    if not os.path.exists(os.path.join(HERE, "build/reveal_T.png")):
        build_reveal_map()
    load()
    if args.stills is not None:
        for t in args.stills:
            Image.fromarray(frame(t, int(t * FPS))).save(os.path.join(HERE, f"build/still_{t:05.2f}.png"))
        return
    t0, t1 = args.range if args.range else (0, DUR)
    frames = list(range(int(round(t0 * FPS)), int(round(t1 * FPS))))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(args.jobs) as pool:
        for i, buf in enumerate(pool.imap(_work, frames, chunksize=2)):
            enc.stdin.write(buf)
            if i % 60 == 0:
                print(f"{i}/{len(frames)}", file=sys.stderr, flush=True)
    enc.stdin.close()
    enc.wait()
    print("klar:", args.out)


if __name__ == "__main__":
    main()
