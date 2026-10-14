"""Hämtar delad kod, figurer, logga och ljud till kopian i work/<namn>/ (en sanning per del):

  python -I fetch_assets.py

- Ritkod: scene.js + sf.js och audio.py från årsskiftesmallen, tourleif.js och chefen.js från figurmodulerna.
- Logga: officiella logo-final.png -> src/assets/logo-data.js.
- Ljud: ur ljudbanken (library/sounds; Mixkit hämtas och md5-kontrolleras).
"""
import base64
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TPL = os.path.join(ROOT, "library", "templates")
sys.path.insert(0, os.path.join(ROOT, "library", "sounds"))
import sounds  # noqa: E402

CODE = {
    "src/scene.js": "golfkuponger-arsskifte/src/scene.js",
    "src/sf.js": "golfkuponger-arsskifte/src/sf.js",
    "audio.py": "golfkuponger-arsskifte/audio.py",
    "src/tourleif.js": "golfkuponger-tourleif/tourleif.js",
    "src/chefen.js": "golfkuponger-chefen/chefen.js",
}
SOUNDS = {  # lokalt filnamn i audio_chef.py -> (ljudbankens id, godkänt utdrag?)
    "music/m2.mp3": ("music.comical", False),
    "music/m859.mp3": ("music.under-the-sun", False),
    "sfx/s2867.mp3": ("sound.bekraftelse", False),
    "sfx/bank-smack.wav": ("sound.smack-dov-trumma", True),
    "sfx/s195.mp3": ("sound.dorr-knarr", False),
    "sfx/s1788.mp3": ("sound.syrsor", False),
    "sfx/click-soft.mp3": ("sound.mobiltryck", False),
    "sfx/whoosh-short.mp3": ("sound.bollsus", False),
    "sfx/s1530.mp3": ("sound.papper-glid", False),
    "sfx/typing.mp3": ("sound.tangenter", False),
    "sfx/s2354.mp3": ("sound.mejlnotis", False),
    "sfx/s1061.mp3": ("sound.klocktick", False),
}
LOGO = os.path.join(TPL, "golfkuponger-outro", "assets", "logo-final.png")


def main():
    for rel, src in CODE.items():
        shutil.copyfile(os.path.join(TPL, src), os.path.join(HERE, rel))
        print("kod", rel, "<-", src)
    for rel, (sid, cut) in SOUNDS.items():
        dest = os.path.join(HERE, rel)
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(sounds.get(sid, cut), dest)
            print("ljud", rel, "<-", sid)
    assets = os.path.join(HERE, "src", "assets")
    small = os.path.join(assets, "logo-480.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", LOGO, "-vf", "scale=480:-1", small], check=True)
    with open(small, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    with open(os.path.join(assets, "logo-data.js"), "w") as f:
        f.write(f'window.GK_LOGO = "data:image/png;base64,{data}";\n')
    print("logga -> src/assets/logo-data.js")


if __name__ == "__main__":
    main()
