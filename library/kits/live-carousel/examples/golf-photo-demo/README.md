# Photo-mode demo: golf carousel (verified 2026-10-08)

Four "finished" Swedish golf slides, designed in HTML (`design/`) over the golfkuponger-friskvard photos
(`C:\Users\rydqv\video-tools\videos\golfkuponger-friskvard\assets\`), then brought to life by photo mode.

Reproduce from the repo root (PowerShell):

```
python library\kits\live-carousel\examples\golf-photo-demo\design\shoot.py        # -> source\01..04.png (headless Chrome)
$S = "library\kits\live-carousel\examples\golf-photo-demo\source"
.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\new_carousel.py golf-photo --mode photo --images "$S\01.png" "$S\02.png" "$S\03.png" "$S\04.png"
.claude\skills\live-carousel\scripts\py.cmd work\live-carousel\golf-photo\prep_photo.py
.claude\skills\live-carousel\scripts\py.cmd work\live-carousel\golf-photo\prep_photo.py --only 04 --no-accent
copy library\kits\live-carousel\examples\golf-photo-demo\carousel.json work\live-carousel\golf-photo\carousel.json
.claude\skills\live-carousel\scripts\py.cmd .claude\skills\live-carousel\scripts\render_all.py golf-photo
```

`carousel.json` holds the tuned cues: 01 hit 0.5 s + extrusion; 02 extrusion + strong sky/sea drift;
03 extrusion off (dark headline over trees looked rough); 04 extrusion off (detector picked the button as
headline) and `hitAt` moved under the copy. Render: 4 x 6 s slides in ~150 s (2 workers).
