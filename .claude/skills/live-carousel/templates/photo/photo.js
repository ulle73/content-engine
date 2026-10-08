/* Photo carousel engine: bring a finished carousel image to life without changing its pixels at rest.
   Requires engine.js (window.LC). Everything is a pure function of time. */
(function () {
  const L = window.LC;
  const P = {};

  P.loadImg = (src) =>
    new Promise((res, rej) => {
      const i = new Image();
      i.onload = () => res(i);
      i.onerror = () => rej(new Error("failed to load " + src));
      i.src = src;
    });

  /* ---------- cinemagraph sky: WebGL flow-map drift on the movable (cloud) areas ---------- */
  P.cinemagraph = (canvas, imgs, opts = {}) => {
    const gl = canvas.getContext("webgl", { preserveDrawingBuffer: true, premultipliedAlpha: false, antialias: false });
    if (!gl) return null;
    const vs = `attribute vec2 p; varying vec2 uv;
      void main(){ uv = vec2(p.x * 0.5 + 0.5, 0.5 - p.y * 0.5); gl_Position = vec4(p, 0.0, 1.0); }`;
    const fs = `precision highp float;
      varying vec2 uv;
      uniform sampler2D bg; uniform sampler2D clean; uniform sampler2D flow;
      uniform float t; uniform float period; uniform float amp;
      void main(){
        vec4 f = texture2D(flow, uv);
        float m = f.b;
        vec2 dir = vec2(f.g * 2.0 - 1.0, f.r * 2.0 - 1.0);
        // seamless billow: every region sways along the wind with its own phase (period = loop length)
        float ph = (f.g + f.r) * 7.0;
        vec2 off = dir * amp * m * vec2(1.0, 0.8) * sin(6.2831853 * t / period + ph);
        vec4 mv = texture2D(clean, uv - off);
        vec4 base = texture2D(bg, uv);
        gl_FragColor = vec4(mix(base.rgb, mv.rgb, smoothstep(0.03, 0.35, m)), 1.0);
      }`;
    const sh = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
    ["bg", "clean", "flow"].forEach((name, unit) => {
      const tex = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, imgs[name]);
      gl.uniform1i(gl.getUniformLocation(prog, name), unit);
    });
    const uT = gl.getUniformLocation(prog, "t");
    gl.uniform1f(gl.getUniformLocation(prog, "period"), opts.period || 3);
    gl.uniform1f(gl.getUniformLocation(prog, "amp"), opts.amp || 0.012);
    gl.viewport(0, 0, canvas.width, canvas.height);
    return (t) => {
      gl.uniform1f(uT, t);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    };
  };

  /* ---------- masked full-frame layer ---------- */
  P.masked = (parent, maskUrl, background, cls) => {
    const d = document.createElement("div");
    d.className = "full masked " + (cls || "");
    d.style.webkitMaskImage = d.style.maskImage = `url(${maskUrl})`;
    d.style.background = background;
    parent.appendChild(d);
    return d;
  };

  /* ---------- 3D extrusion behind a white headline matte (face restored on top) ---------- */
  /* extrusion colours: opts.front / opts.back = [left, right]; defaults are a magenta -> orange pair */
  const EXT_FRONT = ["#ff4fb8", "#ff8a3d"];
  const EXT_BACK = ["#5b0f6e", "#8a2a0c"];
  const mixHex = (a, b, s) => {
    const pa = parseInt(a.slice(1), 16),
      pb = parseInt(b.slice(1), 16);
    const ch = (sh) => Math.round(((pa >> sh) & 255) * (1 - s) + ((pb >> sh) & 255) * s);
    return `rgb(${ch(16)}, ${ch(8)}, ${ch(0)})`;
  };
  P.extrusion = (parent, maskUrl, n = 10, opts = {}) => {
    const wrap = document.createElement("div");
    wrap.className = "full";
    parent.appendChild(wrap);
    const shadow = P.masked(wrap, maskUrl, "rgba(12, 10, 40, 0.38)", "ext-shadow");
    const layers = [];
    for (let i = n; i >= 1; i--) {
      const s = (i - 1) / Math.max(1, n - 1);
      const F = opts.front || EXT_FRONT,
        B = opts.back || EXT_BACK;
      const g = `linear-gradient(${opts.angle || 100}deg, ${mixHex(F[0], B[0], s)} 18%, ${mixHex(F[1], B[1], s)} 82%)`;
      layers.push({ el: P.masked(wrap, maskUrl, g), i });
    }
    const dir = opts.dir || [0.5, 0.86];
    return (depth) => {
      const on = depth > 0.3;
      wrap.style.opacity = on ? 1 : 0;
      if (!on) return;
      for (const l of layers) {
        const k = (l.i / n) * depth;
        l.el.style.transform = `translate(${(dir[0] * k).toFixed(2)}px, ${(dir[1] * k).toFixed(2)}px)`;
      }
      shadow.style.transform = `translate(${(dir[0] * depth * 1.6).toFixed(2)}px, ${(dir[1] * depth * 1.6).toFixed(2)}px)`;
      shadow.style.filter = `blur(${(depth * 0.45).toFixed(2)}px)`;
    };
  };

  /* ---------- brush word: pop (always >= 1 so the baked word stays covered) + wet-paint shine ---------- */
  P.brush = (parent, url, box, opts = {}) => {
    const cx = (box[0] + box[2]) / 2,
      cy = (box[1] + box[3]) / 2;
    const wrap = document.createElement("div");
    wrap.className = "full";
    wrap.style.transformOrigin = `${cx}px ${cy}px`;
    parent.appendChild(wrap);
    const shadow = P.masked(wrap, url, "rgba(46, 6, 58, 0.55)", "");
    const img = document.createElement("img");
    img.className = "full";
    img.src = url;
    img.alt = "";
    wrap.appendChild(img);
    const shine = P.masked(
      wrap,
      url,
      "linear-gradient(105deg, rgba(255,255,255,0) 42%, rgba(255,255,255,0.9) 50%, rgba(255,255,255,0) 58%)",
      "shine",
    );
    shine.style.backgroundSize = "300% 100%";
    return (pop, rot, shineP, lift) => {
      // pop: extra scale (>= 0), rot: degrees, shineP: 0..1 sweep (outside = hidden), lift: shadow depth px
      wrap.style.transform = `scale(${(1 + Math.max(0, pop)).toFixed(4)}) rotate(${rot.toFixed(3)}deg)`;
      const vis = shineP > 0 && shineP < 1;
      shine.style.opacity = vis ? 1 : 0;
      shine.style.backgroundPosition = `${(100 - shineP * 100).toFixed(2)}% 0`;
      shadow.style.opacity = lift > 0.2 ? 1 : 0;
      shadow.style.transform = `translate(${(lift * 0.6).toFixed(2)}px, ${(lift * 0.9).toFixed(2)}px)`;
    };
  };

  /* ---------- light flare (impact) ---------- */
  P.flare = (parent, x, y) => {
    const glow = document.createElement("div");
    glow.className = "flare-glow";
    glow.style.left = x - 300 + "px";
    glow.style.top = y - 300 + "px";
    const streak = document.createElement("div");
    streak.className = "flare-streak";
    streak.style.left = x - 520 + "px";
    streak.style.top = y - 9 + "px";
    parent.appendChild(glow);
    parent.appendChild(streak);
    return (t, t0) => {
      const dt = t - t0;
      if (dt < 0 || dt > 1.2) {
        glow.style.opacity = 0;
        streak.style.opacity = 0;
        return;
      }
      const e = Math.exp(-dt * 4.2);
      glow.style.opacity = e.toFixed(3);
      glow.style.transform = `scale(${(0.35 + L.easeOut(Math.min(1, dt / 0.35)) * 0.9).toFixed(3)})`;
      streak.style.opacity = (Math.exp(-dt * 5.5)).toFixed(3);
      streak.style.transform = `scaleX(${(0.3 + L.easeOut(Math.min(1, dt / 0.25)) * 1.1).toFixed(3)})`;
    };
  };

  /* ---------- ring ---------- */
  P.ring = (parent, cls) => {
    const r = document.createElement("div");
    r.className = "ring " + (cls || "");
    parent.appendChild(r);
    return (t, t0, x, y, maxS = 6, life = 0.7) => {
      const dt = t - t0;
      if (dt < 0 || dt > life) {
        r.style.opacity = 0;
        return;
      }
      r.style.opacity = (1 - dt / life).toFixed(3);
      r.style.transform = `translate(${x}px, ${y}px) scale(${(0.3 + L.easeOut(dt / life) * maxS).toFixed(3)})`;
    };
  };

  /* ---------- camera: gentle seamless push + decaying shakes ---------- */
  P.camera = (el, DUR, hits, opts = {}) => {
    const push = opts.push === undefined ? 0.018 : opts.push;
    el.style.transformOrigin = opts.origin || "50% 45%";
    return (t) => {
      let sx = 0,
        sy = 0;
      for (const [t0, amp] of hits) {
        const dt = t - t0;
        if (dt < 0 || dt > 0.6) continue;
        const e = Math.exp(-dt * 9) * amp;
        sx += Math.sin(dt * 61 + t0 * 3) * e;
        sy += Math.cos(dt * 53 + t0 * 5) * e;
      }
      const s = 1 + push * (1 - Math.cos((Math.PI * 2 * t) / DUR)) * 0.5;
      el.style.transform = `translate(${sx.toFixed(2)}px, ${sy.toFixed(2)}px) scale(${s.toFixed(5)})`;
    };
  };

  /* ---------- pills that light up in sequence (lit copy always covers the baked pill) ---------- */
  P.pills = (parent, pills, onTimes, offTimes) => {
    const els = pills.map((p) => {
      const [x0, y0, x1, y1] = p.box;
      const d = document.createElement("div");
      d.className = "pill-lit";
      d.textContent = p.label;
      d.style.left = x0 + "px";
      d.style.top = y0 + "px";
      d.style.width = x1 - x0 + "px";
      d.style.height = y1 - y0 + "px";
      parent.appendChild(d);
      return { el: d, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
    });
    const spark = document.createElement("div");
    spark.className = "spark";
    parent.appendChild(spark);
    const xs = [pills[0].box[0] - 60, ...els.map((e) => e.cx)];
    const ts = [onTimes[0] - 0.22, ...onTimes];
    return (t) => {
      els.forEach((e, i) => {
        const on = L.prog(t, onTimes[i], onTimes[i] + 0.06);
        const off = L.prog(t, offTimes[i], offTimes[i] + 0.22);
        const v = on * (1 - off);
        const pop = P.pop(t, onTimes[i], 26, 6);
        e.el.style.opacity = v.toFixed(3);
        e.el.style.transform = `scale(${(1 + 0.12 * pop + 0.02 * v).toFixed(4)})`;
      });
      // spark travels pill to pill, igniting each one
      const live = t >= ts[0] && t <= ts[ts.length - 1] + 0.15;
      spark.style.opacity = live ? (1 - L.prog(t, ts[ts.length - 1], ts[ts.length - 1] + 0.15)).toFixed(3) : 0;
      if (live) {
        let x = xs[xs.length - 1];
        for (let i = 0; i < ts.length - 1; i++) {
          if (t <= ts[i + 1]) {
            x = L.lerp(xs[i], xs[i + 1], L.easeInOut(L.prog(t, ts[i], ts[i + 1])));
            break;
          }
        }
        spark.style.transform = `translate(${x.toFixed(1)}px, ${els[0].cy.toFixed(1)}px)`;
      }
    };
  };

  /* ---------- two-colour echo of a matte (left magenta / right orange) ---------- */
  P.echo = (parent, maskUrl) => {
    const a = P.masked(parent, maskUrl, "#ff4fb8", "");
    const b = P.masked(parent, maskUrl, "#ff8a3d", "");
    return (d) => {
      const on = d > 0.3;
      a.style.opacity = b.style.opacity = on ? 0.95 : 0;
      a.style.transform = `translate(${(-d).toFixed(2)}px, ${(d * 0.55).toFixed(2)}px)`;
      b.style.transform = `translate(${d.toFixed(2)}px, ${(d * 0.55).toFixed(2)}px)`;
    };
  };

  /* pop envelope: 0 -> fast rise -> slow settle (never negative) */
  P.pop = (t, t0, rise = 18, fall = 3.2) => {
    const a = t - t0;
    return a <= 0 ? 0 : (1 - Math.exp(-a * rise)) * Math.exp(-a * fall);
  };

  /* ---------- lift: the photo's own pixels under a matte, as a movable layer that covers the baked copy ----------
     Keep scale >= 1 so the lifted copy always covers the original pixels underneath. */
  P.lift = (parent, imgUrl, maskUrl, box, opts = {}) => {
    const cx = (box[0] + box[2]) / 2,
      cy = opts.originBottom ? box[3] : (box[1] + box[3]) / 2;
    const wrap = document.createElement("div");
    wrap.className = "full";
    wrap.style.transformOrigin = `${cx}px ${cy}px`;
    parent.appendChild(wrap);
    const shadow = P.masked(wrap, maskUrl, opts.shadow || "rgba(8, 12, 30, 0.45)", "");
    const face = P.masked(wrap, maskUrl, `url(${imgUrl}) 0 0 / 100% 100% no-repeat`, "");
    return (scale, dy = 0, depth = 0, rot = 0) => {
      wrap.style.transform = `translateY(${dy.toFixed(2)}px) scale(${Math.max(1, scale).toFixed(4)}) rotate(${rot.toFixed(3)}deg)`;
      shadow.style.opacity = depth > 0.2 ? 1 : 0;
      shadow.style.transform = `translate(${(depth * 0.5).toFixed(2)}px, ${(depth * 0.9).toFixed(2)}px)`;
      shadow.style.filter = `blur(${(depth * 0.35).toFixed(2)}px)`;
    };
  };

  /* ---------- shine: a light band sweeping across a matte (text, a logo, a card) ---------- */
  P.shine = (parent, maskUrl, angle = 105) => {
    const s = P.masked(parent, maskUrl, `linear-gradient(${angle}deg, rgba(255,255,255,0) 42%, rgba(255,255,255,0.85) 50%, rgba(255,255,255,0) 58%)`, "shine");
    s.style.backgroundSize = "300% 100%";
    return (p) => {
      const vis = p > 0 && p < 1;
      s.style.opacity = vis ? 1 : 0;
      if (vis) s.style.backgroundPosition = `${(100 - p * 100).toFixed(2)}% 0`;
    };
  };

  /* ---------- light leak: a soft coloured glow drifting across the frame (periodic => seamless) ---------- */
  P.leak = (parent, color, DUR) => {
    const d = document.createElement("div");
    d.className = "leak";
    d.style.background = `radial-gradient(circle, ${color} 0%, rgba(0,0,0,0) 62%)`;
    parent.appendChild(d);
    return (t, gain = 1) => {
      const a = (Math.PI * 2 * t) / DUR;
      const x = 540 + 520 * Math.cos(a) - 500;
      const y = 300 + 220 * Math.sin(2 * a) - 500;
      d.style.opacity = (gain * (0.5 + 0.5 * Math.sin(a + 1.3))).toFixed(3);
      d.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
    };
  };

  /* ---------- drifting motes (dust / sparkles / fireflies): periodic in t so loops are seamless ---------- */
  P.motes = (parent, n, seed, o) => {
    const ps = [];
    for (let i = 0; i < n; i++) {
      const d = document.createElement("div");
      d.className = "particle mote";
      const h = (k) => L.hash(seed + i * 13.7 + k * 3.1);
      d.style.background = o.colors[Math.floor(h(1) * o.colors.length)];
      if (o.glow) d.style.boxShadow = `0 0 ${6 + h(9) * 8}px ${2 + h(8) * 3}px ${o.glow}`;
      parent.appendChild(d);
      ps.push({
        el: d,
        x: o.x0 + h(2) * (o.x1 - o.x0),
        y: o.y0 + h(3) * (o.y1 - o.y0),
        vx: o.vx[0] + h(4) * (o.vx[1] - o.vx[0]),
        vy: o.vy[0] + h(5) * (o.vy[1] - o.vy[0]),
        size: o.size[0] + h(6) * (o.size[1] - o.size[0]),
        ph: h(7),
        tw: h(10),
      });
    }
    return (t, gain = 1) => {
      for (const p of ps) {
        const u = (t / o.period + p.ph) % 1;
        const life = Math.sin(Math.PI * u);
        const x = p.x + p.vx * (u - 0.5) * o.period + (o.wobble || 0) * Math.sin(u * Math.PI * 4 + p.ph * 9);
        const y = p.y + p.vy * (u - 0.5) * o.period;
        const tw = o.twinkle ? 0.55 + 0.45 * Math.sin(((Math.PI * 2 * t) / o.period) * o.twinkle + p.tw * 20) : 1;
        p.el.style.opacity = (Math.max(0, life) * tw * gain * (o.alpha || 1)).toFixed(3);
        p.el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) scale(${p.size.toFixed(2)})`;
      }
    };
  };

  /* ---------- count-up number that covers a baked number (pair with a clean plate of that box) ---------- */
  P.counter = (parent, box, opts = {}) => {
    const d = document.createElement("div");
    d.className = "counter-num";
    Object.assign(d.style, { left: box[0] + "px", top: box[1] + "px", width: box[2] - box[0] + "px", height: box[3] - box[1] + "px" });
    if (opts.style) Object.assign(d.style, opts.style);
    parent.appendChild(d);
    const dec = opts.decimals || 0;
    return (p) => {
      const v = (opts.to || 0) * L.clamp(p);
      d.textContent = (opts.prefix || "") + v.toFixed(dec) + (opts.suffix || "");
    };
  };

  /* ---------- pointer cursor (move it with style.transform) ---------- */
  P.cursor = (parent) => {
    const svgNS = "http://www.w3.org/2000/svg";
    const s = document.createElementNS(svgNS, "svg");
    s.setAttribute("viewBox", "0 0 46 58");
    s.setAttribute("width", "54");
    s.setAttribute("height", "68");
    s.style.cssText = "position:absolute;left:0;top:0;overflow:visible;opacity:0;filter:drop-shadow(0 6px 10px rgba(0,0,0,.35))";
    s.innerHTML = '<path d="M4 3 L4 46 L15 36 L23 54 L31 50 L23 33 L39 33 Z" fill="#ffffff" stroke="#111" stroke-width="3" stroke-linejoin="round"/>';
    parent.appendChild(s);
    return s;
  };

  window.PH = P;
})();
