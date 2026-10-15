// Riktigt köpflöde på golfkuponger.se i mobilvy, för filmens mobilskärm. Trycker ALDRIG på Betala, fyller bara "Tourleif".
import { launch } from '../../.claude/skills/animate/tools/pw.mjs';
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url)), OUT = path.join(HERE, 'src', 'assets', 'flow');
fs.mkdirSync(OUT, { recursive: true });
const geo = {};
const b = await launch(); const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'sv-SE' });
const p = await ctx.newPage();
await p.goto('https://golfkuponger.se', { waitUntil: 'networkidle' });
for (const name of ['Avslå', 'Avvisa', 'Neka']) { const btn = p.getByRole('button', { name }); if (await btn.count()) { await btn.first().click(); break; } }
await p.waitForTimeout(1200);
// dölj chattbubblan "Hjälp" (inte en del av flödet)
await p.addStyleTag({ content: '[id*="chat" i],[class*="chat" i],[id*="help" i] iframe{display:none!important}' });
await p.screenshot({ path: path.join(OUT, 'home-full.png'), fullPage: true });
const yellow = p.getByRole('link', { name: /Använd friskvårdsbidraget/i }).first();
geo.yellow = await yellow.boundingBox();
geo.homeScroll0 = await p.evaluate(() => scrollY);
await yellow.click(); await p.waitForTimeout(2500);
geo.afterYellowUrl = p.url(); geo.afterYellowScroll = await p.evaluate(() => scrollY);
await p.screenshot({ path: path.join(OUT, 'packages-view.png') });
const buy = p.getByRole('button', { name: /Köp nu/i }).or(p.getByRole('link', { name: /Köp nu/i }));
const n = await buy.count(); geo.buyCount = n;
// den synliga "Köp nu" (populäraste kortet i mitten)
let target = null;
for (let i = 0; i < n; i++) { const bb = await buy.nth(i).boundingBox(); if (bb && bb.x > 40 && bb.x + bb.width < 350 && bb.y > 0 && bb.y < 844) { target = buy.nth(i); geo.buy = bb; break; } }
await p.screenshot({ path: path.join(OUT, 'packages-full.png'), fullPage: true });
if (target) { await target.click(); await p.waitForTimeout(5000); }
geo.checkoutUrl = p.url();
await p.screenshot({ path: path.join(OUT, 'checkout-0.png'), fullPage: true });
const first = p.getByLabel(/Förnamn/i).first();
if (await first.count()) {
  geo.first = await first.boundingBox(); geo.firstScroll = await p.evaluate(() => scrollY);
  await first.scrollIntoViewIfNeeded(); await first.click();
  const name = 'Tourleif';
  for (let i = 1; i <= name.length; i++) { await p.keyboard.type(name[i - 1]); await p.waitForTimeout(120); await p.screenshot({ path: path.join(OUT, `checkout-type-${i}.png`), fullPage: true }); }
  geo.firstAfter = await first.boundingBox(); geo.scrollAfter = await p.evaluate(() => scrollY);
}
const pay = p.getByRole('button', { name: /Betala/i }).first();
if (await pay.count()) { geo.pay = await pay.boundingBox(); geo.payText = await pay.innerText(); }
geo.docH = await p.evaluate(() => document.documentElement.scrollHeight);
fs.writeFileSync(path.join(OUT, 'geo.json'), JSON.stringify(geo, null, 1));
await b.close(); console.log(JSON.stringify(geo, null, 1));
