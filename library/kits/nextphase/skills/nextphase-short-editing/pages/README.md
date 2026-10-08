# pages/ — sidfångster för page-highlight

Originalets fångster (sidor från Anthropics dokumentation m.fl.) togs bort vid importen.

`example-page.png` + `example-page.json` är en **egen platshållarsida** (neutral text, inga riktiga
påståenden) renderad som en äkta 9:16-ram (CSS 640 px × 1,6875 = 1080×1920) med markeringsrektanglar
i sidecar-JSON:en — exakt det format `ui-blocks/page-highlight.html` läser.

Gör egna med: `python library/kits/nextphase/skills/nextphase-short-editing/scripts/shoot-page-9x16.py <url> pages/<namn>.png --hl "fras"`
(kräver Python-paketet `playwright`, se `library/kits/nextphase/SETUP.md`).
