# Backgrounds — LOCAL first (free), kie.ai optional

There are two ways to get a background. **Default to the local one.**

## 1. LOCAL painter (free, offline, no key) — `carousel_localbg.py`
The midnight world is drawn procedurally in canvas by `bg_local.html`: void-black field,
a teal bloom emitted from *inside* the scene, silhouette flora with rim light, starfield,
drifting spores, amber florets, vignette and grain. Nothing is downloaded or paid for.

Per slide in `plan.json`:
```json
"bg_scene": "deep-bloom",   // which scene preset to paint
"bg_seed": 1037,            // same scene + same seed = the exact same painting
"bg_tweak": {"bloom": {"intensity": 0.7}, "amber": 4}   // optional raw overrides
```
Then: `library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/carousel_run.py localbg <run>` (or `build` = localbg + render + export).

### Scene presets (`carousel_localbg.SCENES`)
| scene | what it looks like | use it for |
|---|---|---|
| `deep-bloom` | bloom low-centre, deep flora standing in it | the signature slide, hooks |
| `far-field` | wide, quiet, mostly black sky, small distant glow | long headlines |
| `starfield` | almost empty black + stars, flora only skims the bottom | a big single statement |
| `dandelion` | a hero dandelion clock catching the light | one big idea |
| `amber-meadow` | tiny warm amber florets in the foreground | the CTA / warmest slide |
| `mist` | horizontal haze drifting through the light | calm, cinematic body slides |
| `close-flora` | tall out-of-focus stems in front, light behind | most depth, data slides |

If you set no `bg_scene`, the painter rotates through them so no two neighbouring slides match.
Preview the whole vocabulary any time: `library/.venv/Scripts/python library/kits/carousel-generator/carousel/scripts/carousel_localbg.py --preview`.

### Tuning knobs (`bg_tweak`)
`bloom{x,y,r,intensity}` (x/y/r are fractions of the canvas) · `blooms2[]` secondary pockets ·
`flora{density,height}` · `horizon` (0–1, where flora is rooted) · `stars`, `brightStars`,
`spores`, `mist`, `amber` (counts) · `topGuard` (how much of the top is held to black) · `grain`.

## 2. kie.ai Nano Banana Pro (PAID, optional)
Only if the user explicitly wants photographic AI backgrounds and has a `KIE_API_KEY`.
Write an `image_prompt` per slide and run `carousel_run.py generate <run>`. Keep the shared
style sentence (already appended by `carousel_run.py`) on every slide so the set matches:

```
[SCENE for this slide].
Midnight bioluminescent nocturnal macro photograph of a wild meadow. Pure void-black field;
the ONLY light is a soft teal bioluminescent glow emitted from INSIDE the scene, low in the
frame. Wild flora (queen anne's lace, dandelion clocks, grass seed heads) is silhouette with a
thin teal rim light, never fully exposed. Deep shadow, heavy grain, shallow depth of field,
out-of-focus black foreground stems. Edges fall off to pure black; nothing touches the frame.
Keep the TOP HALF unbroken black (headline room). Cinematic, quiet, premium.
No text, no letters, no logos, no UI, no panels.
```

## Rules either way
- **Keep the top ~45% unbroken black.** The headline lives there.
- **Light comes from inside the scene**, never from the viewer. No key light, no sun.
- **Teal is light, never paint.** It only appears as glow.
- **Amber is only tiny foreground flora accents** — never in the UI, never large.
- **Edges fall off to black.** Nothing touches the frame.
- Vary the scene slide to slide, keep one palette and one finish across the set.
