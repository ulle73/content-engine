/* Live Carousel engine: everything is a pure function of time (seek-safe both ways). */
(function () {
  const E = {};
  const TAU = Math.PI * 2;

  E.clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  E.lerp = (a, b, s) => a + (b - a) * s;
  E.prog = (t, t0, t1) => E.clamp((t - t0) / (t1 - t0));
  E.easeInOut = (s) => (s < 0.5 ? 4 * s * s * s : 1 - Math.pow(-2 * s + 2, 3) / 2);
  E.easeOut = (s) => 1 - Math.pow(1 - s, 3);
  E.easeIn = (s) => s * s * s;
  E.easeOutQuint = (s) => 1 - Math.pow(1 - s, 5);
  E.easeOutBack = (s, k = 1.7) => 1 + (k + 1) * Math.pow(s - 1, 3) + k * Math.pow(s - 1, 2);
  E.hash = (n) => {
    const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  };

  /* Damped spring impulse: 0 at dt=0, kicks to +1-ish, rings out. */
  E.kick = (dt, freq = 3, damp = 7) =>
    dt < 0 ? 0 : Math.exp(-damp * dt) * Math.sin(TAU * freq * dt);
  /* Damped spring settle: 0 -> 1 with overshoot. */
  E.settle = (dt, freq = 2.2, damp = 6) =>
    dt <= 0 ? 0 : 1 - Math.exp(-damp * dt) * Math.cos(TAU * freq * dt);
  /* Smooth pulse (gaussian) centred at c, width w. */
  E.pulse = (t, c, w) => Math.exp(-Math.pow((t - c) / w, 2));

  /*
   * Ball path: waypoints [{t, x, y, h, ease, contact}] where (x, y) is the ball CENTRE.
   * Segment i -> i+1 is a parabola: x eases (default linear), y = lerp - 4h s(1-s).
   * contact: {q, dir} marks a surface hit at that waypoint (squash amount).
   */
  E.makePath = (pts) => {
    const at = (t) => {
      if (t <= pts[0].t) {
        const p = pts[0];
        return { x: p.x, y: p.y, vx: 0, vy: 0 };
      }
      for (let i = 0; i < pts.length - 1; i++) {
        const a = pts[i];
        const b = pts[i + 1];
        if (t <= b.t) {
          const T = b.t - a.t;
          const s = (t - a.t) / T;
          const h = b.h || 0;
          const ez = b.ease || "linear";
          let sx = s;
          let dsx = 1;
          if (ez === "inOut") {
            sx = E.easeInOut(s);
            dsx = s < 0.5 ? 12 * s * s : 3 * Math.pow(-2 * s + 2, 2);
          } else if (ez === "out") {
            sx = E.easeOut(s);
            dsx = 3 * Math.pow(1 - s, 2);
          } else if (ez === "in") {
            sx = E.easeIn(s);
            dsx = 3 * s * s;
          }
          const x = a.x + (b.x - a.x) * sx;
          const y = a.y + (b.y - a.y) * sx - 4 * h * s * (1 - s);
          const vx = ((b.x - a.x) * dsx) / T;
          const vy = ((b.y - a.y) * dsx - 4 * h * (1 - 2 * s)) / T;
          return { x, y, vx, vy };
        }
      }
      const p = pts[pts.length - 1];
      return { x: p.x, y: p.y, vx: 0, vy: 0 };
    };
    const contacts = pts.filter((p) => p.contact);
    return { at, pts, contacts };
  };

  /*
   * Ball renderer: pos > squash (origin bottom) > stretch (rotate along velocity).
   * Returns the deformation state so callers can reuse it.
   */
  E.ballState = (path, t, r, opts = {}) => {
    const p = path.at(t);
    const speed = Math.hypot(p.vx, p.vy);
    const kStretch = opts.stretch === undefined ? 1 : opts.stretch;
    let st = E.clamp((speed / 5200) * kStretch, 0, 0.42 * kStretch);
    let q = 0;
    for (const c of path.contacts) {
      const dt = t - c.t;
      if (dt > -0.06 && dt < 0.5) {
        const amt = c.contact.q === undefined ? 0.45 : c.contact.q;
        // fast squash over ~2 frames, springy recovery
        const env = dt < 0 ? E.pulse(dt, 0, 0.03) : Math.exp(-dt * 16) * Math.cos(dt * 38);
        q += amt * env;
        st *= E.clamp(Math.abs(dt) / 0.09);
      }
    }
    const ang = Math.atan2(p.vy, p.vx);
    return { x: p.x, y: p.y, vx: p.vx, vy: p.vy, st, q, ang, r };
  };

  E.applyBall = (els, s) => {
    // els: {pos, squash, stretch}
    els.pos.style.transform = `translate(${s.x - s.r}px, ${s.y - s.r}px)`;
    const sq = 1 + s.q;
    els.squash.style.transform = `scale(${sq}, ${1 / sq})`;
    const a = 1 + s.st;
    els.stretch.style.transform = `rotate(${s.ang}rad) scale(${a}, ${1 / a}) rotate(${-s.ang}rad)`;
  };

  E.makeBall = (parent, cls, r) => {
    const pos = document.createElement("div");
    pos.className = "ball-pos " + (cls || "");
    pos.style.width = pos.style.height = 2 * r + "px";
    const squash = document.createElement("div");
    squash.className = "ball-squash";
    const stretch = document.createElement("div");
    stretch.className = "ball-stretch";
    squash.appendChild(stretch);
    pos.appendChild(squash);
    parent.appendChild(pos);
    return { pos, squash, stretch };
  };

  /* Dot grid with shockwave ripples, drawn on a canvas. */
  E.makeGrid = (canvas, opts) => {
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    const gap = opts.gap || 40;
    const dots = [];
    for (let y = gap / 2 + 4; y < H; y += gap) {
      for (let x = gap / 2 + 4; x < W; x += gap) dots.push([x, y]);
    }
    return (t, waves, alive) => {
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = opts.color;
      for (const [x0, y0] of dots) {
        let dx = 0;
        let dy = 0;
        let grow = 0;
        for (const w of waves) {
          const dt = t - w.t;
          if (dt < 0 || dt > 1.6) continue;
          const ex = x0 - w.x;
          const ey = y0 - w.y;
          const d = Math.hypot(ex, ey) || 1;
          const R = dt * (w.v || 1500);
          const band = Math.exp(-Math.pow((d - R) / 70, 2)) * Math.exp(-dt * 2.2) * (w.a || 1);
          dx += (ex / d) * band * 26;
          dy += (ey / d) * band * 26;
          grow += band;
        }
        // gentle breathing when the scene is alive
        const br = alive ? alive * 0.6 * Math.sin(t * 3.1 + x0 * 0.013 + y0 * 0.009) : 0;
        const rad = 2.4 + grow * 3.2 + br;
        ctx.globalAlpha = E.clamp(0.22 + grow * 0.55, 0, 0.85);
        ctx.beginPath();
        ctx.arc(x0 + dx, y0 + dy, Math.max(0.6, rad), 0, TAU);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    };
  };

  /* Timeline ruler: ticks + frame labels continuing across slides, playhead, keyframe diamonds. */
  E.makeRuler = (root, opts) => {
    const { frameStart, frames, width } = opts;
    const px = width / frames; // px per frame
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", width);
    svg.setAttribute("height", 100);
    svg.setAttribute("viewBox", `0 0 ${width} 100`);
    svg.classList.add("ruler-svg");
    let ticks = "";
    for (let f = 0; f <= frames; f++) {
      const x = f * px;
      const gf = frameStart + f;
      const major = gf % 30 === 0;
      const mid = gf % 10 === 0;
      const h = major ? 30 : mid ? 18 : 9;
      ticks += `<line x1="${x.toFixed(2)}" y1="0" x2="${x.toFixed(2)}" y2="${h}" stroke-width="${major ? 3 : 2}" />`;
    }
    svg.innerHTML = `<g class="ruler-ticks">${ticks}</g>`;
    root.appendChild(svg);
    const labels = document.createElement("div");
    labels.className = "ruler-labels";
    for (let f = 0; f <= frames; f++) {
      const gf = frameStart + f;
      if (gf % 30 !== 0) continue;
      const l = document.createElement("div");
      l.className = "ruler-label";
      l.style.left = f * px + "px";
      const sec = gf / 30;
      l.textContent = String(Math.floor(sec / 60)).padStart(2, "0") + ":" + String(sec % 60).padStart(2, "0");
      labels.appendChild(l);
    }
    root.appendChild(labels);
    const head = document.createElement("div");
    head.className = "playhead";
    head.innerHTML = '<div class="playhead-cap"></div><div class="playhead-line"></div>';
    root.appendChild(head);
    const keys = (opts.keys || []).map((k) => {
      const d = document.createElement("div");
      d.className = "kf";
      d.style.left = (k / opts.duration) * width + "px";
      root.appendChild(d);
      return { t: k, el: d };
    });
    return (t) => {
      head.style.transform = `translateX(${(t / opts.duration) * width}px)`;
      for (const k of keys) {
        const dt = t - k.t;
        if (dt < 0) {
          k.el.style.opacity = 0;
          k.el.style.transform = "translate(-50%, 0) rotate(45deg) scale(0)";
        } else {
          const s = E.settle(dt, 2.6, 7);
          k.el.style.opacity = 1;
          k.el.style.transform = `translate(-50%, 0) rotate(45deg) scale(${s})`;
        }
      }
    };
  };

  /* Deterministic particle burst (diamonds / dots) from a point with gravity. */
  E.makeBurst = (parent, n, seed, cls) => {
    const parts = [];
    for (let i = 0; i < n; i++) {
      const d = document.createElement("div");
      d.className = "particle " + (cls || "");
      if (E.hash(seed + i * 7.3) > 0.55) d.classList.add("alt");
      parent.appendChild(d);
      const ang = -Math.PI / 2 + (E.hash(seed + i * 3.1) - 0.5) * Math.PI * 1.7;
      const spd = 520 + E.hash(seed + i * 5.7) * 900;
      parts.push({ el: d, ang, spd, rot: (E.hash(seed + i * 9.9) - 0.5) * 900, size: 0.6 + E.hash(seed + i * 1.3) * 0.9 });
    }
    return (t, t0, x, y, life = 1.1) => {
      const dt = t - t0;
      for (const p of parts) {
        if (dt < 0 || dt > life) {
          p.el.style.opacity = 0;
          continue;
        }
        const px = x + Math.cos(p.ang) * p.spd * dt;
        const py = y + Math.sin(p.ang) * p.spd * dt + 0.5 * 2600 * dt * dt;
        const o = 1 - Math.pow(dt / life, 2);
        p.el.style.opacity = o;
        p.el.style.transform = `translate(${px}px, ${py}px) rotate(${45 + p.rot * dt}deg) scale(${p.size * (1 - 0.4 * dt / life)})`;
      }
    };
  };

  /* ---------- layout helpers (build-time only) ---------- */
  E.rel = (el, root) => {
    let x = 0,
      y = 0,
      n = el;
    while (n && n !== root) {
      x += n.offsetLeft;
      y += n.offsetTop;
      n = n.offsetParent;
    }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight };
  };

  E.buildWord = (el) => {
    const word = el.dataset.word;
    el.innerHTML = "";
    return [...word].map((c) => {
      const s = document.createElement("span");
      s.className = "ch";
      s.textContent = c;
      // intentional-layering markers on the word apply to every glyph
      for (const attr of ["data-layout-allow-overlap", "data-layout-allow-occlusion"]) {
        if (el.hasAttribute(attr)) s.setAttribute(attr, "");
      }
      const b = document.createElement("i");
      b.style.cssText = "display:inline-block;width:0;height:0;vertical-align:baseline";
      s.appendChild(b);
      el.appendChild(s);
      return { el: s, c, base: b };
    });
  };

  /* Largest font-size (<= maxF) that fits at wdth >= minW, then tune wdth to fill target exactly. */
  E.fitWord = (el, chars, target, maxF = 400, minW = 52) => {
    const setW = (w) => chars.forEach((c) => c.el.style.setProperty("--w", w));
    let F = maxF;
    for (; F > 120; F -= 4) {
      el.style.fontSize = F + "px";
      setW(minW);
      if (el.scrollWidth <= target) break;
    }
    let lo = minW,
      hi = 150;
    for (let i = 0; i < 22; i++) {
      const mid = (lo + hi) / 2;
      setW(mid);
      if (el.scrollWidth > target) hi = mid;
      else lo = mid;
    }
    setW(lo);
    return { F, w: lo };
  };

  /* Per-glyph geometry: centre x, cap top, baseline (uses canvas ink metrics). */
  E.measureWord = (chars, F, root) => {
    const mc = document.createElement("canvas").getContext("2d");
    mc.font = `900 ${F}px Anybody`;
    return chars.map((c) => {
      const r = E.rel(c.el, root);
      const b = E.rel(c.base, root);
      const asc = mc.measureText(c.c).actualBoundingBoxAscent;
      return { cx: r.x + r.w / 2, top: b.y - asc, base: b.y, w: r.w, left: r.x };
    });
  };

  /* Clock tween driving a render(t) function; registers the paused timeline. */
  E.run = (DUR, render) => {
    const tl = gsap.timeline({ paused: true });
    const clock = { t: 0 };
    tl.fromTo(clock, { t: 0 }, { t: DUR, duration: DUR, ease: "none", onUpdate: () => render(clock.t) }, 0);
    render(0);
    window.__timelines["main"] = tl;
  };

  window.LC = E;
})();
