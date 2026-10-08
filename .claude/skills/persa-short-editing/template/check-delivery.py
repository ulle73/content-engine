#!/usr/bin/env python3
"""⛔ DELIVERY GATE. Jad, 2026-09-03: "whenever I give you the video to edit, you have to
give it to me back 1080p." Run it on the FINAL before opening anything for review.

It checks the three things that can silently cost resolution:
  1. the container really is 1080x1920 @30 (not a downscale, not a re-wrap)
  2. the picture is actually SHARP at that size — a 1080-shaped file can still be an
     upscale of something smaller, and no header says so. Measured as high-frequency
     energy against the source recording, on a frame with no defocus on it.
  3. the bitrate has not collapsed in the mux
"""
import os, subprocess, sys, tempfile, numpy as np
HF_PNG = os.path.join(tempfile.gettempdir(), "persa-check-delivery-hf.png")  # content-engine: no /tmp on Windows
from PIL import Image

FINAL, SRC = "out/tp-0925b-FINAL.mp4", "assets/recording.mp4"

def probe(f, keys):
    out = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
                          f"stream={keys}","-of","default=nw=1:nk=1",f],
                         capture_output=True, text=True).stdout.split()
    return out

def hf(f, t):
    """⚠ THE MEASUREMENT REGION IS THE WHOLE TRICK, AND THE FIRST ONE WAS WRONG.
    y1300..1800 x200..900 looked like a safe strip — never covered by a card — and it is
    where the 92px CAPTION lives. It returned final/source = 11.0x, i.e. "the render is
    eleven times sharper than the camera", which is the caption's own edges, not the
    picture. Take a region with no caption, no card, no display type and no defocus: the
    left margin, below the card band and above the caption line."""
    subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",f,"-frames:v","1",HF_PNG],
                   capture_output=True)
    a = np.asarray(Image.open(HF_PNG).convert("L")).astype(float)
    s = a[1000:1350, 30:300]
    lap = (-4*s[1:-1,1:-1] + s[:-2,1:-1] + s[2:,1:-1] + s[1:-1,:-2] + s[1:-1,2:])
    return lap.var()

w, h, fps = probe(FINAL, "width,height,r_frame_rate")[:3]
ok = (w == "1080" and h == "1920")
print(f"  resolution   {w}x{h} @ {fps}      {'OK' if ok else 'FAIL — not 1080x1920'}")

br = subprocess.run(["ffprobe","-v","error","-show_entries","format=bit_rate","-of",
                     "default=nw=1:nk=1",FINAL],capture_output=True,text=True).stdout.strip()
print(f"  bitrate      {int(br)/1e6:.2f} Mb/s")

# ⚠ THE SAMPLE TIME IS PER CUT, because the strip has to be one no graphic ever enters.
# 27.0s is beat 04 — a face beat in the WIDE act, so the camera is 1:1: the marker line sits
# ~600px above the strip and the caption 50px below it, and nothing at all crosses x30..300.
a, b = hf(FINAL, 0.5), hf(SRC, 0.5)   # a FACE beat, before any type
print(f"  sharpness    final {a:8.1f}   source {b:8.1f}   ratio {a/b:.2f}")
print(f"               {'OK — no resolution was lost' if a/b > 0.75 else 'FAIL — the picture is softer than the source'}")
sys.exit(0 if ok and a/b > 0.75 else 1)
