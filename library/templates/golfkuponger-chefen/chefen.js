// Chefen – Tourleifs återkommande motspelare (Jonas 2026-10-13/14, "Låt chefen betala din golf").
// Flint med gråa tinningar, glasögon, mustasch, marinblå kavaj, vit skjorta, grön slips. Tecknad premiumstil.
//
//   chefen(t, { expr: 'ovetande' | 'skeptisk' | 'nojd', x: 540, y: 860, s: 1, cap: false, mug: true, thumbK: 1, thumbY: 1230 })
//
// Kräver chefenDefs() i svg:ens <defs>; med cap: true även tourleifDefs() (#tlCap) och loggsymbolen #gklogo (se tourleif-modulen).
'use strict';

function chefenDefs() {
  return `<linearGradient id="blazer" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#26385A"/><stop offset="1" stop-color="#16223A"/></linearGradient>
  <radialGradient id="bossSkin" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#F3CBA5"/><stop offset="1" stop-color="#D99E76"/></radialGradient>`;
}

// expr: 'ovetande' (dricker kaffe, nöjd i sin värld), 'skeptisk' (ett ögonbryn upp, läser), 'nojd' (ler, tummen upp)
function chefen(t, o = {}) {
  const expr = o.expr || 'ovetande', x = o.x ?? 540, y = o.y ?? 860, sc = o.s ?? 1, f = (n) => n.toFixed(1);
  const bob = Math.sin(t * 1.8) * 2;
  let s = `<g transform="translate(${f(x)},${f(y + bob)}) scale(${sc}) translate(-540,-860)">`;
  // kavaj, skjorta, slips
  s += `<path d="M220,1360 C232,1190 370,1120 540,1120 C710,1120 848,1190 860,1360Z" fill="url(#blazer)"/>
    <path d="M462,1120 L540,1290 L618,1120Z" fill="#F8F4EC"/>
    <path d="M520,1150 L560,1150 L572,1300 L540,1330 L508,1300Z" fill="#0F5A3E"/><path d="M522,1138 L558,1138 L552,1160 L528,1160Z" fill="#0B4430"/>
    <path d="M462,1120 L505,1250 L470,1235 L430,1140Z" fill="#1c2b47"/><path d="M618,1120 L575,1250 L610,1235 L650,1140Z" fill="#1c2b47"/>
    <rect x="502" y="1070" width="76" height="66" rx="20" fill="#D59A72"/>`;
  // huvud: flint, grå tinningar, öron
  s += `<circle cx="352" cy="905" r="40" fill="#E2A985"/><circle cx="728" cy="905" r="40" fill="#E2A985"/>
    <ellipse cx="540" cy="890" rx="192" ry="225" fill="url(#bossSkin)"/>
    <path d="M352,860 C350,770 380,720 410,700 C392,760 392,820 400,880Z" fill="#B8BCC0"/><path d="M728,860 C730,770 700,720 670,700 C688,760 688,820 680,880Z" fill="#B8BCC0"/>
    <ellipse cx="500" cy="720" rx="60" ry="26" fill="#fff" opacity=".25"/>`;
  // ögonbryn, glasögon, ögon
  const browL = expr === 'skeptisk' ? 'M408,818 Q452,770 500,800' : expr === 'nojd' ? 'M410,826 Q452,806 500,818' : 'M410,834 Q452,824 500,830';
  const browR = expr === 'skeptisk' ? 'M672,838 Q628,834 580,840' : expr === 'nojd' ? 'M670,826 Q628,806 580,818' : 'M670,834 Q628,824 580,830';
  s += `<g stroke="#8E9296" stroke-width="15" stroke-linecap="round" fill="none"><path d="${browL}"/><path d="${browR}"/></g>`;
  if (expr === 'ovetande' || expr === 'nojd') {
    s += `<g stroke="#2b1a10" stroke-width="10" stroke-linecap="round" fill="none"><path d="M425,892 Q455,872 485,892"/><path d="M595,892 Q625,872 655,892"/></g>`;
  } else {
    s += `<ellipse cx="455" cy="892" rx="22" ry="18" fill="#fff"/><ellipse cx="625" cy="892" rx="22" ry="12" fill="#fff"/>
      <circle cx="455" cy="898" r="10" fill="#2b1a10"/><circle cx="625" cy="896" r="9" fill="#2b1a10"/>`;
  }
  s += `<g fill="none" stroke="#1d1d1d" stroke-width="8"><rect x="402" y="852" width="106" height="82" rx="26"/><rect x="572" y="852" width="106" height="82" rx="26"/><path d="M508,886 Q540,872 572,886"/></g>
    <rect x="408" y="858" width="94" height="70" rx="22" fill="#fff" opacity=".12"/><rect x="578" y="858" width="94" height="70" rx="22" fill="#fff" opacity=".12"/>`;
  // näsa, mustasch, mun
  s += `<path d="M532,930 Q556,980 526,992" stroke="#C0845E" stroke-width="8" fill="none" stroke-linecap="round"/>
    <path d="M462,1012 Q500,990 540,1006 Q580,990 618,1012 Q585,1030 540,1020 Q495,1030 462,1012Z" fill="#9EA3A8"/>`;
  if (expr === 'nojd') s += `<path d="M476,1036 Q540,1092 604,1036 Q540,1064 476,1036Z" fill="#5B1717"/><path d="M490,1040 Q540,1060 590,1040 L586,1050 Q540,1068 494,1050Z" fill="#fff"/>`;
  else if (expr === 'skeptisk') s += `<path d="M500,1050 Q540,1040 585,1056" stroke="#5B1717" stroke-width="9" fill="none" stroke-linecap="round"/>`;
  else s += `<path d="M498,1046 Q540,1060 582,1046" stroke="#5B1717" stroke-width="9" fill="none" stroke-linecap="round"/>`;
  if (o.cap) s += `<path d="M352,818 C346,660 445,612 540,612 C635,612 734,660 728,818 Q540,792 352,818Z" fill="url(#tlCap)"/>
    <use href="#gklogo" x="466" y="650" width="148" height="140"/><path d="M332,816 Q540,786 748,816 Q756,850 540,862 Q324,850 332,816Z" fill="#0B4430"/>`;
  // tummen upp
  if (expr === 'nojd' && o.thumb !== false) {
    const k = o.thumbK ?? 1;
    s += `<g transform="translate(790,${o.thumbY ?? 1230}) rotate(${f(-10 * k)}) scale(${(0.6 + 0.4 * k).toFixed(2)})">
      <path d="M-70,40 L-70,-40 Q-70,-60 -50,-60 L40,-60 Q60,-60 60,-40 L60,40 Q60,60 40,60 L-50,60 Q-70,60 -70,40Z" fill="#E2A985"/>
      <path d="M-20,-60 L-20,-150 Q-20,-178 4,-178 Q28,-178 28,-150 L28,-60Z" fill="#E2A985"/>
      <path d="M-70,-28 L60,-28 M-70,6 L60,6 M-70,38 L60,38" stroke="#C0845E" stroke-width="5"/>
      <rect x="-82" y="40" width="152" height="70" rx="10" fill="url(#blazer)"/></g>`;
  }
  if (expr === 'ovetande' && o.mug !== false) {
    const lift = (Math.sin(t * 1.4) + 1) / 2;
    s += `<g transform="translate(700,${f(1150 - 120 * lift)})"><rect x="-55" y="-70" width="110" height="130" rx="18" fill="#F8F4EC"/><rect x="-55" y="-30" width="110" height="22" fill="#0F5A3E"/>
      <path d="M55,-40 C100,-40 100,30 55,30" stroke="#F8F4EC" stroke-width="16" fill="none"/>
      <path d="M-20,-90 C-30,-120 0,-130 -10,-160 M15,-90 C5,-120 35,-130 25,-160" stroke="#fff" stroke-width="6" fill="none" opacity="${(0.5 * (1 - lift)).toFixed(2)}" stroke-linecap="round"/></g>`;
  }
  return s + '</g>';
}


if (typeof window !== 'undefined') window.CHEFEN = { chefen, chefenDefs, expressions: ['ovetande', 'skeptisk', 'nojd'] };
