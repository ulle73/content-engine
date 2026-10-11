/* Cut template runtime. Inlined into the generated index.html by compose.js (after GLUE_WORDS and breakLines).
 * Reads the JSON config in #cut-config and builds ONE paused, seekable GSAP timeline (window.__timelines.main).
 * Deterministic: no clocks, no Math.random (hash-based noise), every tween placed at an absolute time.
 * After text layout it reports the measured text boxes as one console line "[cut-layout] {...}" which the renderer's
 * QA step reads (safe zones, line breaks, font loading). */
(function () {
  const C = JSON.parse(document.getElementById('cut-config').textContent);
  const $ = (id) => document.getElementById(id);
  const all = (root, sel) => Array.from(root.querySelectorAll(sel));
  const rnd = (i, salt) => { const x = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453; return x - Math.floor(x); };
  const tl = gsap.timeline({ paused: true });
  // Three curves for everything that is UI motion; the camera has its own slow sine.
  const E = { enter: 'power3.out', move: 'power3.inOut', exit: 'power2.in', camera: 'sine.inOut' };
  const BEATS = C.beats ? C.beats.times.map((b) => ({ t: b[0], down: b[1] === 1 })) : [];
  const layoutReport = [];

  /** Beat-quantized step for n staggered hits inside `avail` seconds (falls back to `fallback`). */
  function beatStep(n, avail, fallback) {
    if (!C.beats || n < 2) return fallback;
    const p = C.beats.period;
    for (const step of [p, p / 2, p / 4]) if (step >= 0.12 && step * (n - 1) <= avail * 0.65) return step;
    return fallback;
  }

  // ------------------------------------------------------------------ typography: fit + balanced line breaks
  function offsetIn(el, stop) {
    let x = 0, y = 0;
    for (let n = el; n && n !== stop; n = n.offsetParent) { x += n.offsetLeft; y += n.offsetTop; }
    return { x, y };
  }

  function groupsOf(tb, style) {
    if (style === 'caption') return [];
    const chunks = all(tb, '.ck');
    return chunks.length ? chunks : [tb];
  }

  function lineCount(ws) {
    const tops = [];
    ws.forEach((w) => { const t = w.offsetTop; if (!tops.some((x) => Math.abs(x - t) < 3)) tops.push(t); });
    return tops.length;
  }

  function layout(scene) {
    const box = $('X-' + scene.id);
    const tb = $('TB-' + scene.id);
    if (!box || !tb) return;
    const t = scene.text;
    tb.style.lineHeight = String(t.leading);
    tb.style.letterSpacing = t.tracking + 'em';
    const sizes = t.sizes.slice();
    for (let s = sizes[sizes.length - 1]; s > 26;) { s = Math.floor(s * 0.92); sizes.push(s); }
    const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;white-space:pre;left:0;top:0';
    probe.textContent = '          ';
    // Set the block at one size with balanced breaks; null when it does not fit.
    const attempt = (fs, maxLines) => {
      tb.style.fontSize = fs + 'px';
      all(tb, 'br.lb').forEach((b) => b.remove());
      tb.appendChild(probe);
      const space = probe.offsetWidth / 10;
      probe.remove();
      const lines = [];
      if (t.style === 'caption') {
        if (!all(tb, '.w').every((w) => w.offsetWidth <= t.maxW + 1)) return null;
      } else {
        for (const g of groupsOf(tb, t.style)) {
          const ws = Array.from(g.children).filter((c) => c.classList.contains('w'));
          const texts = ws.map((w) => w.textContent);
          const res = breakLines(ws.map((w) => w.offsetWidth), space, t.maxW, { texts, maxChars: t.maxChars, maxLines });
          if (!res) return null;
          res.lines.forEach(([a, b], k) => {
            lines.push(texts.slice(a, b).join(' '));
            if (k < res.lines.length - 1) { const br = document.createElement('br'); br.className = 'lb'; ws[b - 1].after(br); }
          });
          if (lineCount(ws) !== res.lines.length) return null;
        }
      }
      return tb.scrollWidth <= t.maxW + 2 && tb.offsetHeight <= t.maxH ? { fs, lines } : null;
    };
    let chosen = null;
    let at = -1;
    for (let i = 0; i < sizes.length && !chosen; i++) {
      chosen = attempt(sizes[i], i < t.sizes.length ? t.maxLines : t.maxLines + 3);
      at = i;
    }
    // Copy text reads better in fewer lines: one step down the scale is worth it when it saves a line.
    if (chosen && chosen.lines.length >= 3 && !/slam|extrusion|caption|chunk/.test(t.style) && at + 1 < t.sizes.length) {
      const smaller = attempt(sizes[at + 1], t.maxLines);
      if (smaller && smaller.lines.length < chosen.lines.length) chosen = smaller;
      else chosen = attempt(sizes[at], t.maxLines);
    }
    if (!chosen) chosen = { fs: sizes[sizes.length - 1], lines: [], forced: true };
    // Measured box of the words (canvas px) for the safe-zone QA and the plate.
    const ws = all(tb, '.w');
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const root = $('root');
    ws.forEach((w) => {
      const p = offsetIn(w, root);
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x + w.offsetWidth); y1 = Math.max(y1, p.y + w.offsetHeight);
    });
    const plate = $('PL-' + scene.id);
    if (plate && ws.length) {
      const o = offsetIn(box, root);
      const pad = [chosen.fs * 0.32, chosen.fs * 0.5];
      Object.assign(plate.style, {
        left: (x0 - o.x - pad[1]) + 'px', top: (y0 - o.y - pad[0]) + 'px',
        width: (x1 - x0 + pad[1] * 2) + 'px', height: (y1 - y0 + pad[0] * 2) + 'px', borderRadius: Math.round(chosen.fs * 0.28) + 'px',
      });
    }
    const last = chosen.lines[chosen.lines.length - 1] || '';
    layoutReport.push({
      id: scene.id, fs: chosen.fs, lines: chosen.lines, forced: Boolean(chosen.forced),
      orphan: chosen.lines.length > 1 && !/\s/.test(last) && ws.length >= 3,
      box: ws.length ? { x: Math.round(x0), y: Math.round(y0), w: Math.round(x1 - x0), h: Math.round(y1 - y0) } : null,
      legible: t.legible ? t.legible.mode : null,
    });
  }

  // ------------------------------------------------------------------ layer visibility and transitions
  function show(scene) {
    const L = $('L-' + scene.id);
    tl.set(L, { opacity: 1 }, scene.winStart);
    if (scene.winEnd < C.total - 1e-3) tl.set(L, { opacity: 0 }, scene.winEnd);
  }

  /** Directional motion blur through the scene's SVG filter (x or y), peaking mid-move. */
  function motionBlur(el, side, id, axis, from, to, d, at, ease) {
    const g = $('MB' + side + 'G-' + id);
    if (!g) return;
    const val = (v) => (axis === 'x' ? v + ' 0' : '0 ' + v);
    tl.set(el, { filter: 'url(#MB' + side + '-' + id + ')' }, at);
    tl.fromTo(g, { attr: { stdDeviation: val(from) } }, { attr: { stdDeviation: val(to) }, duration: d, ease, immediateRender: false }, at);
    tl.set(el, { filter: 'none' }, at + d + 0.001);
  }

  function transitionIn(scene, prev) {
    const t = scene.transition;
    if (!t || !prev) return;
    const T = scene.start, d = t.d, a = T - d / 2;
    const inn = $('T-' + scene.id), out = $('T-' + prev.id);
    const outOpts = { immediateRender: false };
    switch (t.type) {
      case 'fade':
        tl.fromTo(inn, { opacity: 0 }, { opacity: 1, duration: d, ease: 'sine.inOut' }, a);
        break;
      case 'blur':
        tl.fromTo(inn, { opacity: 0, filter: 'blur(28px)' }, { opacity: 1, filter: 'blur(0px)', duration: d, ease: E.enter }, a);
        tl.fromTo(out, { filter: 'blur(0px)' }, { filter: 'blur(28px)', duration: d, ease: E.exit, ...outOpts }, a);
        tl.set(inn, { filter: 'none' }, a + d + 0.001);
        break;
      case 'flash': {
        const f = $('flash');
        tl.fromTo(f, { opacity: 0 }, { opacity: 1, duration: d / 2, ease: E.exit, ...outOpts }, a);
        tl.fromTo(f, { opacity: 1 }, { opacity: 0, duration: d / 2 + 0.12, ease: E.enter, ...outOpts }, T);
        tl.fromTo(inn, { scale: 1.08 }, { scale: 1, duration: 0.5, ease: E.enter }, T);
        break;
      }
      case 'whip':
        tl.fromTo(inn, { xPercent: 100 }, { xPercent: 0, duration: d, ease: E.move }, a);
        tl.fromTo(out, { xPercent: 0 }, { xPercent: -100, duration: d, ease: E.move, ...outOpts }, a);
        motionBlur(out, 'O', scene.id, 'x', 0, 70, d / 2, a, E.exit);
        motionBlur(inn, 'I', scene.id, 'x', 70, 0, d / 2, T, E.enter);
        break;
      case 'push':
        tl.fromTo(inn, { yPercent: 100 }, { yPercent: 0, duration: d, ease: E.move }, a);
        tl.fromTo(out, { yPercent: 0 }, { yPercent: -100, duration: d, ease: E.move, ...outOpts }, a);
        motionBlur(out, 'O', scene.id, 'y', 0, 55, d / 2, a, E.exit);
        motionBlur(inn, 'I', scene.id, 'y', 55, 0, d / 2, T, E.enter);
        break;
      case 'speed-ramp':
        // Cut the curve: the outgoing shot accelerates out, hard cut at top speed, the incoming one brakes in.
        tl.fromTo(out, { xPercent: 0 }, { xPercent: -16, duration: d / 2, ease: 'power3.in', ...outOpts }, a);
        tl.fromTo(inn, { xPercent: 16 }, { xPercent: 0, duration: d / 2, ease: E.enter }, T);
        motionBlur(out, 'O', scene.id, 'x', 0, 60, d / 2, a, 'power3.in');
        motionBlur(inn, 'I', scene.id, 'x', 60, 0, d / 2, T, E.enter);
        break;
      case 'zoom':
        tl.fromTo(out, { scale: 1, opacity: 1, filter: 'blur(0px)' }, { scale: 1.7, opacity: 0, filter: 'blur(14px)', duration: d, ease: 'power3.in', ...outOpts }, a);
        tl.fromTo(inn, { scale: 1.45, opacity: 0, filter: 'blur(14px)' }, { scale: 1, opacity: 1, filter: 'blur(0px)', duration: d, ease: E.enter }, a);
        tl.set(inn, { filter: 'none' }, a + d + 0.001);
        break;
      case 'wipe': {
        tl.fromTo(inn, { clipPath: 'inset(0% 0% 0% 100%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: d, ease: E.move }, a);
        const edge = $('E-' + scene.id);
        if (edge) {
          tl.fromTo(edge, { x: C.W }, { x: -160, duration: d, ease: E.move }, a);
        }
        break;
      }
      case 'iris': {
        const r = Math.ceil(Math.hypot(C.W, C.H) / 2) + 20;
        tl.fromTo(inn, { clipPath: 'circle(0px at 50% 50%)' }, { clipPath: `circle(${r}px at 50% 50%)`, duration: d, ease: E.move }, a);
        break;
      }
      case 'light-leak': {
        tl.fromTo(inn, { opacity: 0 }, { opacity: 1, duration: d, ease: 'sine.inOut' }, a);
        const leak = $('LK-' + scene.id);
        if (leak) {
          tl.fromTo(leak, { xPercent: -45, opacity: 0 }, { xPercent: 35, duration: d * 1.4, ease: 'sine.inOut' }, a - d * 0.2);
          tl.to(leak, { opacity: 1, duration: d * 0.55, ease: E.enter }, a - d * 0.2);
          tl.to(leak, { opacity: 0, duration: d * 0.85, ease: E.exit }, a + d * 0.35);
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
          { scale: 1.17, xPercent: 1.6 * dir, yPercent: -0.8 * dir, duration: dur, ease: E.camera }, ws);
        break;
      case 'push-in':
        tl.fromTo(cam, { scale: 1.02 }, { scale: 1.15, duration: dur, ease: E.camera }, ws);
        break;
      case 'pull-back':
        tl.fromTo(cam, { scale: 1.26 }, { scale: 1.03, duration: dur, ease: 'power2.out' }, ws);
        break;
      case 'micro-push':
        tl.fromTo(cam, { scale: 1.03, xPercent: 0.4 * dir }, { scale: 1.085, xPercent: -0.4 * dir, duration: dur, ease: E.camera }, ws);
        break;
      default:
        break;
    }
    if (fx.includes('punch-in')) {
      const at = scene.textAt || scene.start + 0.05;
      tl.fromTo(F, { scale: 1 }, { scale: 1.16, duration: 0.24, ease: E.enter }, at);
    }
    if (fx.includes('beat-punch')) {
      // A short zoom kick and a light blink on every downbeat (every beat when the bar is long); one kick without music.
      const pf = $('PF-' + scene.id);
      const lo = scene.start + 0.15, hi = scene.end - 0.25;
      let hits = BEATS.filter((b) => b.down && b.t >= lo && b.t <= hi).map((b) => b.t);
      if (hits.length < 2) hits = BEATS.filter((b) => b.t >= lo && b.t <= hi).map((b) => b.t).filter((_, k) => k % 2 === 0);
      if (!hits.length) hits = [scene.textAt || scene.start + 0.2];
      const len = Math.min(0.42, (C.beats ? C.beats.period : 0.5) * 0.8);
      hits.forEach((at) => {
        tl.fromTo(shk, { scale: 1 }, { scale: 1.035, duration: len * 0.18, ease: E.enter, immediateRender: false }, at - 0.02);
        tl.to(shk, { scale: 1, duration: len * 0.82, ease: E.move }, at - 0.02 + len * 0.18);
        if (pf) tl.fromTo(pf, { opacity: 0.16 }, { opacity: 0, duration: len, ease: E.exit, immediateRender: false }, at - 0.02);
      });
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
        { filter: 'brightness(1) contrast(1) saturate(1)', duration: len, ease: E.move }, scene.start + 0.1);
      const bloom = $('BL-' + scene.id);
      if (bloom) {
        tl.fromTo(bloom, { opacity: 0, scale: 0.6 }, { opacity: 0.85, scale: 1.15, duration: len * 0.7, ease: E.enter }, scene.start + len * 0.35);
        tl.to(bloom, { opacity: 0.18, duration: len * 0.6, ease: E.move }, scene.start + len * 1.05);
      }
    }
    if (fx.includes('focus-rack')) {
      tl.fromTo(B, { filter: 'blur(18px)' }, { filter: 'blur(0px)', duration: 0.9, ease: E.enter }, scene.start + 0.05);
    }
    const tex = $('GT-' + scene.id);
    if (tex) {
      const step = 1 / 24;
      for (let i = 0; ws + i * step < we; i++) {
        tl.set(tex, { x: (rnd(i, 1) - 0.5) * 240, y: (rnd(i, 2) - 0.5) * 240 }, ws + i * step);
      }
    }
    if (fx.includes('light-sweep')) {
      const sw = $('SW-' + scene.id);
      tl.fromTo(sw, { xPercent: -130 }, { xPercent: 130, duration: 1.1, ease: E.move }, scene.start + Math.min(1.2, (scene.end - scene.start) * 0.35));
    }
    if (fx.includes('leak-overlay')) {
      const lo = $('LO-' + scene.id);
      tl.fromTo(lo, { xPercent: -30, opacity: 0 }, { xPercent: 25, duration: dur, ease: 'sine.inOut' }, ws);
      tl.to(lo, { opacity: 0.75, duration: dur * 0.4, ease: 'sine.out' }, ws);
      tl.to(lo, { opacity: 0.25, duration: dur * 0.6, ease: 'sine.in' }, ws + dur * 0.4);
    }
    const logo = $('LG-' + scene.id);
    if (logo) {
      const at = scene.textAt || scene.start + 0.15;
      const ring = $('LR-' + scene.id);
      if (logo.classList.contains('logo-sting')) {
        tl.fromTo(logo, { opacity: 0, scale: 1.7 }, { opacity: 1, scale: 1, duration: 0.28, ease: 'power4.in' }, at);
        const f = $('flash');
        tl.fromTo(f, { opacity: 0.55 }, { opacity: 0, duration: 0.24, ease: E.enter, immediateRender: false }, at + 0.28);
        if (ring) tl.fromTo(ring, { opacity: 0.9, scale: 0.5 }, { opacity: 0, scale: 2.4, duration: 0.75, ease: E.enter, immediateRender: false }, at + 0.28);
      } else {
        tl.fromTo(logo, { opacity: 0.55, filter: 'blur(26px)', scale: 1.04 }, { opacity: 1, filter: 'blur(0px)', scale: 1, duration: 0.7, ease: E.enter }, at);
        tl.set(logo, { filter: 'none' }, at + 0.701);
        const f = $('flash');
        tl.fromTo(f, { opacity: 0.35 }, { opacity: 0, duration: 0.3, ease: E.enter, immediateRender: false }, at + 0.4);
      }
    }
  }

  // ------------------------------------------------------------------ text styles
  function text(scene, next) {
    const t = scene.text;
    if (!t) return;
    const box = $('X-' + scene.id), tb = $('TB-' + scene.id), scrim = $('SC-' + scene.id), plate = $('PL-' + scene.id);
    const words = all(tb, '.w'), inner = all(tb, '.wi'), chars = all(tb, '.ch');
    const t0 = scene.textAt || scene.start + 0.12;
    const end = scene.end;
    const avail = Math.max(0.6, end - t0 - 0.3);
    if (scrim) tl.fromTo(scrim, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: 'sine.out' }, Math.max(scene.winStart, t0 - 0.25));
    if (plate) tl.fromTo(plate, { opacity: 0, scaleX: 0.92 }, { opacity: 1, scaleX: 1, duration: 0.4, ease: E.enter }, Math.max(scene.winStart, t0 - 0.08));
    const rise = (stagger) => tl.fromTo(inner, { yPercent: 115 }, { yPercent: 0, duration: 0.6, ease: E.enter, stagger }, t0);
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
        const step = beatStep(lines.length, avail, 0.14);
        lines.forEach((line, k) => tl.fromTo(line.els, { yPercent: 115 }, { yPercent: 0, duration: 0.75, ease: E.enter }, t0 + k * step));
        break;
      }
      case 'slam':
      case 'extrusion': {
        const step = beatStep(words.length, avail, Math.min(0.38, Math.max(0.12, (avail * 0.6) / Math.max(1, words.length))));
        words.forEach((w, i) => {
          // Lands (scale 1) on the beat: the in-tween ends at t0 + i * step.
          const land = t0 + i * step;
          tl.fromTo(w, { scale: 2.3, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.17, ease: 'power4.in' }, Math.max(scene.winStart, land - 0.17));
          if (t.style === 'extrusion') {
            tl.fromTo(w, { '--d': 0 }, { '--d': 46, duration: 0.09, ease: E.enter, immediateRender: false }, land);
            tl.to(w, { '--d': 22, duration: 0.5, ease: E.enter }, land + 0.09);
          }
          const F = $('F-' + scene.id);
          if (F && !scene.effects.includes('punch-in')) {
            tl.fromTo(F, { scale: 1 + 0.025 * i }, { scale: 1 + 0.025 * (i + 1), duration: 0.12, ease: E.enter, immediateRender: false }, land);
          }
        });
        break;
      }
      case 'blur-in':
        tl.fromTo(words, { opacity: 0, filter: 'blur(18px)', scale: 1.08 },
          { opacity: 1, filter: 'blur(0px)', scale: 1, duration: 0.75, ease: E.enter, stagger: Math.min(0.08, avail / 3 / Math.max(1, words.length)) }, t0);
        tl.set(words, { filter: 'none' }, t0 + 0.75 + 0.08 * words.length + 0.01);
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
          tl.fromTo(ch, { x: x0, opacity: 0 }, { x: 0, opacity: 1, duration: 1.1, ease: E.enter }, t0);
        });
        break;
      }
      case 'cascade':
        tl.fromTo(chars, { yPercent: -70, opacity: 0, rotation: -10 },
          { yPercent: 0, opacity: 1, rotation: 0, duration: 0.5, ease: 'back.out(2)', stagger: Math.min(0.03, (avail * 0.5) / Math.max(1, chars.length)) }, t0);
        break;
      case 'highlight': {
        rise(0.06);
        all(tb, '.mk').forEach((mk, k) => tl.fromTo(mk, { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: E.move }, t0 + 0.45 + k * 0.12));
        break;
      }
      case 'shimmer':
        rise(0.06);
        tl.fromTo(inner, { backgroundPosition: '100% 0' }, { backgroundPosition: '0% 0', duration: 1.0, ease: E.move }, t0 + 0.6);
        break;
      case 'lower-third': {
        const panel = $('LP-' + scene.id), bar = $('LB-' + scene.id);
        tl.fromTo(panel, { clipPath: 'inset(0% 100% 0% 0%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: 0.5, ease: E.enter }, t0);
        tl.fromTo(bar, { scaleY: 0 }, { scaleY: 1, duration: 0.35, ease: E.enter }, t0);
        tl.fromTo(inner, { yPercent: 115 }, { yPercent: 0, duration: 0.5, ease: E.enter, stagger: 0.04 }, t0 + 0.2);
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
        tl.fromTo(tb, { opacity: 0 }, { opacity: 1, duration: 0.15, ease: E.enter }, t0);
        break;
      }
      case 'caption': {
        const per = beatStep(words.length, avail * 1.5, avail / Math.max(1, words.length));
        tl.set(words, { opacity: 0 }, 0);
        words.forEach((w, i) => {
          const at = t0 + i * per;
          tl.set(w, { opacity: 1 }, at);
          tl.fromTo(w, { scale: 1.18 }, { scale: 1, duration: 0.14, ease: E.enter }, at);
          if (i < words.length - 1) tl.set(w, { opacity: 0 }, at + per);
        });
        break;
      }
      case 'chunk': {
        // 2–4 word phrases swapped on a single frame (on the beat with music); no shadow tricks, no box.
        const cks = all(tb, '.ck');
        const per = beatStep(cks.length, avail * 1.5, avail / Math.max(1, cks.length));
        tl.set(cks, { opacity: 0 }, 0);
        cks.forEach((ck, i) => {
          const at = t0 + i * per;
          tl.set(ck, { opacity: 1 }, at);
          if (i < cks.length - 1) tl.set(ck, { opacity: 0 }, at + per);
        });
        break;
      }
      default:
        rise(0.06);
    }
    // Hard swaps (cut, flash, glitch, speed ramp) or the end of the film: get the text out cleanly first.
    const fadeOut = [box, scrim, plate].filter(Boolean);
    if (next && (!next.transition || next.transition.cut)) {
      tl.to(fadeOut, { opacity: 0, duration: 0.18, ease: E.exit }, end - 0.2);
    } else if (next && !['whip', 'push'].includes(next.transition.type)) {
      // Dissolving transitions: clear the words before the next scene's picture arrives, so two texts never mix.
      tl.to(fadeOut, { opacity: 0, duration: 0.2, ease: E.exit }, Math.max(t0 + 0.6, end - next.transition.d / 2 - 0.2));
    }
  }

  // ------------------------------------------------------------------ end card
  function endCard(e) {
    if (!e) return;
    const id = e.id;
    tl.fromTo($('EB-' + id), { scale: 1.12 }, { scale: 1, duration: e.end - e.winStart, ease: 'power1.out' }, e.winStart);
    const t0 = e.textAt || e.start + 0.1;
    const logo = $('ELW-' + id);
    if (logo) tl.fromTo(logo, { scale: 0.72, opacity: 0, filter: 'blur(14px)' }, { scale: 1, opacity: 1, filter: 'blur(0px)', duration: 0.8, ease: 'expo.out' }, t0);
    if (logo) tl.set(logo, { filter: 'none' }, t0 + 0.801);
    const tb = $('TB-' + id);
    if (tb) tl.fromTo(all(tb, '.wi'), { yPercent: 115 }, { yPercent: 0, duration: 0.65, ease: E.enter, stagger: 0.06 }, t0 + 0.25);
    const pill = $('EP-' + id);
    if (pill) tl.fromTo(pill, { yPercent: 70, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.55, ease: E.enter }, t0 + 0.55);
    const sw = $('SW-' + id);
    if (sw) tl.fromTo(sw, { xPercent: -130 }, { xPercent: 130, duration: 1.2, ease: E.move }, t0 + 0.9);
    const tex = $('GT-' + id);
    if (tex) {
      for (let i = 0; e.winStart + i / 24 < e.end; i++) tl.set(tex, { x: (rnd(i, 4) - 0.5) * 240, y: (rnd(i, 5) - 0.5) * 240 }, e.winStart + i / 24);
    }
  }

  function build() {
    const scenes = C.scenes.concat(C.endcard ? [C.endcard] : []);
    scenes.forEach((s) => { if (s.text) layout(s); });
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
    // A bundled face that failed to load (bad file, missing glyph table) – unused faces stay 'unloaded', which is fine.
    const fonts = [];
    if (document.fonts && document.fonts.forEach) {
      document.fonts.forEach((f) => { if (f.status === 'error') fonts.push(f.family.replace(/['"]/g, '') + ' ' + f.weight); });
    }
    console.warn('[cut-layout] ' + JSON.stringify({ format: C.format, texts: layoutReport, missingFonts: fonts }));
  }

  if (document.fonts && document.fonts.ready) document.fonts.ready.then(build);
  else build();
})();
