// "Spola tillbaka"-versionen (kort, ~26 s + slutbild). Återanvänder scene.js (ritning) och sf.js (märke, gubbe, ikoner).
// Allt styrs av verklig tid rt. Varje del ritas med scene.js-funktionerna i scentid, så spolningen är filmen baklänges.
'use strict';

// ---------- Verklig tidslinje ----------
const M = {
  stop: 12.55,                 // förbudsmärket slår ner (Jonas: 2 s golfbana först – "ååh, golf" – sedan tas den ifrån en)
  cry: 14.4,                   // gråtande gubben
  pause: 16.4,                 // paus (frys)
  rew: 20.0, rewEnd: 22.0,     // spola tillbaka
  play: 22.0,                  // ▶ spelar igen, kalendern står still på 13 nov
  slow: [22.9, 23.4],          // två lugna blad (13 -> 14 -> 15 nov) innan bollen
  end: 29.75,                  // irisen stängd -> slutbild
};
const OFF1 = 2.95;             // varv 1: scentid = verklig tid + OFF1 (bollen 12,1 scen = 9,15 verklig)
const OFF2 = -11.75;           // varv 2: scentid = verklig tid + OFF2 (bollen 12,1 scen = 23,85 verklig)
const REW_TO = 2.45;           // spolningen landar här i varv 1 (13 november överst)
const CAL_SHIFT = (M.play + OFF2) - (REW_TO + OFF1); // så att bladen fortsätter exakt där spolningen slutade

// Texter (verklig tid). Läsregeln kontrolleras i render.mjs.
TEXTS.length = 0;
TEXTS.push(
  { id: 't1', win: [0.15, 5.4], size: 104, lines: ['VAD HÄNDER MED DITT', 'FRISKVÅRDSBIDRAG', '{VID ÅRSSKIFTET?}'], fg: C.cream, box: C.cream, boxFg: C.deep },
  { id: 't3', win: [5.4, 9.05], size: 124, lines: ['DEN {31 DECEMBER}', 'BRINNER DET INNE.'], fg: C.cream, box: C.red, boxFg: C.cream },
  { id: 'sent', win: [12.6, 14.35], size: 160, lines: ['{FÖR SENT.}'], fg: '#ffffff', box: '#E0201B', boxFg: '#ffffff' },
  { id: 'paus', win: [16.5, 20.0], size: 120, lines: ['DET HÄR', 'BEHÖVER INTE', '{HÄNDA DIG.}'], fg: C.cream, box: '#F3D27A', boxFg: '#082f27' },
  { id: 't4', win: [25.25, 29.2], size: 126, lines: ['ANVÄND', 'FRISKVÅRDEN', 'TILL {GOLF I TID.}'], fg: C.deep, box: C.deep, boxFg: C.cream },
);

// ---------- Rivscheman (scentid) ----------
const TEAR1 = [], TEAR2 = [];
(function () {
  for (let k = 0; k < 31; k++) TEAR1[k] = -100;      // oktober redan avriven: varv 1 börjar 1 november
  TEAR1[31] = 0.75 + OFF1; TEAR1[32] = 1.25 + OFF1;
  const A = [[1.7, 33], [5.0, 75], [6.6, 84]].map(([t, k]) => [t + OFF1, k]);
  for (let k = 33; k <= 84; k++) {
    let i = 0; while (i < A.length - 2 && k > A[i + 1][1]) i++;
    const [t0, k0] = A[i], [t1, k1] = A[i + 1];
    TEAR1[k] = t0 + (t1 - t0) * (k - k0) / (k1 - k0);
  }
  [6.95, 7.3, 7.6, 7.9, 8.2].forEach((t, i) => { TEAR1[85 + i] = t + OFF1; });
  TEAR1[90] = TL.impact + 0.02;
  const stopK = topAt(TEAR1, REW_TO + OFF1);
  for (let k = 0; k <= 90; k++) TEAR2[k] = k < stopK ? TEAR1[k] + CAL_SHIFT : 1e9;
  M.slow.forEach((t, i) => { TEAR2[stopK + i] = t + OFF2; });
})();
function topAt(arr, t) { let n = 0; while (n < 90 && arr[n] <= t) n++; return n; }
function useTears(arr) { for (let k = 0; k <= 90; k++) TEAR[k] = arr[k]; }

// ---------- Varvens egenheter ----------
const IGN1 = 0.6 + OFF1;
const burn1 = (t) => Math.pow(clamp((t - IGN1) / (TL.impact - IGN1)), 1.25) + 0.02 * sstep(IGN1, IGN1 + 0.3, t); // helt uppbränt vid nyår
const flame1 = (t) => sstep(IGN1, IGN1 + 0.5, t) * (0.5 + 0.5 * prog(t, IGN1, TL.impact)) * (1 - sstep(TL.impact, TL.impact + 0.14, t));
const B0 = burn1(REW_TO + OFF1); // så mycket hann brinna innan vi spolade tillbaka
const burn2 = () => B0;
const flame2 = (t) => (0.5 + 0.5 * prog(REW_TO + OFF1, IGN1, TL.impact)) * (1 - sstep(TL.impact, TL.impact + 0.14, t));
const springBallOrig = springBall, springNoteOrig = springNote;
// Varv 1: bollen rullar sakta mot koppen och stannar på kanten – precis då slår förbudsmärket ner.
function springBall1(t) {
  const land2 = 14.02;
  if (t < land2) return springBallOrig(t);
  const p = prog(t, land2, M.stop + OFF1 - 0.05), e = 1 - Math.pow(1 - p, 2.2), x = lerp(530, 765, e);
  return shadow(x, 1194, 15) + ball(x, 1188, 15, x * 4);
}
// Varv 2: kortet har bara brunnit lite – det singlar ner och blir en golfkupong.
function springNote2(t) {
  const a = 13.45, land = 14.65, flip0 = 14.95, flip1 = 15.35;
  if (t < a) return '';
  const p = eOut(prog(t, a, land)), x = lerp(250, 330, p) + Math.sin(p * 9) * 60 * (1 - p), y = lerp(560, 1100, p);
  const rot = Math.sin(p * 8) * 22 * (1 - p) - 6;
  const fp = prog(t, flip0, flip1), sx = Math.cos(fp * Math.PI), hop = Math.sin(fp * Math.PI) * 40;
  const face = sx >= 0 ? note(t, { burn: B0 + 0.02, flame: 0, rot, id: 'spr2' }) : coupon(t);
  let s = `<g transform="translate(${f1(x)},${f1(y - hop)}) rotate(${f1(rot)}) scale(${(1.25 * Math.max(0.02, Math.abs(sx))).toFixed(3)},1.25)" filter="url(#shS)">${face}</g>`;
  if (t > flip1) {
    [[-150, -90, 0], [170, -70, 1.3], [120, 80, 2.4], [-180, 60, 3.3]].forEach(([dx, dy, ph]) => {
      const k = Math.max(0, Math.sin((t - flip1) * 3 + ph)), q = 18 * k;
      if (q > 1) s += `<path transform="translate(${f1(x + dx)},${f1(y + dy)})" d="M0,${-q} L${q * 0.16},${-q * 0.16} L${q},0 L${q * 0.16},${q * 0.16} L0,${q} L${-q * 0.16},${q * 0.16} L${-q},0 L${-q * 0.16},${-q * 0.16}Z" fill="#FFF3C4"/>`;
    });
  }
  return s;
}
function setRun(n) {
  if (n === 1) { useTears(TEAR1); burnAt = burn1; flameAt = flame1; springNote = () => ''; springBall = springBall1; }
  else { useTears(TEAR2); burnAt = burn2; flameAt = flame2; springNote = springNote2; springBall = springBallOrig; }
}

// ---------- En bildruta av kalender/bana i scentid (samma som scene.js renderAt, utan text) ----------
function drawScene(t) {
  const top = topPage(t), d = top + (t > TL.impact ? 2 : 0);
  const drift = 1 + 0.035 * sstep(0, 12, t);
  const shake = t > TL.impact ? Math.exp(-(t - TL.impact) * 9) * 16 : 0;
  const sx = shake * Math.sin(t * 95), sy = shake * Math.cos(t * 77);
  const push = 1 + 0.45 * eIn(prog(t, TL.revealStart, TL.revealEnd));
  const camOld = `translate(${f1(HOLE.x + sx)},${f1(HOLE.y + sy)}) scale(${(drift * push).toFixed(4)}) translate(${-HOLE.x},${-HOLE.y})`;
  let s = '';
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
  return s;
}

// ---------- Delarna ----------
function partStop(rt) {
  setRun(1);
  const t = rt - (M.stop - 0.25); // som A-forbud: slår i vid t = 0,25
  const T0 = 0.25, land = clamp(t / T0), hit = t >= T0;
  const sc = hit ? 1 + 0.06 * Math.exp(-(t - T0) * 9) * Math.cos((t - T0) * 40) : lerp(2.6, 1, eIn(land));
  const shake = hit ? Math.exp(-(t - T0) * 8) * 26 : 0, sx = shake * Math.sin(t * 90), sy = shake * Math.cos(t * 71);
  const pulse = hit ? 0.5 + 0.5 * Math.cos((t - T0) * Math.PI * 2 * 1.6) : 0;
  const flood = hit ? clamp((t - T0) / 0.12) : 0;
  return `<g transform="translate(${f1(sx)},${f1(sy)})">${drawScene(rt + OFF1)}`
    + `<rect x="-40" y="-40" width="1160" height="2000" fill="#C4111B" opacity="${(flood * (0.42 + 0.14 * pulse)).toFixed(2)}" style="mix-blend-mode:multiply"/>`
    + (hit ? alarmLights(t, pulse) : '')
    + (hit && t - T0 < 0.5 ? `<circle cx="540" cy="930" r="${f1(520 + (t - T0) * 900)}" fill="none" stroke="#FFD2CC" stroke-width="${f1(30 * (1 - (t - T0) / 0.5))}" opacity=".6"/>` : '')
    + `<g opacity="${clamp(land * 1.5).toFixed(2)}">${prohibition(540, 930, 540, sc, hit ? pulse : 0.3)}</g></g>`;
}
function partCry(tc) {
  return background(9, 80) + `<rect width="1080" height="1920" fill="#B3121B" opacity=".28" style="mix-blend-mode:multiply"/><rect width="1080" height="1920" fill="url(#redVig)"/>` + cryingGuy(tc);
}
function partPause(rt) {
  const p = rt - M.pause, k = eBack(prog(p, 0.02, 0.3));
  return `<g filter="url(#gray)">${partCry(M.pause - M.cry)}</g><rect width="1080" height="1920" fill="#06140d" opacity="${(0.55 * sstep(0, 0.15, p)).toFixed(2)}"/>`
    + `<rect width="1080" height="1920" fill="url(#scan)" opacity=".5"/>` + (k > 0.01 ? pauseIcon(540, 940, 0.9 * k) : '');
}
// Allt utom spolningen: vilken del gäller vid verklig tid rt?
function partAt(rt) {
  if (rt < M.stop - 0.25) { setRun(1); return drawScene(rt + OFF1); }
  if (rt < M.cry) return partStop(rt);
  if (rt < M.pause) return partCry(rt - M.cry);
  return partPause(rt);
}
function partRewind(rt) {
  const p = prog(rt, M.rew, M.rewEnd), e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
  const u = lerp(M.pause - 0.001, REW_TO, e); // filmen baklänges: gråten -> märket -> banan -> december -> november
  const inner = partAt(u);
  const pulse = 0.92 + 0.08 * Math.sin(rt * 18);
  return trackingSlices(inner, rt, 26) + `<rect width="1080" height="1920" fill="#0a1a12" opacity=".22"/>` + vhs(rt, 1.2)
    + rewindIcon('solid', 560, 940, pulse * eBack(prog(rt, M.rew, M.rew + 0.25)));
}
function partPlay(rt) {
  setRun(2);
  let s = drawScene(rt + OFF2);
  const p = rt - M.play;
  if (p < 0.85) {
    const k = eBack(prog(p, 0, 0.18)), fade = 1 - sstep(0.6, 0.83, p);
    s += `<g opacity="${fade.toFixed(2)}" transform="translate(560,940) scale(${(0.95 * k + 0.25 * sstep(0.6, 0.83, p)).toFixed(3)})" filter="url(#iconGlow)">
      <path d="M-120,-170 Q-120,-200 -92,-186 L170,-22 Q196,0 170,22 L-92,186 Q-120,200 -120,170Z" fill="#F8F4EC" stroke="#F8F4EC" stroke-width="20" stroke-linejoin="round"/></g>`;
  }
  return s;
}

function renderAt(rt) {
  let svg = defs() + sfDefs();
  if (rt < M.rew) svg += partAt(rt);
  else if (rt < M.rewEnd) svg += partRewind(rt);
  else svg += partPlay(rt);
  document.getElementById('svg').innerHTML = svg;
  document.getElementById('text').innerHTML = (rt >= M.rew && rt < M.rewEnd) ? '' : textLayer(rt);
}

window.SCENE = { W, H, FPS, duration: M.end, TEXTS, renderAt, M,
  ready: Promise.all([...['112px Anton', '700 28px Inter', '600 28px Inter'].map((f) => document.fonts.load(f)),
    Promise.race([new Promise((ok) => { const i = new Image(); i.src = window.GK_LOGO; i.decode().then(ok, ok); }), new Promise((ok) => setTimeout(ok, 3000))])]).then(() => document.fonts.ready) };
