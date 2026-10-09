/* Cut template runtime. Inlined into the generated index.html by compose.js.
 * Reads the JSON config in #cut-config and builds ONE paused, seekable GSAP timeline (window.__timelines.main).
 * Deterministic: no clocks, no Math.random (hash-based noise), every tween placed at an absolute time. */
(function () {
  const C = JSON.parse(document.getElementById('cut-config').textContent);
  const $ = (id) => document.getElementById(id);
  const all = (root, sel) => Array.from(root.querySelectorAll(sel));
  const rnd = (i, salt) => { const x = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453; return x - Math.floor(x); };
  const tl = gsap.timeline({ paused: true });

  // ------------------------------------------------------------------ text fitting (before any tween)
  function fit(scene) {
    const box = $('X-' + scene.id);
    const tb = $('TB-' + scene.id);
    if (!box || !tb) return;
    const t = scene.text;
    const maxW = t.maxW;
    const maxH = t.maxH;
    let fs = t.base;
    for (let k = 0; k < 40; k++) {
      tb.style.fontSize = fs + 'px';
      const words = all(tb, '.w');
      const wide = words.some((w) => w.offsetWidth > maxW + 1);
      if (!wide && tb.scrollWidth <= maxW + 1 && tb.offsetHeight <= maxH) break;
      fs = Math.max(22, Math.floor(fs * 0.93));
    }
  }

  // ------------------------------------------------------------------ layer visibility and transitions
  function show(scene) {
    const L = $('L-' + scene.id);
    tl.set(L, { opacity: 1 }, scene.winStart);
    if (scene.winEnd < C.total - 1e-3) tl.set(L, { opacity: 0 }, scene.winEnd);
  }

  function transitionIn(scene, prev) {
    const t = scene.transition;
    if (!t || !prev) return;
    const T = scene.start, d = t.d, a = T - d / 2;
    const inn = $('T-' + scene.id), out = $('T-' + prev.id);
    const outOpts = { immediateRender: false };
    switch (t.type) {
      case 'fade':
        tl.fromTo(inn, { opacity: 0 }, { opacity: 1, duration: d, ease: 'none' }, a);
        break;
      case 'blur':
        tl.fromTo(inn, { opacity: 0, filter: 'blur(28px)' }, { opacity: 1, filter: 'blur(0px)', duration: d, ease: 'power2.out' }, a);
        tl.fromTo(out, { filter: 'blur(0px)' }, { filter: 'blur(28px)', duration: d, ease: 'power2.in', ...outOpts }, a);
        break;
      case 'flash': {
        const f = $('flash');
        tl.fromTo(f, { opacity: 0 }, { opacity: 1, duration: d / 2, ease: 'power2.in', ...outOpts }, a);
        tl.fromTo(f, { opacity: 1 }, { opacity: 0, duration: d / 2 + 0.12, ease: 'power2.out', ...outOpts }, T);
        tl.fromTo(inn, { scale: 1.08 }, { scale: 1, duration: 0.5, ease: 'power3.out' }, T);
        break;
      }
      case 'whip':
        tl.fromTo(inn, { xPercent: 100, filter: 'blur(26px)' }, { xPercent: 0, filter: 'blur(0px)', duration: d, ease: 'expo.inOut' }, a);
        tl.fromTo(out, { xPercent: 0, filter: 'blur(0px)' }, { xPercent: -100, filter: 'blur(26px)', duration: d, ease: 'expo.inOut', ...outOpts }, a);
        break;
      case 'push':
        tl.fromTo(inn, { yPercent: 100 }, { yPercent: 0, duration: d, ease: 'power4.inOut' }, a);
        tl.fromTo(out, { yPercent: 0 }, { yPercent: -100, duration: d, ease: 'power4.inOut', ...outOpts }, a);
        break;
      case 'zoom':
        tl.fromTo(out, { scale: 1, opacity: 1, filter: 'blur(0px)' }, { scale: 1.7, opacity: 0, filter: 'blur(14px)', duration: d, ease: 'power3.in', ...outOpts }, a);
        tl.fromTo(inn, { scale: 1.45, opacity: 0, filter: 'blur(14px)' }, { scale: 1, opacity: 1, filter: 'blur(0px)', duration: d, ease: 'power3.out' }, a);
        break;
      case 'wipe': {
        tl.fromTo(inn, { clipPath: 'inset(0% 0% 0% 100%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: d, ease: 'power3.inOut' }, a);
        const edge = $('E-' + scene.id);
        if (edge) {
          tl.fromTo(edge, { x: C.W }, { x: -160, duration: d, ease: 'power3.inOut' }, a);
        }
        break;
      }
      case 'iris': {
        const r = Math.ceil(Math.hypot(C.W, C.H) / 2) + 20;
        tl.fromTo(inn, { clipPath: 'circle(0px at 50% 50%)' }, { clipPath: `circle(${r}px at 50% 50%)`, duration: d, ease: 'power2.inOut' }, a);
        break;
      }
      case 'light-leak': {
        tl.fromTo(inn, { opacity: 0 }, { opacity: 1, duration: d, ease: 'sine.inOut' }, a);
        const leak = $('LK-' + scene.id);
        if (leak) {
          tl.fromTo(leak, { xPercent: -45, opacity: 0 }, { xPercent: 35, duration: d * 1.4, ease: 'sine.inOut' }, a - d * 0.2);
          tl.to(leak, { opacity: 1, duration: d * 0.55, ease: 'power2.out' }, a - d * 0.2);
          tl.to(leak, { opacity: 0, duration: d * 0.85, ease: 'power2.in' }, a + d * 0.35);
        }
        break;
      }
      case 'glitch': {
        const steps = 7;
        for (let k = 0; k < steps; k++) {
          const at = a + (k / steps) * d;
          const target = at < T ? out : inn;
          const dx = (rnd(k, scene.idx + 3) - 0.5) * 120;
          const hue = Math.round((rnd(k, scene.idx + 9) - 0.5) * 140);
          tl.set(target, { x: dx, filter: `hue-rotate(${hue}deg) saturate(2.2) contrast(1.3)` }, at);
        }
        tl.set(out, { x: 0, filter: 'none' }, T);
        tl.set(inn, { x: 0, filter: 'none' }, T + d / 2);
        const bars = $('GB-' + scene.id);
        if (bars) {
          for (let k = 0; k < steps; k++) {
            tl.set(bars, { opacity: k % 2 ? 0 : 0.9, y: Math.round(rnd(k, scene.idx + 21) * C.H * 0.8) }, a + (k / steps) * d);
          }
          tl.set(bars, { opacity: 0 }, T + d / 2);
        }
        break;
      }
      default:
        break;
    }
  }

  // ------------------------------------------------------------------ per-scene effects
  function effects(scene) {
    const fx = scene.effects;
    const ws = scene.winStart, we = scene.winEnd, dur = Math.max(0.1, we - ws);
    const cam = $('C-' + scene.id), shk = $('K-' + scene.id), F = $('F-' + scene.id), B = $('B-' + scene.id);
    const dir = scene.idx % 2 ? 1 : -1;
    switch (scene.camera) {
      case 'ken-burns':
        tl.fromTo(cam, { scale: 1.06, xPercent: -1.6 * dir, yPercent: 0.8 * dir },
          { scale: 1.17, xPercent: 1.6 * dir, yPercent: -0.8 * dir, duration: dur, ease: 'sine.inOut' }, ws);
        break;
      case 'push-in':
        tl.fromTo(cam, { scale: 1.02 }, { scale: 1.15, duration: dur, ease: 'power1.inOut' }, ws);
        break;
      case 'pull-back':
        tl.fromTo(cam, { scale: 1.26 }, { scale: 1.03, duration: dur, ease: 'power2.out' }, ws);
        break;
      case 'micro-push':
        tl.fromTo(cam, { scale: 1.03 }, { scale: 1.08, duration: dur, ease: 'none' }, ws);
        break;
      default:
        break;
    }
    if (fx.includes('punch-in')) {
      tl.fromTo(F, { scale: 1 }, { scale: 1.16, duration: 0.24, ease: 'power3.out' }, scene.start + 0.05);
    }
    if (fx.includes('drift') || fx.includes('shake')) {
      const drift = fx.includes('drift'), shake = fx.includes('shake');
      const p = { t: 0 };
      const ph = scene.idx * 1.7;
      tl.fromTo(p, { t: 0 }, {
        t: dur, duration: dur, ease: 'none',
        onUpdate: () => {
          const t = p.t;
          let x = 0, y = 0, r = 0;
          if (drift) {
            x += 7 * Math.sin(1.1 * t + ph) + 3 * Math.sin(2.7 * t + ph * 2);
            y += 6 * Math.sin(0.9 * t + ph * 3) + 2.5 * Math.sin(2.3 * t);
            r += 0.35 * Math.sin(0.7 * t + ph);
          }
          if (shake) {
            const local = t - (scene.start - ws);
            if (local >= 0 && local < 0.7) {
              const amp = 22 * Math.exp(-local * 6);
              x += amp * Math.sin(local * 63);
              y += amp * 0.7 * Math.cos(local * 51);
              r += amp * 0.03 * Math.sin(local * 40);
            }
          }
          gsap.set(shk, { x, y, rotation: r });
        },
      }, ws);
    }
    if (fx.includes('dark-to-light')) {
      const len = Math.min(dur * 0.75, 3.2);
      tl.fromTo(F, { filter: 'brightness(0.05) contrast(1.25) saturate(0.6)' },
        { filter: 'brightness(1) contrast(1) saturate(1)', duration: len, ease: 'power2.inOut' }, scene.start + 0.1);
      const bloom = $('BL-' + scene.id);
      if (bloom) {
        tl.fromTo(bloom, { opacity: 0, scale: 0.6 }, { opacity: 0.85, scale: 1.15, duration: len * 0.7, ease: 'power2.out' }, scene.start + len * 0.35);
        tl.to(bloom, { opacity: 0.18, duration: len * 0.6, ease: 'power2.inOut' }, scene.start + len * 1.05);
      }
    }
    if (fx.includes('focus-rack')) {
      tl.fromTo(B, { filter: 'blur(18px)' }, { filter: 'blur(0px)', duration: 0.9, ease: 'power2.out' }, scene.start + 0.05);
    }
    if (fx.includes('grain')) {
      const tex = $('GT-' + scene.id);
      const step = 1 / 24;
      for (let i = 0; ws + i * step < we; i++) {
        tl.set(tex, { x: (rnd(i, 1) - 0.5) * 240, y: (rnd(i, 2) - 0.5) * 240 }, ws + i * step);
      }
    }
    if (fx.includes('light-sweep')) {
      const sw = $('SW-' + scene.id);
      tl.fromTo(sw, { xPercent: -130 }, { xPercent: 130, duration: 1.1, ease: 'power2.inOut' }, scene.start + Math.min(1.2, (scene.end - scene.start) * 0.35));
    }
    if (fx.includes('leak-overlay')) {
      const lo = $('LO-' + scene.id);
      tl.fromTo(lo, { xPercent: -30, opacity: 0 }, { xPercent: 25, duration: dur, ease: 'sine.inOut' }, ws);
      tl.to(lo, { opacity: 0.75, duration: dur * 0.4, ease: 'sine.out' }, ws);
      tl.to(lo, { opacity: 0.25, duration: dur * 0.6, ease: 'sine.in' }, ws + dur * 0.4);
    }
  }

  // ------------------------------------------------------------------ text styles
  function text(scene, next) {
    const t = scene.text;
    if (!t) return;
    const box = $('X-' + scene.id), tb = $('TB-' + scene.id), scrim = $('SC-' + scene.id);
    const words = all(tb, '.w'), inner = all(tb, '.wi'), chars = all(tb, '.ch');
    const t0 = scene.start + (scene.transition && !scene.transition.cut ? scene.transition.d / 2 : 0) + 0.12;
    const end = scene.end;
    const avail = Math.max(0.6, end - t0 - 0.3);
    if (scrim) tl.fromTo(scrim, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: 'power1.out' }, Math.max(scene.winStart, t0 - 0.2));
    const rise = (stagger) => tl.fromTo(inner, { yPercent: 115 }, { yPercent: 0, duration: 0.6, ease: 'power4.out', stagger }, t0);
    switch (t.style) {
      case 'rise':
        rise(Math.min(0.07, avail / 3 / Math.max(1, inner.length)));
        break;
      case 'line-reveal': {
        const lines = [];
        words.forEach((w, i) => {
          const top = Math.round(w.offsetTop);
          let line = lines.find((l) => Math.abs(l.top - top) < 4);
          if (!line) { line = { top, els: [] }; lines.push(line); }
          line.els.push(inner[i]);
        });
        lines.forEach((line, k) => tl.fromTo(line.els, { yPercent: 115 }, { yPercent: 0, duration: 0.75, ease: 'expo.out' }, t0 + k * 0.14));
        break;
      }
      case 'slam':
      case 'extrusion': {
        const step = Math.min(0.38, Math.max(0.12, (avail * 0.6) / Math.max(1, words.length)));
        words.forEach((w, i) => {
          tl.fromTo(w, { scale: 2.3, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.17, ease: 'power4.in' }, t0 + i * step);
          if (t.style === 'extrusion') {
            tl.fromTo(w, { '--d': 0 }, { '--d': 46, duration: 0.09, ease: 'power2.out', immediateRender: false }, t0 + i * step + 0.17);
            tl.to(w, { '--d': 22, duration: 0.5, ease: 'power3.out' }, t0 + i * step + 0.26);
          }
          const F = $('F-' + scene.id);
          if (F && !scene.effects.includes('punch-in')) {
            tl.fromTo(F, { scale: 1 + 0.025 * i }, { scale: 1 + 0.025 * (i + 1), duration: 0.12, ease: 'power3.out', immediateRender: false }, t0 + i * step + 0.17);
          }
        });
        break;
      }
      case 'blur-in':
        tl.fromTo(words, { opacity: 0, filter: 'blur(18px)', scale: 1.08 },
          { opacity: 1, filter: 'blur(0px)', scale: 1, duration: 0.75, ease: 'power2.out', stagger: Math.min(0.08, avail / 3 / Math.max(1, words.length)) }, t0);
        break;
      case 'typewriter': {
        const per = Math.min(0.055, (avail * 0.6) / Math.max(1, chars.length));
        tl.set(chars, { opacity: 0 }, 0);
        chars.forEach((ch, k) => tl.set(ch, { opacity: 1 }, t0 + k * per));
        const caret = $('CR-' + scene.id);
        if (caret) {
          for (let k = 0; t0 + k * 0.5 < end; k++) tl.set(caret, { opacity: k % 2 ? 0 : 1 }, t0 + k * 0.5);
        }
        break;
      }
      case 'tracking-in': {
        // Tracking via transforms (letter-spacing tweens snap to whole pixels): every letter slides in from a wider spread.
        const mid = tb.offsetWidth / 2;
        chars.forEach((ch) => {
          const x0 = (ch.offsetLeft + ch.offsetWidth / 2 - mid) * 0.32;
          tl.fromTo(ch, { x: x0, opacity: 0 }, { x: 0, opacity: 1, duration: 1.1, ease: 'power3.out' }, t0);
        });
        break;
      }
      case 'cascade':
        tl.fromTo(chars, { yPercent: -70, opacity: 0, rotation: -10 },
          { yPercent: 0, opacity: 1, rotation: 0, duration: 0.5, ease: 'back.out(2)', stagger: Math.min(0.03, (avail * 0.5) / Math.max(1, chars.length)) }, t0);
        break;
      case 'highlight': {
        rise(0.06);
        all(tb, '.mk').forEach((mk, k) => tl.fromTo(mk, { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: 'power2.out' }, t0 + 0.45 + k * 0.12));
        break;
      }
      case 'shimmer':
        rise(0.06);
        tl.fromTo(inner, { backgroundPosition: '100% 0' }, { backgroundPosition: '0% 0', duration: 1.0, ease: 'power2.inOut' }, t0 + 0.6);
        break;
      case 'lower-third': {
        const panel = $('LP-' + scene.id), bar = $('LB-' + scene.id);
        tl.fromTo(panel, { clipPath: 'inset(0% 100% 0% 0%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: 0.5, ease: 'power3.out' }, t0);
        tl.fromTo(bar, { scaleY: 0 }, { scaleY: 1, duration: 0.35, ease: 'power3.out' }, t0);
        tl.fromTo(inner, { yPercent: 115 }, { yPercent: 0, duration: 0.5, ease: 'power3.out', stagger: 0.04 }, t0 + 0.2);
        break;
      }
      case 'scramble': {
        const glyphs = 'ABCDEFGHJKLMNPQRSTUVWXYZÅÄÖ0123456789#%&';
        const real = chars.map((c) => c.textContent);
        const p = { v: 0 };
        const len = Math.min(1.0, avail * 0.6);
        tl.fromTo(p, { v: 0 }, {
          v: 1, duration: len, ease: 'none',
          onUpdate: () => {
            const done = p.v * real.length;
            const tick = Math.floor(p.v * 30);
            chars.forEach((c, k) => {
              if (real[k] === ' ') return;
              c.textContent = k < done || p.v >= 1 ? real[k] : glyphs[Math.floor(rnd(k + tick * 31, 7) * glyphs.length)];
            });
          },
        }, t0);
        tl.fromTo(tb, { opacity: 0 }, { opacity: 1, duration: 0.15 }, t0);
        break;
      }
      case 'caption': {
        const per = avail / Math.max(1, words.length);
        tl.set(words, { opacity: 0 }, 0);
        words.forEach((w, i) => {
          const at = t0 + i * per;
          tl.set(w, { opacity: 1 }, at);
          tl.fromTo(w, { scale: 1.25 }, { scale: 1, duration: 0.14, ease: 'power3.out' }, at);
          if (i < words.length - 1) tl.set(w, { opacity: 0 }, at + per);
        });
        break;
      }
      default:
        rise(0.06);
    }
    // Hard swaps (cut, flash, glitch) or the end of the film: get the text out cleanly first.
    if (next && (!next.transition || next.transition.cut)) {
      tl.to(box, { opacity: 0, duration: 0.18, ease: 'power1.in' }, end - 0.2);
    } else if (next && !['whip', 'push'].includes(next.transition.type)) {
      // Dissolving transitions: clear the words before the next scene's picture arrives, so two texts never mix.
      tl.to(box, { opacity: 0, duration: 0.2, ease: 'power1.in' }, Math.max(t0 + 0.6, end - next.transition.d / 2 - 0.2));
    }
  }

  // ------------------------------------------------------------------ end card
  function endCard(e) {
    if (!e) return;
    const id = e.id;
    tl.fromTo($('EB-' + id), { scale: 1.12 }, { scale: 1, duration: e.end - e.winStart, ease: 'power1.out' }, e.winStart);
    const t0 = e.start + 0.1;
    const logo = $('ELW-' + id);
    if (logo) tl.fromTo(logo, { scale: 0.72, opacity: 0, filter: 'blur(14px)' }, { scale: 1, opacity: 1, filter: 'blur(0px)', duration: 0.8, ease: 'expo.out' }, t0);
    const tb = $('TB-' + id);
    if (tb) tl.fromTo(all(tb, '.wi'), { yPercent: 115 }, { yPercent: 0, duration: 0.65, ease: 'power4.out', stagger: 0.06 }, t0 + 0.25);
    const pill = $('EP-' + id);
    if (pill) tl.fromTo(pill, { yPercent: 70, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.55, ease: 'power3.out' }, t0 + 0.55);
    const sw = $('SW-' + id);
    if (sw) tl.fromTo(sw, { xPercent: -130 }, { xPercent: 130, duration: 1.2, ease: 'power2.inOut' }, t0 + 0.9);
    const tex = $('GT-' + id);
    if (tex) {
      for (let i = 0; e.winStart + i / 24 < e.end; i++) tl.set(tex, { x: (rnd(i, 4) - 0.5) * 240, y: (rnd(i, 5) - 0.5) * 240 }, e.winStart + i / 24);
    }
  }

  function build() {
    const scenes = C.scenes.concat(C.endcard ? [C.endcard] : []);
    scenes.forEach((s) => { if (s.text) fit(s); });
    scenes.forEach((s, i) => {
      show(s);
      transitionIn(s, scenes[i - 1]);
      if (!s.isEnd) {
        effects(s);
        text(s, scenes[i + 1]);
      }
    });
    endCard(C.endcard);
    tl.to({}, { duration: C.total }, 0);
    window.__timelines['main'] = tl;
  }

  if (document.fonts && document.fonts.ready) document.fonts.ready.then(build);
  else build();
})();
