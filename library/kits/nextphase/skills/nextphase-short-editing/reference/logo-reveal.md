# LOGO BLUR-REVEAL — the house hook for "there's a tool that…"

Jad's spec, 2026-08-04: *"whenever I start a video, like, there's a tool that came free
and things like that — show the logo, but on top of the logo there's a filter that blurs
it. And then once I say the name, the logo appears again and we can see it without the blur."*

This is the **default hook** for any reel that withholds a product name for a few seconds.
It replaces the "small dark screenshot with a highlighter on it" opener, which he rejected:
a cropped article card is unreadable at reel scale and gives the viewer nothing to look at
while the hook line runs.

---

## The move

1. **From second one**, the tool's **real logo** sits in the top zone, heavily **blurred**,
   slightly oversized, on a soft coral glow. The viewer knows a product is coming and
   cannot yet tell which — that curiosity is the retention device.
2. It **holds blurred** for the whole tease (typically 3–7s) while he says what the thing
   does but not what it's called. Give it slow life — a gentle scale drift and a breathing
   glow — so it is never a frozen frame.
3. **On the exact transcript onset of the name**, the blur resolves to `0`, the scale
   settles inward, and the wordmark pops in beneath it.
4. A `magic-reveal` **crests on the unblur**, and the hook `riser` ends there.

The reveal instant is the payoff beat — it takes the coral flash, not a separate one.

## The timing rule

**IN** = the start of the composition (or the layout).
**REVEAL** = the word onset of the product name, pulled from `transcript.json`. Never a
round number. If he names it at `7.04`, the blur hits `0` at `7.04`, not `7.0`.
**OUT** = the graphic's normal exit, ≥1.2s after the reveal so the sharp logo is actually
read. Revealing and cutting inside half a second wastes the whole build.

## Geometry and values

Measured on a 1080-wide top zone; scale with the logo box.

| Logo box | blur start | blur end | scale | glow |
|---|---|---|---|---|
| 360px | `26px` | `0` | `1.12 → 1.00` | radius 320px, coral @ .28 |
| 260px | `20px` | `0` | `1.10 → 1.00` | radius 240px, coral @ .26 |

- Under ~14px the blur reads as a render bug rather than a deliberate tease.
- Over ~34px the shape dissolves and there is nothing to be curious about.
- Resolve over **0.55–0.70s** with `power3.out`. Faster feels like a glitch; slower drags.
- The wordmark enters **+0.12s after** the blur lands, never with it — the logo resolves,
  *then* it is named.

## Hard rules

- **`filter: blur()` is the one non-transform property allowed to animate.** It is already
  in `motion-grammar.md` as **blur-in**; it is a compositing filter, not layout, so it does
  not stutter. Everything else in the scene still obeys transforms-only.
- **The logo must be the project's own file** — repo `icon.png`, site favicon/OG image,
  brand SVG. Never redraw a logo, never substitute a generic mark, never use an emoji.
- **Blur the logo only.** Never the caption, never the camera, never the cutout.
- Keep the blurred logo **on a plain token background** (`--cream` or the coral glow). A
  blurred logo on top of a busy screenshot reads as a mistake.
- If the tool has no usable logo file, do **not** fake it — open on the real product UI
  instead and skip this move.

## Sourcing the logo

```bash
# repo app icon (best — usually 512–1024px, transparent or on brand colour)
curl -sL -o logo.png https://raw.githubusercontent.com/<owner>/<repo>/main/resources/build/icon.png
# site favicon / OG image
curl -sL -o logo.svg https://<product>.dev/favicon.svg
# GitHub org avatar (fallback)
curl -sL -o logo.png "https://github.com/<org>.png?size=512"
```
Verify it actually rendered before using it — a 404 saved as `.png` is a text file.

## The brick

`components/logo-blur-reveal.html` is the working scene: markup, CSS and the GSAP calls,
with the two timing variables at the top. Copy it into the video's `build.py` and set
`REVEAL` to the name's word onset.

## Sound

- `riser` from the top of the hook, **cresting on REVEAL**.
- `magic-reveal` **at** REVEAL, gain ~0.15 (this is the hero moment).
- `futuristic-click` +0.12s on the wordmark.
