import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, writeFile, copyFile, mkdir, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {schedule, readTime} from './build.mjs';

const conv = messages => schedule({messages: structuredClone(messages)}).messages;

test('nästa meddelande kommer först när föregående hunnit läsas (läsregeln)', () => {
  const m = conv([{side: 'recv', text: 'Hej! Spelar du golf i helgen? ⛳'}, {side: 'sent', text: 'Ja!'}, {side: 'recv', text: 'Ok'}]);
  for (let i = 1; i < m.length; i++) assert.ok(m[i]._start >= m[i - 1]._start + readTime(m[i - 1]) - 1e-9);
});

test('skrivandet börjar aldrig innan föregående meddelande har kommit', () => {
  const m = conv([{side: 'sent', text: 'Ok'}, {side: 'sent', text: 'En längre fråga som tar tid att skriva klart'}, {side: 'recv', text: 'Ja'}, {side: 'recv', text: 'Absolut, vi ses där klockan tio!'}]);
  for (let i = 1; i < m.length; i++) if (m[i]._typing !== null) assert.ok(m[i]._typing >= m[i - 1]._start + 0.4 - 1e-9, `meddelande ${i + 1}`);
});

test('manuell tid som bryter läsregeln stoppar bygget', () => {
  assert.throws(() => conv([{side: 'recv', text: 'En ganska lång första fråga här'}, {side: 'sent', text: 'Svar', at: 1}]), /läsregeln/);
});

test('reaktion kommer efter sitt meddelande och filmen räcker till den', () => {
  const data = schedule({messages: [{side: 'recv', text: 'Snyggt', reaction: '❤️'}]});
  assert.ok(data.messages[0]._reaction > data.messages[0]._start);
  assert.ok(data.duration >= data.messages[0]._reaction + 1.2);
});

test('bygget skriver tider, längd och ljud och nekar filer utanför assets/', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'imessage-test-'));
  try {
    await copyFile(new URL('./build.mjs', import.meta.url), join(dir, 'build.mjs'));
    await writeFile(join(dir, 'index.html'), '<div data-duration="12"><!-- SOUNDS:START --><!-- SOUNDS:END --></div>');
    await mkdir(join(dir, 'assets'));
    await writeFile(join(dir, 'assets', 'ping.mp3'), 'placeholder');
    await writeFile(join(dir, 'conversation.json'), JSON.stringify({contact: 'A', sounds: {received: 'assets/ping.mp3'}, messages: [{side: 'recv', text: 'Hej'}, {side: 'sent', text: 'Hej igen', at: 5, sound: false}]}));
    execFileSync(process.execPath, ['build.mjs'], {cwd: dir, env: {...process.env, IMESSAGE_SKIP_APPLE: '1'}});
    const generated = await readFile(join(dir, 'conversation.generated.js'), 'utf8');
    const html = await readFile(join(dir, 'index.html'), 'utf8');
    assert.match(generated, /"_start": 5/);
    assert.match(html, /data-duration="8"/);
    assert.match(html, /id="message-sound-0" class="clip" src="assets\/ping.mp3"/);
    assert.doesNotMatch(html, /message-sound-1/);
    await writeFile(join(dir, 'conversation.json'), JSON.stringify({messages: [{side: 'recv', text: 'Hej', image: 'assets/../secret'}]}));
    assert.throws(() => execFileSync(process.execPath, ['build.mjs'], {cwd: dir, stdio: 'ignore', env: {...process.env, IMESSAGE_SKIP_APPLE: '1'}}));
  } finally { await rm(dir, {recursive: true, force: true}); }
});

test('emoji-delmängden tar bara bildtecken, inte å/ä/ö eller siffror', async () => {
  const {emojiCodepoints} = await import('./apple-resurser.mjs');
  const cps = emojiCodepoints(['Hej 1 å ⛳', '❤️', '👍🏽']);
  assert.ok(cps.includes(0x26f3) && cps.includes(0x2764) && cps.includes(0x1f44d) && cps.includes(0x1f3fd));
  assert.ok(!cps.includes(0xe5) && !cps.includes(0x31));
});
