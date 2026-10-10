// Typography: type scale, Swedish-aware balanced line breaking and the brand font map.
// breakLines() is self-contained on purpose: compose.js inlines its source into the browser runtime, where it runs
// with real measured word widths. Node (tests, planning) runs the same function with estimated widths.
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const FONTS_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'fonts');

/**
 * Bundled OFL fonts (edit-renderer/fonts, licences in fonts/OFL.txt). Nothing is fetched at render time.
 * key: lower-case family name. css: the family name used in the composition.
 */
export const FONT_FACES = {
  inter: { css: 'Inter', fallback: 'sans-serif', files: [['inter-400.woff2', 400], ['inter-500.woff2', 500], ['inter-600.woff2', 600], ['inter-700.woff2', 700]] },
  anton: { css: 'Anton', fallback: 'sans-serif', files: [['anton.woff2', 400]], display: true },
  'caveat brush': { css: 'Caveat Brush', fallback: 'cursive', files: [['caveat-brush.ttf', 400]], script: true },
  'playfair display': { css: 'Playfair Display', fallback: 'serif', serif: true,
    files: [['playfair-500.woff2', 500], ['playfair-600.woff2', 600], ['playfair-700.woff2', 700], ['playfair-500-italic.woff2', 500, 'italic']] },
};
const ALIASES = { playfair: 'playfair display', caveat: 'caveat brush', 'caveatbrush': 'caveat brush', serif: 'playfair display',
  georgia: 'playfair display', 'times new roman': 'playfair display', times: 'playfair display' };
// Generic UI fallbacks in brand kits ("Inter, Arial, sans-serif") – Inter covers them without a warning.
const GENERIC = new Set(['arial', 'helvetica', 'helvetica neue', 'sans-serif', 'system-ui', '-apple-system', 'segoe ui', 'roboto',
  'montserrat', 'manrope', 'poppins', 'dm sans', 'open sans', 'lato']);

/**
 * Brand font_family ("Playfair Display, Georgia, serif") → {text, display, warning}. text is the face for body copy;
 * display is the poster face (Anton unless the brand's own face is a display/serif face).
 */
export function resolveBrandFonts(fontFamily, { display = null } = {}) {
  const names = String(fontFamily || '').split(',').map((s) => s.trim().replace(/^['"]|['"]$/g, '').toLowerCase()).filter(Boolean);
  let text = null;
  let warning = null;
  for (const name of names) {
    const key = FONT_FACES[name] ? name : ALIASES[name];
    if (key) { text = key; break; }
    if (GENERIC.has(name)) { text = 'inter'; break; }
  }
  if (!text) {
    text = 'inter';
    if (names.length) warning = `Typsnittet ${String(fontFamily).split(',')[0].trim().replace(/^['"]|['"]$/g, '')} finns inte i renderaren; Inter används.`;
  }
  if (FONT_FACES[text].display || FONT_FACES[text].script) {
    // A display or script face is for headlines, never for running copy.
    return { text: 'inter', display: text, warning };
  }
  const displayKey = display && FONT_FACES[String(display).toLowerCase()] ? String(display).toLowerCase() : 'anton';
  return { text, display: FONT_FACES[text].serif && !display ? text : displayKey, warning };
}

export function fontFiles(keys) {
  const out = [];
  for (const key of new Set(keys)) {
    for (const [file, weight, style = 'normal'] of FONT_FACES[key].files) {
      if (existsSync(join(FONTS_DIR, file))) out.push({ key, family: FONT_FACES[key].css, file, weight, style });
    }
  }
  return out;
}

/**
 * Type scale (major third, 1.25) in px for a 1080-wide reference canvas. Every text size in the cut comes from these
 * steps so headlines, body copy and labels relate to each other across scenes.
 */
export const SCALE = [36, 44, 56, 70, 88, 110, 138, 172, 215];
export const ROLE = {
  // style: [center step, side step] (indexes into SCALE)
  slam: [7, 6], extrusion: [7, 6], caption: [7, 6], chunk: [6, 5], rise: [5, 4], 'line-reveal': [5, 4], 'blur-in': [5, 4],
  typewriter: [4, 3], 'tracking-in': [4, 4], cascade: [5, 4], highlight: [5, 4], shimmer: [5, 4], 'lower-third': [2, 2],
  scramble: [4, 4], 'weight-shift': [5, 4], script: [6, 5],
};
const DISPLAY_STYLES = new Set(['slam', 'extrusion', 'caption', 'chunk']);

/** Max characters per line by format and role (display hooks on 9:16 stay at ~22). */
export function maxChars(format, style) {
  const display = DISPLAY_STYLES.has(style);
  const table = { '9:16': [22, 26], '4:5': [24, 30], '1:1': [24, 30], '16:9': [32, 42] };
  const [d, b] = table[format] || table['9:16'];
  return display ? d : b;
}

/** Steps (px, descending) a text block may use, scaled to the canvas. */
export function sizeSteps(format, style, position, W, H) {
  const [c, s] = ROLE[style] || ROLE.rise;
  const top = position === 'center' ? c : s;
  // 16:9 is wide but short: scale by the shorter side. Portrait/square scale by width.
  const k = Math.min(W, H) / 1080 * (format === '1:1' ? 0.94 : 1);
  return SCALE.slice(0, top + 1).reverse().map((v) => Math.round(v * k));
}

/** Leading and tracking per role and size (tighter as type grows; condensed caps get a hair of air). */
export function metrics(style, face) {
  if (DISPLAY_STYLES.has(style) && face === 'anton') return { leading: 0.98, tracking: 0.01 };
  if (DISPLAY_STYLES.has(style)) return { leading: 1.0, tracking: -0.02 };
  if (style === 'lower-third') return { leading: 1.12, tracking: -0.005 };
  if (face === 'playfair display') return { leading: 1.08, tracking: -0.01 };
  return { leading: 1.06, tracking: -0.022 };
}

/** Swedish (and English) function words that belong with the next word: never end a line on them. */
export const GLUE_WORDS = ['i', 'på', 'en', 'ett', 'och', 'att', 'av', 'för', 'till', 'med', 'om', 'som', 'den', 'det', 'de', 'är',
  'vid', 'din', 'min', 'sin', 'ditt', 'mitt', 'sitt', 'dina', 'mina', 'sina', 'er', 'ert', 'era', 'vår', 'vårt', 'våra', 'hos',
  'från', 'utan', 'över', 'under', 'efter', 'innan', 'än', 'eller', 'men', 'så', 'inte', 'bara', 'mer', 'mest', 'alla', 'varje',
  'när', 'där', 'du', 'vi', 'jag', 'ni', 'han', 'hon', 'man', 'kan', 'ska', 'vill', 'får', 'mot', 'per', 'nu', 'ny', 'nya', 'nytt',
  'the', 'a', 'an', 'of', 'to', 'in', 'on', 'for', 'and', 'with', 'your', 'our', 'my'];

export function isGlue(word) {
  const w = String(word || '').toLowerCase().replace(/[^\p{L}\p{N}%]/gu, '');
  return GLUE_WORDS.includes(w) || /^\d+([.,]\d+)?%?$/.test(w);
}

/**
 * Balanced line breaking (Knuth-style DP over break points; only GLUE_WORDS comes from outside, the runtime defines it too).
 *   widths: word widths (px), space: inter-word space (px), maxW: line width (px)
 *   opts.texts: word strings (for Swedish glue words / numbers / char limits), opts.maxChars, opts.maxLines
 * Returns {lines: [[from, to)...], widths: [...], cost} with the fewest lines that fit, balanced, or null when a word
 * is wider than maxW or the text needs more than maxLines lines. Rules:
 *   - lines as equal as possible (squared deviation from the mean line),
 *   - never a single-word last line when the text has 3+ words (no orphans),
 *   - no line break after a short function word or between a number and its unit ("400 klubbar", "på två"),
 *   - no line longer than maxChars characters (single long words excepted).
 */
export function breakLines(widths, space, maxW, opts) {
  const o = opts || {};
  const n = widths.length;
  if (!n) return { lines: [], widths: [], cost: 0 };
  const texts = o.texts || [];
  const maxLines = o.maxLines || 4;
  const limit = o.maxChars || 0;
  const clean = (s) => String(s || '').toLowerCase().replace(/[^\p{L}\p{N}%]/gu, '');
  const chars = widths.map((_, i) => String(texts[i] || '').length || 1);
  // glue[i]: a break after word i is bad.
  const glue = widths.map((_, i) => {
    if (i >= n - 1) return 0;
    const w = clean(texts[i]);
    if (/^\d+([.,]\d+)?%?$/.test(w)) return 4; // number → keep with its unit (strong)
    if (/[,:;.!?–—]$/.test(String(texts[i] || '').trim())) return -0.5; // punctuation is a natural break
    return GLUE_WORDS.includes(w) ? 1 : 0;
  });
  const lineW = (a, b) => { let s = 0; for (let k = a; k < b; k++) s += widths[k]; return s + space * (b - a - 1); };
  const lineC = (a, b) => { let s = 0; for (let k = a; k < b; k++) s += chars[k]; return s + (b - a - 1); };
  const fits = (a, b) => lineW(a, b) <= maxW + 0.5 && (b - a === 1 || !limit || lineC(a, b) <= limit);
  for (let i = 0; i < n; i++) if (widths[i] > maxW + 0.5) return null;
  for (let k = 1; k <= Math.min(maxLines, n); k++) {
    const mean = (lineW(0, n) - space * (k - 1)) / k;
    // best[j][m]: min cost to set words [0, j) in m lines; prev for the path.
    const best = Array.from({ length: n + 1 }, () => new Array(k + 1).fill(Infinity));
    const prev = Array.from({ length: n + 1 }, () => new Array(k + 1).fill(-1));
    best[0][0] = 0;
    for (let m = 1; m <= k; m++) {
      for (let j = 1; j <= n; j++) {
        for (let i = j - 1; i >= 0; i--) {
          if (!fits(i, j)) break;
          if (best[i][m - 1] === Infinity) continue;
          if (j === n && m === k && k > 1 && n >= 3 && j - i === 1) continue; // orphan: single-word last line
          const dev = (lineW(i, j) - mean) / maxW;
          let cost = dev * dev;
          if (j < n) cost += glue[j - 1] > 0 ? 0.15 * glue[j - 1] : glue[j - 1] < 0 ? -0.02 : 0;
          const total = best[i][m - 1] + cost;
          if (total < best[j][m]) { best[j][m] = total; prev[j][m] = i; }
        }
      }
    }
    if (best[n][k] === Infinity) continue;
    const lines = [];
    for (let j = n, m = k; m > 0; m--) { const i = prev[j][m]; lines.unshift([i, j]); j = i; }
    return { lines, widths: lines.map(([a, b]) => lineW(a, b)), cost: best[n][k] };
  }
  return null;
}

/** Rough advance widths (em) for planning/tests without a browser: narrow, regular and wide glyph classes. */
export function estimateWidth(text, size, { condensed = false, tracking = 0 } = {}) {
  let em = 0;
  for (const ch of String(text)) {
    let w = /[iljtf.,:;!'|]/.test(ch) ? 0.3 : /[mwMWÅÄÖ@%]/.test(ch) ? 0.86 : /[A-ZÅÄÖ0-9]/.test(ch) ? 0.68 : 0.56;
    if (condensed) w *= 0.62;
    em += w + tracking;
  }
  return em * size;
}

/** Plan a text block in Node (used for tests and the meta report). */
export function planLines(text, { size, maxW, maxChars: limit, maxLines = 4, condensed = false } = {}) {
  const list = String(text).replace(/\*/g, '').split(/\s+/).filter(Boolean);
  const widths = list.map((w) => estimateWidth(w, size, { condensed }));
  const res = breakLines(widths, size * 0.26, maxW, { texts: list, maxChars: limit, maxLines });
  return res && res.lines.map(([a, b]) => list.slice(a, b).join(' '));
}
