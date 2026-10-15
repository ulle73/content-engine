"""Ljudbanken: godkända ljud som ska återanvändas (library/sounds/LIBRARY.json).

  python library/sounds/sounds.py list                    # alla ljud med roll och licens
  python library/sounds/sounds.py get <id> [--cut]         # skriver ut sökväg (hämtar/klipper vid behov)
  python library/sounds/sounds.py copy <id> <fil> [--cut]  # kopierar till t.ex. work/<film>/sfx/
  python library/sounds/sounds.py fetch                    # hämtar alla Mixkit-ljud till .cache/

Ljud med fri vidarespridning (CC0, Pixabay, eget material) ligger i files/. Mixkit-ljud får inte ligga i mallar
eller verktyg (licensen), så de hämtas från Mixkit till library/sounds/.cache/ (gitignorerat) och kontrolleras mot md5.
`--cut` ger exakt det utdrag som godkändes (bank.cut) som 48 kHz stereo-wav.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = HERE / ".cache"
SR = 48000


def items() -> dict[str, dict]:
    data = json.loads((HERE / "LIBRARY.json").read_text(encoding="utf-8"))
    return {i["id"]: i for i in data["items"]}


def _fetch(item: dict) -> Path:
    bank = item["bank"]
    if bank.get("file"):
        return ROOT / bank["file"]
    url = bank["url"]
    dest = CACHE / f"{item['id']}{Path(url).suffix}"
    if not dest.exists():
        CACHE.mkdir(exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        md5 = hashlib.md5(data).hexdigest()
        if bank.get("md5") and md5 != bank["md5"]:
            raise SystemExit(f"{item['id']}: fel version från {url} (md5 {md5} ≠ {bank['md5']}) – utdrag och nivåer stämmer inte längre")
        dest.write_bytes(data)
    return dest


def _load(path: Path):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def _onset(x, frac):
    import numpy as np
    e = (x.astype(np.float64) ** 2).mean(1)
    k = int(0.005 * SR)
    c = np.concatenate([[0.0], np.cumsum(e)])
    env = (c[k:] - c[:-k]) / k
    return int(np.argmax(env >= frac * env.max()))


def get(sound_id: str, cut: bool = False) -> Path:
    item = items()[sound_id]
    src = _fetch(item)
    spec = item["bank"].get("cut")
    if not cut or not spec:
        return src
    dest = CACHE / f"{sound_id}.cut.wav"
    if dest.exists():
        return dest
    import numpy as np
    x = _load(src)
    if spec.get("start") == "onset":
        a = max(0, _onset(x, spec.get("onset_frac", 0.05)) - int(spec.get("pre", 0.0) * SR))
    else:
        a = int(float(spec.get("start", 0.0)) * SR)
    seg = x[a:a + int(spec["dur"] * SR)].copy()
    n = len(seg)
    for key, sl in (("fade_in", slice(None)), ("fade_out", slice(None))):
        f = int(spec.get(key, 0.0) * SR)
        if f:
            ramp = np.linspace(0, 1, min(f, n))[:, None]
            if key == "fade_in":
                seg[:len(ramp)] *= ramp
            else:
                seg[n - len(ramp):] *= ramp[::-1]
    CACHE.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(dest)],
                   input=seg.astype(np.float32).tobytes(), check=True)
    return dest


def main(argv: list[str]) -> None:
    if not argv or argv[0] == "list":
        for i in items().values():
            b = i["bank"]
            print(f"{i['id']:32s} {b['role'][:60]:60s} {b['license']}")
        return
    cmd, cut = argv[0], "--cut" in argv
    args = [a for a in argv[1:] if a != "--cut"]
    if cmd == "get":
        print(get(args[0], cut))
    elif cmd == "copy":
        dest = Path(args[1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(get(args[0], cut), dest)
        print(dest)
    elif cmd == "fetch":
        for i in items().values():
            if not i["bank"].get("file"):
                print(_fetch(i))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
