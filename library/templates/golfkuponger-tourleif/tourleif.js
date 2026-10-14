// Tourleif – Golfkupongers återkommande tecknade figur (Jonas 2026-10-13: "spara honom så vi alltid använder honom").
// Grön golfkeps med Golfkupongers RIKTIGA logga (symbol #gklogo, byggd från logo-final.png – aldrig AI), grön piké med
// krämvit krage, varm hudton. Ritas som SVG i 1080×1920-koordinater med huvudets mitt i (540, 890) i normalskala.
//
//   tourleif(t, { expr: 'glad' | 'jublar' | 'forvanad' | 'grat' | 'lurig' | 'blinkar', x: 540, y: 860, s: 1 })
//
// t = sekunder (blinkningar, snyftningar, tårflöde är deterministiska). Kräver i sidan:
//   <svg width="0" height="0"><defs><symbol id="gklogo" viewBox="0 0 960 912"><image id="gklogoImg" width="960" height="912"/></symbol></defs></svg>
//   + logo-data.js (window.GK_LOGO) och tourleifDefs() i svg:ens <defs>. Se sheet.html.
'use strict';

function tourleifDefs() {
  return `<linearGradient id="tlCap" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1B7552"/><stop offset="1" stop-color="#0C4A33"/></linearGradient>
  <radialGradient id="tlSkin" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#F7D3AE"/><stop offset="1" stop-color="#E2AA80"/></radialGradient>
  <linearGradient id="tlGold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBE7A1"/><stop offset=".45" stop-color="#D9AC4A"/><stop offset="1" stop-color="#8E6420"/></linearGradient>
  <linearGradient id="tlShirtLight" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".14"/><stop offset="1" stop-color="#000" stop-opacity=".12"/></linearGradient>
  <linearGradient id="tlTear" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#BFE8FF"/><stop offset="1" stop-color="#4FA8E8"/></linearGradient>`;
}

function tourleif(t, o = {}) {
  const expr = o.expr || 'glad', x = o.x ?? 540, y = o.y ?? 860, sc = o.s ?? 1;
  const f = (n) => n.toFixed(1);
  const bounce = expr === 'jublar' ? Math.abs(Math.sin(t * 6)) * 14 : expr === 'grat' ? Math.abs(Math.sin(t * 7)) * 8 : Math.sin(t * 2) * 2;
  const tilt = expr === 'grat' ? Math.sin(t * 3.5) * 1.5 : expr === 'jublar' ? Math.sin(t * 6) * 2 : 0;
  const blink = expr === 'glad' || expr === 'forvanad' ? ((t % 3.2) > 3.05 ? 0.12 : 1) : 1;
  let s = `<g transform="translate(${f(x)},${f(y)}) scale(${sc}) translate(-540,-860)">`;
  if (expr === 'grat') s += `<ellipse cx="240" cy="1290" rx="160" ry="28" fill="#6DBBEF" opacity=".75"/><ellipse cx="840" cy="1290" rx="160" ry="28" fill="#6DBBEF" opacity=".75"/>`;
  // kropp: piké med krage och knappar
  s += `<g transform="translate(0,${f(bounce * 0.5)})"><path d="M240,1340 C250,1185 380,1128 540,1128 C700,1128 830,1185 840,1340Z" fill="#1F6B4B"/>
    <path d="M240,1340 C250,1185 380,1128 540,1128 C700,1128 830,1185 840,1340Z" fill="url(#tlShirtLight)"/>
    <path d="M468,1128 L540,1205 L612,1128Z" fill="#F8F4EC"/><path d="M540,1205 L540,1300" stroke="#0f4a33" stroke-width="5"/>
    <circle cx="540" cy="1232" r="6" fill="#F8F4EC"/><circle cx="540" cy="1268" r="6" fill="#F8F4EC"/></g>`;
  s += `<g transform="translate(0,${f(bounce)}) rotate(${f(tilt)} 540 900)">`;
  s += `<rect x="498" y="1080" width="84" height="70" rx="22" fill="#DFA67C"/>
    <circle cx="342" cy="905" r="44" fill="#E9B78E"/><circle cx="738" cy="905" r="44" fill="#E9B78E"/>
    <ellipse cx="540" cy="890" rx="200" ry="235" fill="url(#tlSkin)"/>`;
  // kepsen med Golfkupongers logga
  s += `<path d="M334,818 C328,646 438,598 540,598 C642,598 752,646 746,818 Q540,792 334,818Z" fill="url(#tlCap)"/>
    <path d="M540,600 L540,640 M440,612 Q420,700 412,808 M640,612 Q660,700 668,808" stroke="#0a3f2c" stroke-width="3.5" fill="none" opacity=".55"/>
    <circle cx="540" cy="600" r="11" fill="url(#tlGold)"/>
    <use href="#gklogo" x="462" y="640" width="156" height="148"/>
    <ellipse cx="540" cy="872" rx="190" ry="20" fill="#2a1a0e" opacity=".22"/>
    <path d="M314,816 Q540,784 766,816 Q776,852 540,866 Q304,852 314,816Z" fill="#0B4430"/>
    <path d="M318,818 Q540,788 762,818" stroke="#2d7a5a" stroke-width="4" fill="none"/>`;
  // kinder och näsa (alla uttryck)
  const cheeks = `<ellipse cx="398" cy="990" rx="42" ry="24" fill="#EF8A76" opacity="${expr === 'forvanad' ? 0.3 : 0.5}"/><ellipse cx="682" cy="990" rx="42" ry="24" fill="#EF8A76" opacity="${expr === 'forvanad' ? 0.3 : 0.5}"/>
    <path d="M532,932 Q548,974 526,984" stroke="#C98B62" stroke-width="7" fill="none" stroke-linecap="round"/>`;
  const openEyes = (big) => [452, 628].map((ex) => `<ellipse cx="${ex}" cy="912" rx="${big ? 30 : 26}" ry="${f((big ? 36 : 30) * blink)}" fill="#fff" stroke="#3a2412" stroke-width="4"/>
      ${blink > 0.5 ? `<circle cx="${ex + 3}" cy="915" r="${big ? 11 : 14}" fill="#2b1a10"/><circle cx="${ex + 8}" cy="909" r="4" fill="#fff"/>` : ''}`).join('');
  if (expr === 'glad') {
    s += `<g stroke="#3a2412" stroke-linecap="round" fill="none"><path d="M405,862 Q452,846 500,858" stroke-width="13"/><path d="M675,862 Q628,846 580,858" stroke-width="13"/></g>
      ${openEyes(false)}${cheeks}
      <path d="M462,1010 Q540,1080 618,1010 Q540,1042 462,1010Z" fill="#5B1717"/><path d="M478,1014 Q540,1036 602,1014 L598,1024 Q540,1044 482,1024Z" fill="#fff"/>`;
  } else if (expr === 'jublar') {
    s += `<g stroke="#3a2412" stroke-linecap="round" fill="none"><path d="M400,848 Q452,822 505,838" stroke-width="14"/><path d="M680,848 Q628,822 575,838" stroke-width="14"/>
      <path d="M410,922 Q452,892 500,922" stroke-width="13"/><path d="M670,922 Q628,892 580,922" stroke-width="13"/></g>${cheeks}
      <path d="M440,1000 Q540,1000 640,1000 Q630,1110 540,1118 Q450,1110 440,1000Z" fill="#5B1717"/>
      <path d="M452,1002 L628,1002 L622,1024 Q540,1032 458,1024Z" fill="#fff"/><ellipse cx="540" cy="1090" rx="52" ry="20" fill="#E2656B"/>`;
  } else if (expr === 'forvanad') {
    s += `<g stroke="#3a2412" stroke-linecap="round" fill="none"><path d="M405,846 Q452,816 500,836" stroke-width="13"/><path d="M675,846 Q628,816 580,836" stroke-width="13"/></g>
      ${openEyes(true)}${cheeks}<ellipse cx="540" cy="1050" rx="34" ry="42" fill="#5B1717"/><ellipse cx="540" cy="1072" rx="20" ry="10" fill="#E2656B"/>`;
  } else if (expr === 'lurig') {
    s += `<g stroke="#3a2412" stroke-linecap="round" fill="none"><path d="M405,872 Q452,860 500,868" stroke-width="13"/><path d="M580,848 Q628,820 675,840" stroke-width="13"/></g>
      <ellipse cx="452" cy="918" rx="26" ry="15" fill="#fff" stroke="#3a2412" stroke-width="4"/><ellipse cx="628" cy="912" rx="26" ry="21" fill="#fff" stroke="#3a2412" stroke-width="4"/>
      <path d="M424,906 Q452,898 480,906" stroke="#3a2412" stroke-width="6" fill="none"/>
      <circle cx="468" cy="920" r="11" fill="#2b1a10"/><circle cx="644" cy="914" r="12" fill="#2b1a10"/>${cheeks}
      <path d="M468,1032 Q560,1064 624,1000" stroke="#5B1717" stroke-width="11" fill="none" stroke-linecap="round"/>`;
  } else if (expr === 'blinkar') {
    const w = Math.max(0, Math.sin(Math.min(1, (t % 2) / 0.35) * Math.PI));
    s += `<g stroke="#3a2412" stroke-linecap="round" fill="none"><path d="M405,862 Q452,846 500,858" stroke-width="13"/><path d="M580,${f(864 + 12 * w)} Q628,${f(850 + 12 * w)} 675,${f(866 + 12 * w)}" stroke-width="13"/></g>
      <ellipse cx="452" cy="912" rx="26" ry="30" fill="#fff" stroke="#3a2412" stroke-width="4"/><circle cx="455" cy="915" r="14" fill="#2b1a10"/><circle cx="460" cy="909" r="4" fill="#fff"/>
      ${w > 0.5 ? `<path d="M602,914 Q628,932 654,914" stroke="#3a2412" stroke-width="9" fill="none" stroke-linecap="round"/>`
        : `<ellipse cx="628" cy="912" rx="26" ry="${f(30 * (1 - w))}" fill="#fff" stroke="#3a2412" stroke-width="4"/><circle cx="631" cy="915" r="${f(14 * (1 - w))}" fill="#2b1a10"/>`}${cheeks}
      <path d="M468,1022 Q550,1072 624,1008" stroke="#5B1717" stroke-width="11" fill="none" stroke-linecap="round"/>`;
  } else { // grat
    const flow = (t * 220) % 120;
    s += `<g stroke="#3a2412" stroke-linecap="round" fill="none">
      <path d="M400,884 Q452,872 505,848" stroke-width="15"/><path d="M680,884 Q628,872 575,848" stroke-width="15"/>
      <path d="M410,918 Q452,890 500,920" stroke-width="13"/><path d="M670,918 Q628,890 580,920" stroke-width="13"/>
      <path d="M420,936 Q452,950 490,936" stroke-width="6" opacity=".5"/><path d="M660,936 Q628,950 590,936" stroke-width="6" opacity=".5"/></g>${cheeks}
      <path d="M452,1012 Q540,980 628,1012 Q656,1098 540,1112 Q424,1098 452,1012Z" fill="#5B1717"/>
      <path d="M464,1014 Q540,990 616,1014 L610,1032 Q540,1012 470,1032Z" fill="#fff"/><ellipse cx="540" cy="1088" rx="56" ry="20" fill="#E2656B"/>`;
    for (const dir of [-1, 1]) {
      const x0 = 540 + dir * 128, y0 = 918;
      const d = `M${x0},${y0} C${x0 + dir * 110},${y0 - 60} ${x0 + dir * 235},${y0 - 10} ${x0 + dir * 300},${y0 + 360}`;
      s += `<path d="${d}" stroke="url(#tlTear)" stroke-width="34" fill="none" stroke-linecap="round" opacity=".95"/>
        <path d="${d}" stroke="#E6F7FF" stroke-width="8" fill="none" stroke-dasharray="30 90" stroke-dashoffset="${-flow}" stroke-linecap="round" opacity=".8"/>`;
      for (let i = 0; i < 7; i++) {
        const r1 = ((i * 0.618 + (dir > 0 ? 0.3 : 0.7)) % 1), life = ((t * 1.6 + r1) % 1);
        const bx = x0 + dir * (150 + r1 * 170) + dir * life * 40, by = y0 + 70 + life * 300 + r1 * 40, z = 0.6 + ((i * 0.37) % 1) * 0.8;
        s += `<path transform="translate(${f(bx)},${f(by)}) scale(${z.toFixed(2)})" d="M0,-16 C9,-4 12,4 12,8 C12,16 -12,16 -12,8 C-12,4 -9,-4 0,-16Z" fill="#8FD0FF"/>`;
      }
    }
  }
  return s + '</g></g>';
}

if (typeof window !== 'undefined') window.TOURLEIF = { tourleif, tourleifDefs, expressions: ['glad', 'jublar', 'forvanad', 'grat', 'lurig', 'blinkar'] };
