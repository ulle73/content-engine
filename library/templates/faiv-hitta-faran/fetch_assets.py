"""Hämtar Mixkit-ljuden som mallen använder. De får inte ligga i mallen (Mixkits licens förbjuder
vidarespridning i mallar och verktyg), så de hämtas till den här kopian vid första körningen.

  python -I fetch_assets.py
"""
import hashlib
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# Låten är kalibrerad (takter, frasstart 76,97 s, slutton 96,16 s) mot exakt den här versionen.
TRACK = ("music/driving-ambition.mp3", "https://assets.mixkit.co/music/32/32.mp3", "b17640d37a7293618724a030392ba400")
SFX = {  # Mixkit Sound Effects Free License; id -> filnamn i sfx-mixkit/ (alla kandidater, för audition.py)
    1808: "electric-switch", 2301: "quick-bass-switch", 2579: "light-switch-sound", 3180: "machine-activation-short",
    2602: "electronics-power-up", 1143: "cinematic-whoosh-deep-impact", 1436: "camera-auto-focus",
    1437: "camera-lens-autofocus", 2859: "computer-digital-lock", 2857: "gear-fast-lock-tap", 2847: "data-scaner",
    3124: "modern-technology-select", 2589: "shot-light-energy-flowing",
}


def get(url, path, md5=None):
    dest = os.path.join(HERE, path)
    if os.path.exists(dest):
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    if md5 and hashlib.md5(data).hexdigest() != md5:
        raise SystemExit(f"{url}: fel version (md5 matchar inte) – takterna i audio.py stämmer inte längre")
    with open(dest, "wb") as f:
        f.write(data)
    print("hämtade", path)


def main():
    get(TRACK[1], TRACK[0], TRACK[2])
    for sid, name in SFX.items():
        get(f"https://assets.mixkit.co/active_storage/sfx/{sid}/{sid}-preview.mp3", f"sfx-mixkit/{name}.mp3")


if __name__ == "__main__":
    main()
