// Hämtar Apples egna resurser till en lokal cache och kopierar dem in i mallen (assets/ är gitignorerat).
// Repot är publikt: inga Apple-filer får committas. Jonas beslut 2026-11-12: Apples typsnitt, emoji och ljud exakt.
//
//   SF Pro Text/Display  – Apples officiella paket (developer.apple.com/fonts), packas upp med 7-Zip
//   Apple Color Emoji    – macOS 26-emojin som TTF (github.com/samuelngs/apple-emoji-ttf), delmängd per film
//   SentMessage/ReceivedMessage + tangentbordsklick (key_press_*) – iOS UISounds (github.com/extratone/iOSSystemSounds), omvandlade till wav
//   iphone-17.png        – Jonas telefonram (ingen nedladdning; ligger i cachen eller i Downloads)
//
// Cache: $IMESSAGE_CACHE eller ~/.cache/imessage-mall. Körs av build.mjs; kan också köras separat: node apple-resurser.mjs
import {access, copyFile, mkdir, readFile, rm, writeFile, readdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {homedir, tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';

const here = new URL('./', import.meta.url);
const CACHE = process.env.IMESSAGE_CACHE || join(homedir(), '.cache', 'imessage-mall');
const SF_DMG = 'https://devimages-cdn.apple.com/design/resources/download/SF-Pro.dmg';
const EMOJI_TTF = 'https://github.com/samuelngs/apple-emoji-ttf/releases/download/macos-26-20260722-484daf4e/AppleColorEmoji-Linux.ttf';
const SOUNDS = 'https://raw.githubusercontent.com/extratone/iOSSystemSounds/04048879c4b16f2372009e1a1d75207647ce16da/caf/';
const FONTS = ['SF-Pro-Text-Regular.otf', 'SF-Pro-Text-Medium.otf', 'SF-Pro-Text-Semibold.otf', 'SF-Pro-Display-Regular.otf', 'SF-Pro-Display-Semibold.otf'];
const SOUND_NAMES = ['SentMessage', 'ReceivedMessage', 'key_press_click', 'key_press_delete', 'key_press_modifier', 'Tritone', 'Rebound'];
// Sms-signaler (låsskärmens notis) finns inte i extratone-samlingen; de kommer ur rob-paprocki/iOS-System-Sounds (fast commit).
const IOS_ARCHIVE = 'https://raw.githubusercontent.com/rob-paprocki/iOS-System-Sounds/1b93552344eaf00270b0b6195a1bd3ff7f2f25f0/';
const SOUND_URLS = {
  Tritone: IOS_ARCHIVE + 'Current/UI%20Sounds/iPhone/SMS%20Received%201.caf',
  Rebound: IOS_ARCHIVE + 'Current/Ringtones%20%26%20Alert%20Tones/Encore%20Infinitum/Rebound%20Encore%20Infinitum.caf',
};

const has = p => access(p).then(() => true, () => false);
const log = m => console.log(`  apple: ${m}`);

async function download(url, file) {
  log(`hämtar ${url.split('/').pop()} …`);
  const res = await fetch(url);
  if (!res.ok) throw Error(`kunde inte hämta ${url} (${res.status})`);
  await writeFile(file, Buffer.from(await res.arrayBuffer()));
}

function sevenZip() {
  for (const c of [process.env.SEVENZIP, 'C:/Program Files/7-Zip/7z.exe', '7z', '7zz']) {
    if (!c) continue;
    try { execFileSync(c, ['i'], {stdio: 'ignore'}); return c; } catch {}
  }
  throw Error('7-Zip behövs för att packa upp Apples SF Pro-paket (installera 7-Zip eller sätt SEVENZIP).');
}

async function findFile(dir, name) {
  for (const e of await readdir(dir, {withFileTypes: true})) {
    const p = join(dir, e.name);
    if (e.isDirectory()) { const f = await findFile(p, name); if (f) return f; }
    else if (e.name === name) return p;
  }
  return null;
}

async function ensureFonts() {
  const dir = join(CACHE, 'fonts');
  if ((await Promise.all(FONTS.map(f => has(join(dir, f))))).every(Boolean)) return dir;
  await mkdir(dir, {recursive: true});
  const work = join(tmpdir(), `sf-pro-${process.pid}`);
  await mkdir(work, {recursive: true});
  try {
    const z = sevenZip();
    await download(SF_DMG, join(work, 'SF-Pro.dmg'));
    execFileSync(z, ['x', '-y', 'SF-Pro.dmg'], {cwd: work, stdio: 'ignore'});
    const pkg = await findFile(work, 'SFProFontsPackage.pkg') || await findFile(work, 'SF Pro Fonts.pkg');
    if (!pkg) throw Error('hittade inget typsnittspaket i SF-Pro.dmg');
    const inner = join(work, 'pkg'); await mkdir(inner);
    execFileSync(z, ['x', '-y', pkg], {cwd: inner, stdio: 'ignore'});
    for (const p of await readdir(inner)) if (p.startsWith('Payload')) execFileSync(z, ['x', '-y', p], {cwd: inner, stdio: 'ignore'});
    for (const f of FONTS) {
      const src = await findFile(inner, f);
      if (!src) throw Error(`${f} saknas i Apples paket`);
      await copyFile(src, join(dir, f));
    }
  } finally { await rm(work, {recursive: true, force: true}); }
  return dir;
}

async function ensureEmojiFont() {
  const file = join(CACHE, 'AppleColorEmoji-Linux.ttf');
  if (!(await has(file))) { await mkdir(CACHE, {recursive: true}); await download(EMOJI_TTF, file); }
  return file;
}

async function ensureSounds() {
  const dir = join(CACHE, 'ljud');
  await mkdir(dir, {recursive: true});
  for (const n of SOUND_NAMES) {
    const wav = join(dir, `${n}.wav`);
    if (await has(wav)) continue;
    const caf = join(dir, `${n}.caf`);
    await download(SOUND_URLS[n] || SOUNDS + `${n}.caf`, caf);
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', caf, '-c:a', 'pcm_s16le', '-ar', '44100', '-ac', '2', wav]);
    await rm(caf);
  }
  return dir;
}

async function ensureFrame() {
  const file = join(CACHE, 'iphone-17.png');
  if (await has(file)) return file;
  const dl = join(homedir(), 'Downloads', 'iphone17-3d-flat.png');
  if (await has(dl)) { await mkdir(CACHE, {recursive: true}); await copyFile(dl, file); return file; }
  throw Error(`telefonramen saknas – lägg Jonas iphone17-3d-flat.png i ${CACHE} som iphone-17.png`);
}

/** Emoji-tecken i samtalet (bara bildtecken, så å/ä/ö, siffror och skiljetecken tas från SF Pro). */
export function emojiCodepoints(texts) {
  const set = new Set([0xfe0f, 0x200d, 0x20e3]);
  const re = /\p{Extended_Pictographic}|\p{Emoji_Modifier}|\p{Regional_Indicator}|[\u{E0020}-\u{E007F}]/gu;
  for (const t of texts) for (const m of String(t || '').matchAll(re)) set.add(m[0].codePointAt(0));
  return [...set].sort((a, b) => a - b);
}

async function subsetEmoji(ttf, codepoints, out) {
  const list = codepoints.map(c => 'U+' + c.toString(16).toUpperCase()).join(',');
  const stamp = out.replace(/\.woff2$/, '.txt');
  if (existsSync(out) && existsSync(stamp) && (await readFile(stamp, 'utf8')) === list) return false;
  const args = [ttf, `--unicodes=${list}`, `--output-file=${out}`, '--flavor=woff2', '--layout-features=*', '--no-hinting'];
  const runners = [['uvx', ['--from', 'fonttools[woff]', 'pyftsubset', ...args]], ['pyftsubset', args]];
  let lastError;
  for (const [cmd, a] of runners) {
    try { execFileSync(cmd, a, {stdio: ['ignore', 'ignore', 'pipe']}); await writeFile(stamp, list); return true; }
    catch (e) { lastError = e; }
  }
  throw Error(`kunde inte skapa emoji-delmängden (behöver uv eller fonttools[woff]): ${String(lastError?.stderr || lastError?.message).slice(0, 200)}`);
}

/** Lägger Apples resurser i mallens assets/ och skapar emoji-delmängden för samtalets emoji. */
export async function prepareAppleAssets(data) {
  const fontsDir = new URL('assets/fonts/', here), soundDir = new URL('assets/ljud/', here);
  await mkdir(fontsDir, {recursive: true}); await mkdir(soundDir, {recursive: true});
  const [fonts, sounds, frame, emoji] = await Promise.all([ensureFonts(), ensureSounds(), ensureFrame(), ensureEmojiFont()]);
  for (const f of FONTS) if (!(await has(new URL(f, fontsDir)))) await copyFile(join(fonts, f), new URL(f, fontsDir));
  for (const n of SOUND_NAMES) if (!(await has(new URL(`${n}.wav`, soundDir)))) await copyFile(join(sounds, `${n}.wav`), new URL(`${n}.wav`, soundDir));
  if (!(await has(new URL('assets/iphone-17.png', here)))) await copyFile(frame, new URL('assets/iphone-17.png', here));
  const texts = [data.contact, ...(data.messages || []).flatMap(m => [m.text, m.reaction])];
  const cps = emojiCodepoints(texts);
  const out = new URL('assets/fonts/apple-emoji.woff2', here);
  const made = await subsetEmoji(emoji, cps, out.pathname.replace(/^\/([A-Za-z]:)/, '$1'));
  if (made) log(`emoji-delmängd med ${cps.length - 3} tecken`);
}

if (/apple-resurser\.mjs$/.test(process.argv[1] || '')) {
  const data = JSON.parse(await readFile(new URL('conversation.json', here), 'utf8'));
  await prepareAppleAssets(data).catch(e => { console.error(`Stopp: ${e.message}`); process.exit(1); });
  console.log(`Klart. Cache: ${CACHE}`);
}
