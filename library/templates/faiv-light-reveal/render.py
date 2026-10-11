"""Render FAIV "Mörker → ljus" end to end: HyperFrames picture → SFX (+ music) mix from sfx.json →
edit-renderer/src/finish.js (−14 LUFS, H.264). FAIV has no brand outro clip, so none is appended.

    python library/templates/faiv-light-reveal/render.py [--out work/faiv-light-reveal] [--publish]
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import template_render  # noqa: E402

if __name__ == "__main__":
    template_render.main(HERE, item_id="faiv.template.morker-till-ljus", work_name="faiv-light-reveal", outro=None,
                         still_at=3.2, review_times=[0.6, 1.8, 3.4, 4.3, 5.6, 6.9, 8.9, 11.4])
