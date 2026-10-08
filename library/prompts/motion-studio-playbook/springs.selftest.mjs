// node library/prompts/motion-studio-playbook/springs.selftest.mjs   -> prints "springs OK" or throws
import assert from "node:assert/strict";
import { springFrom, springStep, springVel, track, trackObj, hold, hash, noise1, boil, beatInfo, pulse } from "./springs.mjs";

const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

// Step response: starts at 0 with zero velocity, settles at 1, for all damping regimes.
for (const zeta of [0.4, 0.75, 1, 1.6]) {
  const o = { freq: 2, zeta };
  near(springStep(0, o), 0);
  near(springStep(5, o), 1, 1e-4);
  assert.ok(Math.abs(springVel(0.0005, o)) < 0.2, `initial velocity ~0 (zeta ${zeta})`);
  const peak = Math.max(...Array.from({ length: 400 }, (_, i) => springStep(i / 100, o)));
  if (zeta < 1) assert.ok(peak > 1.001, `underdamped overshoots (zeta ${zeta})`);
  else assert.ok(peak <= 1 + 1e-9, `no overshoot (zeta ${zeta})`);
}

// springFrom honours initial position and velocity.
for (const zeta of [0.5, 1, 2]) {
  near(springFrom(0, 3, 0, 10, { zeta }), 3);
  const h = 1e-5;
  const v = (springFrom(h, 3, 4, 10, { zeta }) - springFrom(0, 3, 4, 10, { zeta })) / h;
  near(v, 4, 1e-2);
}

// track(): continuous at every key, reaches the last target, independent of evaluation order.
const keys = [{ t: 0, v: 0 }, { t: 0.5, v: 100 }, { t: 0.8, v: -50 }, { t: 2, v: 20, spring: { freq: 4, zeta: 1 } }];
for (const k of keys.slice(1)) near(track(k.t - 1e-7, keys), track(k.t + 1e-7, keys), 1e-3);
near(track(10, keys), 20, 1e-3);
const forward = [0.1, 0.6, 1.3, 2.2].map((t) => track(t, keys));
const backward = [2.2, 1.3, 0.6, 0.1].map((t) => track(t, keys)).reverse();
assert.deepEqual(forward, backward);

const box = trackObj(10, [{ t: 0, v: { x: 0, w: 10 } }, { t: 1, v: { x: 5, w: 40 } }]);
near(box.x, 5, 1e-3); near(box.w, 40, 1e-3);
assert.equal(hold(1.5, [{ t: 0, v: "button" }, { t: 1, v: "loader" }, { t: 2, v: "check" }]), "loader");

// Seeded noise: deterministic, in range, smooth.
assert.equal(hash(7, 3), hash(7, 3));
assert.notEqual(hash(7, 3), hash(7, 4));
for (let i = 0; i < 1000; i++) { const r = hash(i, i * 3); assert.ok(r >= 0 && r < 1); }
assert.ok(Math.abs(noise1(2.5001, 9) - noise1(2.5, 9)) < 1e-3);
assert.equal(boil(1.0, 12), boil(1.04, 12));
assert.notEqual(boil(1.0, 12), boil(1.1, 12));

// Beats.
const beats = [0.5, 1.0, 1.5, 2.0];
assert.deepEqual(beatInfo(1.25, beats).index, 1);
near(beatInfo(1.25, beats).phase, 0.5);
near(pulse(1.0, beats), 1);
assert.ok(pulse(1.3, beats) < 0.2);

console.log("springs OK");
