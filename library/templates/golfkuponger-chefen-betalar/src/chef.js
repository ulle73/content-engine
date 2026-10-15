// "Låt chefen betala din golf" – miljöer och rekvisita: vägg, dörr, kontor, mobil, kvitto, GODKÄNT-stämpel.
// Ritar i 1080×1920 som scene.js. Figurerna kommer från modulerna tourleif.js och chefen.js.
'use strict';

function chefDefs() {
  return `<linearGradient id="wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7A5233"/><stop offset="1" stop-color="#3E2817"/></linearGradient>
  <linearGradient id="woodTop" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8C6040"/><stop offset=".5" stop-color="#A0714C"/><stop offset="1" stop-color="#7A5233"/></linearGradient>
  <linearGradient id="door" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5A3B22"/><stop offset=".5" stop-color="#6E4A2C"/><stop offset="1" stop-color="#4C3119"/></linearGradient>
  <linearGradient id="brass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBE7A1"/><stop offset=".5" stop-color="#D9AC4A"/><stop offset="1" stop-color="#9C7128"/></linearGradient>
  <linearGradient id="leather" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0E3A29"/><stop offset=".5" stop-color="#175A40"/><stop offset="1" stop-color="#0E3A29"/></linearGradient>
  <filter id="inkRough"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="6"/></filter>`;
}

const f1c = (n) => n.toFixed(1);

// ---------- Miljöer ----------
function wall(t, tone = '#174a34') {
  let s = `<radialGradient id="wallG" cx="35%" cy="25%" r="95%"><stop offset="0" stop-color="${tone}"/><stop offset=".6" stop-color="#0c3123"/><stop offset="1" stop-color="#061a12"/></radialGradient>
    <rect width="1080" height="1920" fill="url(#wallG)"/><g filter="url(#blur30)" transform="rotate(34)">`;
  [[-260, 150, 0.9], [-80, 90, 0.6], [120, 190, 0.75], [360, 110, 0.5]].forEach(([yy, h, op], i) => {
    s += `<rect x="-200" y="${yy}" width="2600" height="${h}" fill="url(#beam)" opacity="${(op * (0.85 + 0.15 * Math.sin(t * 0.7 + i))).toFixed(2)}"/>`;
  });
  return s + '</g>';
}
function doorScene(t) {
  let s = wall(t) + goldDust(t);
  s += `<rect x="0" y="1250" width="1080" height="670" fill="url(#table)"/><rect x="0" y="1250" width="1080" height="670" fill="url(#speck)" opacity=".6"/>
    <rect x="0" y="1236" width="1080" height="16" fill="#0a2a1d"/>
    <g filter="url(#sh)"><rect x="560" y="520" width="400" height="740" rx="10" fill="#3a2414"/>
    <rect x="580" y="540" width="360" height="720" rx="6" fill="url(#door)"/></g>
    <rect x="612" y="580" width="296" height="300" rx="8" fill="none" stroke="#3e2816" stroke-width="10"/><rect x="612" y="920" width="296" height="300" rx="8" fill="none" stroke="#3e2816" stroke-width="10"/>
    <circle cx="905" cy="900" r="20" fill="url(#brass)"/><rect x="895" y="900" width="40" height="12" rx="6" fill="url(#brass)"/>
    <g filter="url(#shS)"><rect x="640" y="640" width="240" height="84" rx="10" fill="url(#brass)"/></g>
    <text x="760" y="698" text-anchor="middle" font-family="Anton" font-size="52" letter-spacing="6" fill="#3a2a10">CHEFEN</text>`;
  return s;
}
function office(t, bossExpr, bossOpts = {}) {
  let s = wall(t, '#1a4f37') + goldDust(t);
  // tavla med golfbana
  s += `<g filter="url(#shS)"><rect x="96" y="560" width="250" height="190" rx="6" fill="url(#brass)"/><rect x="110" y="574" width="222" height="162" fill="#9fd2e3"/>
    <path d="M110,680 C170,650 240,670 332,650 L332,736 L110,736Z" fill="#7CBC6C"/><path d="M110,705 C200,695 260,700 332,690 L332,736 L110,736Z" fill="#5AA55A"/>
    <line x1="270" y1="690" x2="270" y2="640" stroke="#fff" stroke-width="3"/><path d="M270,640 L292,648 L270,656Z" fill="#D6A536"/></g>`;
  // stol
  s += `<g filter="url(#sh)"><rect x="330" y="560" width="420" height="700" rx="80" fill="url(#leather)"/></g>
    ${[[400, 640], [540, 620], [680, 640], [400, 780], [540, 760], [680, 780]].map(([cx, cy]) => `<circle cx="${cx}" cy="${cy}" r="9" fill="#082a1d"/>`).join('')}`;
  s += chefen(t, { expr: bossExpr, x: 540, y: 820, s: 0.95, ...bossOpts });
  // skrivbord
  s += `<g filter="url(#sh)"><rect x="-20" y="1160" width="1120" height="60" rx="8" fill="url(#woodTop)"/><rect x="0" y="1214" width="1080" height="706" fill="url(#wood)"/></g>
    <rect x="0" y="1214" width="1080" height="6" fill="#D6A536" opacity=".55"/>
    <g filter="url(#shS)"><path d="M380,1150 L700,1150 L720,1192 L360,1192Z" fill="url(#brass)"/></g>
    <text x="540" y="1182" text-anchor="middle" font-family="Anton" font-size="34" letter-spacing="8" fill="#3a2a10">CHEFEN</text>
    <g transform="translate(150,1100)"><rect x="-38" y="0" width="76" height="62" rx="8" fill="#B5683C"/><circle cx="-18" cy="-14" r="30" fill="#2f7a4b"/><circle cx="18" cy="-24" r="34" fill="#3E8E57"/><circle cx="2" cy="-48" r="26" fill="#4FA066"/></g>`;
  return s;
}

// ---------- Mobil, mejl med pdf, kvitto ----------
function phone(cx, cy, w, scroll, notif) {
  const h = w * 2.06, x = cx - w / 2, y = cy - h / 2, r = w * 0.13;
  let s = `<clipPath id="scr"><rect x="${f1c(x + 10)}" y="${f1c(y + 10)}" width="${f1c(w - 20)}" height="${f1c(h - 20)}" rx="${f1c(r - 6)}"/></clipPath>
    <g filter="url(#sh)"><rect x="${f1c(x)}" y="${f1c(y)}" width="${f1c(w)}" height="${f1c(h)}" rx="${f1c(r)}" fill="#111"/></g>
    <g clip-path="url(#scr)"><image href="assets/site/site-${scroll}.png" x="${f1c(x + 10)}" y="${f1c(y + 10)}" width="${f1c(w - 20)}" height="${f1c((w - 20) * 844 / 390)}"/></g>
    <rect x="${f1c(cx - w * 0.16)}" y="${f1c(y + 18)}" width="${f1c(w * 0.32)}" height="${f1c(w * 0.075)}" rx="${f1c(w * 0.04)}" fill="#111"/>
    <rect x="${f1c(x)}" y="${f1c(y)}" width="${f1c(w)}" height="${f1c(h)}" rx="${f1c(r)}" fill="none" stroke="#3a3a3a" stroke-width="4"/>`;
  if (notif > 0) { // mejlnotis glider ner
    const ny = y + 30 - 140 * (1 - notif);
    s += `<g clip-path="url(#scr)" opacity="${Math.min(1, notif * 1.5).toFixed(2)}"><g filter="url(#shS)"><rect x="${f1c(x + 24)}" y="${f1c(ny)}" width="${f1c(w - 48)}" height="${f1c(w * 0.34)}" rx="22" fill="#F8F4EC"/></g>
      <rect x="${f1c(x + 44)}" y="${f1c(ny + 22)}" width="${f1c(w * 0.15)}" height="${f1c(w * 0.15)}" rx="10" fill="#0F5A3E"/><use href="#gklogo" x="${f1c(x + 48)}" y="${f1c(ny + 26)}" width="${f1c(w * 0.13)}" height="${f1c(w * 0.13)}"/>
      <text x="${f1c(x + 64 + w * 0.15)}" y="${f1c(ny + 50)}" font-family="Inter" font-weight="700" font-size="${f1c(w * 0.06)}" fill="#082f27">Golfkuponger</text>
      <text x="${f1c(x + 64 + w * 0.15)}" y="${f1c(ny + 50 + w * 0.08)}" font-family="Inter" font-weight="600" font-size="${f1c(w * 0.052)}" fill="#3b4a43">Ditt kvitto (pdf)</text></g>`;
  }
  return s;
}
function pdfIcon(cx, cy, sc = 1, rot = 0) {
  return `<g transform="translate(${f1c(cx)},${f1c(cy)}) rotate(${f1c(rot)}) scale(${sc.toFixed(3)})" filter="url(#shS)">
    <path d="M-80,-105 L40,-105 L80,-65 L80,105 L-80,105Z" fill="#FBF8F1"/><path d="M40,-105 L40,-65 L80,-65Z" fill="#E2D6BC"/>
    <rect x="-80" y="-10" width="160" height="56" fill="#C8462E"/><text x="0" y="32" text-anchor="middle" font-family="Anton" font-size="40" fill="#fff" letter-spacing="3">PDF</text>
    <path d="M-55,-70 L20,-70 M-55,-48 L40,-48 M-55,70 L55,70 M-55,86 L30,86" stroke="#9a9a8e" stroke-width="6" stroke-linecap="round"/></g>`;
}
function receipt(cx, cy, sc = 1, rot = 0) {
  let zig = '';
  for (let i = 16; i >= 0; i--) zig += ` L${f1c(-150 + i * 18.75)},${i % 2 ? 222 : 210}`;
  return `<g transform="translate(${f1c(cx)},${f1c(cy)}) rotate(${f1c(rot)}) scale(${sc.toFixed(3)})" filter="url(#shS)">
    <path d="M-150,-220 L150,-220 L150,210${zig} Z" fill="#FBF8F1"/>
    <use href="#gklogo" x="-48" y="-205" width="96" height="91"/>
    <text x="0" y="-80" text-anchor="middle" font-family="Anton" font-size="46" letter-spacing="8" fill="#082f27">KVITTO</text>
    <path d="M-120,-56 L120,-56" stroke="#0F5A3E" stroke-width="3" stroke-dasharray="6 6"/>
    <text x="-120" y="-16" font-family="Inter" font-weight="700" font-size="24" fill="#3b4a43">Golfkupong</text>
    <text x="-120" y="20" font-family="Inter" font-weight="600" font-size="22" fill="#6b7a73">Friskvård · Golf</text>
    <path d="M-120,48 L120,48" stroke="#c9c2b0" stroke-width="2"/>
    <text x="-120" y="90" font-family="Inter" font-weight="700" font-size="26" fill="#082f27">BETALD</text><text x="120" y="90" text-anchor="end" font-family="Inter" font-weight="700" font-size="26" fill="#0F7A50">✓</text>
    <path d="M-120,120 L120,120" stroke="#c9c2b0" stroke-width="2"/></g>`;
}
function stamp(cx, cy, k, rot = -12) {
  // k: 0 = ovanför (stor), 1 = landad. Grön stämpel med lite grov färg.
  const sc = k < 1 ? lerp(2.4, 1, eIn(k)) : 1, op = Math.min(1, k * 2);
  return `<g transform="translate(${cx},${cy}) rotate(${rot}) scale(${sc.toFixed(3)})" opacity="${op.toFixed(2)}" filter="url(#inkRough)">
    <rect x="-270" y="-82" width="540" height="164" rx="22" fill="none" stroke="#0F8A55" stroke-width="16"/>
    <rect x="-250" y="-62" width="500" height="124" rx="14" fill="none" stroke="#0F8A55" stroke-width="5"/>
    <text x="0" y="40" text-anchor="middle" font-family="Anton" font-size="118" letter-spacing="10" fill="#0F8A55">GODKÄNT</text></g>`;
}
