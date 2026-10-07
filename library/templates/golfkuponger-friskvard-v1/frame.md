---
version: alpha
name: Golfkuponger Editorial — Frame (video / frame layer)
description: >
  editorial-forest preset re-cut to the Golfkuponger brand as captured from the experiment-site
  theme: deep forest green / warm cream / gold, Playfair Display 500 for display, Inter for body and
  tracked uppercase chrome. Photo-led: real course photography from the site carries the mood, with
  a deep-green scrim for legibility. Flat UI chrome, 2px hairlines, 6/8px radii, gold GK emblem as
  the identity stamp.
unit: the frame — 1080×1080 (1:1) for this video
principle: atoms are sacred · composition is free · numbers come from the site

colors:
  green: "#073C2B"        # brand heading green / gravity surfaces (--gk-surface-green)
  green-deep: "#01170F"   # deepest ground, photo scrim base (--gk-deep)
  green-lite: "#153F2D"   # secondary green tile (--gk-green-soft)
  pink: "#D6A536"         # ACCENT = brand gold (--gk-gold); key name kept for script compatibility
  pink-deep: "#B98516"    # darker gold for gold-on-cream text (--gk-surface-light-icon)
  cream: "#F8F4EC"        # paper ground (--gk-cream)
  cream-2: "#FFFDF8"      # card paper (--gk-paper)
  ink: "#142018"          # body ink on cream (--gk-ink)

typography:
  body:        { fontFamily: "Inter", cqw: 3.1, weight: 400, lineHeight: 1.38 }
  body-card:   { fontFamily: "Inter", cqw: 2.6, weight: 400, lineHeight: 1.34 }
  label:       { fontFamily: "Inter", cqw: 2.2, weight: 600, tracking: "0.18em", upper: true }
  caption-mono:{ fontFamily: "Inter", cqw: 2.0, weight: 600, tracking: "0.14em", upper: true }
  title-card-sm:{ fontFamily: "Playfair Display", cqw: 5.0, weight: 500, lineHeight: 1.02, tracking: "-0.01em" }
  title-card:  { fontFamily: "Playfair Display", cqw: 6.0, weight: 500, lineHeight: 1.0, tracking: "-0.01em" }
  headline:    { fontFamily: "Playfair Display", cqw: 7.4, weight: 500, lineHeight: 1.04, tracking: "-0.015em" }
  headline-xl: { fontFamily: "Playfair Display", cqw: 9.0, weight: 500, lineHeight: 1.0, tracking: "-0.02em" }
  display:     { fontFamily: "Playfair Display", cqw: 11.0, weight: 500, lineHeight: 1.0, tracking: "-0.02em" }
  display-hero:{ fontFamily: "Playfair Display", cqw: 14.0, weight: 500, lineHeight: 0.96, tracking: "-0.02em" }
  stat-figure: { fontFamily: "Playfair Display", cqw: 20.0, weight: 600, lineHeight: 0.92, tracking: "-0.03em" }
  stat-figure-unit:{ fontFamily: "Playfair Display", cqw: 8.0, weight: 500, lineHeight: 0.92 }
  name:        { fontFamily: "Inter", cqw: 3.6, weight: 600, lineHeight: 1.0 }

spacing:
  slide-pad: "7cqw"
  rule: "2px"
  rule-card: "2.5px"
  radius-card: "6px"
  radius-step: "8px"

components:
  topbar:
    typography: "{typography.label} — 'GOLFKUPONGER.SE' left, 'FRISKVÅRD' right"
    placement: "top edge inside slide-pad"
    description: "Quiet brand spine on content frames; may be omitted on the full-bleed hook and the close."
  photo-plate:
    description: "Full-bleed course photo from capture/assets with a deep-green scrim (green-deep → transparent, ≤ 78% opacity) under any text. Slow push-in only."
  gold-rule:
    border: "2px solid {colors.pink}"
    description: "Short 2px gold hairline under a headline or figure; the main accent mark."
  chip:
    backgroundColor: "{colors.cream-2} with 2px {colors.green} border, or {colors.green} with cream text"
    rounded: "{spacing.radius-card}"
    typography: "{typography.label}"
    description: "Activity chips (Greenfee · Range · Lektioner · Simulator)."
  logo-card:
    backgroundColor: "#FFFFFF"
    rounded: "{spacing.radius-step}"
    description: "White 8px card holding one real portal logo at its native colors, generous inner padding; never recolor or crop a logo."
  name-tag:
    typography: "{typography.caption-mono} on a {colors.green-deep} tag, gold left rule"
    description: "Club name label on photo frames."
  emblem:
    description: "Gold GK emblem (assets golfkuponger-logo.png) — identity stamp for the close; the gold wordmark (golfkuponger-loggan02) sits on green-deep only."
---

## Overview

A calm, premium Swedish golf brand. One message per frame, large Playfair headlines, real course
photography, gold used sparingly as the single accent. Feels like the experiment-site homepage in
motion: deep forest green, warm cream paper, gold detailing.

## Colors

- Grounds: `green-deep` / `green` for hook, stat and close; `cream` for the portal frame.
- Headlines: cream on green/photo, `green` on cream. Gold (`pink` key) only for one word, a figure,
  or a 2px rule — never a whole paragraph.
- Body: `cream` at ≥ 86% on green; `ink` on cream.
- No fourth color family. Portal logos keep their own colors on white `logo-card`s.

## Typography

- Playfair Display 500 (600 for the big figure) for every headline and stat; Inter 400 body;
  Inter 600 uppercase, tracked 0.14–0.18em for labels. No third face.
- Legibility floor for a feed video: any load-bearing line ≥ 3cqw (≈ 32px at 1080).
- Swedish characters (å ä ö) must render in both faces — both are loaded locally below.

## Depth & Surface

Flat chrome: no box-shadows on UI, 2px hairlines, 6/8px radii. Photographs may carry a deep-green
scrim gradient purely for text legibility — that is the only gradient allowed.

## Composition Rules (1:1)

- Safe area 7cqw; keep text out of the outer 7cqw and the bottom 12cqw on photo frames.
- One subject per frame; left-aligned or centered stacks; headline ≤ 86cqw wide.
- Hook and close may be centered; content frames lean left.

## Approved Real Entities

- Golfkuponger brand marks: `golfkuponger-logo.png` (gold emblem), `golfkuponger-loggan02-2026-04-10-cropped.png` (gold wordmark on black).
- Benefit portals shown on golfkuponger.se/pages/friskvard: **Benifex, ePassi, Söderberg & Partners, Edenred** — use the captured logo files exactly as supplied.
- Clubs named on the homepage: Bro Hof Slott, Halmstad GK, Falsterbo GK, Österåker GK.

## Numerals & Claims (hard rule)

Only figures from the site: **5 000 kr** max skattefritt friskvårdsbidrag per år (arbetsgivaren
bestämmer beloppet), **300+** anslutna golfklubbar, giltig **12 månader**. Nothing else.

## Font loading

Fonts ship as local files in `assets/fonts/` — do NOT link Google Fonts. Paste this `<style>` into
every frame's `<head>`/`<template>`:

```html
<style>
@font-face{font-family:'Inter';src:url("assets/fonts/inter-400.woff2") format('woff2');font-weight:400;font-style:normal;font-display:block;}
@font-face{font-family:'Inter';src:url("assets/fonts/inter-500.woff2") format('woff2');font-weight:500;font-style:normal;font-display:block;}
@font-face{font-family:'Inter';src:url("assets/fonts/inter-600.woff2") format('woff2');font-weight:600;font-style:normal;font-display:block;}
@font-face{font-family:'Inter';src:url("assets/fonts/inter-700.woff2") format('woff2');font-weight:700;font-style:normal;font-display:block;}
@font-face{font-family:'Playfair Display';src:url("assets/fonts/playfair-500.woff2") format('woff2');font-weight:500;font-style:normal;font-display:block;}
@font-face{font-family:'Playfair Display';src:url("assets/fonts/playfair-600.woff2") format('woff2');font-weight:600;font-style:normal;font-display:block;}
@font-face{font-family:'Playfair Display';src:url("assets/fonts/playfair-700.woff2") format('woff2');font-weight:700;font-style:normal;font-display:block;}
@font-face{font-family:'Playfair Display';src:url("assets/fonts/playfair-500-italic.woff2") format('woff2');font-weight:500;font-style:italic;font-display:block;}
</style>
```
