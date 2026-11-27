// 3D-telefon modellerad efter iPhone 18 Pro (Silver) – Apples produktbilder och tekniska specifikation (apple.com, 2026-11-25):
// 150,0 × 71,9 × 8,75 mm, aluminium-unibody, kameraplatå över hela bredden upptill (nederkant ≈ 30 % av höjden),
// tre linser med tjocka polerade ringar i triangel uppe till vänster, blixt (metallring) + mikrofon + LiDAR till höger,
// färgmatchat bakglas nedtill, Apple-loggan (formen från apple.com, assets/apple-logo.svg) spegelblank mitt på glaset.
// Ritas med three.js i en egen WebGL-duk som filmen lägger in i sin canvas. Återanvändbar modul (library/templates/
// golfkuponger-telefon3d, README.md): sätt window.T3_STORLEK = { W, H } före laddningen, rita appens skärm i T3.skarmDuk
// (620×1325 px) och anropa T3.rita(lage, vrid) per bildruta. Ursprung: work/gk-ny-app-reveal (godkänd 2026-11-25).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { SVGLoader } from 'three/addons/loaders/SVGLoader.js';

const MM = { w: 71.9, h: 150.0, d: 8.75, r: 12.2 };
const SKARM = { w: 620, h: 1325 };
const { W, H } = window.T3_STORLEK || { W: 1080, H: 1920 }, CX = W / 2, CY = H / 2;   // skärmdukens pixlar (statusrad + emulatorbild 620×1278)

// ---------- renderare och kamera (1 enhet = 1 px i bildens mitt) ----------
const duk = document.createElement('canvas'); duk.width = W; duk.height = H;
const rend = new THREE.WebGLRenderer({ canvas: duk, antialias: true, alpha: true, preserveDrawingBuffer: true });
rend.setPixelRatio(1); rend.setSize(W, H, false); rend.setClearColor(0x000000, 0);
rend.outputColorSpace = THREE.SRGBColorSpace; rend.toneMapping = THREE.ACESFilmicToneMapping; rend.toneMappingExposure = 1.0;
const scen = new THREE.Scene();
const FOV = 16, AVST = (H / 2) / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
const kam = new THREE.PerspectiveCamera(FOV, W / H, 50, AVST * 3); kam.position.set(0, 0, AVST); kam.lookAt(0, 0, 0);

// ---------- studioljus: mörk studio med softboxar (ger metallen riktiga reflexer och gradienter) ----------
function studio() {
  const s = new THREE.Scene(); s.background = new THREE.Color(0x07090a);
  const box = (w, h, styrka, pos, farg = [1, 1, 1]) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(farg[0] * styrka, farg[1] * styrka, farg[2] * styrka), side: THREE.DoubleSide }));
    m.position.set(...pos); m.lookAt(0, 0, 0); s.add(m);
  };
  box(7, 3.5, 7, [-1.5, 6, 3]);                 // stor softbox snett ovanifrån framifrån
  box(1.4, 9, 5, [-6, 0.5, 1.5]);               // smal list vänster
  box(1.4, 9, 3.5, [6, 0, -1.5], [0.85, 1, 0.93]);   // list höger bak, lätt mint
  box(6, 3, 2.4, [1.5, 2.0, 7]);                // front (syns i plana ytor rakt mot kameran)
  box(11, 6, 4.4, [-1.0, 3.2, -7]);             // stor softbox bakom (baksidan speglar den – ljust silver upptill)
  box(11, 3, 1.3, [0, -3.6, -7]);               // svagare nertill → gradient över baksidan
  box(9, 1.6, 1.0, [0, -6, 2]);                 // golvreflex
  return s;
}
const pmrem = new THREE.PMREMGenerator(rend);
scen.environment = pmrem.fromScene(studio(), 0.02).texture;
const nyckel = new THREE.DirectionalLight(0xffffff, 1.2); nyckel.position.set(-1.0, 1.6, 1.4); scen.add(nyckel);
const bakNyckel = new THREE.DirectionalLight(0xffffff, 1.0); bakNyckel.position.set(-1.0, 1.4, -1.4); scen.add(bakNyckel);

// ---------- former ----------
// rundad rektangel med mjukare "kontinuerliga" hörn (som Apples); r = [nv, nh, öh, öv] eller ett tal
function form(w, h, r) {
  const [rnv, rnh, roh, rov] = Array.isArray(r) ? r : [r, r, r, r];
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2, k = 0.38;
  s.moveTo(x + rnv, y); s.lineTo(x + w - rnh, y);
  s.bezierCurveTo(x + w - rnh * k, y, x + w, y + rnh * k, x + w, y + rnh); s.lineTo(x + w, y + h - roh);
  s.bezierCurveTo(x + w, y + h - roh * k, x + w - roh * k, y + h, x + w - roh, y + h); s.lineTo(x + rov, y + h);
  s.bezierCurveTo(x + rov * k, y + h, x, y + h - rov * k, x, y + h - rov); s.lineTo(x, y + rnv);
  s.bezierCurveTo(x, y + rnv * k, x + rnv * k, y, x + rnv, y);
  return s;
}
function plan(w, h, r, mat, z, bak = false) {
  const g = new THREE.ShapeGeometry(form(w, h, r), 40);
  const pos = g.attributes.position, uv = g.attributes.uv;
  for (let i = 0; i < pos.count; i++) uv.setXY(i, (pos.getX(i) + w / 2) / w, (pos.getY(i) + h / 2) / h);
  const m = new THREE.Mesh(g, mat); m.position.z = z; if (bak) m.rotation.y = Math.PI; return m;
}
// svarv kring lokal y-axel; profil = [[radie, höjd], …]
const svarv = (profil, mat, seg = 96) => new THREE.Mesh(new THREE.LatheGeometry(profil.map(([r, h]) => new THREE.Vector2(r, h)), seg), mat);
// liten canvas-textur med koncentriska ringar (blixtens diffusor)
function ringTextur() {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  const rg = g.createRadialGradient(128, 128, 0, 128, 128, 128); rg.addColorStop(0, '#f6f4ec'); rg.addColorStop(0.55, '#dcd9cf'); rg.addColorStop(1, '#b9b7ae');
  g.fillStyle = rg; g.fillRect(0, 0, 256, 256);
  for (let r = 14; r < 128; r += 9) { g.beginPath(); g.arc(128, 128, r, 0, Math.PI * 2); g.strokeStyle = `rgba(120,118,110,${0.25 + 0.2 * Math.sin(r)})`; g.lineWidth = 2.2; g.stroke(); }
  g.beginPath(); g.arc(128, 128, 22, 0, Math.PI * 2); g.fillStyle = '#fffbe9'; g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---------- material (Silver) ----------
const alu = new THREE.MeshPhysicalMaterial({ color: 0xe9ebed, metalness: 1, roughness: 0.34 });          // pärlblästrad aluminium
const aluPolerad = new THREE.MeshPhysicalMaterial({ color: 0xe6e8ea, metalness: 1, roughness: 0.1, side: THREE.DoubleSide });    // linsringarnas polerade kant
const svartGlas = new THREE.MeshPhysicalMaterial({ color: 0x030405, metalness: 0, roughness: 0.03, clearcoat: 1, clearcoatRoughness: 0.02 });
const bakGlas = new THREE.MeshPhysicalMaterial({ color: 0xe2e4e6, metalness: 0.75, roughness: 0.4, clearcoat: 0.6, clearcoatRoughness: 0.25 });   // färgmatchat frostat glas
const svartMatt = new THREE.MeshStandardMaterial({ color: 0x050607, roughness: 0.75, side: THREE.DoubleSide });
const tubMork = new THREE.MeshPhysicalMaterial({ color: 0x0c0d10, metalness: 0.6, roughness: 0.35, side: THREE.DoubleSide });
const linsElement = new THREE.MeshPhysicalMaterial({ color: 0x141a3a, metalness: 0.7, roughness: 0.06, clearcoat: 1, clearcoatRoughness: 0, iridescence: 0.8, iridescenceIOR: 1.6 });
const tackGlas = new THREE.MeshPhysicalMaterial({ color: 0x000000, metalness: 0, roughness: 0, clearcoat: 1, transparent: true, opacity: 0.28, depthWrite: false });

// ---------- telefonen ----------
const tel = new THREE.Group(); scen.add(tel);
const B = 2.6;   // sidornas rundning
const kroppGeo = new THREE.ExtrudeGeometry(form(MM.w - 2 * B, MM.h - 2 * B, MM.r - B), { depth: MM.d - 2 * B, bevelEnabled: true, bevelThickness: B, bevelSize: B, bevelSegments: 14, curveSegments: 48 });
kroppGeo.center(); tel.add(new THREE.Mesh(kroppGeo, alu));
const FRAM = MM.d / 2, BAK = -MM.d / 2;

// framsidan: svart glas + skärm + glans
tel.add(plan(MM.w - 0.9, MM.h - 0.9, MM.r - 0.45, svartGlas, FRAM + 0.02));
const skarmDuk = document.createElement('canvas'); skarmDuk.width = SKARM.w; skarmDuk.height = SKARM.h;
const skarmTex = new THREE.CanvasTexture(skarmDuk); skarmTex.colorSpace = THREE.SRGBColorSpace; skarmTex.anisotropy = 8;
const sw = MM.w - 3.4, sh = sw * SKARM.h / SKARM.w;
tel.add(plan(sw, sh, MM.r - 1.9, new THREE.MeshBasicMaterial({ map: skarmTex, toneMapped: false }), FRAM + 0.05));
tel.add(plan(MM.w - 1.0, MM.h - 1.0, MM.r - 0.5, new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.02, transparent: true, opacity: 0.06, depthWrite: false }), FRAM + 0.09));

// baksidan. Koordinater sett bakifrån (bx åt höger, by uppåt) → telefonens x = -bx.
const P = (bx, by) => [-bx, by];
// färgmatchat bakglas nedtill (glipa ≈ 3,5 mm under platån)
const PLAT_NED = 30.5, PLAT_TJ = 1.55;   // platåns nederkant (mm från mitten) och höjd över baksidan
const glasH = (MM.h / 2 - 3.4) + (PLAT_NED - 3.5);
const glas = plan(MM.w - 6.4, glasH, [9, 9, 4, 4], bakGlas, BAK - 0.02, true); glas.position.y = (-(MM.h / 2 - 3.4) + (PLAT_NED - 3.5)) / 2; tel.add(glas);
// kameraplatån: hela bredden, raka sidor i linje med ramen, rundade nedre hörn
const platH = MM.h / 2 - PLAT_NED - 0.4, pb = 0.9;
const platGeo = new THREE.ExtrudeGeometry(form(MM.w - 0.6 - 2 * pb, platH - 2 * pb, [8, 8, MM.r - 1.2, MM.r - 1.2]), { depth: PLAT_TJ + B * 0.55 - 2 * pb, bevelEnabled: true, bevelThickness: pb, bevelSize: pb, bevelSegments: 8, curveSegments: 40 });
platGeo.center();
const plat = new THREE.Mesh(platGeo, alu); plat.position.set(0, PLAT_NED + platH / 2, BAK - PLAT_TJ / 2 + B * 0.55 / 2); tel.add(plat);
const PZ = BAK - PLAT_TJ;   // platåns yta

// linser: tjock polerad ring i kroppens färg, svart tub, täckglas, linselement som speglar ljuset
function lins(bx, by) {
  const g = new THREE.Group(); const [x, y] = P(bx, by); g.position.set(x, y, PZ); g.rotation.x = -Math.PI / 2; tel.add(g);
  g.add(svarv([[8.7, -0.2], [8.7, 0.55], [8.55, 1.05], [8.2, 1.42], [7.6, 1.55], [7.05, 1.45], [6.85, 1.2], [6.8, 0.8]], aluPolerad));
  g.add(svarv([[6.8, 0.8], [6.8, -0.4], [0.01, -0.4]], svartMatt));
  g.add(svarv([[6.5, 0.25], [5.6, 0.35], [4.6, 0.45], [4.0, 0.5]], tubMork));
  // linselementet: låg kupol (bas r 3,9 mm vid y 0,45, topp ≈ 1,1 mm – under täckglaset)
  const KR = 12, KT = Math.asin(3.9 / KR), kupol = new THREE.Mesh(new THREE.SphereGeometry(KR, 64, 24, 0, Math.PI * 2, 0, KT), linsElement);
  kupol.position.y = 0.45 - KR * Math.cos(KT); g.add(kupol);
  const pupill = new THREE.Mesh(new THREE.CircleGeometry(1.3, 40), new THREE.MeshPhysicalMaterial({ color: 0x05060a, roughness: 0.05, clearcoat: 1 }));
  pupill.rotation.x = -Math.PI / 2; pupill.position.y = 0.45 + KR * (1 - Math.cos(KT)) + 0.01; g.add(pupill);
  const tg = new THREE.Mesh(new THREE.CircleGeometry(6.8, 64), tackGlas); tg.rotation.x = -Math.PI / 2; tg.position.y = 1.18; g.add(tg);
}
lins(-21.0, 61.0); lins(-21.0, 42.2); lins(-2.6, 51.6);
// blixt: polerad metallring + diffusor med ringar
{
  const g = new THREE.Group(); const [x, y] = P(22.0, 61.2); g.position.set(x, y, PZ); g.rotation.x = -Math.PI / 2; tel.add(g);
  g.add(svarv([[3.9, -0.2], [3.9, 0.25], [3.75, 0.45], [3.3, 0.5], [3.15, 0.35]], aluPolerad));
  const d = new THREE.Mesh(new THREE.CircleGeometry(3.15, 64), new THREE.MeshPhysicalMaterial({ map: ringTextur(), roughness: 0.25, clearcoat: 1, metalness: 0.2 }));
  d.rotation.x = -Math.PI / 2; d.position.y = 0.33; g.add(d);
}
// LiDAR: blank svart cirkel; mikrofon: litet hål
{
  const [x, y] = P(23.0, 41.6); const m = new THREE.Mesh(new THREE.CircleGeometry(3.4, 64), svartGlas); m.position.set(x, y, PZ - 0.03); m.rotation.y = Math.PI; tel.add(m);
  const [mx, my] = P(19.6, 51.4); const h = new THREE.Mesh(new THREE.CircleGeometry(0.42, 24), svartMatt); h.position.set(mx, my, PZ - 0.03); h.rotation.y = Math.PI; tel.add(h);
}
// knappar: vänster (sett framifrån) åtgärdsknapp + volym, höger sidoknapp + kamerakontroll (safirglas)
const knapp = (sida, y, len, mat = alu) => { const m = new THREE.Mesh(new RoundedBoxGeometry(1.0, len, 2.6, 3, 0.48), mat); m.position.set(sida * (MM.w / 2 + 0.2), y, 0); tel.add(m); };
knapp(-1, 41, 7); knapp(-1, 28, 12.5); knapp(-1, 13, 12.5); knapp(1, 24, 17.5);
knapp(1, -24, 11, new THREE.MeshPhysicalMaterial({ color: 0xc9ccce, metalness: 0.4, roughness: 0.08, clearcoat: 1 }));

// Apple-loggan: höjd 14,5 mm, mitt 16 mm under telefonens mitt (mätt på Apples bild av Silver-baksidan)
{
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17 48"><path d="m15.5752 19.0792a4.2055 4.2055 0 0 0 -2.01 3.5376 4.0931 4.0931 0 0 0 2.4908 3.7542 9.7779 9.7779 0 0 1 -1.2755 2.6351c-.7941 1.1431-1.6244 2.2862-2.8878 2.2862s-1.5883-.734-3.0443-.734c-1.42 0-1.9252.7581-3.08.7581s-1.9611-1.0589-2.8876-2.3584a11.3987 11.3987 0 0 1 -1.9373-6.1487c0-3.61 2.3464-5.523 4.6566-5.523 1.2274 0 2.25.8062 3.02.8062.734 0 1.8771-.8543 3.2729-.8543a4.3778 4.3778 0 0 1 3.6822 1.841zm-6.8586-2.0456a1.3865 1.3865 0 0 1 -.2527-.024 1.6557 1.6557 0 0 1 -.0361-.337 4.0341 4.0341 0 0 1 1.0228-2.5148 4.1571 4.1571 0 0 1 2.7314-1.4078 1.7815 1.7815 0 0 1 .0361.373 4.1487 4.1487 0 0 1 -.9867 2.587 3.6039 3.6039 0 0 1 -2.5148 1.3236z"/></svg>';   // = assets/apple-logo.svg (fetch fungerar inte för file://)
  const former = new SVGLoader().parse(svg).paths.flatMap(p => SVGLoader.createShapes(p));
  const geo = new THREE.ShapeGeometry(former, 24); geo.computeBoundingBox();
  const bb = geo.boundingBox, hoj = bb.max.y - bb.min.y, sk = 14.5 / hoj;
  geo.translate(-(bb.min.x + bb.max.x) / 2, -(bb.min.y + bb.max.y) / 2, 0);
  const logga = new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({ color: 0xf4f5f6, metalness: 0.55, roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.05, side: THREE.DoubleSide }));
  logga.scale.set(sk, -sk, 1);            // SVG har y nedåt
  logga.rotation.y = Math.PI; logga.position.set(0, -16, BAK - 0.05); tel.add(logga);
}

// ---------- API för telefon.js ----------
// lage: { x, y (överkant, px), w (bredd, px) }, vrid: { rx, ry, rz, skala, z, dx, dy (px), axel: [x,y,z], vinkel }
window.T3 = {
  duk, skarmDuk, SKARM,
  rita(lage, vrid) {
    const s = lage.w / MM.w * (vrid.skala || 1), cyPx = lage.y + MM.h * lage.w / MM.w / 2;
    tel.scale.setScalar(s);
    tel.position.set(lage.x + (vrid.dx || 0) - CX, -(cyPx + (vrid.dy || 0) - CY), vrid.z || 0);
    tel.rotation.set(vrid.rx || 0, vrid.ry || 0, vrid.rz || 0, 'YXZ');
    if (vrid.axel && vrid.vinkel) tel.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(...vrid.axel).normalize(), vrid.vinkel));
    skarmTex.needsUpdate = true;
    rend.render(scen, kam);
    return duk;
  },
  // punkt i skärmduken (px) → bildens px, med telefonens läge från senaste rita()
  projicera(u, v) {
    tel.updateMatrixWorld();
    const q = new THREE.Vector3((u / SKARM.w - 0.5) * sw, (0.5 - v / SKARM.h) * sh, FRAM + 0.05).applyMatrix4(tel.matrixWorld).project(kam);
    return [(q.x + 1) / 2 * W, (1 - q.y) / 2 * H];
  },
};
