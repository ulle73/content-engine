// Playwright loader + browser launcher shared by every tool (content-engine adaptation, Windows-first).
//
// Where Playwright comes from (first hit wins):
//   1. normal Node resolution from this skill (a node_modules beside or above it)
//   2. <repo>/work/animate/node_modules/playwright   (setup.ps1 installs it there: local, gitignored, no global install)
//   3. ANIMATE_PLAYWRIGHT=<path to a playwright package folder>
//   4. the global npm root (the upstream skill's `npm i -g playwright`)
//
// Which browser runs the pages:
//   default        the system Chrome (no 150 MB Chromium download): ANIMATE_CHROME=<chrome.exe> or the usual install paths
//   fallback       Playwright's own Chromium, when no system Chrome is found or it fails to launch
//   ANIMATE_BROWSER=bundled forces Playwright's Chromium (`npx playwright install chromium` first)
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
export const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// the repo this skill sits in when it lives at <repo>/.claude/skills/animate
export const REPO = path.resolve(SKILL, '..', '..', '..');
export const WORK = path.join(REPO, 'work', 'animate');

function loadPlaywright() {
  const tries = [
    () => require('playwright'),
    () => require(path.join(WORK, 'node_modules', 'playwright')),
    () => (process.env.ANIMATE_PLAYWRIGHT ? require(path.resolve(process.env.ANIMATE_PLAYWRIGHT)) : null),
    () => require(path.join(execSync('npm root -g', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(), 'playwright')),
  ];
  for (const t of tries) { try { const m = t(); if (m) return m; } catch { /* next */ } }
  console.error('Playwright not found. Install it locally (no browser download needed, the system Chrome is used):\n' +
    '  powershell -ExecutionPolicy Bypass -File .claude/skills/animate/setup.ps1\n' +
    'or: npm i -D playwright --prefix work/animate   (with PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1)');
  process.exit(1);
}
export const playwright = loadPlaywright();
export const { chromium } = playwright;

export function findChrome() {
  const env = process.env.ANIMATE_CHROME || process.env.CHROME_PATH;
  if (env && fs.existsSync(env)) return env;
  const c = process.platform === 'win32'
    ? [process.env.PROGRAMFILES, process.env['PROGRAMFILES(X86)'], process.env.LOCALAPPDATA].filter(Boolean).map((d) => path.join(d, 'Google', 'Chrome', 'Application', 'chrome.exe'))
    : process.platform === 'darwin'
      ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
      : ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  return c.find((p) => fs.existsSync(p)) || null;
}

let said = false;
// chromium.launch() with the system Chrome by default; same options as Playwright's launch()
export async function launch(opts = {}) {
  const want = (process.env.ANIMATE_BROWSER || 'chrome').toLowerCase();
  const exe = want === 'bundled' ? null : findChrome();
  if (exe) {
    try {
      const b = await chromium.launch({ ...opts, executablePath: exe });
      if (!said && process.env.ANIMATE_QUIET !== '1') { said = true; console.error(`browser: system Chrome ${b.version()} (${exe})`); }
      return b;
    } catch (e) {
      console.error(`system Chrome failed to launch (${String(e.message).split('\n')[0]}); trying Playwright's Chromium`);
    }
  }
  return chromium.launch(opts);
}
