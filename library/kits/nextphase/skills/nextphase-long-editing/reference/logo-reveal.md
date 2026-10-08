# LOGO BLUR-REVEAL — the house hook for "there's a tool that…"

Jad's spec, 2026-08-04: *"whenever I start a video, like, there's a tool that came free and
things like that — show the logo, but on top of the logo there's a filter that blurs it. And
then once I say the name, the logo appears again and we can see it without the blur."*

The **default cold open** for any video that withholds a product name for a few seconds. It
replaces the "small dark screenshot with a highlighter on it" opener, which he rejected: a
cropped article card is unreadable at video scale and gives the viewer nothing to look at while
the hook line runs.

⇄ Ported from the short unchanged except for the geometry table and the hold length.

---

## The move

1. **From second one**, the tool's **real logo** sits centred, heavily **blurred**, slightly
   oversized, on a soft coral glow over the dark grid. The viewer knows a product is coming and
   cannot yet tell which — that curiosity is the retention device.
2. It **holds blurred** for the whole tease while he says what the thing does but not what it is
   called. Give it slow life — a gentle scale drift and a breathing glow — so it is never a
   frozen frame.
3. **On the exact transcript onset of the name**, the blur resolves to `0`, the scale settles
   inward, and the wordmark pops in beneath it.
4. A `magic-reveal` **crests on the unblur**, and the cold-open `riser` ends there.

The reveal instant **is** the payoff spike. It takes the coral flash — not a separate one.

## Timing

**IN** = the start of the composition (or the layout).
**REVEAL** = the word onset of the product name, pulled from `transcript-tight.json`. Never a
round number. If he names it at `7.04`, the blur hits `0` at `7.04`, not `7.0`.
**OUT** = the normal exit, **≥1.2s after** the reveal so the sharp logo is actually read.
Revealing and cutting inside half a second wastes the whole build.

⇄ **Long-form hold: 4–10s** (the short's is 3–7s). A 16:9 cold open has more room and the tease
can breathe — but past ~10s the viewer stops wondering and starts leaving. If the hook line runs
longer than that, reveal on time and cut to a second graphic; do not stretch the blur.

## Geometry and values

⇄ Scaled for a 1920×1080 frame. The 360px box is the short's; on 16:9 it reads small.

| Logo box | blur start | blur end | scale | glow |
|---|---|---|---|---|
| **440px** (16:9 default) | `30px` | `0` | `1.12 → 1.00` | radius 400px, coral @ .28 |
| 340px | `24px` | `0` | `1.10 → 1.00` | radius 300px, coral @ .26 |

- Under ~14px the blur reads as a render bug rather than a deliberate tease.
- Over ~34px the shape dissolves and there is nothing to be curious about.
- Resolve over **0.55–0.70s** with `power3.out`. Faster feels like a glitch; slower drags.
- The wordmark enters **+0.12s after** the blur lands, never with it — the logo resolves,
  *then* it is named.
- ⇄ Wordmark at `--font-mono` 700 **96px** in `--on` (the short uses 84px on `--ink`).

## Hard rules

- **`filter: blur()` is the one non-transform property allowed to animate.** It is already in
  `motion-grammar.md` as **blur-in**; it is a compositing filter, not layout, so it does not
  stutter. Everything else in the scene still obeys transforms-only.
- **The logo must be the project's own file** — repo `icon.png`, site favicon or OG image, brand
  SVG. Never redraw a logo, never substitute a generic mark, never use an emoji.
- **Blur the logo only.** Never the caption, never the camera, never the cutout.
- Keep the blurred logo **on a plain token background** (`.bg-darkgrid` or the coral glow). A
  blurred logo on a busy screenshot reads as a mistake.
- ⇄ **Check the logo against the dark background.** Many logos are dark-on-transparent and
  vanish on `--dark`. If it does, put it on a `--on` rounded plate (48px radius, 32px padding)
  rather than recolouring the mark — recolouring someone's logo is a brand violation.
- If the tool has no usable logo file, do **not** fake it — open on the real product UI instead
  and skip this move.

## Sourcing the logo

```bash
# repo app icon (best — usually 512–1024px, transparent or on brand colour)
curl -sL -o logo.png https://raw.githubusercontent.com/<owner>/<repo>/main/resources/build/icon.png
# site favicon / OG image
curl -sL -o logo.svg https://<product>.dev/favicon.svg
# GitHub org avatar (fallback)
curl -sL -o logo.png "https://github.com/<org>.png?size=512"
```
**Verify it actually rendered before using it** — a 404 saved as `.png` is a text file.
`file logo.png` should say PNG, not ASCII text.

## The brick

`components/logo-blur-reveal.html` is the working scene: markup, CSS and the GSAP calls, with
the two timing variables at the top. Copy it into the segment and set `REVEAL` to the name's
word onset **in segment time** (`at(t)` — see `assembly.md` §3).

## Sound

- `riser` from the top of the cold open, **cresting on REVEAL**.
- `magic-reveal` **at** REVEAL, gain ~0.15 (this is the hero moment).
- `futuristic-click` +0.12s on the wordmark.
- ⇄ The music bed **drops to silence ~3s before REVEAL** and returns on it. See
  `sound-design.md` — the drop map.
