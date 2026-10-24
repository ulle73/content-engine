// Renderar exemplet: befintlig film + Blender-klipp med alfa ovanpå, i Remotion.
//   node library/templates/golfkuponger-blender-3d/remotion-exempel/render.mjs <publicDir> <ut.mp4> [props.json]
// publicDir ska innehålla film.mp4 och de WebM-klipp som props.lager pekar på (standard: golfboll.webm, titel.webm).
// Remotion lånas från motion-renderer/node_modules (samma version som produktionen, ingen egen installation).
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
// motion-renderer i repot, eller i huvudutcheckningen när vi kör i en git worktree utan node_modules
const kandidater = [path.resolve(HERE, '../../../../motion-renderer'), process.env.MOTION_RENDERER].filter(Boolean);
for (let d = HERE; d !== path.dirname(d); d = path.dirname(d)) {
  if (path.basename(d) === '.claude') kandidater.push(path.join(path.dirname(d), 'motion-renderer'));
}
const MR = kandidater.find((d) => fs.existsSync(path.join(d, 'node_modules', '@remotion', 'renderer')));
if (!MR) throw new Error('Hittar inte motion-renderer/node_modules – kör npm ci i motion-renderer eller sätt MOTION_RENDERER');
const require = createRequire(path.join(MR, 'package.json'));
const { bundle } = require('@remotion/bundler');
const { renderMedia, selectComposition } = require('@remotion/renderer');

const [publicDir, ut, propsFil] = process.argv.slice(2);
if (!publicDir || !ut) throw new Error('Användning: render.mjs <publicDir> <ut.mp4> [props.json]');
const inputProps = propsFil ? JSON.parse(fs.readFileSync(propsFil, 'utf8')) : {};
// Använd motion-rendererns redan nedladdade Chrome Headless Shell – annars laddar Remotion ner en ny (113 MB) i cwd.
const shell = path.join(MR, 'node_modules', '.remotion', 'chrome-headless-shell', 'win64', 'chrome-headless-shell-win64',
  'chrome-headless-shell.exe');
const browserExecutable = process.env.REMOTION_BROWSER || (fs.existsSync(shell) ? shell : null);
if (!browserExecutable) throw new Error(`Hittar inte ${shell} – sätt REMOTION_BROWSER (ingen automatisk nedladdning)`);

const serveUrl = await bundle({
  entryPoint: path.join(HERE, 'src', 'index.jsx'),
  publicDir: path.resolve(publicDir),
  enableCaching: false,                       // ingen webpack-cache i .cache/ i arbetskatalogen
  webpackOverride: (c) => ({
    ...c,
    resolve: { ...c.resolve, modules: [path.join(MR, 'node_modules'), 'node_modules'] },
  }),
});
const composition = await selectComposition({ serveUrl, id: 'Blender3dOverlay', inputProps, browserExecutable });
await renderMedia({
  serveUrl, composition, inputProps, browserExecutable, codec: 'h264', outputLocation: path.resolve(ut),
  onProgress: ({ progress }) => process.stdout.write(`\r${Math.round(progress * 100)} %`),
});
console.log('\nKLART', path.resolve(ut));
