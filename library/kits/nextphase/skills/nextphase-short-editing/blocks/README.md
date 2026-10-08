# Registry blocks & components

Installed 2026-08-07 via `npx hyperframes add`. Config lives in `../hyperframes.json`
(`blocks/` for blocks, `components/` for components, `assets/` for assets), so re-running
`npx hyperframes add <name> --dir .claude/skills/nextphase-short-editing` from the repo root
puts new items in the same place.

## Blocks — sub-compositions, included by src

| file | composition id | ships | native size |
|---|---|---|---|
| `blocks/data-chart.html` | `data-chart` | 15s | 1920×1080 |
| `blocks/code-snippet-dark-2026.html` | `vscode-dark-2026` | 11s | 1920×1080 |
| `blocks/liquid-glass-notification.html` | `liquid-glass-notification` | 8s | 1920×1080 |

```html
<div class="clip band"
     data-composition-id="data-chart"
     data-composition-src="blocks/data-chart.html"
     data-start="0" data-duration="12"
     data-width="1920" data-height="1080" data-track-index="1"></div>
```

### Every one of them is 16:9 — this kit is 9:16

They are all authored at 1920×1080. Dropped into a 1080×1920 short they either overflow or
letterbox. The working pattern is a **scaled band**: keep the block at its native size and
scale the placeholder down to the frame width, then position the band vertically.

```css
.band{position:absolute;left:0;width:1920px;height:1080px;
      transform-origin:top left;transform:scale(.5625);   /* 1920 → 1080 wide */
      overflow:hidden}
#chart{top:300px}      /* 1080×607 once scaled */
```

Verified: `data-chart` + `code-snippet-dark-2026` both render correctly in a 1080×1920 host
this way. The house plate fills whatever the band does not cover, so it reads as a designed
frame rather than a letterbox.

### `code-snippet-dark-2026` cannot be snapshotted standalone

Its markup lives inside `<template id="vscode-dark-2026-template">`, so nothing is in the
live DOM until a host clones it. Running `hyperframes snapshot` on the file alone fails with
*"Could not determine composition duration"* — that is expected, not a broken block. It also
carries no `data-duration` of its own: **the host must supply it** (`data-duration="11"`).
`data-chart` and `liquid-glass-notification` do render standalone.

### `liquid-glass-notification` is off-palette by default

It draws a WebGPU liquid-glass field in vivid blue/orange behind iOS-style notification
cards. The notification cards are the reusable part; the background is nothing like the house
plate. Either restyle the field to coral/cream or mask to just the cards. It also depends on
`blocks/lib/liquid-glass.iife.js` and needs WebGPU — check it renders on the render target
before committing a video to it.

## Components — snippets, pasted into a host

| file | what it does |
|---|---|
| `components/caption-blend-difference.html` | captions that auto-invert per pixel via `mix-blend-mode:difference` — white on dark areas, black on light. Needs `isolation:isolate` on a shared ancestor of the video and the caption layer. Variants: `.blend-difference`, `-soft` (exclusion), `-screen`. |
| `components/parallax-zoom.html` | a card grid where the focal card scales up to fill the frame while siblings push outward. Drive `--pz-progress` 0→1 from the paused GSAP timeline. Tunables: `--pz-focus-scale`, `--pz-sibling-push`, `--pz-sibling-fade`. |

`caption-blend-difference` is worth a look against the current caption spec: the kit's three
styles are Parallax / Weight Shift / Highlighted, and this is a fourth behaviour, not a
restyle of those. It solves the real problem of a caption crossing a light and a dark region
in the same shot — but it is not in the caption table yet, so treat it as a candidate rather
than an approved style.
