"""Hämtar filmens ljud ur ljudbanken (library/sounds) till de filnamn som audio.py/audio2.py använder,
och bygger loggan (officiell fil) till src/assets/. Körs från kopian i work/<namn>/:

  python -I fetch_assets.py
"""
import base64
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "library", "sounds"))
import sounds  # noqa: E402

# lokalt filnamn -> (ljudbankens id, godkänt utdrag?)
ASSETS = {
    "music/m77.mp3": ("music.running-out-of-time", False),
    "music/m859.mp3": ("music.under-the-sun", False),
    "sfx/s1104.mp3": ("sound.kalenderblad", False),
    "sfx/s1102.mp3": ("sound.bladdring", False),
    "sfx/s2384.mp3": ("sound.papper-snabbriv", False),
    "sfx/s1061.mp3": ("sound.klocktick", False),
    "sfx/s2590.mp3": ("sound.tandsticka", False),
    "sfx/s1330.mp3": ("sound.eld-sprak", False),
    "sfx/s2073.mp3": ("sound.boll-studs", False),
    "sfx/s1530.mp3": ("sound.papper-glid", False),
    "sfx/whoosh-short.mp3": ("sound.bollsus", False),
    "sfx/golf14.mp3": ("sound.golftraff", False),
    "sfx/putt-inbeeld.wav": ("sound.boll-i-hal", False),
    "sfx/rip/cut342541.wav": ("sound.papper-riv", False),
    "sfx/v2/cut/L3.wav": ("sound.larm-anlaggning", True),
    "sfx/v2/cut/M2.wav": ("sound.smack-dov-trumma", True),
    "sfx/v2/cut/P1.wav": ("sound.kassettknapp", False),
    "sfx/v2/cry-peterpiotr.mp3": ("sound.grat-man", False),
    "sfx/rewind-1088.mp3": ("sound.spola-tillbaka", False),
}
LOGO = os.path.join(ROOT, "library", "templates", "golfkuponger-outro", "assets", "logo-final.png")


def main():
    for rel, (sid, cut) in ASSETS.items():
        dest = os.path.join(HERE, rel)
        if os.path.exists(dest):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(sounds.get(sid, cut), "rb") as src, open(dest, "wb") as out:
            out.write(src.read())
        print("ljud", rel, "<-", sid)
    assets = os.path.join(HERE, "src", "assets")
    os.makedirs(assets, exist_ok=True)
    small = os.path.join(assets, "logo-480.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", LOGO, "-vf", "scale=480:-1", small], check=True)
    with open(small, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    with open(os.path.join(assets, "logo-data.js"), "w") as f:
        f.write(f'window.GK_LOGO = "data:image/png;base64,{data}";\n')
    print("logga -> src/assets/logo-data.js (officiell logo-final.png)")


if __name__ == "__main__":
    main()
