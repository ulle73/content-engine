"""Generate an original instrumental track locally with ACE-Step 1.5 (free, CPU ok, ~4x realtime).

Usage:
  python library/tools/make_music.py 38 work/music/track.wav "uplifting premium acoustic pop, warm strings" [--bpm 112]

Requires the local ACE-Step install (default C:/Users/rydqv/video-tools/ACE-Step-1.5, override with
ACESTEP_DIR) and uv on PATH. Tip: ask for a few seconds more than you need – tracks end with a
natural outro a little before the requested length – then measure the beat grid with
`npx hyperframes beats` and start the music on a phrase boundary.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ACESTEP_DIR = Path(os.environ.get("ACESTEP_DIR", "C:/Users/rydqv/video-tools/ACE-Step-1.5"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("seconds", type=int)
    parser.add_argument("out")
    parser.add_argument("caption")
    parser.add_argument("--bpm", type=int)
    args = parser.parse_args()

    script = ACESTEP_DIR / "gen_track.py"
    if not script.exists():
        print(f"Hittar inte {script}. Installera ACE-Step eller sätt ACESTEP_DIR.", file=sys.stderr)
        return 1
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["uv", "run", "--no-sync", "python", str(script), str(args.seconds), str(out), args.caption]
    if args.bpm:
        cmd.append(str(args.bpm))
    return subprocess.call(cmd, cwd=ACESTEP_DIR)


if __name__ == "__main__":
    sys.exit(main())
