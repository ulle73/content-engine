# Motion studio-playbook

Egna promptmallar och verktyg för motion design med kod (HTML/Canvas, HyperFrames, Remotion).
Skrivna för content-engine – inspirerade av publika tekniker, ingen artikeltext inklistrad.
Index: `LIBRARY.json` (kit `motion-studio-playbook`).

| Fil | Vad |
|---|---|
| `01-render-contract.md` | seek(t) som ren funktion av tiden, seedat brus, motion blur |
| `02-showreel-one-liner.md` | Showreel på en rad + varianter |
| `03-brand-reel.md` | Produktreel från URL (hook, montering, 3 funktioner, bevis, CTA) |
| `04-reference-prompt.md` | Referensvideo → style_guide.md + shotlist.md |
| `05-xml-spec.md` | XML-brief + "en form klipper aldrig"-exempel |
| `06-springs-track.md`, `springs.mjs` | Fjädrar i sluten form, track(), brus, takt (självtest: `springs.selftest.mjs`) |
| `07-beat-grid.md`, `beat_grid.py`, `sfx_synth.py` | Taktgrid och syntetiserade ljudeffekter |
| `08-directors-brief.md` | Regissörsbrief för längre filmer |
| `09-critique-loop.md`, `review.py` | Kritikloop och granskningsverktyg |
| `10-package-as-skill.md` | Gör ett arbetsflöde till en skill |
| `11-parallel-chapters.md` | Underagenter per kapitel |

Python-verktygen körs med `library\.venv\Scripts\python.exe` (numpy + Pillow). Utdata till `work/…`.
