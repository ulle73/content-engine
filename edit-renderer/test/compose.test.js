// node --test test/    (HF_LINT=1 also runs `hyperframes lint` on every generated composition)
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { compose, FORMATS, words } from '../src/compose.js';
import { lint } from '../src/render.js';
import { resolve, SUPPORT } from '../src/support.js';

const tmp = mkdtempSync(join(tmpdir(), 'cut-test-'));
process.on('exit', () => rmSync(tmp, { recursive: true, force: true }));
const fake = (name) => { const p = join(tmp, name); writeFileSync(p, 'x'); return p; };
const VIDEO = fake('clip.mp4');
const IMAGE = fake('still.jpg');
const LOGO = fake('logo.png');

const transitions = Object.keys(SUPPORT.transitions);
const styles = Object.keys(SUPPORT.text);
const effects = Object.keys(SUPPORT.effects);

/** One scene per text style, cycling through every transition and every effect: the whole template in one film. */
function coverageSpec(format = '9:16') {
  const scenes = styles.map((style, i) => ({
    id: `s${i + 1}`, purpose: i === 0 ? 'hook' : 'body', duration_s: 1.6,
    asset_id: i % 2 ? 'img' : 'vid', asset_kind: i % 2 ? 'image' : 'video', trim_start_s: i % 2 ? 0 : 0.5,
    fit: i % 3 === 2 ? 'contain' : 'cover', text: `Rad ${i + 1} med *betoning* åäö`, text_style: `cut.text.${style}`,
    text_position: null, audio: i === 2 ? 'keep' : i === 0 ? 'mute' : null,
    effects: effects.filter((_, k) => k % styles.length === i).map((e) => `cut.effect.${e}`),
    transition_in: i ? `cut.transition.${transitions[i % transitions.length]}` : null,
  }));
  scenes[1].effects.push('hyperframes.registry.confetti');
  return {
    schema: 'cut/v1', format, fps: 30, title: 'Täckningstest', caption: '', recipe_id: null, brand: 'faiv', scenes,
    music_asset_id: null, music_volume: 1, cta: { text: 'Beställ *idag*', url: 'https://faiv.se/', duration_s: 2.5 },
  };
}

const files = {
  vid: { path: VIDEO, kind: 'video', duration: 6, hasAudio: true },
  img: { path: IMAGE, kind: 'image' },
  logo: { path: LOGO, kind: 'image' },
};
const brand = { name: 'FAIV', background: '#0b0b0d', foreground: '#ffffff', accent: '#f2a900', paper: '#f7f3ea', ink: '#111111' };

test('support map resolves catalog ids and native ids', () => {
  assert.equal(resolve('transitions', 'hyperframes.registry.whip-pan'), 'whip');
  assert.equal(resolve('text', 'cut.text.slam'), 'slam');
  assert.equal(resolve('effects', 'hyperframes.registry.confetti'), null);
});

test('emphasis markup becomes accent words', () => {
  assert.deepEqual(words('Din *chef betalar* golf'), [
    { text: 'Din', em: false }, { text: 'chef', em: true }, { text: 'betalar', em: true }, { text: 'golf', em: false }]);
});

for (const format of Object.keys(FORMATS)) {
  test(`builds a composition covering every treatment (${format})`, async () => {
    const out = join(tmp, format.replace(':', 'x'));
    const spec = coverageSpec(format);
    const result = compose({ spec, brand, files, outDir: out, logoId: 'logo' });
    const total = styles.length * 1.6 + 2.5;
    assert.equal(result.total, Math.round(total * 1000) / 1000);
    const html = readFileSync(join(out, 'index.html'), 'utf8');
    const { W, H } = FORMATS[format];
    assert.match(html, new RegExp(`data-composition-id="main" data-start="0" data-duration="${result.total}" data-width="${W}" data-height="${H}"`));
    assert.match(html, /window\.__timelines\['main'\] = tl/);
    // Videos are timed directly (never inside a timed wrapper), trimmed, and muted unless kept.
    const videos = [...html.matchAll(/<video [^>]+>/g)].map((m) => m[0]);
    assert.equal(videos.length, Math.ceil(styles.length / 2));
    assert.ok(videos.every((v) => /data-start="[\d.]+"/.test(v) && /data-media-start="[\d.]+"/.test(v)));
    assert.ok(videos.some((v) => v.includes('data-has-audio="true"')));
    assert.ok(videos.some((v) => v.includes(' muted ')));
    assert.ok(!/crossorigin/.test(html));
    // Every native transition and text style is used; the end card has the logo and the CTA host.
    const used = new Set(result.config.scenes.map((s) => s.transition?.type).filter(Boolean));
    assert.deepEqual([...used].sort(), [...transitions].sort());
    assert.deepEqual(result.config.scenes.map((s) => s.text.style), styles);
    assert.match(html, /faiv\.se</);
    assert.match(html, /assets\/logo\.png/);
    assert.ok(result.warnings.some((w) => w.includes('hyperframes.registry.confetti')));
    // Windows overlap only for dissolving transitions and never leave the film.
    for (const s of result.config.scenes) {
      assert.ok(s.winStart >= 0 && s.winEnd <= result.total && s.winStart <= s.start && s.winEnd >= s.end);
    }
    if (process.env.HF_LINT) {
      const findings = await lint(out);
      assert.deepEqual(findings.errors.map((e) => `${e.code}: ${e.message}`), []);
    }
  });
}
