// Stilbilder för "spola tillbaka"-versionen. Återanvänder ritfunktionerna i scene.js.
'use strict';

function tblock(lines, size, fg, box, boxFg, top = 300, shadow = true) {
  let h = `<div class="block" style="top:${top}px;color:${fg};font-size:${size}px">`;
  for (const ln of lines) {
    const inner = ln.replace(/\{(.+?)\}/g, (_, w) => `<span class="hl" style="margin-top:${/[ÅÄÖ]/i.test(w) ? '0.08em' : '0'}"><span class="box" style="top:${/[ÅÄÖ]/i.test(w) ? '-0.17em' : '0'};background:${box};box-shadow:0 6px 14px rgba(0,0,0,.25)"></span><span class="w" style="color:${boxFg}">${w}</span></span>`);
    h += `<span class="line" style="text-shadow:${shadow ? '0 4px 0 rgba(0,0,0,.22), 0 10px 24px rgba(0,0,0,.35)' : 'none'}">${inner}</span>`;
  }
  return h + '</div>';
}
const osd = (x, y, txt, size = 52) => `<div class="osd" style="left:${x}px;top:${y}px;font-size:${size}px">${txt}</div>`;

function sfDefs() {
  return `<defs>
    <linearGradient id="tear" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#BFE8FF"/><stop offset="1" stop-color="#4FA8E8"/></linearGradient>
    <linearGradient id="capG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1B7552"/><stop offset="1" stop-color="#0C4A33"/></linearGradient>
    <radialGradient id="skin" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#F7D3AE"/><stop offset="1" stop-color="#E2AA80"/></radialGradient>
    <radialGradient id="emoji" cx="40%" cy="30%" r="80%"><stop offset="0" stop-color="#FFE27A"/><stop offset="1" stop-color="#F0A21E"/></radialGradient>
    <radialGradient id="redVig" cx="50%" cy="45%" r="75%"><stop offset=".45" stop-color="#7a0b10" stop-opacity="0"/><stop offset="1" stop-color="#7a0b10" stop-opacity=".55"/></radialGradient>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".22"/></pattern>
    <filter id="gray"><feColorMatrix type="saturate" values="0.25"/></filter>
    <filter id="bigSh" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="24" stdDeviation="22" flood-color="#000" flood-opacity=".45"/></filter>
    <filter id="neon" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter>
    <linearGradient id="beaconRay" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FF3B30" stop-opacity=".9"/><stop offset="1" stop-color="#FF3B30" stop-opacity="0"/></linearGradient>
    <radialGradient id="alarmEdge" cx="50%" cy="50%" r="72%"><stop offset=".55" stop-color="#FF1E1E" stop-opacity="0"/><stop offset="1" stop-color="#FF1E1E" stop-opacity=".55"/></radialGradient>
    <filter id="iconGlow" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="18" flood-color="#FFF3C4" flood-opacity=".55"/></filter>
  </defs>`;
}

// Förbudsmärket, byggt i kod (Jonas 2026-10-13): jättestort, självlysande genomskinligt rött som sticker ut över
// skärmen, slår ner med studs och skak, sedan pulserande larm med roterande varningsljus ("Tjernobyl").
function prohibition(cx, cy, R, sc = 1, glowK = 1) {
  const w = R * 0.19, rr = R - w / 2;
  const ring = `<circle r="${rr}" fill="none" stroke="#FF5A4E" stroke-width="${w}"/><rect x="${-rr}" y="${-w / 2}" width="${2 * rr}" height="${w}" fill="#FF5A4E" transform="rotate(45)"/>`;
  return `<g transform="translate(${cx},${cy}) scale(${sc.toFixed(3)})">
    <g filter="url(#neon)" opacity="${(0.55 + 0.45 * glowK).toFixed(2)}">${ring}</g>
    <g opacity=".88">${ring}</g>
    <circle r="${rr}" fill="none" stroke="#FFD2CC" stroke-width="${f1(w * 0.12)}" opacity="${(0.25 + 0.35 * glowK).toFixed(2)}"/></g>`;
}
function alarmLights(t, k) {
  // två roterande strålkastare (som en varningsfyr) + pulserande kantglöd
  let s = '';
  for (const [x, y, ph] of [[-40, 260, 0], [1120, 260, Math.PI]]) {
    const a = (t * 210 + ph * 57.3) % 360;
    s += `<g transform="translate(${x},${y}) rotate(${f1(a)})" opacity="${(0.25 + 0.4 * k).toFixed(2)}" style="mix-blend-mode:screen"><path d="M0,0 L1700,-200 L1700,200Z" fill="url(#beaconRay)"/></g>`;
  }
  return s + `<rect width="1080" height="1920" fill="url(#alarmEdge)" opacity="${(0.4 + 0.6 * k).toFixed(2)}"/><rect width="1080" height="1920" fill="#FF2A2A" opacity="${(0.1 * k * k).toFixed(3)}" style="mix-blend-mode:screen"/>`;
}

// Gråtande golfare (egen figur): keps med Golfkupongers riktiga logga, pikétröja, tårfontäner, snyftningar.
function cryingGuy(t, cx = 540, cy = 860) {
  const flow = (t * 220) % 120, sob = Math.abs(Math.sin(t * 7)) * 8, tilt = Math.sin(t * 3.5) * 1.5;
  let s = `<g transform="translate(${cx - 540},${cy - 860})">`;
  s += `<ellipse cx="240" cy="1290" rx="160" ry="28" fill="#6DBBEF" opacity=".75"/><ellipse cx="840" cy="1290" rx="160" ry="28" fill="#6DBBEF" opacity=".75"/>`;
  s += `<g transform="translate(0,${f1(sob * 0.5)})"><path d="M240,1340 C250,1185 380,1128 540,1128 C700,1128 830,1185 840,1340Z" fill="#1F6B4B"/>
    <path d="M240,1340 C250,1185 380,1128 540,1128 C700,1128 830,1185 840,1340Z" fill="url(#pageLight)"/>
    <path d="M468,1128 L540,1205 L612,1128Z" fill="#F8F4EC"/><path d="M540,1205 L540,1300" stroke="#0f4a33" stroke-width="5"/>
    <circle cx="540" cy="1232" r="6" fill="#F8F4EC"/><circle cx="540" cy="1268" r="6" fill="#F8F4EC"/></g>`;
  s += `<g transform="translate(0,${f1(sob)}) rotate(${f1(tilt)} 540 900)">`;
  s += `<rect x="498" y="1080" width="84" height="70" rx="22" fill="#DFA67C"/>`;
  s += `<circle cx="342" cy="905" r="44" fill="#E9B78E"/><circle cx="738" cy="905" r="44" fill="#E9B78E"/>
    <ellipse cx="540" cy="890" rx="200" ry="235" fill="url(#skin)"/>`;
  // keps: kulle, sömmar, knapp, riktig logga, skärm framifrån
  s += `<path d="M334,818 C328,646 438,598 540,598 C642,598 752,646 746,818 Q540,792 334,818Z" fill="url(#capG)"/>
    <path d="M540,600 L540,640 M440,612 Q420,700 412,808 M640,612 Q660,700 668,808" stroke="#0a3f2c" stroke-width="3.5" fill="none" opacity=".55"/>
    <circle cx="540" cy="600" r="11" fill="url(#goldS)"/>
    <use href="#gklogo" x="462" y="640" width="156" height="148"/>
    <ellipse cx="540" cy="872" rx="190" ry="20" fill="#2a1a0e" opacity=".22"/>
    <path d="M314,816 Q540,784 766,816 Q776,852 540,866 Q304,852 314,816Z" fill="#0B4430"/>
    <path d="M318,818 Q540,788 762,818" stroke="#2d7a5a" stroke-width="4" fill="none"/>`;
  s += `<g stroke="#3a2412" stroke-linecap="round" fill="none">
    <path d="M400,884 Q452,872 505,848" stroke-width="15"/><path d="M680,884 Q628,872 575,848" stroke-width="15"/>
    <path d="M410,918 Q452,890 500,920" stroke-width="13"/><path d="M670,918 Q628,890 580,920" stroke-width="13"/>
    <path d="M420,936 Q452,950 490,936" stroke-width="6" opacity=".5"/><path d="M660,936 Q628,950 590,936" stroke-width="6" opacity=".5"/></g>
    <ellipse cx="398" cy="990" rx="42" ry="24" fill="#EF8A76" opacity=".5"/><ellipse cx="682" cy="990" rx="42" ry="24" fill="#EF8A76" opacity=".5"/>
    <path d="M532,932 Q548,974 526,984" stroke="#C98B62" stroke-width="7" fill="none" stroke-linecap="round"/>
    <path d="M452,1012 Q540,980 628,1012 Q656,1098 540,1112 Q424,1098 452,1012Z" fill="#5B1717"/>
    <path d="M464,1014 Q540,990 616,1014 L610,1032 Q540,1012 470,1032Z" fill="#fff"/>
    <ellipse cx="540" cy="1088" rx="56" ry="20" fill="#E2656B"/>`;
  for (const dir of [-1, 1]) {
    const x0 = 540 + dir * 128, y0 = 918;
    const d = `M${x0},${y0} C${x0 + dir * 110},${y0 - 60} ${x0 + dir * 235},${y0 - 10} ${x0 + dir * 300},${y0 + 360}`;
    s += `<path d="${d}" stroke="url(#tear)" stroke-width="34" fill="none" stroke-linecap="round" opacity=".95"/>
      <path d="${d}" stroke="#E6F7FF" stroke-width="8" fill="none" stroke-dasharray="30 90" stroke-dashoffset="${-flow}" stroke-linecap="round" opacity=".8"/>`;
    const r = rng(dir > 0 ? 3 : 4);
    for (let i = 0; i < 7; i++) {
      const life = ((t * 1.6 + r()) % 1), bx = x0 + dir * (150 + r() * 170) + dir * life * 40, by = y0 + 70 + life * 300 + r() * 40;
      s += `<path transform="translate(${f1(bx)},${f1(by)}) scale(${(0.6 + r() * 0.8).toFixed(2)})" d="M0,-16 C9,-4 12,4 12,8 C12,16 -12,16 -12,8 C-12,4 -9,-4 0,-16Z" fill="#8FD0FF"/>`;
    }
  }
  return s + '</g></g>';
}

function cryingEmoji(t) {
  const flow = (t * 220) % 120;
  let s = `<ellipse cx="540" cy="1250" rx="330" ry="40" fill="#6DBBEF" opacity=".8"/>
    <circle cx="540" cy="880" r="310" fill="url(#emoji)"/>
    <g stroke="#6B3A06" stroke-linecap="round" fill="none"><path d="M370,720 Q420,700 470,668" stroke-width="18"/><path d="M710,720 Q660,700 610,668" stroke-width="18"/>
    <path d="M380,800 Q425,770 475,800" stroke-width="15"/><path d="M700,800 Q655,770 605,800" stroke-width="15"/></g>
    <path d="M445,930 Q540,895 635,930 Q665,1050 540,1075 Q415,1050 445,930Z" fill="#6B1E12"/><ellipse cx="540" cy="1045" rx="60" ry="22" fill="#E2656B"/>`;
  for (const dir of [-1, 1]) {
    const x = 540 + dir * 120;
    s += `<path d="M${x - 34},800 L${x + 34},800 L${x + 48},1250 L${x - 48},1250Z" fill="url(#tear)" opacity=".95"/>
      <path d="M${x},810 L${x},1240" stroke="#E6F7FF" stroke-width="8" stroke-dasharray="30 90" stroke-dashoffset="${-flow}" stroke-linecap="round" opacity=".8"/>`;
  }
  return s;
}

function vhs(t, strength = 1) {
  const r = rng(Math.floor(t * 30));
  let s = `<rect width="1080" height="1920" fill="url(#scan)"/>`;
  for (let i = 0; i < 4; i++) {
    const y = r() * 1920, h = 6 + r() * 30;
    s += `<rect x="0" y="${f1(y)}" width="1080" height="${f1(h)}" fill="#fff" opacity="${(0.05 + r() * 0.12 * strength).toFixed(2)}"/>`;
  }
  return s;
}
// Dela upp en bild i horisontella band och förskjut dem (bandspelarens "tracking").
function trackingSlices(inner, t, amp = 22) {
  const r = rng(Math.floor(t * 30) + 7);
  let s = '', y = 0, i = 0;
  while (y < 1920) {
    const h = 40 + r() * 220, dx = (r() < 0.35 ? (r() - 0.5) * 2 * amp : 0);
    s += `<clipPath id="sl${i}"><rect x="-100" y="${f1(y)}" width="1300" height="${f1(h)}"/></clipPath><g clip-path="url(#sl${i})" transform="translate(${f1(dx)},0)">${inner}</g>`;
    y += h; i++;
  }
  return s;
}
function rewindIcon(kind, cx, cy, sc = 1, col = '#F8F4EC') {
  const tri = (x) => `<path d="M${x},0 L${x + 150},-118 Q${x + 168},-130 ${x + 168},-108 L${x + 168},108 Q${x + 168},130 ${x + 150},118Z" fill="${col}" stroke="${col}" stroke-width="22" stroke-linejoin="round"/>`;
  let g = '';
  if (kind === 'solid') g = tri(-170) + tri(-10);
  if (kind === 'ring') g = `<circle r="250" fill="none" stroke="${col}" stroke-width="26"/><g transform="scale(.62) translate(6,0)">${tri(-170)}${tri(-10)}</g>`;
  if (kind === 'arrow') g = `<path d="M-170,-60 A190,190 0 1 1 -120,140" fill="none" stroke="${col}" stroke-width="56" stroke-linecap="round"/><path d="M-255,-120 L-110,-150 L-160,0Z" fill="${col}" stroke="${col}" stroke-width="18" stroke-linejoin="round"/>`;
  return `<g transform="translate(${cx},${cy}) scale(${sc})" filter="url(#iconGlow)">${g}</g>`;
}
function pauseIcon(cx, cy, sc = 1) {
  return `<g transform="translate(${cx},${cy}) scale(${sc})" filter="url(#iconGlow)">
    <rect x="-150" y="-200" width="100" height="400" rx="26" fill="#F8F4EC"/><rect x="50" y="-200" width="100" height="400" rx="26" fill="#F8F4EC"/></g>`;
}

// Kalenderscen med valfri sida och brännivå (för stillbilder).
function calScene(t, k, burn, flame, extra = '') {
  const d = k;
  return background(t, d) + `<g>${weather(t, d)}${goldDust(t)}${calendar(5, k)}${tornPages(t, k)}
    <g transform="translate(${NOTE_POS.x},${NOTE_POS.y}) rotate(${NOTE_POS.rot}) scale(${NOTE_POS.s})" filter="url(#shS)">${note(t, { burn, flame, rot: NOTE_POS.rot, id: 'sf' })}</g>
    ${decor(t, d)}</g>` + extra;
}

const FRAMES = {
  // 1. Bollen igenom för sent: banan, röd ton, förbudsmärket landar
  'A-forbud'(t) {
    const T0 = 0.25, land = clamp(t / T0), hit = t >= T0;
    const sc = hit ? 1 + 0.06 * Math.exp(-(t - T0) * 9) * Math.cos((t - T0) * 40) : lerp(2.6, 1, eIn(land));
    const shake = hit ? Math.exp(-(t - T0) * 8) * 26 : 0, sx = shake * Math.sin(t * 90), sy = shake * Math.cos(t * 71);
    const pulse = hit ? 0.5 + 0.5 * Math.cos((t - T0) * Math.PI * 2 * 1.6) : 0; // larm 1,6 Hz
    const flood = hit ? clamp((t - T0) / 0.12) : 0;
    const keep = springNote; springNote = () => ''; // kortet har brunnit upp helt
    const course = spring(14.4); springNote = keep;
    const svg = defs() + sfDefs() + `<g transform="translate(${f1(sx)},${f1(sy)})">` + course
      + `<rect x="-40" y="-40" width="1160" height="2000" fill="#C4111B" opacity="${(flood * (0.42 + 0.14 * pulse)).toFixed(2)}" style="mix-blend-mode:multiply"/>`
      + (hit ? alarmLights(t, pulse) : '')
      + (hit && t - T0 < 0.5 ? `<circle cx="540" cy="930" r="${f1(520 + (t - T0) * 900)}" fill="none" stroke="#FFD2CC" stroke-width="${f1(30 * (1 - (t - T0) / 0.5))}" opacity=".6"/>` : '')
      + `<g opacity="${clamp(land * 1.5).toFixed(2)}">${prohibition(540, 930, 540, sc, hit ? pulse : 0.3)}</g></g>`;
    const txt = t > T0 + 0.05 ? tblock(['{FÖR SENT.}'], 160, '#ffffff', '#E0201B', '#ffffff') : '';
    return { svg, html: txt };
  },
  // 2a. Egen gråtande golfare
  'B-gubbe'(t) {
    const svg = defs() + sfDefs() + background(9, 80) + `<rect width="1080" height="1920" fill="#B3121B" opacity=".28" style="mix-blend-mode:multiply"/><rect width="1080" height="1920" fill="url(#redVig)"/>` + cryingGuy(t);
    return { svg, html: tblock(['BIDRAGET', '{BRANN INNE.}'], 120, '#F8F4EC', '#D7261E', '#F8F4EC') };
  },
  // 2b. Emoji-variant
  'B-emoji'(t) {
    const svg = defs() + sfDefs() + background(9, 80) + `<rect width="1080" height="1920" fill="#B3121B" opacity=".28" style="mix-blend-mode:multiply"/><rect width="1080" height="1920" fill="url(#redVig)"/>` + cryingEmoji(t);
    return { svg, html: tblock(['BIDRAGET', '{BRANN INNE.}'], 120, '#F8F4EC', '#D7261E', '#F8F4EC') };
  },
  // 3. Paus: bilden fryser, avfärgas, pausikon + text
  'C-paus'(t) {
    const frozen = `<g filter="url(#gray)">${background(9, 80)}${cryingGuy(0.4)}</g><rect width="1080" height="1920" fill="#06140d" opacity=".55"/>`;
    const svg = defs() + sfDefs() + frozen + pauseIcon(540, 940, 0.9) + vhs(t, 0.6);
    return { svg, html: tblock(['DET HÄR', 'BEHÖVER INTE', '{HÄNDA DIG.}'], 120, '#F8F4EC', '#F3D27A', '#082f27') + osd(80, 1170, '❚❚ PAUS') + osd(80, 1236, 'TOR 31 DEC 2026', 40) };
  },
  // 4. Spola tillbaka: scenen spelas baklänges med tracking-fel och ikon
  'D-spola'(t) {
    const scene = calScene(t, 70, 0.6, 0.8);
    const svg = defs() + sfDefs() + trackingSlices(scene, t, 26) + `<rect width="1080" height="1920" fill="#0a1a12" opacity=".25"/>` + rewindIcon('solid', 560, 900, 1) + vhs(t, 1.2);
    return { svg, html: osd(80, 1170, '◀◀ SPOLA TILLBAKA') + osd(80, 1236, '10 DEC 2026', 40) };
  },
  // 5. Tre ikonval för spola tillbaka
  'E-ikoner'(t) {
    const svg = defs() + sfDefs() + background(9, 60) + rewindIcon('solid', 540, 560, 0.85) + rewindIcon('ring', 540, 1060, 0.8) + rewindIcon('arrow', 540, 1560, 0.75);
    return { svg, html: osd(70, 600, 'S1', 46) + osd(70, 1100, 'S2', 46) + osd(70, 1600, 'S3', 46) };
  },
  // 6. Andra varvet: bollen skjuts igenom redan i november
  'F-november'(t) {
    const k = 44; // 14 nov
    const flash = `<circle cx="${HOLE.x}" cy="${HOLE.y}" r="150" fill="none" stroke="#fff6cf" stroke-width="8" opacity=".85"/>`;
    const svg = defs() + sfDefs() + calScene(t, k, 0.35, 0.7, flash + ball(HOLE.x + 40, HOLE.y + 30, 44, 30));
    return { svg, html: tblock(['14 NOVEMBER.', '{NU HINNER DU.}'], 124, '#F8F4EC', '#F3D27A', '#082f27') };
  },
};

window.SF = {
  names: Object.keys(FRAMES),
  render(name, t = 1.0) { const f = FRAMES[name](t); document.getElementById('svg').innerHTML = f.svg; document.getElementById('text').innerHTML = f.html; },
  ready: Promise.all([...['112px Anton', '700 28px Inter', '52px Mono'].map((f) => document.fonts.load(f)),
    Promise.race([new Promise((ok) => { const i = new Image(); i.src = window.GK_LOGO; i.decode().then(ok, ok); }), new Promise((ok) => setTimeout(ok, 3000))])]).then(() => document.fonts.ready),
};
