// Stillbilder ur demo.html (förhandsbild till biblioteket eller kontroll av en ny rörelse).
//   node library/templates/golfkuponger-telefon3d/still.mjs <url till demo.html> <ut.jpg> [t] [format 9x16|16x9|4x5]
// Sidan måste serveras över http (ES-moduler laddas inte från file://), t.ex. preview-servern "telefon3d" i
// .claude/launch.json eller: python -m http.server 8767 --directory library/templates/golfkuponger-telefon3d
import { launch } from '../../../.claude/skills/animate/tools/pw.mjs';

const [url, ut, t = '2.2', format = '9x16'] = process.argv.slice(2);
if (!url || !ut) { console.error('användning: node still.mjs <url> <ut.jpg> [t] [format]'); process.exit(1); }
const [W, H] = { '9x16': [1080, 1920], '16x9': [1920, 1080], '4x5': [1080, 1350] }[format];
const browser = await launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.goto(`${url}${url.includes('?') ? '&' : '?'}t=${t}&format=${format}`);
await page.waitForFunction(() => document.title === 'klar', null, { timeout: 30000 });
await page.locator('#film').screenshot({ path: ut, type: 'jpeg', quality: 86 });
await browser.close();
console.log(`stillbild: ${ut} (t=${t}, ${format})`);
