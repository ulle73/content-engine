// "Ingen portal? Låt chefen betala din golf" – huvudtidslinje (verklig tid). Ritar med scene.js, sf.js, tourleif.js, chef.js.
'use strict';

// ---------- Texter (läsregeln kontrolleras i render.mjs) ----------
TEXTS.length = 0;
TEXTS.push(
  { id: 't1', win: [0.15, 3.6], size: 99, lines: ['INGEN FÖRMÅNSPORTAL', 'PÅ {JOBBET?}'], fg: C.cream, box: '#F3D27A', boxFg: C.deep },
  { id: 't2', win: [3.65, 7.1], size: 116, lines: ['KÖP DIREKT PÅ', '{GOLFKUPONGER.SE}'], fg: C.cream, box: '#F3D27A', boxFg: C.deep },
  { id: 't3', win: [10.6, 13.45], size: 120, lines: ['KVITTOT KOMMER', '{SOM PDF.}'], fg: C.cream, box: '#F3D27A', boxFg: C.deep },
  { id: 't4', win: [13.5, 16.7], size: 120, lines: ['LÅT CHEFEN BETALA', '{DIN GOLF.}'], fg: C.cream, box: '#F3D27A', boxFg: C.deep },
  { id: 't5', win: [18.5, 23.25], size: 105, lines: ['FRISKVÅRDSBIDRAGET:', 'CHEFEN BETALAR.', '{DU SPELAR.}'], fg: C.deep, box: C.deep, boxFg: C.cream },
);
const END = 23.75;

// ---------- Hjälpare ----------
const ease = (u) => (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2);
const seg = (t, a, b) => ease(prog(t, a, b));

// ---------- 1. Dörren "FÖRMÅNSPORTAL" ----------
function bricks() {
  let s = `<rect x="580" y="540" width="360" height="720" fill="#8E4A32"/>`;
  for (let r = 0; r < 24; r++) {
    const y = 540 + r * 30, off = r % 2 ? 0 : 36;
    for (let c = -1; c < 6; c++) s += `<rect x="${580 + off + c * 72 + 3}" y="${y + 3}" width="66" height="24" rx="3" fill="${['#A85A3C', '#9C5236', '#B26445'][(r * 7 + c * 3 + 30) % 3]}"/>`;
  }
  return s + `<rect x="580" y="540" width="360" height="720" fill="url(#vig)"/><rect x="580" y="540" width="360" height="40" fill="#000" opacity=".35"/>`;
}
function cobweb(t) {
  let s = '<g stroke="#EDE7DA" stroke-width="2.4" fill="none" opacity=".85">';
  for (let i = 0; i <= 6; i++) { const a = i / 6 * Math.PI / 2; s += `<path d="M584,544 L${f1(584 + Math.cos(a) * 170)},${f1(544 + Math.sin(a) * 170)}"/>`; }
  for (let r = 40; r <= 160; r += 30) {
    let d = '';
    for (let i = 0; i <= 6; i++) { const a = i / 6 * Math.PI / 2, rr = r - (i % 2) * 8; d += `${i ? 'L' : 'M'}${f1(584 + Math.cos(a) * rr)},${f1(544 + Math.sin(a) * rr)} `; }
    s += `<path d="${d}"/>`;
  }
  const sy = 700 + Math.sin(t * 2.2) * 30;
  s += `<path d="M860,580 L860,${f1(sy)}"/></g><g transform="translate(860,${f1(sy)})"><ellipse rx="13" ry="16" fill="#1d1410"/><circle cy="-14" r="8" fill="#1d1410"/>
    ${[-1, 1].map((d) => [0, 1, 2].map((i) => `<path d="M0,${-6 + i * 7} q${d * 16},-8 ${d * 24},${6 + i * 3}" stroke="#1d1410" stroke-width="3" fill="none"/>`).join('')).join('')}</g>`;
  return s;
}
function partDoor(t) {
  const open = seg(t, 0.5, 1.1);
  let s = wall(t) + goldDust(t);
  s += `<rect x="0" y="1250" width="1080" height="670" fill="url(#table)"/><rect x="0" y="1250" width="1080" height="670" fill="url(#speck)" opacity=".6"/><rect x="0" y="1236" width="1080" height="16" fill="#0a2a1d"/>`;
  s += `<g filter="url(#sh)"><rect x="560" y="520" width="400" height="740" rx="10" fill="#3a2414"/></g>`;
  s += bricks() + (open > 0.3 ? `<g opacity="${sstep(0.3, 0.8, open).toFixed(2)}">${cobweb(t)}</g>` : '');
  // dörrbladet svänger upp mot kameran (gångjärn till vänster)
  const sx = 1 - 0.88 * open;
  s += `<g transform="translate(580,0) scale(${sx.toFixed(3)},1) translate(-580,0)">
    <rect x="580" y="540" width="360" height="720" rx="6" fill="url(#door)"/><rect x="580" y="540" width="360" height="720" fill="#000" opacity="${(0.35 * open).toFixed(2)}"/>
    <rect x="612" y="580" width="296" height="300" rx="8" fill="none" stroke="#3e2816" stroke-width="10"/><rect x="612" y="920" width="296" height="300" rx="8" fill="none" stroke="#3e2816" stroke-width="10"/>
    <circle cx="905" cy="900" r="20" fill="url(#brass)"/>
    <rect x="610" y="640" width="300" height="84" rx="10" fill="url(#brass)"/>
    <text x="760" y="697" text-anchor="middle" font-family="Anton" font-size="46" letter-spacing="4" fill="#3a2a10">FÖRMÅNSPORTAL</text></g>`;
  // dammpuff när dörren slås upp
  if (t > 0.9 && t < 2.0) {
    const p = prog(t, 0.9, 2.0);
    for (let i = 0; i < 8; i++) s += `<circle cx="${f1(620 + i * 40 + p * (i - 4) * 18)}" cy="${f1(1240 - p * 60 - (i % 3) * 14)}" r="${f1(16 + p * 30)}" fill="#d9cdb6" opacity="${(0.4 * (1 - p)).toFixed(2)}"/>`;
  }
  s += tourleif(t, { expr: t < 1.1 ? 'glad' : 'forvanad', x: 300, y: 1000, s: 0.7 });
  return s;
}

// ---------- 2. Mobilen: riktiga skärmar från golfkuponger.se ----------
const PHN = { x0: 252, y0: 560, k: 576 / 390 };          // skärmens vänster/överkant på duken, duk-px per sid-px
const PIMG = 576 / 780;                                    // bilderna är tagna i 2x
const S_PK = 2419 - (1150 - PHN.y0) / PHN.k;                 // scroll där "Köp nu" hamnar på y≈1150
const S_NAME = 935 - (1000 - PHN.y0) / PHN.k;                // scroll där förnamnsfältet hamnar på y≈1000
const S_PAY = 783;                                          // kassans max-scroll
const PAY_Y = 1487;                                         // "Betala nu" (sid-px)
const TYPE_T0 = 7.6, TYPE_DT = 0.12;
function phoneScreen(t) {
  // returnerar innehåll i "skärm-koordinater" (duk) + fokus för kameran
  const X = PHN.x0, Y = PHN.y0, W = 576, Hs = 844 * PHN.k;
  let s = `<rect x="${X}" y="${Y}" width="${W}" height="${f1(Hs)}" fill="#fff"/>`;
  const page = (id, scrollPx, dx = 0, hPx = 6455) => `<use href="#${id}" x="${f1(X + dx)}" y="${f1(Y - scrollPx * PHN.k)}" width="${W}" height="${f1(hPx * PHN.k)}"/>`;
  if (t < 6.45) {
    const sc = S_PK * seg(t, 4.75, 5.95);
    s += page('im-pk', sc);
  } else if (t < 9.55) {
    const slide = seg(t, 6.45, 6.85);
    if (slide < 1) s += page('im-pk', S_PK, -W * slide);
    let sc = S_NAME * seg(t, 6.9, 7.4);
    if (t > 8.8) sc = lerp(S_NAME, S_PAY, seg(t, 8.8, 9.3));
    const n = clamp(Math.floor((t - TYPE_T0) / TYPE_DT) + 1, 0, 8);
    s += page(`im-co${n}`, sc, W * (1 - slide), 1627);
    if (t > 9.4) { // "Betala nu" trycks: knappen mörknar ett ögonblick
      const k = Math.exp(-Math.pow((t - 9.48) / 0.07, 2));
      s += `<rect x="${f1(X + 14 * PHN.k)}" y="${f1(Y + (678.6 + 0) * PHN.k)}" width="${f1(362 * PHN.k)}" height="${f1(49.6 * PHN.k)}" rx="12" fill="#000" opacity="${(0.25 * k).toFixed(2)}"/>`;
    }
  } else if (t < 11.05) {
    // tack: stor grön bock som ritas fram
    const cx = X + W / 2, cy = Y + Hs / 2, R = 150;  // mitt på skärmen
    const ring = seg(t, 9.65, 10.05), chk = seg(t, 9.95, 10.3), pop = t > 10.3 ? 1 + 0.08 * Math.exp(-(t - 10.3) * 8) * Math.cos((t - 10.3) * 30) : 1;
    s += `<rect x="${X}" y="${Y}" width="${W}" height="${f1(Hs)}" fill="#F4FAF6"/>
      <g transform="translate(${cx},${cy}) scale(${pop.toFixed(3)})">
      <circle r="${R}" fill="#E3F4EA" opacity="${ring.toFixed(2)}"/>
      <circle r="${R}" fill="none" stroke="#1E9E5A" stroke-width="22" stroke-linecap="round" stroke-dasharray="${f1(2 * Math.PI * R)}" stroke-dashoffset="${f1(2 * Math.PI * R * (1 - ring))}" transform="rotate(-90)"/>
      <path d="M-70,0 L-20,52 L78,-58" fill="none" stroke="#1E9E5A" stroke-width="30" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="230" stroke-dashoffset="${f1(230 * (1 - chk))}"/></g>`;
    if (t > 10.25) [[-210, -140, 0], [200, -160, 1.1], [220, 120, 2.2], [-200, 150, 3.0], [0, -230, 4.1]].forEach(([dx, dy, ph]) => {
      const k = Math.max(0, Math.sin((t - 10.25) * 5 + ph)), q = 22 * k;
      if (q > 1) s += `<path transform="translate(${f1(cx + dx)},${f1(cy + dy)})" d="M0,${-q} L${q * 0.16},${-q * 0.16} L${q},0 L${q * 0.16},${q * 0.16} L0,${q} L${-q * 0.16},${q * 0.16} L${-q},0 L${-q * 0.16},${-q * 0.16}Z" fill="#D6A536"/>`;
    });
    if (t > 10.6) { // mejlnotis glider in
      const nt = seg(t, 10.6, 10.85), ny = Y + 24 - 160 * (1 - nt);
      s += `<g filter="url(#shS)"><rect x="${X + 22}" y="${f1(ny)}" width="${W - 44}" height="150" rx="28" fill="#FBF8F1"/></g>
        <rect x="${X + 46}" y="${f1(ny + 32)}" width="86" height="86" rx="18" fill="#0F5A3E"/><use href="#gklogo" x="${X + 52}" y="${f1(ny + 38)}" width="74" height="74"/>
        <text x="${X + 152}" y="${f1(ny + 70)}" font-family="Inter" font-weight="700" font-size="32" fill="#082f27">Golfkuponger</text>
        <text x="${X + 152}" y="${f1(ny + 112)}" font-family="Inter" font-weight="600" font-size="28" fill="#3b4a43">Ditt kvitto (pdf) 📎</text>`;
    }
  } else {
    // pdf:en öppnas: riktigt kvitto (anonymiserat) + raden "Underlag för friskvårdsbidrag"
    const op = sstep(11.05, 11.3, t), sc = 310 * seg(t, 11.8, 12.4) + 344 * seg(t, 12.55, 13.05);
    const kh = 1990 * (W / 1418);
    s += `<rect x="${X}" y="${Y}" width="${W}" height="${f1(Hs)}" fill="#E9E9EC"/>
      <g opacity="${op.toFixed(2)}"><use href="#im-kv1" x="${X + 8}" y="${f1(Y + 20 - sc)}" width="${W - 16}" height="${f1(kh * (W - 16) / W)}"/>
      <rect x="${X + 8}" y="${f1(Y + 34 + kh - sc)}" width="${W - 16}" height="120" fill="#fff"/>
      <use href="#im-kvu" x="${X + 8}" y="${f1(Y + 46 + kh - sc)}" width="${W - 16}" height="${f1(120 * (W - 16) / 1418)}"/></g>`;
    const hl = seg(t, 13.0, 13.3);   // guldmarkering under "Underlag för friskvårdsbidrag"
    if (hl > 0) s += `<rect x="${X + 30}" y="${f1(Y + 46 + kh - sc + 23 * (W - 16) / 560)}" width="${f1((W - 140) * hl)}" height="${f1(16 * (W - 16) / 560)}" rx="4" fill="#F3D27A" opacity=".55" style="mix-blend-mode:multiply"/>`;
  }
  return s;
}
function tap(x, y, t, t0) {
  const p = (t - t0) / 0.45;
  if (p < -0.4 || p > 1) return '';
  const k = clamp(p), pre = clamp((p + 0.4) / 0.4);
  return `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(30 + 10 * (1 - pre))}" fill="#fff" opacity="${(0.55 * (p < 0 ? pre : 1 - k)).toFixed(2)}"/>
    <circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(30 + 70 * k)}" fill="none" stroke="#fff" stroke-width="${f1(6 * (1 - k))}" opacity="${(0.8 * (1 - k)).toFixed(2)}"/>`;
}
function partPhone(t) {
  const X = PHN.x0, Y = PHN.y0, W = 576, Hs = 844 * PHN.k;
  const rise = 1 - seg(t, 3.6, 4.2);
  // kamera: zooma mot förnamnsfältet när han skriver, panorera upp till "Betala nu", tillbaka till bocken
  const zoom = 1 + 0.45 * seg(t, 7.4, 7.8) * (1 - seg(t, 8.65, 8.95));
  const up = -(Y + (PAY_Y - S_PAY) * PHN.k - 1150) * seg(t, 8.8, 9.3) * (1 - seg(t, 9.55, 9.95));
  const rz = 0.8 * seg(t, 11.3, 11.7);           // zooma in på pdf-kvittot
  const fx = 540, fy = rz > 0 ? 600 : 1000;
  let s = wall(t) + goldDust(t);
  s += `<g transform="translate(0,${f1(rise * 1500 + up)}) translate(${fx},${fy}) scale(${(zoom + rz).toFixed(3)}) translate(${-fx},${-fy})">
    <g filter="url(#sh)"><rect x="${X - 16}" y="${Y - 16}" width="${W + 32}" height="${f1(Hs + 32)}" rx="78" fill="#111"/></g>
    <clipPath id="scrn"><rect x="${X}" y="${Y}" width="${W}" height="${f1(Hs)}" rx="64"/></clipPath>
    <g clip-path="url(#scrn)">${phoneScreen(t)}</g>
    <rect x="${X + W / 2 - 90}" y="${Y + 14}" width="180" height="44" rx="22" fill="#111"/>
    <rect x="${X - 16}" y="${Y - 16}" width="${W + 32}" height="${f1(Hs + 32)}" rx="78" fill="none" stroke="#3a3a3a" stroke-width="5"/>`;
  s += tap(X + 195 * PHN.k, Y + 426 * PHN.k, t, 4.6);                                    // gula knappen
  s += tap(X + 195 * PHN.k, Y + (2419 - S_PK) * PHN.k, t, 6.2);                         // Köp nu
  s += tap(X + 195 * PHN.k, Y + (935 - S_NAME) * PHN.k, t, 7.45);                       // förnamn
  s += tap(X + 195 * PHN.k, Y + (PAY_Y - S_PAY) * PHN.k, t, 9.42);                      // Betala nu
  s += tap(X + W / 2, Y + 24 + 75, t, 11.0);                                          // mejlnotisen
  return s + '</g>';
}

// ---------- 3. Chefen godkänner ----------
function paper(cx, cy, w, rot = 0, extra = '') {
  const h = w * 1990 / 1418;
  return `<g transform="translate(${f1(cx)},${f1(cy)}) rotate(${f1(rot)})" filter="url(#shS)">
    <rect x="${f1(-w / 2 - 6)}" y="${f1(-h / 2 - 6)}" width="${f1(w + 12)}" height="${f1(h + 12)}" fill="#fff"/>
    <use href="#im-kv1" x="${f1(-w / 2)}" y="${f1(-h / 2)}" width="${f1(w)}" height="${f1(h)}"/>${extra}</g>`;
}
function partOffice(t) {
  const STAMP = 15.8;
  const expr = t < 14.6 ? 'ovetande' : t < STAMP + 0.05 ? 'skeptisk' : 'nojd';
  let s = office(t, expr, { mug: expr === 'ovetande', thumbK: seg(t, STAMP + 0.15, STAMP + 0.45), thumbY: 1040 });
  // Tourleif lämnar kvittot och blinkar efter stämpeln
  s += tourleif(t, { expr: t > STAMP + 0.6 ? 'blinkar' : 'glad', x: 190, y: 1200, s: 0.52 });
  // kvittot: glider in på bordet -> chefen lyfter det och läser (ögonen över kanten) -> ner -> stämpel
  const inP = seg(t, 13.5, 14.3), lift = seg(t, 14.6, 14.95) * (1 - seg(t, 15.45, 15.7));
  const cx = lerp(-300, 560, inP), cy = lerp(1185, 1128, lift), w = lerp(300, 360, lift), rot = lerp(-6, 0, lift);
  s += paper(cx, cy, w, rot);
  if (t >= STAMP - 0.25) {
    const k = clamp((t - (STAMP - 0.25)) / 0.25);
    s += stamp(560, 1150, k, -12);
    if (t > STAMP && t < STAMP + 0.6) {
      const p = prog(t, STAMP, STAMP + 0.6);
      s += `<circle cx="560" cy="1150" r="${f1(200 + p * 400)}" fill="none" stroke="#9FE3BC" stroke-width="${f1(18 * (1 - p))}" opacity=".7"/>`;
    }
  }
  if (t > 14.6 && t < STAMP) { // tick-tack: svettdroppe hos Tourleif
    s += `<path transform="translate(${f1(268 + Math.sin(t * 9) * 2)},${f1(1050 + (t - 14.6) * 40)})" d="M0,-16 C9,-4 12,4 12,8 C12,16 -12,16 -12,8 C-12,4 -9,-4 0,-16Z" fill="#8FD0FF"/>`;
  }
  // skak vid stämpeln
  const sh = t > STAMP ? Math.exp(-(t - STAMP) * 9) * 18 : 0;
  return `<g transform="translate(${f1(sh * Math.sin(t * 90))},${f1(sh * Math.cos(t * 70))})">${s}</g>`;
}

// ---------- 4. Golfbanan ----------
function partGolf(t) {
  const kn = springNote, kb = springBall; springNote = () => ''; springBall = () => '';
  const course = spring(15.5 + (t - 18.3) * 0.2); springNote = kn; springBall = kb;
  let s = course + chefen(t, { expr: 'nojd', x: 280, y: 1080, s: 0.42, cap: true }) + tourleif(t, { expr: 'jublar', x: 660, y: 1010, s: 0.6 });
  // iris till mörkgrönt (slutbildens första bildruta)
  if (t > 23.2) {
    const r = 2300 * (1 - eIn(prog(t, 23.2, END - 0.02)));
    s += `<path d="M0,0 H1080 V1920 H0Z M${f1(660 - r)},1010 a${r},${r} 0 1,0 ${2 * r},0 a${r},${r} 0 1,0 ${-2 * r},0Z" fill="#0c140f" fill-rule="evenodd"/>`;
  }
  return s;
}

// ---------- Övergångar och ram ----------
function frame(t) {
  if (t < 3.6) return partDoor(t);
  if (t < 13.4) {
    let s = partPhone(t);
    if (t < 4.0) s = `<g opacity="${sstep(3.6, 3.9, t).toFixed(2)}">${s}</g>`;
    return (t < 4.0 ? partDoor(t) : '') + s;
  }
  if (t < 18.3) {
    let s = partOffice(t);
    if (t < 13.7) s = partPhone(t) + `<g opacity="${sstep(13.4, 13.65, t).toFixed(2)}">${s}</g>`;
    return s;
  }
  // cirkelvisk från stämpeln till banan
  const r = 2200 * eIn(prog(t, 18.3, 18.75));
  if (r < 2150) return partOffice(18.3) + `<clipPath id="wipe"><circle cx="560" cy="1150" r="${f1(r)}"/></clipPath><g clip-path="url(#wipe)">${partGolf(t)}</g>`;
  return partGolf(t);
}
function renderAt(t) {
  document.getElementById('svg').innerHTML = defs() + sfDefs() + `<defs>${tourleifDefs()}${chefenDefs()}${chefDefs()}</defs>` + frame(t) + `<rect width="1080" height="1920" fill="url(#vig)"/>`;
  document.getElementById('text').innerHTML = textLayer(t);
}
const FLOW = ['packages-full', 'checkout-0', ...[1, 2, 3, 4, 5, 6, 7, 8].map((i) => `checkout-type-${i}`)].map((n) => `assets/flow/${n}.png`).concat(['assets/kvitto-sida1.png', 'assets/kvitto-underlag.png']);
window.SCENE = { W: 1080, H: 1920, FPS: 30, duration: END, TEXTS, renderAt,
  ready: Promise.all([...['112px Anton', '700 28px Inter', '600 28px Inter'].map((x) => document.fonts.load(x)),
    Promise.race([new Promise((ok) => { const i = new Image(); i.src = window.GK_LOGO; i.decode().then(ok, ok); }), new Promise((ok) => setTimeout(ok, 3000))]),
    ...FLOW.map((src) => new Promise((ok) => { const im = new Image(); im.onload = () => im.decode().then(ok, ok); im.onerror = ok; im.src = src; }))]).then(() => document.fonts.ready) };
