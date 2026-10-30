// Platform safe zones: where Reels/TikTok/Instagram/YouTube put their own UI. Text must stay clear of these bands.
// The composition's layout margins (FORMATS[*].safe) are derived from them with a little breathing room, and the
// measured text boxes from the browser are checked against them after layout (see render.js → QA).

/** Unsafe bands as fractions of the canvas (top/bottom of height, left/right of width). */
export const PLATFORM_ZONES = {
  // Reels/TikTok/Shorts: status + tabs on top, caption/handle/audio/CTA at the bottom, action rail on the right.
  // The owner's rule (2026-10-13): keep text, logo and product out of the top ~14 % (270 px), the bottom ~35 %
  // (670 px) and ~6 % per side; the right keeps 14 % for the like/comment/share rail.
  '9:16': { top: 0.14, bottom: 0.35, left: 0.06, right: 0.14, platform: 'Reels/TikTok' },
  // Instagram feed 4:5 is shown whole, but the profile grid crops it to 3:4 and the like bar hugs the bottom.
  '4:5': { top: 0.05, bottom: 0.07, left: 0.06, right: 0.06, platform: 'Instagram-flödet' },
  '1:1': { top: 0.05, bottom: 0.06, left: 0.05, right: 0.05, platform: 'flödet' },
  // YouTube/LinkedIn players: title on top, progress bar + captions at the bottom.
  '16:9': { top: 0.08, bottom: 0.12, left: 0.05, right: 0.05, platform: 'YouTube/LinkedIn' },
};

export const FORMATS = {
  '9:16': { W: 1080, H: 1920, safe: { top: 290, bottom: 690, left: 108, right: 156 } },
  '4:5': { W: 1080, H: 1350, safe: { top: 110, bottom: 150, left: 90, right: 90 } },
  '1:1': { W: 1080, H: 1080, safe: { top: 80, bottom: 90, left: 80, right: 80 } },
  '16:9': { W: 1920, H: 1080, safe: { top: 100, bottom: 140, left: 140, right: 140 } },
};

/** Unsafe rectangles in px: [{zone, x0, y0, x1, y1}]. */
export function unsafeRects(format) {
  const fmt = FORMATS[format] || FORMATS['9:16'];
  const z = PLATFORM_ZONES[format] || PLATFORM_ZONES['9:16'];
  const { W, H } = fmt;
  return [
    { zone: 'top', x0: 0, y0: 0, x1: W, y1: Math.round(H * z.top) },
    { zone: 'bottom', x0: 0, y0: Math.round(H * (1 - z.bottom)), x1: W, y1: H },
    { zone: 'left', x0: 0, y0: 0, x1: Math.round(W * z.left), y1: H },
    { zone: 'right', x0: Math.round(W * (1 - z.right)), y0: 0, x1: W, y1: H },
  ];
}

/**
 * boxes: [{id, x, y, w, h}] in canvas px (measured text boxes). Returns violations [{id, zone, px}] where a box
 * reaches more than `tolerance` px into an unsafe band.
 */
export function checkSafeZones(boxes, format, { tolerance = 2 } = {}) {
  const out = [];
  const rects = unsafeRects(format);
  for (const b of boxes || []) {
    if (!b || !(b.w > 0) || !(b.h > 0)) continue;
    const bx0 = b.x, by0 = b.y, bx1 = b.x + b.w, by1 = b.y + b.h;
    for (const r of rects) {
      const ix = Math.min(bx1, r.x1) - Math.max(bx0, r.x0);
      const iy = Math.min(by1, r.y1) - Math.max(by0, r.y0);
      if (ix <= 0 || iy <= 0) continue;
      const depth = r.zone === 'top' ? r.y1 - by0 : r.zone === 'bottom' ? by1 - r.y0 : r.zone === 'left' ? r.x1 - bx0 : bx1 - r.x0;
      if (depth > tolerance) out.push({ id: b.id, zone: r.zone, px: Math.round(depth) });
    }
  }
  return out;
}

/** The layout margins must contain the platform bands (guards edits of FORMATS). */
export function marginsCoverZones(format) {
  const fmt = FORMATS[format];
  const z = PLATFORM_ZONES[format];
  return fmt.safe.top >= fmt.H * z.top && fmt.safe.bottom >= fmt.H * z.bottom
    && fmt.safe.left >= fmt.W * z.left && fmt.safe.right >= fmt.W * z.right;
}

const ZONE_SV = { top: 'övre', bottom: 'nedre', left: 'vänstra', right: 'högra' };

export function describeViolations(violations, format) {
  const z = PLATFORM_ZONES[format] || PLATFORM_ZONES['9:16'];
  const byScene = {};
  for (const v of violations) (byScene[v.id] ||= []).push(`${ZONE_SV[v.zone]} ${v.px} px`);
  return Object.entries(byScene).map(([id, parts]) =>
    `Säker yta: texten i scen ${id} går in i ${z.platform}-gränssnittets zon (${parts.join(', ')}).`);
}
