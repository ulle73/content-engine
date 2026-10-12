"""Bildförberedelse: retusch (märkestext), gradering av mörka bilden, uppskalning.

Kör: ../../.venv/Scripts/python.exe -I prep.py
Skriver build/dark.png, build/lit.png (2x, linjerade), build/deer_mask.png m.m.
"""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

SRC_W, SRC_H = 941, 1672
SCALE = 2
rng = np.random.default_rng(7)
import os  # noqa: E402
DARKEN = float(os.environ.get('DARKEN', '0.55'))  # 0,55 = rådjuret svårt men hittbart (0,4 och 0,48 syntes för tydligt)
OUT = os.environ.get('PREP_OUT', 'build')

# Rektanglar (x0, y0, x1, y1) i källkoordinater – bokstäver, spegling i kromlisten, modellemblem.
BADGES = [
    (386, 903, 554, 917),
    (386, 920, 554, 931),
    (294, 961, 336, 977),
    (607, 961, 648, 977),
]
# Rådjurets ungefärliga plats i källkoordinater (för markering och mörkläggning).
DEER = dict(x0=800, y0=650, x1=870, y1=735)


def retouch(a):
    """Fyll varje rektangel radvis med linjär övergång mellan flankerna till vänster och höger.

    Bakluckans struktur är horisontell (lister, kromlinje), så radvis interpolation bevarar den.
    """
    a = a.copy()
    for x0, y0, x1, y1 in BADGES:
        left = a[y0:y1, x0 - 6:x0].mean(1)
        right = a[y0:y1, x1:x1 + 6].mean(1)
        n = x1 - x0
        for i in range(n):
            t = (i + 0.5) / n
            a[y0:y1, x0 + i] = left * (1 - t) + right * t
        a[y0:y1, x0:x1] += rng.normal(0, 0.8, (y1 - y0, n, 1))
    return a


def soft_ellipse(h, w, cx, cy, rx, ry, feather):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    return np.clip((1 + feather - d) / feather, 0, 1)


def main():
    dark = np.asarray(Image.open("src/dark.webp").convert("RGB"), np.float32)
    lit = np.asarray(Image.open("src/lit.webp").convert("RGB"), np.float32)

    dark = retouch(dark)
    lit = retouch(lit)

    # --- Gradering av mörka bilden: rådjuret och högra vägkanten nästan svarta ---
    h, w = SRC_H, SRC_W
    # stor mjuk zon runt rådjuret + kanten bakom. DARKEN styr hur mycket (0 = orört).
    zone = soft_ellipse(h, w, 835, 690, 150, 120, 0.9)
    luma = dark.mean(2, keepdims=True)
    desat = luma + (dark - luma) * (1 - 0.35 * DARKEN / 0.4 * zone[..., None])
    dark = desat * (1 - DARKEN * zone)[..., None]

    np.clip(dark, 0, 255, out=dark)
    np.clip(lit, 0, 255, out=lit)

    big = (SRC_W * SCALE, SRC_H * SCALE)
    for name, arr in (("dark", dark), ("lit", lit)):
        im = Image.fromarray(arr.astype(np.uint8)).resize(big, Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=45, threshold=2))
        im.save(f"{OUT}/{name}.png")

    # Rådjursmask (för dimning/fokus) i 2x
    m = soft_ellipse(big[1], big[0], 835 * SCALE, 693 * SCALE, 70 * SCALE, 70 * SCALE, 0.8)
    Image.fromarray((m * 255).astype(np.uint8)).save(f"{OUT}/deer_mask.png")
    print("ok", big)


if __name__ == "__main__":
    main()
