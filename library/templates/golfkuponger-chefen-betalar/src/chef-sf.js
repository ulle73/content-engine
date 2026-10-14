// Stilbilder för "Låt chefen betala din golf".
'use strict';
const D2 = () => defs() + sfDefs() + `<defs>${tourleifDefs()}${chefenDefs()}${chefDefs()}</defs>`;
const CF = {
  '1-dorr'(t) {
    return { svg: D2() + doorScene(t) + tourleif(t, { expr: 'lurig', x: 300, y: 1000, s: 0.7 }),
      html: tblock(['LÅT CHEFEN', 'BETALA {DIN GOLF.}'], 124, '#F8F4EC', '#F3D27A', '#082f27') };
  },
  '2-kontor'(t) {
    return { svg: D2() + office(t, 'ovetande') + tourleif(t + 0.2, { expr: 'blinkar', x: 210, y: 1170, s: 0.55 }),
      html: tblock(['CHEFEN VET BARA', 'INTE OM DET ÄN.'], 116, '#F8F4EC', '#F3D27A', '#082f27') };
  },
  '3-mobil'(t) {
    return { svg: D2() + wall(t) + goldDust(t) + phone(470, 960, 380, 0, 1) + pdfIcon(850, 1150, 1.1, 14),
      html: tblock(['INGEN PORTAL? KÖP DIREKT.', 'KVITTOT KOMMER {SOM PDF.}'], 92, '#F8F4EC', '#F3D27A', '#082f27') };
  },
  '4-stampel'(t) {
    return { svg: D2() + office(t, 'nojd') + receipt(540, 1230, 0.8, -4) + stamp(540, 1190, 1),
      html: tblock(['LÄMNA KVITTOT', 'TILL {CHEFEN.}'], 124, '#F8F4EC', '#F3D27A', '#082f27') };
  },
  '5-golf'(t) {
    const kn = springNote, kb = springBall; springNote = () => ''; springBall = () => '';
    const course = spring(15.5); springNote = kn; springBall = kb;
    return { svg: D2() + course + chefen(t, { expr: 'nojd', x: 280, y: 1080, s: 0.42, cap: true }) + tourleif(t, { expr: 'jublar', x: 660, y: 1010, s: 0.6 }),
      html: tblock(['FRISKVÅRDSBIDRAGET:', 'CHEFEN BETALAR.', '{DU SPELAR.}'], 112, '#082f27', '#082f27', '#F8F4EC', 300, false) };
  },
};
window.SF = { names: Object.keys(CF), render(n, t = 1) { const f = CF[n](t); document.getElementById('svg').innerHTML = f.svg; document.getElementById('text').innerHTML = f.html; },
  ready: Promise.all([...['112px Anton', '700 28px Inter', '600 28px Inter'].map((x) => document.fonts.load(x)),
    Promise.race([new Promise((ok) => { const i = new Image(); i.src = window.GK_LOGO; i.decode().then(ok, ok); }), new Promise((ok) => setTimeout(ok, 3000))]),
    ...[0, 1, 2].map((i) => new Promise((ok) => { const im = new Image(); im.onload = ok; im.onerror = ok; im.src = `assets/site/site-${i}.png`; }))]).then(() => document.fonts.ready) };
