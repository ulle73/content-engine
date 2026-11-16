// Bygger tidslinjen för iMessage-mallen från conversation.json.
// Skriver conversation.generated.js (läses av chattkomponenten) och uppdaterar längd + ljud i index.html.
// Tiderna följer läsregeln (skills/video-regler): ett meddelande syns minst max(5/6, tecken/12) + 0,9 s
// innan nästa kommer. Bryter en manuell tid (`at`) mot regeln stoppas bygget.
import {access, copyFile, mkdir, readFile, writeFile} from 'node:fs/promises';

const here = new URL('./', import.meta.url);
const chars = s => Array.from(typeof s === 'string' ? s : '').length;
const round = n => Math.round(n * 100) / 100;

/** Lästid enligt läsregeln. Bild utan text: 1,5 s. Bild med text: textens lästid + 0,8 s. */
export function readTime(m) {
  const n = chars(m.text);
  const text = n ? Math.max(5 / 6, n / 12) + 0.9 : 0;
  return m.image ? (n ? text + 0.8 : 1.5) : text;
}

/** Hur länge någon skriver innan meddelandet kommer. Skickat: tecken i fältet. Mottaget: skriver-prickar. */
export function typingTime(m, speed = 1) {
  const n = chars(m.text);
  const base = m.side === 'sent' ? Math.min(2.4, Math.max(0.6, n * 0.065)) : Math.min(2.6, Math.max(1.1, 0.8 + n * 0.04));
  return base / speed;
}

/** Räknar fram _typing, _start och _reaction för varje meddelande. Kastar fel med svensk förklaring. */
export function schedule(data) {
  if (!Array.isArray(data.messages) || !data.messages.length || data.messages.length > 100) throw Error('Ange 1–100 meddelanden.');
  const speed = Number.isFinite(data.typingSpeed) && data.typingSpeed > 0 ? data.typingSpeed : 1;
  const first = Number.isFinite(data.firstAt) ? data.firstAt : 0.6;
  // Egen hastighet för dina meddelanden (det som skrivs på tangentbordet); annars typingSpeed.
  const sentSpeed = Number.isFinite(data.sentTypingSpeed) && data.sentTypingSpeed > 0 ? data.sentTypingSpeed : null;
  let prev = null;
  for (const [i, m] of data.messages.entries()) {
    const label = `Meddelande ${i + 1}`;
    if (!['sent', 'recv'].includes(m.side)) throw Error(`${label}: side måste vara "sent" (du) eller "recv" (den andra).`);
    if (!chars(m.text) && !m.image) throw Error(`${label}: ange text, image eller båda.`);
    const typing = m.typing === false ? 0 : typingTime(m, m.side === 'sent' && sentSpeed ? sentSpeed : speed);
    let start;
    if (!prev) start = Math.max(first, m.typing === false ? 0 : typing);
    else {
      const earliestRead = prev._start + readTime(prev);
      start = Math.max(earliestRead, prev._start + 0.4 + typing);
      if (m.at !== undefined) {
        if (!Number.isFinite(m.at)) throw Error(`${label}: at måste vara ett tal (sekunder).`);
        if (m.at < earliestRead - 1e-6) throw Error(`${label}: at ${m.at} s bryter läsregeln – meddelande ${i} behöver synas till ${round(earliestRead)} s.`);
        start = m.at;
      }
    }
    if (!prev && m.at !== undefined) {
      if (!Number.isFinite(m.at) || m.at < 0) throw Error(`${label}: at måste vara 0 eller mer.`);
      start = m.at;
    }
    m._start = Math.ceil(start * 100 - 1e-6) / 100; // avrunda uppåt så läsregeln alltid håller
    // Skrivandet börjar tidigast 0,4 s efter förra meddelandet, så ett svar aldrig skrivs innan frågan kommit.
    const typingFrom = prev ? prev._start + 0.4 : 0;
    m._typing = typing ? round(Math.max(typingFrom, start - typing)) : null;
    if (m._typing !== null && m._start - m._typing < 0.3) m._typing = null;
    if (m.overlay && m.image) {
      // overlay (t.ex. glasögon) släpps en stund efter bilden och glider ner under overlay.duration sekunder
      m._overlay = round(m._start + (Number.isFinite(m.overlay.after) ? m.overlay.after : 1));
    } else delete m._overlay;
    if (m.reaction) {
      const delay = Number.isFinite(m.reactionAfter) ? m.reactionAfter : readTime(m) * 0.6;
      m._reaction = round(m._start + Math.max(0.3, delay));
    }
    prev = m;
  }
  // Tangenttryck för dina meddelanden: mänsklig, deterministisk variation; sista trycket strax före skicka.
  for (const [i, m] of data.messages.entries()) {
    delete m._keys;
    if (m.side !== 'sent' || m._typing == null || data.showTyping === false) continue;
    const cs = Array.from(m.text || '');
    if (!cs.length) continue;
    const a = m._typing + 0.05, b = m._start - 0.14;
    const w = cs.map((c, k) => {
      const r = Math.abs(Math.sin((k + 1) * 12.9898 + (i + 1) * 78.233) * 43758.5453) % 1; // 0–1, samma varje bygge
      return (c === ' ' ? 1.35 : 1) * (0.7 + 0.6 * r);
    });
    const total = w.reduce((s, x) => s + x, 0) - w[0];
    let acc = 0;
    m._keys = cs.map((_, k) => { if (k) acc += w[k]; return round(a + (b - a) * (total ? acc / total : 0)); });
  }
  // Tangentbordet: uppe från start och ner strax efter ditt sista skrivna meddelande om något kommer efter det.
  data._kbHide = null;
  if (data.keyboard) {
    const lastTyped = data.messages.findLastIndex(m => m._keys);
    if (lastTyped >= 0 && lastTyped < data.messages.length - 1) data._kbHide = round(data.messages[lastTyped]._start + 0.6);
  }
  const last = data.messages.at(-1);
  const ends = data.messages.map(m => Math.max(m._reaction ? m._reaction + 1.2 : 0, m._overlay ? m._overlay + (m.overlay.duration || 1.6) + (Number.isFinite(m.overlay.hold) ? m.overlay.hold : 2.5) : 0));
  const hold = Number.isFinite(data.endHold) ? data.endHold : 0; // hur länge sista meddelandet står kvar (avslutning)
  const minEnd = Math.max(last._start + Math.max(readTime(last), 2.2, hold) + 0.4, ...ends);
  if (data.duration !== undefined && (!Number.isFinite(data.duration) || data.duration < minEnd)) throw Error(`duration ${data.duration} s är för kort – sista meddelandet behöver synas till ${round(minEnd)} s.`);
  data.duration = data.duration ?? Math.ceil(minEnd * 2) / 2;
  return data;
}

async function assetPath(value, label) {
  if (typeof value !== 'string' || !value.startsWith('assets/') || value.includes('\\') || value.split('/').some(p => p === '..' || p === '.') || /[\u0000-\u001f?#%"<>]/u.test(value)) throw Error(`${label}: filen måste ligga i assets/ (t.ex. assets/bild.jpg).`);
  await access(new URL(value, here)).catch(() => { throw Error(`${label}: hittar inte ${value}.`); });
}

const escapeHtml = value => String(value).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

/** Läser en 16-bitars PCM-wav (44,1 kHz stereo, som apple-resurser.mjs skriver). */
function readWav(buf) {
  let p = 12, fmt = null, data = null;
  while (p + 8 <= buf.length) {
    const id = buf.toString('ascii', p, p + 4), size = buf.readUInt32LE(p + 4);
    if (id === 'fmt ') fmt = {channels: buf.readUInt16LE(p + 10), rate: buf.readUInt32LE(p + 12), bits: buf.readUInt16LE(p + 22)};
    if (id === 'data') data = buf.subarray(p + 8, p + 8 + size);
    p += 8 + size + (size % 2);
  }
  if (!fmt || !data || fmt.bits !== 16 || fmt.channels !== 2 || fmt.rate !== 44100) throw Error('tangentljuden måste vara 16-bitars wav, 44,1 kHz stereo');
  return new Int16Array(data.buffer.slice(data.byteOffset, data.byteOffset + data.length));
}

/** Mixar iPhones tangentklick (ett per tecken) till ett spår: assets/ljud/_tangentbord.wav. */
async function mixKeyboard(data) {
  const dir = new URL('assets/ljud/', here);
  const load = async n => readWav(await readFile(new URL(`${n}.wav`, dir)));
  let click, modifier;
  try { [click, modifier] = await Promise.all([load('key_press_click'), load('key_press_modifier')]); }
  catch (e) { console.warn(`  tangentljud saknas (${e.message}) – tangentbordet blir tyst`); return false; }
  const rate = 44100, gain = Number.isFinite(data.keyboardVolume) ? data.keyboardVolume : 0.7;
  const mix = new Float32Array(Math.ceil(data.duration * rate) * 2);
  for (const m of data.messages) (m._keys || []).forEach((t, k) => {
    const s = Array.from(m.text)[k] === ' ' ? modifier : click;
    const o = Math.round(t * rate) * 2;
    for (let j = 0; j < s.length && o + j < mix.length; j++) mix[o + j] += s[j] * gain;
  });
  const out = Buffer.alloc(44 + mix.length * 2);
  out.write('RIFF', 0); out.writeUInt32LE(36 + mix.length * 2, 4); out.write('WAVEfmt ', 8);
  out.writeUInt32LE(16, 16); out.writeUInt16LE(1, 20); out.writeUInt16LE(2, 22); out.writeUInt32LE(rate, 24);
  out.writeUInt32LE(rate * 4, 28); out.writeUInt16LE(4, 32); out.writeUInt16LE(16, 34); out.write('data', 36); out.writeUInt32LE(mix.length * 2, 40);
  for (let j = 0; j < mix.length; j++) out.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(mix[j]))), 44 + j * 2);
  await writeFile(new URL('_tangentbord.wav', dir), out);
  return true;
}

const OUTRO_LEN = 3.1;
/** Kopierar Spotlight-slutbilden (edit-renderer/outros/golfkuponger) in i assets/outro/. */
async function prepareOutro() {
  const dest = new URL('assets/outro/spotlight-9x16.mp4', here);
  if (await access(dest).then(() => true, () => false)) return;
  let dir = new URL('./', here);
  for (let i = 0; i < 6; i++) {
    const src = new URL('edit-renderer/outros/golfkuponger/spotlight-9x16.mp4', dir);
    if (await access(src).then(() => true, () => false)) {
      await mkdir(new URL('assets/outro/', here), {recursive: true});
      await copyFile(src, dest);
      return;
    }
    dir = new URL('../', dir);
  }
  throw Error('hittar inte edit-renderer/outros/golfkuponger/spotlight-9x16.mp4 (slutbilden Spotlight)');
}

export async function build() {
  const data = JSON.parse(await readFile(new URL('conversation.json', here), 'utf8'));
  // Tangentbord på/av: "keyboard" i conversation.json, eller IMESSAGE_KEYBOARD=1/0 (make.sh bygger båda varianterna).
  if (process.env.IMESSAGE_KEYBOARD === '1') data.keyboard = true;
  if (process.env.IMESSAGE_KEYBOARD === '0') data.keyboard = false;
  data.keyboard = data.keyboard === true;
  // Overlays av/på: IMESSAGE_OVERLAYS=0 tar bort alla (make.sh bygger varianter med och utan).
  if (process.env.IMESSAGE_OVERLAYS === '0') for (const m of data.messages || []) delete m.overlay;
  // Apples typsnitt, emoji och iOS-ljud (gitignorerade) läggs på plats först. IMESSAGE_SKIP_APPLE=1 hoppar över (tester).
  if (!process.env.IMESSAGE_SKIP_APPLE) {
    const {prepareAppleAssets} = await import(new URL('apple-resurser.mjs', here).href);
    await prepareAppleAssets(data);
  }
  // iPhones egna meddelandeljud är standard; "sounds": false stänger av, egna filer går att ange.
  if (data.sounds === undefined) data.sounds = {sent: 'assets/ljud/SentMessage.wav', received: 'assets/ljud/ReceivedMessage.wav'};
  if (data.sounds === false) data.sounds = {};
  if (data.avatar) await assetPath(data.avatar, 'Profilbild');
  if (data.background && String(data.background).startsWith('assets/')) await assetPath(data.background, 'Bakgrund');
  for (const key of ['sent', 'received']) if (data.sounds?.[key]) await assetPath(data.sounds[key], `Ljud (${key})`);
  for (const [i, m] of (data.messages || []).entries()) {
    if (m.image) await assetPath(m.image, `Meddelande ${i + 1}, bild`);
    if (m.sound) await assetPath(m.sound, `Meddelande ${i + 1}, ljud`);
    if (m.overlay) await assetPath(m.overlay.src, `Meddelande ${i + 1}, overlay`);
  }
  // Intro: låsskärm med notisen för första meddelandet; appen öppnas vid _open och meddelandet finns redan där.
  if (data.intro?.lockscreen && data.messages?.length) {
    const it = data.intro, m0 = data.messages[0];
    if (it.wallpaper) await assetPath(it.wallpaper, 'Låsskärmens bakgrund');
    it._notify = Number.isFinite(it.notifyAt) ? it.notifyAt : 0.5;
    const need = it._notify + readTime(m0) + 0.3; // notisen ska hinna läsas innan appen öppnas (läsregeln)
    const dur = Number.isFinite(it.duration) ? it.duration : Math.max(3, need);
    if (dur < need - 1e-6) throw Error(`intro.duration ${dur} s är för kort – notisen behöver synas till ${round(need)} s.`);
    it._open = round(dur - 0.3);
    data.firstAt = it._open;
    m0.typing = false;
    if (m0.sound === undefined) m0.sound = false; // meddelandet var redan levererat som notis
    it._sound = it.sound === false ? null : (it.sound || 'assets/ljud/Tritone.wav');
    if (it._sound) await assetPath(it._sound, 'Notisljud');
  }
  schedule(data);
  // Avslutning: Golfkupongers slutbild Spotlight (3,1 s) efter en tonad övergång till mörkgrönt (#0c140f).
  data._total = data.duration;
  if (data.outro === 'spotlight') {
    await prepareOutro();
    data._total = round(data.duration + OUTRO_LEN);
  }
  await writeFile(new URL('conversation.generated.js', here), `window.CHAT_CONFIG = ${JSON.stringify(data, null, 2)};\n`);

  const target = new URL('index.html', here);
  let html = await readFile(target, 'utf8');
  html = html.replace(/data-duration="[\d.]+"/g, `data-duration="${data.duration}"`);
  const sounds = data.messages.map((m, i) => {
    const src = m.sound === false ? null : m.sound || (m.side === 'sent' ? data.sounds?.sent : data.sounds?.received);
    return src ? `<audio id="message-sound-${i}" class="clip" src="${escapeHtml(src)}" data-start="${m._start}" data-duration="${round(Math.min(0.55, data.duration - m._start))}" data-track-index="${2 + (i % 2)}" data-volume="${data.sounds?.volume ?? 0.8}"></audio>` : '';
  }).filter(Boolean).join('\n  ');
  let keyClip = '';
  if (data.keyboard && data.keyboardSounds !== false && await mixKeyboard(data)) {
    keyClip = `\n  <audio id="keyboard-sound" class="clip" src="assets/ljud/_tangentbord.wav" data-start="0" data-duration="${data.duration}" data-track-index="4" data-volume="1"></audio>`;
  }
  const introClip = data.intro?._sound ? `\n  <audio id="intro-sound" class="clip" src="${escapeHtml(data.intro._sound)}" data-start="${data.intro._notify}" data-duration="1.2" data-track-index="6" data-volume="0.9"></audio>` : '';
  html = html.replace(/<!-- SOUNDS:START -->[\s\S]*?<!-- SOUNDS:END -->/, `<!-- SOUNDS:START -->\n  ${sounds}${keyClip}${introClip}\n  <!-- SOUNDS:END -->`);
  html = html.replace(/(data-composition-id="main" data-start="0" data-duration=")[\d.]+"/, `$1${data._total}"`);
  const outro = data.outro === 'spotlight'
    ? `<div id="outro-fade" data-layout-allow-occlusion></div>\n  <video id="outro-video" class="clip" src="assets/outro/spotlight-9x16.mp4" data-start="${data.duration}" data-duration="${OUTRO_LEN}" data-track-index="7" data-has-audio="true" playsinline></video>`
    : '';
  html = html.replace(/<!-- OUTRO:START -->[\s\S]*?<!-- OUTRO:END -->/, `<!-- OUTRO:START -->\n  ${outro}\n  <!-- OUTRO:END -->`);
  await writeFile(target, html);
  return data;
}

if (/build.mjs$/.test(process.argv[1] || '')) {
  try {
    const data = await build();
    console.log(`${data.messages.length} meddelanden, ${data.duration} sekunder.`);
    for (const [i, m] of data.messages.entries()) console.log(`  ${String(i + 1).padStart(2)}  ${m.side === 'sent' ? 'du ' : 'den'}  ${m._typing ?? '   '} → ${m._start} s${m._reaction ? `  reaktion ${m._reaction} s` : ''}  ${(m.text || '[bild]').slice(0, 40)}`);
  } catch (e) {
    console.error(`Stopp: ${e.message}`);
    process.exit(1);
  }
}
