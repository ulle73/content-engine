#!/usr/bin/env python3
"""Split finished carousel slides into animatable layers. No generative edits: the user's pixels stay.

  py prep_photo.py [--only 01 03] [--cutout] [--edge 70] [--busy 0.06]

For every source/<NN>.(png|jpg|webp) writes assets/<NN>/:
  bg.jpg       the original at 2160x2700 (2x the canvas, so camera pushes stay crisp). Frame 0 shows exactly this.
  clean.jpg    text inpainted away: only the sky shader samples it, right next to moving areas
  flow.png     R,G = wind vector field, B = how much each pixel may move (0 on text, faces, objects, UI)
  text.png     white RGBA matte of the detected text (for shine sweeps and lifted, moving type)
  head.png     matte of the headline only (the line(s) with the tallest letters), in its own tone
  accent.png   saturated shapes over the headline (brush words): re-painted on top of headline effects
  subject.png  (--cutout) the main subject cut out with HyperFrames' free local background remover
  geo.json     boxes in 1080x1350 canvas px: text lines, headline, subject, plus the image's palette
and prep/<NN>_maskvis.jpg: red = held still, green = text lines, blue = headline. LOOK AT IT: if the
headline box is wrong or sky is frozen, tune the flags (or hand-edit geo.json boxes) and re-run.
Non-4:5 images are centre-cropped to 4:5.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "source"
PREP = ROOT / "prep"
CW, CH = 1080, 1350
K = 2
W, H = CW * K, CH * K


def imread(path, flags=cv2.IMREAD_COLOR):
    """cv2.imread that also works with non-ASCII Windows paths (a, a, o with dots)."""
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, flags) if data.size else None


def imwrite(path, img, params=()):
    """cv2.imwrite that also works with non-ASCII Windows paths."""
    ok, buf = cv2.imencode(Path(path).suffix, img, list(params))
    if ok:
        buf.tofile(str(path))
    return ok


def soft(x, a, b):
    return np.clip((x - a) / (b - a), 0, 1)


def rgba(rgb, alpha):
    return np.dstack([rgb, (np.clip(alpha, 0, 1) * 255).astype(np.uint8)])


def smooth_noise(shape, scale, seed):
    r = np.random.default_rng(seed)
    small = r.standard_normal((shape[0] // scale + 3, shape[1] // scale + 3)).astype(np.float32)
    big = cv2.resize(small, (shape[1] + 3 * scale, shape[0] + 3 * scale), interpolation=cv2.INTER_CUBIC)
    big = big[scale : scale + shape[0], scale : scale + shape[1]]
    return cv2.GaussianBlur(big, (0, 0), scale / 2)


def fit45(im):
    h, w = im.shape[:2]
    target = 4 / 5
    if abs(w / h - target) > 0.01:
        if w / h > target:
            nw = int(round(h * target))
            x0 = (w - nw) // 2
            im = im[:, x0 : x0 + nw]
        else:
            nh = int(round(w / target))
            y0 = (h - nh) // 2
            im = im[y0 : y0 + nh]
        print(f"    cropped to 4:5 from {w}x{h}")
    interp = cv2.INTER_AREA if im.shape[1] > W else cv2.INTER_CUBIC
    return cv2.resize(im, (W, H), interpolation=interp)


def hexc(bgr):
    b, g, r = (int(v) for v in bgr)
    return f"#{r:02x}{g:02x}{b:02x}"


def palette(small, text_a, boxes_tries=()):
    """Dominant colours + an accent pair for effects. Saturated colour inside the text (a brush word,
    a highlight) is the designer's own accent, so it wins over saturated areas of the photo."""
    px = cv2.resize(small, (60, 75), interpolation=cv2.INTER_AREA).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, lab, cen = cv2.kmeans(px, 6, None, crit, 4, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lab.ravel(), minlength=6) / len(lab)
    hsv = cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV)[0]
    order = np.argsort(-counts)
    colors = [hexc(cen[i]) for i in order]
    score = [(hsv[i][1] / 255) * (hsv[i][2] / 255) * (counts[i] > 0.01) for i in range(6)]
    accent = accent2 = hexc(cen[int(np.argmax(score))])
    hsv_full = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    dom_h = int(cv2.cvtColor(cen[order[0]].reshape(1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV)[0, 0, 0])
    dh = np.abs(hsv_full[..., 0].astype(np.int32) - dom_h)
    vivid = (hsv_full[..., 1] > 130) & (hsv_full[..., 2] > 110) & (np.minimum(dh, 180 - dh) > 15)  # not the background's hue
    sat = vivid & (text_a > 0.5)
    for boxes in boxes_tries:  # saturated colour around the headline first, then around any text
        zone = np.zeros_like(vivid)
        for b in boxes:
            zone[b[1] : b[3], b[0] : b[2]] = True
        if (vivid & zone).sum() > 300:
            sat = vivid & zone
            break
    if sat.sum() > 300:
        hues = hsv_full[..., 0][sat].astype(np.float32)
        hues = np.where(hues < 10, hues + 180, hues)  # keep reds/magentas together across the wrap
        cols = small[sat]
        order = np.argsort(hues)
        half = len(order) // 2
        accent = hexc(np.median(cols[order[:half]], axis=0))
        accent2 = hexc(np.median(cols[order[half:]], axis=0))
    return {"colors": colors, "dominant": colors[0], "accent": accent, "accent2": accent2}


def text_lines(small, edge_thr, accent=True):
    """Text = near-white or near-black shapes with hard edges (clouds and glows have soft edges),
    plus saturated hard-edged shapes touching that text (brush words, highlights). Grouped into lines."""
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(gx, gy)
    mn, mx = small.min(axis=2), small.max(axis=2)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hue = hsv[..., 0].astype(np.int32)
    dom_h = int(np.bincount(hue[hsv[..., 1] > 60].ravel(), minlength=180).argmax()) if (hsv[..., 1] > 60).any() else -100
    off_bg = np.minimum(np.abs(hue - dom_h), 180 - np.abs(hue - dom_h)) > 15
    cores = {
        "light": (mn >= 232).astype(np.uint8),
        "dark": (mx <= 32).astype(np.uint8),
        "accent": ((hsv[..., 1] > 110) & (hsv[..., 2] > 90) & off_bg).astype(np.uint8),
    }
    alpha_of = {
        "light": soft(mn.astype(np.float32), 170, 240),
        "dark": soft(255 - mx.astype(np.float32), 170, 235),
        "accent": soft(hsv[..., 1].astype(np.float32), 70, 140) * soft(hsv[..., 2].astype(np.float32), 60, 120),
    }
    glyph = {}
    heights = np.zeros(gray.shape, np.float32)
    for tone, core in cores.items():
        n, lab, st, _ = cv2.connectedComponentsWithStats(core, 8)
        if n <= 1:
            glyph[tone] = np.zeros_like(core)
            continue
        ring = cv2.dilate(core, np.ones((3, 3), np.uint8)) - core
        near = cv2.dilate(lab.astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)
        idx = near[ring > 0]
        cnt = np.bincount(idx, minlength=n)
        edge = np.bincount(idx, weights=grad[ring > 0], minlength=n) / np.maximum(cnt, 1)
        x, y, w, h, a = st[:, 0], st[:, 1], st[:, 2], st[:, 3], st[:, 4]
        sharp = edge > edge_thr if tone != "accent" else np.ones_like(edge, bool)
        keep = (h >= 7) & (h <= 330) & (a >= 15) & (a / np.maximum(w * h, 1) > 0.08) & sharp
        keep[0] = False
        glyph[tone] = keep[lab].astype(np.uint8)
        heights = np.where(glyph[tone] > 0, np.maximum(heights, h[lab].astype(np.float32)), heights)
    # saturated shapes only count when they touch light/dark text (brush words); never on their own
    base = np.maximum(glyph["light"], glyph["dark"])
    near_text = cv2.dilate(base, np.ones((25, 25), np.uint8))
    n, lab, st_a, _ = cv2.connectedComponentsWithStats(glyph["accent"], 8)
    touching = np.unique(lab[(near_text > 0) & (glyph["accent"] > 0)])
    # (content-engine port) saturated scenery touching text (a fairway, sunlit foliage) is not a brush word:
    # drop accent blobs wider than 60% or taller than 35% of the canvas. --no-accent turns accents off.
    big = np.nonzero((st_a[:, 2] > 0.6 * small.shape[1]) | (st_a[:, 3] > 0.35 * small.shape[0]))[0]
    touching = np.setdiff1d(touching, big)
    glyph["accent"] = np.isin(lab, touching[touching > 0]).astype(np.uint8) if accent else np.zeros_like(glyph["accent"])
    allg = np.maximum(base, glyph["accent"])
    alpha = np.zeros(gray.shape, np.float32)
    face = {}
    for tone in cores:
        zone = cv2.dilate(glyph[tone], np.ones((5, 5), np.uint8)).astype(np.float32)
        face[tone] = alpha_of[tone] * zone
        alpha = np.maximum(alpha, face[tone])
    lines_m = cv2.dilate(allg, cv2.getStructuringElement(cv2.MORPH_RECT, (29, 9)))
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(lines_m, 8)
    lines = []
    for i in range(1, n2):
        x, y, w, h, a = st2[i]
        inside = allg[y : y + h, x : x + w] * (lab2[y : y + h, x : x + w] == i)
        if inside.sum() < 50:
            continue
        hs = heights[y : y + h, x : x + w][(inside > 0) & (heights[y : y + h, x : x + w] > 0)]
        nl = int(glyph["light"][y : y + h, x : x + w][inside > 0].sum())
        nd = int(glyph["dark"][y : y + h, x : x + w][inside > 0].sum())
        lines.append({"box": [int(x), int(y), int(x + w), int(y + h)], "glyph_h": float(np.median(hs)) if len(hs) else 0.0, "tone": "light" if nl >= nd else "dark"})
    lines.sort(key=lambda l: (l["box"][1], l["box"][0]))
    return alpha, face, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--cutout", action="store_true", help="cut out the main subject (local model, downloads once)")
    ap.add_argument("--edge", type=float, default=70, help="edge sharpness that counts as text: lower finds softer text, higher ignores texture")
    ap.add_argument("--busy", type=float, default=0.06, help="edge density above which an area is held still")
    ap.add_argument("--no-accent", action="store_true", help="ignore saturated shapes touching text (brush words); use on busy photos")
    a = ap.parse_args()

    PREP.mkdir(exist_ok=True)
    files = sorted(p for p in SRC.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    if not files:
        sys.exit("no images in source/")
    for f in files:
        s = f.stem
        if a.only and s not in a.only:
            continue
        print(f"slide {s}")
        out = ROOT / "assets" / s
        out.mkdir(parents=True, exist_ok=True)
        im = imread(str(f), cv2.IMREAD_COLOR)
        if im is None:
            print(f"    could not read {f}")
            continue
        im = fit45(im)
        imwrite(str(out / "bg.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 93])
        small = cv2.resize(im, (CW, CH), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        geo = {"slide": s, "size": [CW, CH]}

        # ---------- text ----------
        text_a, face, lines = text_lines(small, a.edge, accent=not a.no_accent)
        line_mask = np.zeros((CH, CW), np.uint8)
        for l in lines:
            x0, y0, x1, y1 = l["box"]
            line_mask[max(0, y0 - 4) : y1 + 4, max(0, x0 - 4) : x1 + 4] = 1
        text_a = cv2.GaussianBlur(text_a * line_mask, (0, 0), 0.5)
        white = np.full((CH, CW, 3), 255, np.uint8)
        imwrite(str(out / "text.png"), rgba(white, text_a))
        geo["text"] = [l["box"] for l in lines]
        # headline = the run of wide lines with the tallest letters (blobs and icons are not wide)
        wide = [l for l in lines if (l["box"][2] - l["box"][0]) >= 1.6 * (l["box"][3] - l["box"][1]) and l["glyph_h"] >= 24]
        head = []
        if wide:
            top = max(wide, key=lambda l: l["glyph_h"])
            head = [top]
            cand = [l for l in lines if l["glyph_h"] >= 0.8 * top["glyph_h"] or l in wide]  # big type splits per word
            for l in sorted(cand, key=lambda l: abs(l["box"][1] - top["box"][1])):
                if l is top or l["glyph_h"] < 0.55 * top["glyph_h"] or l["tone"] != top["tone"]:
                    continue
                y0 = min(h["box"][1] for h in head)
                y1 = max(h["box"][3] for h in head)
                if l["box"][1] <= y1 + 0.6 * top["glyph_h"] and l["box"][3] >= y0 - 0.6 * top["glyph_h"]:
                    head.append(l)
        if head:
            hb = [min(l["box"][0] for l in head), min(l["box"][1] for l in head), max(l["box"][2] for l in head), max(l["box"][3] for l in head)]
            geo["headline"] = hb
            geo["headline_tone"] = head[0]["tone"]
            hm = np.zeros_like(text_a)
            for l in head:
                x0, y0, x1, y1 = l["box"]
                hm[max(0, y0 - 4) : y1 + 4, max(0, x0 - 4) : x1 + 4] = 1
            # head.png: only the headline's own tone (pure white or black letters), so it can be re-painted
            # flat on top of an effect (extrusion, echo) and still match the original pixels
            hf = cv2.GaussianBlur(face[geo["headline_tone"]] * hm, (0, 0), 0.5)
            imwrite(str(out / "head.png"), rgba(white, hf))
            # accent.png: saturated shapes over the headline (brush words, stickers). The slide re-paints the
            # original pixels through this matte above the extrusion, so layering stays right.
            zone = cv2.dilate(hm, np.ones((41, 41), np.uint8))
            acc = cv2.dilate(face["accent"] * zone, np.ones((5, 5), np.uint8))
            imwrite(str(out / "accent.png"), rgba(white, cv2.GaussianBlur(acc, (0, 0), 0.8)))
            geo["headline_accent"] = bool(acc.max() > 0.5)
            ink = small[hf > 0.9]
            geo["headline_color"] = hexc(np.median(ink, axis=0)) if len(ink) else ("#ffffff" if geo["headline_tone"] == "light" else "#000000")
        else:
            geo["headline"] = None
            geo["headline_accent"] = False
            imwrite(str(out / "head.png"), rgba(white, np.zeros_like(text_a)))
            imwrite(str(out / "accent.png"), rgba(white, np.zeros_like(text_a)))

        # ---------- subject (optional) ----------
        subj_a = None
        if a.cutout:
            cut = PREP / f"{s}_cut.png"
            src_png = PREP / f"{s}_src.png"
            imwrite(str(src_png), im)
            hf_cli = os.environ.get("LIVE_CAROUSEL_HF", "hyperframes")  # the installed CLI; pin with hyperframes@<version>
            r = subprocess.run([shutil.which("npx") or "npx", "--yes", hf_cli, "remove-background", str(src_png), "-o", str(cut)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0 and cut.exists():
                p = imread(str(cut), cv2.IMREAD_UNCHANGED)
                p = cv2.resize(p, (W, H), interpolation=cv2.INTER_AREA)
                al = p[..., 3].astype(np.float32) / 255
                al = cv2.GaussianBlur(cv2.erode(al, np.ones((3, 3), np.uint8)), (0, 0), 1.2)  # defringe
                solid = (p[..., 3] > 250).astype(np.uint8)
                fill = cv2.inpaint(p[..., :3], (1 - solid) * 255, 5, cv2.INPAINT_TELEA)
                imwrite(str(out / "subject.png"), rgba(fill, al))
                subj_a = cv2.resize(al, (CW, CH), interpolation=cv2.INTER_AREA)
                ys, xs = np.nonzero(subj_a > 0.5)
                if len(xs):
                    geo["subject"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
            else:
                print("    cut-out failed:", (r.stdout + r.stderr).strip()[-300:])

        # ---------- what may move ----------
        edges = cv2.Canny(gray, 50, 150).astype(np.float32) / 255
        density = cv2.GaussianBlur(edges, (0, 0), 10)
        busy = (density > a.busy).astype(np.uint8)
        still = np.maximum(busy, line_mask)
        if subj_a is not None:
            still = np.maximum(still, (subj_a > 0.1).astype(np.uint8))
        still_f = cv2.GaussianBlur(cv2.dilate(still, np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 14)
        move = 1 - np.clip(still_f, 0, 1)
        geo["moving_share"] = round(float((move > 0.5).mean()), 3)

        # ---------- clean plate for the shader's displaced lookups ----------
        holes = cv2.dilate(line_mask, np.ones((9, 9), np.uint8))
        if subj_a is not None:
            holes = np.maximum(holes, cv2.dilate((subj_a > 0.05).astype(np.uint8), np.ones((9, 9), np.uint8)))
        clean = cv2.inpaint(small, holes * 255, 9, cv2.INPAINT_TELEA)
        clean = cv2.resize(clean, (W, H), interpolation=cv2.INTER_CUBIC)
        hole_big = cv2.resize(holes, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
        clean = np.where(hole_big > 0, clean, im)
        imwrite(str(out / "clean.jpg"), clean, [cv2.IMWRITE_JPEG_QUALITY, 90])

        # ---------- wind field ----------
        seed = sum(map(ord, s))
        n1 = smooth_noise((CH, CW), 180, seed * 7 + 1)
        n2 = smooth_noise((CH, CW), 120, seed * 7 + 2)
        n1 = (n1 - n1.min()) / (n1.max() - n1.min() + 1e-6)
        n2 = (n2 - n2.min()) / (n2.max() - n2.min() + 1e-6)
        fx = 0.55 + 0.45 * n1
        fy = (n2 - 0.5) * 0.9
        # OpenCV writes BGR: B=move, G=fx, R=fy -> the shader reads r=fy, g=fx, b=move
        flow = np.dstack([move * 255, np.clip(fx * 0.5 + 0.5, 0, 1) * 255, np.clip(fy * 0.5 + 0.5, 0, 1) * 255])
        imwrite(str(out / "flow.png"), flow.astype(np.uint8))

        geo["palette"] = palette(small, text_a, ([geo["headline"]] if geo.get("headline") else [], geo["text"]))
        (out / "geo.json").write_text(json.dumps(geo, indent=1), encoding="utf-8")

        # ---------- debug view ----------
        vis = small.copy().astype(np.float32)
        red = np.zeros_like(vis)
        red[..., 2] = 255
        vis = vis * (1 - 0.45 * (1 - move[..., None])) + red * 0.45 * (1 - move[..., None])
        vis = vis.astype(np.uint8)
        for l in lines:
            cv2.rectangle(vis, tuple(l["box"][:2]), tuple(l["box"][2:]), (60, 220, 60), 2)
        if geo["headline"]:
            hb = geo["headline"]
            cv2.rectangle(vis, (hb[0] - 6, hb[1] - 6), (hb[2] + 6, hb[3] + 6), (255, 120, 40), 4)
        imwrite(str(PREP / f"{s}_maskvis.jpg"), cv2.resize(vis, (540, 675)), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(f"    {len(lines)} text lines, headline {geo['headline']}, {geo['moving_share'] * 100:.0f}% of the frame can move, accent {geo['palette']['accent']}")


if __name__ == "__main__":
    main()
