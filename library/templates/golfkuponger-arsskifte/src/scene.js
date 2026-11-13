// Golfkuponger – "Vad händer med ditt friskvårdsbidrag vid årsskiftet?" (9:16, tecknad premiumillustration)
// Deterministisk: renderAt(t) ritar exakt bildrutan för tiden t. Ingen slump utan frö, ingen klocka.
// Stil (Jonas 2026-10-13, referens "bild 2"): djupgrönt med diagonala ljusstrålar och guldstoft, ljust stenbord,
// bordskalender med sidbunt och guldringar, rivna blad som landar, grönt presentkort med guldram som brinner,
// säsongsdekor i hörnen (höstkvist -> granris med guldkulor). Den platta första versionen: scene-v1-platt.js.
'use strict';
const W = 1080, H = 1920, FPS = 30;
const C = {
  ink: '#123d2d', cream: '#F8F4EC', gold: '#D6A536', goldHi: '#F3D27A', goldLo: '#A9792A',
  green: '#0f7a50', deep: '#082f27', red: '#C8462E', dark: '#0c140f',
};

// ---------- Tidslinje (sekunder, scentid) ----------
const TL = {
  ignite: 0.9, liftStart: 11.9, ballStart: 12.1, impact: 12.3,
  revealStart: 12.55, revealEnd: 13.35, irisStart: 17.45, end: 18.0,
};
// {…} = markerad ruta. Textfönster i verklig tid (efter tidsförskjutningen D nedan).
const TEXTS = [
  { id: 't1', win: [0.15, 5.4], size: 104, lines: ['VAD HÄNDER MED DITT', 'FRISKVÅRDSBIDRAG', '{VID ÅRSSKIFTET?}'], fg: C.cream, box: C.cream, boxFg: C.deep },
  { id: 't2', win: [5.4, 8.75], size: 116, lines: ['HAR DU', '{FRISKVÅRDSBIDRAG}', 'KVAR?'], fg: C.cream, box: C.gold, boxFg: C.deep },
  { id: 't3', win: [8.75, 12.4], size: 124, lines: ['DEN {31 DECEMBER}', 'BRINNER DET INNE.'], fg: C.cream, box: C.red, boxFg: C.cream },
  { id: 't4', win: [13.95, 17.9], size: 126, lines: ['ANVÄND', 'FRISKVÅRDEN', 'TILL {GOLF I TID.}'], fg: C.deep, box: C.deep, boxFg: C.cream },
];
// Bilden sträcks 0,4 s under bläddringen (1,8–10,75 s, knappt märkbart) och allt efter förskjuts 0,4 s.
const D = 0.4, STRETCH = [1.8, 10.35];
function sceneTime(t) {
  if (t <= STRETCH[0]) return t;
  if (t >= STRETCH[1] + D) return t - D;
  return STRETCH[0] + (t - STRETCH[0]) * (STRETCH[1] - STRETCH[0]) / (STRETCH[1] + D - STRETCH[0]);
}
const TEXT_TOP = 300;

// ---------- Hjälpare ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, u) => a + (b - a) * u;
const prog = (t, a, b) => clamp((t - a) / (b - a));
const sstep = (a, b, x) => { const u = prog(x, a, b); return u * u * (3 - 2 * u); };
const eOut = (u) => 1 - Math.pow(1 - u, 3);
const eIn = (u) => u * u * u;
const eBack = (u) => { const c = 1.7; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); };
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const f1 = (n) => n.toFixed(1);
function hexMix(a, b, u) {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16)), pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return '#' + pa.map((v, i) => Math.round(lerp(v, pb[i], u)).toString(16).padStart(2, '0')).join('');
}
const noise = (x, s) => Math.sin(x * 1.7 + s) * 0.5 + Math.sin(x * 3.1 + s * 2.3) * 0.3 + Math.sin(x * 7.3 + s * 0.7) * 0.2;

// ---------- Kalenderns rivschema ----------
// Sida k = 1 okt + k dagar. Sida 90 = 30 dec (lyfts, rivs av bollen), 91 = 31 dec.
const TEAR = [];
(function buildTears() {
  TEAR[0] = 0.75; TEAR[1] = 1.3;
  const A = [[1.8, 2], [3.0, 12], [5.6, 50], [8.3, 72], [10.0, 84]];
  for (let k = 2; k <= 84; k++) {
    let i = 0; while (i < A.length - 2 && k > A[i + 1][1]) i++;
    const [t0, k0] = A[i], [t1, k1] = A[i + 1];
    TEAR[k] = t0 + (t1 - t0) * (k - k0) / (k1 - k0);
  }
  [10.35, 10.7, 11.0, 11.3, 11.6].forEach((t, i) => { TEAR[85 + i] = t; });
  TEAR[90] = TL.impact + 0.02; // 30 dec blåser bort i smällen
})();
const tearDur = (k) => clamp(((TEAR[k] - (TEAR[k - 1] ?? TEAR[k] - 0.6))) * 3.2, 0.3, 0.7);
const MONTHS = ['JANUARI', 'FEBRUARI', 'MARS', 'APRIL', 'MAJ', 'JUNI', 'JULI', 'AUGUSTI', 'SEPTEMBER', 'OKTOBER', 'NOVEMBER', 'DECEMBER'];
const DAYS = ['SÖNDAG', 'MÅNDAG', 'TISDAG', 'ONSDAG', 'TORSDAG', 'FREDAG', 'LÖRDAG'];
function dateOf(k) { const d = new Date(2026, 9, 1 + k); return { day: d.getDate(), month: MONTHS[d.getMonth()], wd: DAYS[d.getDay()], sun: d.getDay() === 0 }; }
function topPage(t) { let n = 0; while (n < 90 && TEAR[n] <= t) n++; return n; }

// ---------- Layout ----------
// Safe zones (Reels): allt viktigt inom x 65–929, y 270–1250.
const PW = 480, PH = 440, CAL_S = 1.15, HINGE = { x: 420, y: 765 }, DESK_Y = 1175;

// Statiska texturer (beräknas en gång).
const SPECK = (() => { const r = rng(77); let s = ''; for (let i = 0; i < 140; i++) s += `<circle cx="${f1(r() * 180)}" cy="${f1(r() * 180)}" r="${f1(0.6 + r() * 1.6)}" fill="${r() < 0.5 ? '#6d5a40' : '#fff8e8'}" opacity="${(0.15 + r() * 0.35).toFixed(2)}"/>`; return s; })();
const GRAIN = (() => { const r = rng(78); let s = ''; for (let i = 0; i < 90; i++) s += `<circle cx="${f1(r() * 120)}" cy="${f1(r() * 120)}" r="${f1(0.4 + r() * 0.9)}" fill="#8a7650" opacity="${(0.08 + r() * 0.14).toFixed(2)}"/>`; return s; })();

function defs() {
  return `<defs>
  <pattern id="speck" width="180" height="180" patternUnits="userSpaceOnUse">${SPECK}</pattern>
  <pattern id="grain" width="120" height="120" patternUnits="userSpaceOnUse">${GRAIN}</pattern>
  <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FCF8EE"/><stop offset="1" stop-color="#EFE4CB"/></linearGradient>
  <linearGradient id="pageLight" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#5a4320" stop-opacity=".12"/></linearGradient>
  <linearGradient id="band" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#145b41"/><stop offset="1" stop-color="#0c412e"/></linearGradient>
  <linearGradient id="binder" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1a6449"/><stop offset="1" stop-color="#0b3627"/></linearGradient>
  <linearGradient id="goldS" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBE7A1"/><stop offset=".45" stop-color="#D9AC4A"/><stop offset="1" stop-color="#8E6420"/></linearGradient>
  <linearGradient id="goldH" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8E6420"/><stop offset=".35" stop-color="#F6DC8A"/><stop offset=".6" stop-color="#D3A445"/><stop offset="1" stop-color="#8E6420"/></linearGradient>
  <radialGradient id="bauble" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#FFF3C4"/><stop offset=".35" stop-color="#E2B552"/><stop offset="1" stop-color="#6E4A14"/></radialGradient>
  <linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3A7A5C"/><stop offset="1" stop-color="#1A4936"/></linearGradient>
  <linearGradient id="coupon" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F6DA86"/><stop offset=".55" stop-color="#D6A536"/><stop offset="1" stop-color="#B98A2E"/></linearGradient>
  <linearGradient id="table" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E9DCC0"/><stop offset=".35" stop-color="#D5C3A0"/><stop offset="1" stop-color="#8C7858"/></linearGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFF4D6" stop-opacity=".16"/><stop offset=".6" stop-color="#FFF4D6" stop-opacity=".05"/><stop offset="1" stop-color="#FFF4D6" stop-opacity="0"/></linearGradient>
  <linearGradient id="flO" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FF5A14"/><stop offset=".55" stop-color="#FF7A1A"/><stop offset="1" stop-color="#FF3D0D" stop-opacity="0"/></linearGradient>
  <linearGradient id="flM" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FFB22E"/><stop offset="1" stop-color="#FF8A1F" stop-opacity=".2"/></linearGradient>
  <linearGradient id="flI" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#FFFBE6"/><stop offset="1" stop-color="#FFD84A"/></linearGradient>
  <radialGradient id="fireGlow"><stop offset="0" stop-color="#FF9A3C" stop-opacity=".6"/><stop offset="1" stop-color="#FF9A3C" stop-opacity="0"/></radialGradient>
  <radialGradient id="ball" cx="38%" cy="32%" r="70%"><stop offset="0" stop-color="#ffffff"/><stop offset=".7" stop-color="#e9edee"/><stop offset="1" stop-color="#b9c2c5"/></radialGradient>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8FC7DA"/><stop offset=".55" stop-color="#DCEBD6"/><stop offset="1" stop-color="#F6EDCB"/></linearGradient>
  <radialGradient id="sunGlow"><stop offset="0" stop-color="#fff2b0" stop-opacity=".95"/><stop offset="1" stop-color="#fff2b0" stop-opacity="0"/></radialGradient>
  <linearGradient id="hillShade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity=".12"/><stop offset="1" stop-color="#0b3a1f" stop-opacity=".25"/></linearGradient>
  <radialGradient id="holeLight"><stop offset="0" stop-color="#fff6cf" stop-opacity=".95"/><stop offset="1" stop-color="#ffe9a0" stop-opacity="0"/></radialGradient>
  <radialGradient id="vig" cx="50%" cy="50%" r="75%"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".15"/></radialGradient>
  <linearGradient id="ray" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff3c4" stop-opacity=".55"/><stop offset="1" stop-color="#ffe7a0" stop-opacity="0"/></linearGradient>
  <filter id="sh" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="10" dy="18" stdDeviation="16" flood-color="#000" flood-opacity=".4"/></filter>
  <filter id="shS" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="5" dy="8" stdDeviation="7" flood-color="#2a1d0c" flood-opacity=".35"/></filter>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
  <filter id="blur3"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="blur14" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="14"/></filter>
  <filter id="blur30" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="30"/></filter>
  </defs>`;
}

// ---------- Rummet ----------
function background(t, d) {
  const okt = '#24563a', nov = '#164a35', dec = '#134634';
  const c = d < 40 ? hexMix(okt, nov, sstep(24, 40, d)) : hexMix(nov, dec, sstep(48, 66, d));
  let s = `<radialGradient id="bgGrad" cx="32%" cy="26%" r="95%"><stop offset="0" stop-color="${c}"/><stop offset=".55" stop-color="#0c3123"/><stop offset="1" stop-color="#061a12"/></radialGradient>
    <rect width="${W}" height="${H}" fill="url(#bgGrad)"/>`;
  // diagonala ljusstrålar uppifrån vänster
  s += `<g filter="url(#blur30)" transform="rotate(34)">`;
  [[-260, 150, 0.9], [-80, 90, 0.6], [120, 190, 0.75], [360, 110, 0.5], [560, 160, 0.45]].forEach(([y, h, o], i) => {
    s += `<rect x="-200" y="${y}" width="2600" height="${h}" fill="url(#beam)" opacity="${(o * (0.85 + 0.15 * Math.sin(t * 0.7 + i))).toFixed(2)}"/>`;
  });
  s += '</g>';
  // stenbordet
  s += `<rect x="0" y="${DESK_Y}" width="${W}" height="${H - DESK_Y}" fill="url(#table)"/>
    <rect x="0" y="${DESK_Y}" width="${W}" height="${H - DESK_Y}" fill="url(#speck)" opacity=".7"/>
    <path d="M-100,${DESK_Y + 40} L520,${DESK_Y} L1180,${DESK_Y + 420} L700,${H} L-100,${H}Z" fill="#FFF6DE" opacity=".16" filter="url(#blur30)"/>
    <rect x="0" y="${DESK_Y}" width="${W}" height="14" fill="#3a2c18" opacity=".18" filter="url(#blur3)"/>`;
  return s;
}

function goldDust(t) {
  let s = '';
  const r = rng(41);
  for (let i = 0; i < 34; i++) {
    const x0 = r() * 1080, y0 = r() * 1900, sp = 12 + r() * 30, rad = 1.2 + r() * 2.6, ph = r() * 6, tw = 0.35 + 0.65 * Math.abs(Math.sin(t * (0.8 + r() * 1.5) + ph));
    const y = ((y0 - sp * t) % 1900 + 1900) % 1900, x = x0 + Math.sin(t * 0.5 + ph) * 18;
    s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(rad)}" fill="#F3D27A" opacity="${(0.75 * tw).toFixed(2)}"/>`;
  }
  // fyrspetsiga glimtar
  [[118, 218, 26, 0], [968, 640, 22, 1.7], [905, 1010, 16, 3.1], [92, 655, 18, 4.4]].forEach(([x, y, z, ph]) => {
    const k = 0.55 + 0.45 * Math.sin(t * 2.1 + ph), q = z * k;
    s += `<g transform="translate(${x},${y}) rotate(${f1(t * 8 + ph * 20)})" opacity="${(0.5 + 0.5 * k).toFixed(2)}">
      <circle r="${f1(q * 0.9)}" fill="#FFE9A8" opacity=".25" filter="url(#blur3)"/>
      <path d="M0,${-q} L${q * 0.16},${-q * 0.16} L${q},0 L${q * 0.16},${q * 0.16} L0,${q} L${-q * 0.16},${q * 0.16} L${-q},0 L${-q * 0.16},${-q * 0.16}Z" fill="#FFE9A8"/></g>`;
  });
  return s;
}

function weather(t, d) {
  let s = '';
  const wOkt = 1 - sstep(26, 42, d), wDec = sstep(50, 64, d);
  if (wOkt > 0.01) {
    const r = rng(7), cols = ['#D9772C', '#D6A536', '#B4462C', '#E9A23B'];
    for (let i = 0; i < 12; i++) {
      const x0 = 40 + r() * 1000, y0 = r() * 2100, sp = 130 + r() * 110, sw = 30 + r() * 50, ph = r() * 6, z = 0.5 + r() * 0.6, rot = (r() - 0.5) * 300, col = cols[i % 4];
      const y = ((y0 + sp * t) % 2100) - 100, x = x0 + Math.sin(t * 1.6 + ph) * sw;
      s += `<g transform="translate(${f1(x)},${f1(y)}) rotate(${f1(rot * t / 2 + ph * 40)}) scale(${z.toFixed(2)})" opacity="${(wOkt * 0.75).toFixed(2)}">
        <path d="M0,-20 C13,-11 13,11 0,20 C-13,11 -13,-11 0,-20Z" fill="${col}"/><path d="M0,-17 L0,24" stroke="#00000033" stroke-width="2"/></g>`;
    }
  }
  if (wDec > 0.01) {
    const r = rng(11);
    for (let i = 0; i < 34; i++) {
      const x0 = r() * 1080, y0 = r() * 2000, sp = 60 + r() * 90, rad = 2 + r() * 4, ph = r() * 6;
      const y = ((y0 + sp * t) % 2000) - 40, x = x0 + Math.sin(t * 0.9 + ph) * 24;
      s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(rad)}" fill="#F8F4EC" opacity="${(wDec * (0.25 + rad / 16)).toFixed(2)}"/>`;
    }
  }
  return s;
}

// Säsongsdekor i hörnen: höstkvist (okt–nov) som tonar över i granris med guldkulor (dec).
const PINE = (() => {
  const r = rng(55), cols = ['#174a30', '#1f5a3a', '#2c6e47'], paths = ['', '', ''];
  const stems = [[0, 0, 470, 0], [120, 0, 300, -90], [230, 0, 400, 80], [330, 0, 460, -60]];
  let stem = '';
  for (const [x0, y0, x1, y1] of stems) {
    stem += `M${x0},${y0} L${x1},${y1} `;
    const len = Math.hypot(x1 - x0, y1 - y0), ux = (x1 - x0) / len, uy = (y1 - y0) / len;
    for (let s = 6; s < len; s += 6) {
      const px = x0 + ux * s, py = y0 + uy * s, taper = 1 - 0.55 * (s / len);
      for (const side of [-1, 1]) {
        const a = Math.atan2(uy, ux) + side * (0.95 + r() * 0.25) - 0.25 * side;
        const L = (26 + r() * 10) * taper;
        paths[Math.floor(r() * 3)] += `M${f1(px)},${f1(py)} l${f1(Math.cos(a) * L)},${f1(Math.sin(a) * L)} `;
      }
    }
  }
  return { stem, paths, cols };
})();
function pineBranch(tr, baubles) {
  let s = `<g transform="${tr}">`;
  s += `<path d="${PINE.stem}" stroke="#4a3520" stroke-width="7" stroke-linecap="round" fill="none"/>`;
  PINE.paths.forEach((p, i) => { s += `<path d="${p}" stroke="${PINE.cols[i]}" stroke-width="4.2" stroke-linecap="round" fill="none"/>`; });
  for (const [x, y, rr] of baubles) {
    s += `<line x1="${x}" y1="${y - rr - 22}" x2="${x}" y2="${y - rr}" stroke="#C99A3C" stroke-width="2"/>
      <rect x="${x - 7}" y="${y - rr - 8}" width="14" height="10" rx="2" fill="url(#goldS)"/>
      <circle cx="${x}" cy="${y}" r="${rr}" fill="url(#bauble)"/>
      <ellipse cx="${x - rr * 0.35}" cy="${y - rr * 0.4}" rx="${f1(rr * 0.28)}" ry="${f1(rr * 0.18)}" fill="#fff" opacity=".6" transform="rotate(-30 ${x - rr * 0.35} ${y - rr * 0.4})"/>`;
  }
  return s + '</g>';
}
function autumnBranch(tr, t) {
  const r = rng(66), cols = ['#C9672A', '#D99A33', '#A8432A', '#E0B04A'];
  let s = `<g transform="${tr}"><path d="M0,0 C120,10 220,-20 330,10 C380,22 420,10 460,-6" stroke="#5a3e24" stroke-width="7" fill="none" stroke-linecap="round"/>
    <path d="M150,2 C190,-40 220,-60 260,-70 M260,0 C300,40 330,60 370,64" stroke="#5a3e24" stroke-width="4" fill="none" stroke-linecap="round"/>`;
  for (let i = 0; i < 14; i++) {
    const x = 60 + i * 30 + r() * 10, y = (r() - 0.5) * 90, a = (r() - 0.5) * 120 + Math.sin(t * 1.2 + i) * 6, z = 0.8 + r() * 0.5;
    s += `<g transform="translate(${f1(x)},${f1(y)}) rotate(${f1(a)}) scale(${z.toFixed(2)})"><path d="M0,0 C10,-14 30,-14 40,0 C30,14 10,14 0,0Z" fill="${cols[i % 4]}"/><path d="M0,0 L38,0" stroke="#00000030" stroke-width="1.5"/></g>`;
  }
  return s + '</g>';
}
function decor(t, d) {
  const wA = 1 - sstep(34, 56, d), wP = sstep(48, 62, d), sw = Math.sin(t * 0.8) * 1.5;
  let s = '';
  if (wA > 0.01) s += `<g opacity="${wA.toFixed(2)}">${autumnBranch(`translate(1130,-20) rotate(${f1(152 + sw)}) scale(1.2)`, t)}${autumnBranch(`translate(-50,1690) rotate(${f1(-32 - sw)})`, t + 2)}</g>`;
  if (wP > 0.01) s += `<g opacity="${wP.toFixed(2)}">${pineBranch(`translate(1140,-30) rotate(${f1(150 + sw)}) scale(1.2)`, [[300, -40, 22], [430, 30, 17]])}${pineBranch(`translate(-60,1760) rotate(${f1(-30 - sw)})`, [[260, 60, 26], [400, -20, 20], [150, 70, 15]])}</g>`;
  return s;
}

// ---------- Kalendern ----------
// En sida i lokala koordinater: gångjärn i (0,0), sidan nedåt. torn: ojämn överkant (rivet blad).
function pageShape(torn, seed) {
  if (!torn) return `M${-PW / 2},10 Q${-PW / 2},0 ${-PW / 2 + 10},0 L${PW / 2 - 10},0 Q${PW / 2},0 ${PW / 2},10 L${PW / 2},${PH - 10} Q${PW / 2},${PH} ${PW / 2 - 10},${PH} L${-PW / 2 + 10},${PH} Q${-PW / 2},${PH} ${-PW / 2},${PH - 10}Z`;
  const r = rng(seed);
  let d = `M${-PW / 2},${PH - 10} L${-PW / 2},6`;
  for (let x = -PW / 2 + 12; x < PW / 2; x += 12) d += ` L${x},${f1(2 + r() * 9)}`;
  return d + ` L${PW / 2},6 L${PW / 2},${PH - 10} Q${PW / 2},${PH} ${PW / 2 - 10},${PH} L${-PW / 2 + 10},${PH} Q${-PW / 2},${PH} ${-PW / 2},${PH - 10}Z`;
}
function page(k, opts = {}) {
  const dt = dateOf(k), numCol = (dt.sun || k === 91) ? C.red : C.ink, torn = !!opts.torn, id = `pc${k}${opts.tag || ''}`;
  const shp = pageShape(torn, 300 + k);
  return `<g><clipPath id="${id}"><path d="${shp}"/></clipPath>
    <path d="${shp}" fill="url(#paper)" stroke="#CFA64A" stroke-width="2"/>
    <g clip-path="url(#${id})">
      <rect x="${-PW / 2}" y="0" width="${PW}" height="98" fill="url(#band)"/>
      <rect x="${-PW / 2}" y="96" width="${PW}" height="4" fill="url(#goldH)"/>
      <rect x="${-PW / 2}" y="0" width="${PW}" height="${PH}" fill="url(#grain)"/>
      <rect x="${-PW / 2}" y="0" width="${PW}" height="${PH}" fill="url(#pageLight)"/>
    </g>
    <text x="6" y="66" text-anchor="middle" font-family="Inter" font-weight="700" font-size="46" letter-spacing="12" fill="${C.cream}">${dt.month}</text>
    <text x="4" y="156" text-anchor="middle" font-family="Inter" font-weight="700" font-size="25" letter-spacing="8" fill="#4B6357">${dt.wd}</text>
    <text x="0" y="372" text-anchor="middle" font-family="Inter" font-weight="700" font-size="218" letter-spacing="-8" fill="${numCol}">${dt.day}</text>
    ${opts.extra || ''}</g>`;
}

function calendar(t, top) {
  const remaining = 92 - top, layers = 2 + Math.round(6 * remaining / 92);
  let s = `<g transform="translate(${HINGE.x},${HINGE.y}) scale(${CAL_S})">`;
  // skugga på bordet (ljus uppifrån vänster)
  s += `<ellipse cx="70" cy="${PH + 34}" rx="330" ry="44" fill="#2a1d0c" opacity=".35" filter="url(#blur14)"/>`;
  // sidbunten: lager åt vänster/nedåt med guldkant
  for (let i = layers; i >= 1; i--) s += `<rect x="${-PW / 2 - 4 * i}" y="${4 + 3.2 * i}" width="${PW}" height="${PH}" rx="10" fill="${i % 2 ? '#EADBBB' : '#E2CFA8'}" stroke="#C99A3C" stroke-width="1.6"/>`;
  // nästa sida (31 dec) under, toppsidan, lyftet
  const lifting = t >= TL.liftStart && top === 90;
  if (lifting || top >= 90) s += `<g filter="url(#shS)">${page(91)}</g>`;
  if (lifting) {
    const e = TL.impact > t ? eOut(prog(t, TL.liftStart, TL.impact)) : 1;
    if (t < TEAR[90]) s += `<g transform="scale(1,${(1 - 0.58 * e).toFixed(3)}) skewX(${(-6 * e).toFixed(2)})">${page(90, { extra: `<path d="${pageShape(false)}" fill="#3a2a10" opacity="${(0.2 * e).toFixed(2)}"/>` })}</g>`;
  } else if (top <= 90) s += page(top);
  // bindning och guldringar
  s += `<path d="M${-PW / 2 - 16},10 L${-PW / 2 - 16},-52 Q${-PW / 2 - 16},-74 ${-PW / 2 + 6},-74 L${PW / 2 - 6},-74 Q${PW / 2 + 16},-74 ${PW / 2 + 16},-52 L${PW / 2 + 16},10Z" fill="url(#binder)"/>
    <rect x="${-PW / 2 - 16}" y="6" width="${PW + 32}" height="5" fill="url(#goldH)"/>
    <path d="M${-PW / 2 - 6},-64 L${PW / 2 + 6},-64" stroke="#2d7a5a" stroke-width="2" opacity=".6"/>`;
  for (const x of [-150, 150]) {
    s += `<ellipse cx="${x}" cy="-30" rx="15" ry="10" fill="#041a11"/>
      <path d="M${x - 11},-28 C${x - 16},-96 ${x + 16},-96 ${x + 11},-28" fill="none" stroke="url(#goldS)" stroke-width="10" stroke-linecap="round"/>
      <path d="M${x - 7},-40 C${x - 9},-84 ${x + 2},-88 ${x + 5},-82" fill="none" stroke="#FFF3C4" stroke-width="2.5" opacity=".7" stroke-linecap="round"/>`;
  }
  s += '</g>';
  return s;
}

// Rivna blad: faller av och ut ur bild nedåt (Jonas 2026-10-13: inga blad som landar och sedan försvinner).
function tornPages(t, top) {
  let s = `<g transform="translate(${HINGE.x},${HINGE.y}) scale(${CAL_S})">`;
  const FALL = (H - HINGE.y) / CAL_S + 120; // överkanten hamnar under bildens nederkant
  for (let k = Math.max(0, top - 10); k <= Math.min(90, top); k++) {
    const tk = TEAR[k];
    if (t < tk) continue;
    const dur = tearDur(k) * 1.6, p = prog(t, tk, tk + dur);
    if (p >= 1) continue;
    const r = rng(100 + k), dir = r() < 0.5 ? -1 : 1, rx = dir * (60 + r() * 200), spin = dir * (25 + r() * 45);
    const x = rx * eOut(p), y = FALL * p * p - 30 * Math.sin(p * Math.PI); // gravitation, aldrig upp i texten
    const rot = spin * p + dir * 12 * Math.sin(p * Math.PI * 2);
    const sy = 1 - 0.35 * Math.sin(p * Math.PI);
    const pre = k === 90 ? 'scale(1,0.42) skewX(-6)' : '';
    s += `<g filter="url(#shS)" transform="translate(${f1(x)},${f1(y)}) rotate(${f1(rot)}) scale(1,${sy.toFixed(3)}) ${pre}">${page(k, { torn: true, tag: 't' })}</g>`;
  }
  return s + '</g>';
}

// Sidan 31 dec med hål efter bollen.
function holeR(t) {
  if (t < TL.impact) return 0;
  const a = eOut(prog(t, TL.impact, TL.impact + 0.07)) * 64;
  return a + eIn(prog(t, TL.revealStart, TL.revealEnd)) * 2400;
}
const HOLE = { x: 420, y: 765 + 262 * 1.15 };
function holePath(r, seed) {
  if (r <= 0) return '';
  let d = '';
  for (let i = 0; i <= 40; i++) {
    const a = i / 40 * Math.PI * 2, j = 1 + 0.12 * noise(a * 3, seed) + (i % 2 ? 0.07 : -0.05);
    d += (i ? 'L' : 'M') + f1(HOLE.x + Math.cos(a) * r * j) + ',' + f1(HOLE.y + Math.sin(a) * r * j);
  }
  return d + 'Z';
}

// ---------- Presentkortet (friskvårdsbidraget) ----------
function giftIcon(x, y, s = 1) {
  return `<g transform="translate(${x},${y}) scale(${s})" fill="none" stroke="#EBC866" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round">
    <rect x="-24" y="-6" width="48" height="34" rx="3"/><rect x="-28" y="-18" width="56" height="12" rx="3"/>
    <path d="M0,-18 L0,28"/><path d="M0,-18 C-6,-34 -24,-34 -20,-24 C-17,-18 -6,-18 0,-18 C6,-18 17,-18 20,-24 C24,-34 6,-34 0,-18"/></g>`;
}
function note(t, opts = {}) {
  const b = opts.burn ?? 0, flame = opts.flame ?? 0, glow = opts.glow ?? 0;
  const w = 320, h = 146, xb = w / 2 - w * b;
  const edge = [];
  for (let y = -h / 2 - 8; y <= h / 2 + 8; y += 6) edge.push([xb + noise(y / 18, 3) * 13 + (b > 0 ? 0 : 40), y]);
  const clip = b > 0 ? `M${-w / 2 - 10},${-h / 2 - 10} ` + edge.map(([x, y]) => `L${f1(x)},${f1(y)}`).join(' ') + ` L${-w / 2 - 10},${h / 2 + 10}Z` : '';
  const id = 'nclip' + (opts.id || '');
  let s = '';
  if (glow > 0) s += `<ellipse cx="0" cy="0" rx="${w * 0.72}" ry="${h * 0.95}" fill="${C.goldHi}" opacity="${(0.55 * glow).toFixed(2)}" filter="url(#glow)"/>`;
  if (b > 0) s += `<clipPath id="${id}"><path d="${clip}"/></clipPath>`;
  s += `<g ${b > 0 ? `clip-path="url(#${id})"` : ''}>
    <rect x="${-w / 2}" y="${-h / 2}" width="${w}" height="${h}" rx="14" fill="url(#card)"/>
    <rect x="${-w / 2 + 8}" y="${-h / 2 + 8}" width="${w - 16}" height="${h - 16}" rx="9" fill="none" stroke="url(#goldS)" stroke-width="2.6"/>
    ${giftIcon(-w / 2 + 60, -4, 1.1)}
    <text x="${-w / 2 + 112}" y="-4" font-family="Anton" font-size="40" letter-spacing="1" fill="#F3D27A">FRISKVÅRDS-</text>
    <text x="${-w / 2 + 112}" y="42" font-family="Anton" font-size="40" letter-spacing="1" fill="#F3D27A">BIDRAGET</text>
    <path d="M${-w / 2},${-h / 2} L${-w / 2 + 130},${-h / 2} L${-w / 2 + 40},${h / 2} L${-w / 2},${h / 2}Z" fill="#fff" opacity=".07"/>
  </g>`;
  if (b > 0) {
    const pts = edge.map(([x, y]) => `${f1(x)},${f1(y)}`).join(' ');
    s += `<polyline points="${pts}" fill="none" stroke="#1d120a" stroke-width="13" stroke-linejoin="round" opacity=".92"/>
      <polyline points="${pts}" fill="none" stroke="#5a2d12" stroke-width="7" stroke-linejoin="round"/>
      <polyline points="${pts}" fill="none" stroke="#FF8A2A" stroke-width="4" filter="url(#blur3)" opacity="${(0.35 + 0.65 * flame).toFixed(2)}"/>`;
    // glödande punkter längs kanten
    const r = rng(12);
    for (let i = 0; i < 9; i++) {
      const [ex, ey] = edge[Math.floor(r() * edge.length)], fl = 0.5 + 0.5 * Math.sin(t * (6 + r() * 6) + i);
      s += `<circle cx="${f1(ex - 3)}" cy="${f1(ey)}" r="${f1(1.8 + r() * 1.8)}" fill="#FFC15A" opacity="${(fl * (0.3 + 0.7 * flame)).toFixed(2)}"/>`;
    }
  }
  if (flame > 0.01) {
    const rot = -(opts.rot || 0);
    s += `<ellipse cx="${f1(xb + 6)}" cy="-10" rx="${f1(70 + 60 * flame)}" ry="${f1(80 + 60 * flame)}" fill="url(#fireGlow)" opacity="${(0.9 * flame).toFixed(2)}"/>`;
    const tongue = (hh, ww, lean) => `M0,0 C${f1(-ww)},${f1(-hh * 0.25)} ${f1(-ww * 0.8 + lean * 0.3)},${f1(-hh * 0.7)} ${f1(lean)},${f1(-hh)} C${f1(ww * 0.8 + lean * 0.3)},${f1(-hh * 0.7)} ${f1(ww)},${f1(-hh * 0.25)} 0,0Z`;
    [[-58, 0.75], [-26, 1.0], [6, 1.25], [36, 0.95], [62, 0.7]].forEach(([fy, m], i) => {
      const ex = xb + noise(fy / 18, 3) * 13, n1 = noise(t * 9 + i * 3.1, i), n2 = noise(t * 13 + i * 1.7, i + 4);
      const hh = (36 + 46 * flame) * m * (0.82 + 0.22 * n1) * flame, ww = hh * 0.36, lean = n2 * hh * 0.18 + 6;
      s += `<g transform="translate(${f1(ex)},${f1(fy + 8)}) rotate(${rot.toFixed(1)})">
        <path d="${tongue(hh * 1.15, ww * 1.25, lean)}" fill="url(#flO)" filter="url(#blur3)"/>
        <path d="${tongue(hh, ww, lean)}" fill="url(#flM)"/>
        <path d="${tongue(hh * 0.55, ww * 0.5, lean * 0.6)}" fill="url(#flI)"/></g>`;
    });
    const r = rng(5);
    for (let i = 0; i < 16; i++) {
      const ph = r(), sp = 0.6 + r() * 0.8, life = ((t * sp + ph) % 1), ey = 50 - r() * 110, dx = 20 + r() * 50, cv = (r() - 0.5) * 40;
      const x = xb + 8 + life * dx + Math.sin(life * 6 + i) * 6, y = ey - life * (140 + r() * 80), px = x - dx * 0.04, py = y + 9;
      s += `<line x1="${f1(px)}" y1="${f1(py + cv * 0.01)}" x2="${f1(x)}" y2="${f1(y)}" stroke="${i % 3 ? '#FFC15A' : '#FFE9A8'}" stroke-width="${f1(2.6 * (1 - life) + 0.6)}" stroke-linecap="round" opacity="${((1 - life) * flame).toFixed(2)}"/>`;
    }
  }
  return s;
}

const BURN_END = 0.86; // andel av kortet som brunnit upp när bollen kommer (Jonas: 10–20 % kvar)
function burnAt(t) { return BURN_END * Math.pow(clamp((t - TL.ignite) / (TL.impact - TL.ignite)), 1.25) + 0.02 * sstep(TL.ignite, TL.ignite + 0.3, t); }
function flameAt(t) { return sstep(TL.ignite, TL.ignite + 0.5, t) * (0.5 + 0.5 * prog(t, TL.ignite, TL.impact)) * (1 - sstep(TL.impact, TL.impact + 0.14, t)); }
function blinkAt(t) { let g = 0; for (const p of [5.75, 6.2, 6.65]) g = Math.max(g, Math.exp(-Math.pow((t - p) / 0.11, 2))); return g; }

const NOTE_POS = { x: 728, y: 1148, rot: -6, s: 1.2 };
function noteDesk(t) {
  const g = blinkAt(t), sc = 1 + 0.07 * g;
  let s = `<ellipse cx="${NOTE_POS.x + 20}" cy="${NOTE_POS.y + 96}" rx="200" ry="22" fill="#2a1d0c" opacity=".3" filter="url(#blur14)"/>`;
  s += `<g transform="translate(${NOTE_POS.x},${NOTE_POS.y}) rotate(${NOTE_POS.rot}) scale(${(sc * NOTE_POS.s).toFixed(3)})" filter="url(#shS)">`;
  s += note(t, { burn: burnAt(t), flame: flameAt(t), glow: g, rot: NOTE_POS.rot, id: 'desk' });
  s += '</g>';
  if (t > TL.impact && t < TL.impact + 1.2) { // rök när lågan kvävs
    const p = prog(t, TL.impact, TL.impact + 1.2), r = rng(9);
    for (let i = 0; i < 7; i++) {
      const ox = (r() - 0.5) * 70, oy = (r() - 0.5) * 120;
      s += `<circle cx="${f1(NOTE_POS.x - 60 + ox + p * 30)}" cy="${f1(NOTE_POS.y + oy - p * 160)}" r="${f1(14 + p * 34)}" fill="#c9cfcb" opacity="${(0.45 * (1 - p)).toFixed(2)}"/>`;
    }
  }
  return s;
}

// ---------- Bollen och smällen ----------
function ball(x, y, r, rot = 0) {
  return `<g transform="translate(${f1(x)},${f1(y)}) rotate(${f1(rot)})"><circle r="${f1(r)}" fill="url(#ball)"/>
    ${[[-0.35, -0.2], [0.1, -0.4], [0.35, 0.05], [-0.1, 0.25], [0.3, 0.42], [-0.45, 0.25]].map(([a, b]) => `<circle cx="${f1(a * r)}" cy="${f1(b * r)}" r="${f1(r * 0.09)}" fill="#a9b3b6" opacity=".55"/>`).join('')}</g>`;
}
function ballFlight(t) {
  if (t < TL.ballStart || t > TL.impact + 0.02) return '';
  const p = eIn(prog(t, TL.ballStart, TL.impact)), x0 = 1020, y0 = 1760, r0 = 120, r1 = 30;
  let s = '';
  for (let i = 4; i >= 0; i--) {
    const q = clamp(p - i * 0.07);
    const x = lerp(x0, HOLE.x, q), y = lerp(y0, HOLE.y, q) - Math.sin(q * Math.PI) * 120, r = lerp(r0, r1, q);
    s += i ? `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}" fill="#fff" opacity="${(0.12 * (5 - i) / 5).toFixed(2)}"/>` : ball(x, y, r, t * 900);
  }
  return s;
}
function impactFx(t) {
  if (t < TL.impact || t > TL.impact + 0.9) return '';
  const p = prog(t, TL.impact, TL.impact + 0.9), r = rng(21);
  let s = `<circle cx="${HOLE.x}" cy="${HOLE.y}" r="${f1(70 + 300 * eOut(prog(t, TL.impact, TL.impact + 0.35)))}" fill="none" stroke="#fff6cf" stroke-width="${f1(10 * (1 - prog(t, TL.impact, TL.impact + 0.35)))}" opacity=".8"/>`;
  for (let i = 0; i < 26; i++) {
    const a = r() * Math.PI * 2, v = 380 + r() * 520, sz = 8 + r() * 18, spin = (r() - 0.5) * 900;
    const tt = t - TL.impact, x = HOLE.x + Math.cos(a) * v * tt, y = HOLE.y + Math.sin(a) * v * tt + 900 * tt * tt;
    s += `<rect x="${f1(-sz / 2)}" y="${f1(-sz / 3)}" width="${f1(sz)}" height="${f1(sz * 0.66)}" fill="${i % 4 === 0 ? '#F3D27A' : i % 3 ? '#FBF8F1' : '#e6dcc6'}" opacity="${(1 - p).toFixed(2)}" transform="translate(${f1(x)},${f1(y)}) rotate(${f1(spin * tt)})"/>`;
  }
  return s;
}
function holeLight(t) {
  if (t < TL.impact || t > TL.revealEnd) return '';
  const a = sstep(TL.impact, TL.impact + 0.12, t) * (1 - sstep(TL.revealStart + 0.3, TL.revealEnd, t));
  let s = `<g opacity="${a.toFixed(2)}"><circle cx="${HOLE.x}" cy="${HOLE.y}" r="260" fill="url(#holeLight)"/>`;
  for (let i = 0; i < 12; i++) s += `<path d="M0,0 L640,-44 L640,44Z" fill="url(#ray)" transform="translate(${HOLE.x},${HOLE.y}) rotate(${f1(i / 12 * 360 + t * 20)})"/>`;
  return s + '</g>';
}

// ---------- Våren (bakom hålet) ----------
const CUP = { x: 790, y: 1196 };
function springBall(t) {
  const a = TL.revealStart, land1 = 13.6, land2 = 14.02, inCup = 14.78;
  if (t < a) return '';
  if (t < land1) {
    const p = prog(t, a, land1), x = lerp(HOLE.x, 430, p), y = lerp(HOLE.y, 1188, p) - Math.sin(p * Math.PI) * 140, r = lerp(5, 15, eOut(p));
    return shadow(x, 1192, r * p) + ball(x, y, r, t * 600);
  }
  if (t < land2) {
    const p = prog(t, land1, land2), x = lerp(430, 530, p), y = 1188 - Math.sin(p * Math.PI) * 62;
    return shadow(x, 1192, 15) + ball(x, y, 15, t * 600);
  }
  if (t < inCup) {
    const p = prog(t, land2, inCup), e = 1 - Math.pow(1 - p, 1.6), x = lerp(530, CUP.x, e);
    return shadow(x, 1194, 15) + ball(x, 1188, 15, x * 4);
  }
  const p = prog(t, inCup, inCup + 0.1);
  return p < 1 ? ball(CUP.x, 1188 + 12 * p, 15 * (1 - 0.4 * p)) : '';
}
const shadow = (x, y, r) => `<ellipse cx="${f1(x)}" cy="${f1(y + 4)}" rx="${f1(r * 1.1)}" ry="${f1(r * 0.35)}" fill="#1f4a2a" opacity=".35"/>`;
function tree(x, y, s, c = '#5f9e57') {
  return `<g transform="translate(${x},${y}) scale(${s})"><rect x="-5" y="-6" width="10" height="34" rx="3" fill="#7a5a3a"/><circle cx="0" cy="-30" r="30" fill="${c}"/><circle cx="-16" cy="-14" r="20" fill="${c}"/><circle cx="16" cy="-14" r="20" fill="${c}"/><circle cx="-8" cy="-38" r="12" fill="#ffffff2a"/><circle cx="12" cy="-12" r="16" fill="#00000014"/></g>`;
}
function cloud(x, y, s) {
  return `<g transform="translate(${f1(x)},${f1(y)}) scale(${s})" opacity=".95"><g fill="#ffffff"><circle cx="0" cy="0" r="40"/><circle cx="44" cy="8" r="32"/><circle cx="-42" cy="10" r="28"/><rect x="-70" y="10" width="146" height="30" rx="15"/></g><rect x="-70" y="28" width="146" height="12" rx="6" fill="#d9e6ee"/></g>`;
}
function spring(t) {
  const settle = eOut(prog(t, TL.revealStart, TL.revealEnd + 0.6)), z = lerp(1.55, 1.2, settle);
  const wig = Math.exp(-Math.max(0, t - 14.8) * 2.2) * (t > 14.8 ? 1 : 0);
  const fw = (y) => Math.sin(t * 4 + y * 0.05) * 6 + wig * Math.sin(t * 22) * 14;
  let s = `<g transform="translate(560,1120) scale(${z.toFixed(3)}) translate(-560,-1120)">`;
  s += `<rect x="-200" y="-200" width="1480" height="2400" fill="url(#sky)"/>`;
  // solen med mjuka strålar
  s += `<g opacity=".55">${Array.from({ length: 10 }, (_, i) => `<path d="M0,0 L900,-60 L900,60Z" fill="url(#ray)" transform="translate(850,860) rotate(${f1(i * 36 + t * 6)})"/>`).join('')}</g>`;
  s += `<circle cx="850" cy="860" r="170" fill="url(#sunGlow)"/><circle cx="850" cy="860" r="62" fill="#FFE08A"/>`;
  s += cloud(190 + t * 8, 850, 0.9) + cloud(640 + t * 5, 905, 0.6) + cloud(990 + t * 6, 930, 0.5);
  s += `<path d="M-200,1010 C40,950 220,985 380,1000 C560,1018 700,940 900,965 C1040,982 1180,1000 1280,990 L1280,1400 L-200,1400Z" fill="#A9D190"/>`;
  s += tree(120, 990, 0.9, '#6FAE62') + tree(330, 1002, 0.7, '#6FAE62') + tree(930, 975, 0.85, '#6FAE62') + tree(1010, 990, 0.65, '#6FAE62');
  s += `<path d="M-200,1060 C120,1030 300,1050 520,1062 C760,1075 920,1040 1280,1055 L1280,1400 L-200,1400Z" fill="#7CBC6C"/>`;
  s += `<path d="M-200,1060 C120,1030 300,1050 520,1062 C760,1075 920,1040 1280,1055 L1280,1400 L-200,1400Z" fill="url(#hillShade)"/>`;
  s += `<path d="M-200,1100 C200,1085 600,1092 1280,1100 L1280,2200 L-200,2200Z" fill="#5AA55A"/>`;
  for (let i = 0; i < 9; i++) s += `<path d="M${-200 + i * 180},1100 l90,0 l220,1100 l-90,0Z" fill="#ffffff" opacity=".05"/>`;
  s += `<ellipse cx="230" cy="1222" rx="120" ry="26" fill="#EAD9A6"/><ellipse cx="230" cy="1218" rx="104" ry="18" fill="#F2E6BE"/>`;
  s += `<ellipse cx="610" cy="1198" rx="340" ry="66" fill="#3f8a45" opacity=".35"/><ellipse cx="610" cy="1194" rx="340" ry="66" fill="#8FD27F"/><ellipse cx="610" cy="1194" rx="322" ry="58" fill="#74C26A"/>`;
  s += `<ellipse cx="${CUP.x}" cy="${CUP.y}" rx="20" ry="7" fill="#1b2a1f"/>`;
  s += springBall(t);
  s += `<line x1="${CUP.x}" y1="${CUP.y}" x2="${CUP.x}" y2="930" stroke="${C.cream}" stroke-width="7" stroke-linecap="round"/>`;
  s += `<path d="M${CUP.x},932 Q${CUP.x + 60},${942 + fw(0)} ${CUP.x + 120},${958 + fw(30)} Q${CUP.x + 60},${972 + fw(60)} ${CUP.x},${988}Z" fill="${C.gold}"/>`;
  s += `<path d="M-200,1470 C80,1440 300,1480 560,1462 C800,1446 1000,1478 1280,1458 L1280,2300 L-200,2300Z" fill="#4A9450"/>`;
  const r = rng(31);
  for (let i = 0; i < 26; i++) {
    const x = -60 + i * 46 + r() * 20, y = 1470 + r() * 30, h = 26 + r() * 30, sw = Math.sin(t * 2 + i) * 4;
    s += `<path d="M${f1(x)},${f1(y)} q${f1(4 + sw)},${f1(-h)} ${f1(8 + sw)},${f1(-h - 6)} q-2,${f1(h * 0.6)} 6,${f1(h + 6)}Z" fill="#3E8445"/>`;
  }
  for (let i = 0; i < 3; i++) {
    const bx = 120 + i * 70 + t * 40, by = 820 + i * 26 + Math.sin(t * 3 + i) * 6, fl = Math.sin(t * 12 + i * 2) * 8;
    s += `<path d="M${f1(bx - 14)},${f1(by - fl)} Q${f1(bx - 6)},${f1(by - 6)} ${f1(bx)},${f1(by)} Q${f1(bx + 6)},${f1(by - 6)} ${f1(bx + 14)},${f1(by - fl)}" fill="none" stroke="#2f4f3a" stroke-width="3" stroke-linecap="round"/>`;
  }
  s += springNote(t);
  return s + '</g>';
}
// Kortstumpen singlar ner och blir en golfkupong (med guldglimtar).
function springNote(t) {
  const a = 13.45, land = 14.65, flip0 = 14.95, flip1 = 15.35;
  if (t < a) return '';
  const p = eOut(prog(t, a, land)), x = lerp(250, 330, p) + Math.sin(p * 9) * 60 * (1 - p), y = lerp(560, 1100, p);
  const rot = Math.sin(p * 8) * 22 * (1 - p) - 6;
  const fp = prog(t, flip0, flip1), sx = Math.cos(fp * Math.PI), hop = Math.sin(fp * Math.PI) * 40;
  const face = sx >= 0 ? note(t, { burn: BURN_END + 0.02, flame: 0, rot, id: 'spr' }) : coupon(t);
  let s = `<g transform="translate(${f1(x)},${f1(y - hop)}) rotate(${f1(rot)}) scale(${(1.25 * Math.max(0.02, Math.abs(sx))).toFixed(3)},1.25)" filter="url(#shS)">${face}</g>`;
  if (t > flip1) {
    [[-150, -90, 0], [170, -70, 1.3], [120, 80, 2.4], [-180, 60, 3.3]].forEach(([dx, dy, ph]) => {
      const k = Math.max(0, Math.sin((t - flip1) * 3 + ph)), q = 18 * k;
      if (q > 1) s += `<path transform="translate(${f1(x + dx)},${f1(y + dy)})" d="M0,${-q} L${q * 0.16},${-q * 0.16} L${q},0 L${q * 0.16},${q * 0.16} L0,${q} L${-q * 0.16},${q * 0.16} L${-q},0 L${-q * 0.16},${-q * 0.16}Z" fill="#FFF3C4"/>`;
    });
  }
  return s;
}
function coupon(t) {
  const w = 320, h = 146, g = prog(t, 15.6, 16.2);
  return `<clipPath id="cpc"><rect x="${-w / 2}" y="${-h / 2}" width="${w}" height="${h}" rx="12"/></clipPath><g clip-path="url(#cpc)">
    <rect x="${-w / 2}" y="${-h / 2}" width="${w}" height="${h}" rx="12" fill="url(#coupon)"/>
    <line x1="${-w / 2 + 92}" y1="${-h / 2 + 10}" x2="${-w / 2 + 92}" y2="${h / 2 - 10}" stroke="${C.deep}" stroke-width="3" stroke-dasharray="6 7" opacity=".55"/>
    <g transform="translate(${-w / 2 + 46},6)"><line x1="0" y1="26" x2="0" y2="-30" stroke="${C.deep}" stroke-width="4"/><path d="M0,-30 L28,-21 L0,-12Z" fill="${C.deep}"/><ellipse cx="0" cy="27" rx="16" ry="5" fill="${C.deep}" opacity=".6"/></g>
    <text x="${-w / 2 + 112}" y="-24" font-family="Inter" font-weight="700" font-size="14" letter-spacing="2" fill="${C.deep}">FRISKVÅRDSBIDRAGET</text>
    <text x="${-w / 2 + 110}" y="46" font-family="Anton" font-size="76" letter-spacing="3" fill="${C.deep}">GOLF</text>
    <path d="M${f1(-260 + 640 * g)},-120 l60,0 l-120,240 l-60,0Z" fill="#fff" opacity=".45"/></g>
    <rect x="${-w / 2}" y="${-h / 2}" width="${w}" height="${h}" rx="12" fill="none" stroke="#fff3c4" stroke-width="2" opacity=".6"/>`;
}

function iris(t) {
  if (t < TL.irisStart) return '';
  const r = 2300 * (1 - eIn(prog(t, TL.irisStart, TL.end - 0.03))), cx = 560 + (CUP.x - 560) * 1.2, cy = 1120 + (CUP.y - 1120) * 1.2;
  return `<path d="M0,0 H${W} V${H} H0Z M${f1(cx - r)},${f1(cy)} a${r},${r} 0 1,0 ${2 * r},0 a${r},${r} 0 1,0 ${-2 * r},0Z" fill="${C.dark}" fill-rule="evenodd"/>`;
}

// ---------- Text (HTML-lager) ----------
function textLayer(t) {
  let html = '';
  for (const tx of TEXTS) {
    const [a, b] = tx.win;
    if (t < a - 0.001 || t >= b) continue;
    const out = sstep(b - 0.22, b, t);
    html += `<div class="block" style="top:${TEXT_TOP}px;color:${tx.fg};font-size:${tx.size}px">`;
    tx.lines.forEach((ln, i) => {
      const p = eOut(prog(t, a + i * 0.09, a + i * 0.09 + 0.34)), bp = eBack(prog(t, a + i * 0.09 + 0.16, a + i * 0.09 + 0.46));
      const op = p * (1 - out), ty = (1 - p) * 46 - out * 26;
      const inner = ln.replace(/\{(.+?)\}/g, (_, w) => `<span class="hl" style="margin-top:${/[ÅÄÖ]/i.test(w) ? '0.08em' : '0'}"><span class="box" style="top:${/[ÅÄÖ]/i.test(w) ? '-0.17em' : '0'};background:${tx.box};right:0;transform-origin:left;transform:scaleX(${bp.toFixed(3)});box-shadow:0 6px 14px rgba(0,0,0,.25)"></span><span class="w" style="color:${tx.boxFg}">${w}</span></span>`);
      html += `<span class="line" style="opacity:${op.toFixed(3)};transform:translateY(${f1(ty)}px);text-shadow:${tx.fg === C.cream ? '0 4px 0 rgba(0,0,0,.22), 0 10px 24px rgba(0,0,0,.35)' : 'none'}">${inner}</span>`;
    });
    html += '</div>';
  }
  return html;
}

// ---------- Ram ----------
function renderAt(rt) {
  const t = sceneTime(rt);
  const top = topPage(t), d = top + (t > TL.impact ? 2 : 0);
  const drift = 1 + 0.035 * sstep(0, 12, t);
  const shake = t > TL.impact ? Math.exp(-(t - TL.impact) * 9) * 16 : 0;
  const sx = shake * Math.sin(t * 95), sy = shake * Math.cos(t * 77);
  const push = 1 + 0.45 * eIn(prog(t, TL.revealStart, TL.revealEnd));
  const camOld = `translate(${f1(HOLE.x + sx)},${f1(HOLE.y + sy)}) scale(${(drift * push).toFixed(4)}) translate(${-HOLE.x},${-HOLE.y})`;

  let s = defs();
  const r = holeR(t);
  if (r <= 2300) {
    s += background(t, d);
    s += `<g transform="${camOld}">${weather(t, d)}${goldDust(t)}${calendar(t, top)}${tornPages(t, top)}${noteDesk(t)}${decor(t, d)}</g>`;
  }
  if (r > 0) {
    s += `<clipPath id="hole"><path d="${holePath(r * drift * push, 4)}" transform="translate(${f1(sx)},${f1(sy)})"/></clipPath>`;
    s += `<g clip-path="url(#hole)">${spring(t)}</g>`;
    if (r < 500) s += `<path d="${holePath(r * drift * push, 4)}" transform="translate(${f1(sx)},${f1(sy)})" fill="none" stroke="#FBF8F1" stroke-width="${f1(8 + 6 * (1 - r / 500))}" stroke-linejoin="round" opacity="${(1 - r / 500).toFixed(2)}"/>`;
  }
  s += `<g transform="${camOld}">${holeLight(t)}${impactFx(t)}</g>`;
  s += ballFlight(t);
  s += `<rect width="${W}" height="${H}" fill="url(#vig)"/>`;
  s += iris(t);
  document.getElementById('svg').innerHTML = s;
  document.getElementById('text').innerHTML = textLayer(rt);
}

window.SCENE = { W, H, FPS, duration: TL.end + D, TL, TEXTS, renderAt,
  ready: Promise.all(['112px Anton', '700 28px Inter', '600 28px Inter'].map((f) => document.fonts.load(f))).then(() => document.fonts.ready) };
