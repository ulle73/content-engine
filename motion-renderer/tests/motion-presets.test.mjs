import test from "node:test";
import assert from "node:assert/strict";

test("motion presets use deterministic bounded Remotion spring motion", async () => {
  let module;
  try {
    module = await import("../motion-presets.mjs");
  } catch (error) {
    assert.fail("motion-presets.mjs is missing: " + error.message);
  }
  const { motionStyle, beatPulse } = module;
  assert.deepEqual(motionStyle("legacy", 0, 30, 0), {});
  const a = motionStyle("snappy", 8, 30, 0.5);
  const b = motionStyle("snappy", 8, 30, 0.5);
  assert.deepEqual(a, b);
  assert.match(a.transform, /translateY/);
  assert.match(a.transform, /scale/);
  assert.ok(a.opacity >= 0 && a.opacity <= 1);

  const spec = {
    fps: 30,
    beat_map: {enabled: true, beat_frames: [0, 15, 30]},
  };
  assert.ok(beatPulse(spec, 15) > beatPulse(spec, 8));
  assert.equal(beatPulse({fps: 30, beat_map: {enabled: false, beat_frames: []}}, 15), 0);
});
