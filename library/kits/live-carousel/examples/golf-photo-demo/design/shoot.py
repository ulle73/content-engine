"""Screenshot the designed demo slides (1080x1350) with headless Chrome -> ../source/NN.png.

These stand in for a user's "finished carousel" (photo mode animates finished slides with text).
Needs the golfkuponger-friskvard photos in C:/Users/rydqv/video-tools/videos/golfkuponger-friskvard/assets.
Usage (any Python): python library/kits/live-carousel/examples/golf-photo-demo/design/shoot.py
"""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "source"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

OUT.mkdir(exist_ok=True)
for page in sorted(HERE.glob("slide-*.html")):
    n = page.stem.split("-")[1]
    target = OUT / f"{n}.png"
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
         "--window-size=1080,1350", "--allow-file-access-from-files", "--virtual-time-budget=3000",
         f"--screenshot={target}", page.as_uri()],
        check=True, capture_output=True,
    )
    print(target)
