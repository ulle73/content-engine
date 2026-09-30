import test from "node:test";
import assert from "node:assert/strict";
import { validateSpec, validateBrand } from "../validate.mjs";
const base = () => ({
  version: 1,
  template_id: "monthly-wrapped",
  template_version: 1,
  aspect_ratio: "9:16",
  fps: 30,
  seed: 42,
  brand_id: "golfkuponger",
  scenes: [
    {
      id: "first",
      component: "hero",
      duration_frames: 90,
      props: { headline: "September" },
      transition: "cut",
      transition_frames: 0,
      background: "solid",
      effects: [],
      sfx: [],
    },
  ],
  audio: {
    enabled: true,
    gain: 0.7,
    music: "bed",
    music_asset_id: null,
    fade_frames: 15,
    ducking: 0.3,
  },
  end_card_asset_id: null,
});
test("canonical valid data", () =>
  assert.equal(validateSpec(base()).scenes[0].id, "first"));
test("film footage has media and no destructive effects or clip sound cues", () => {
  const s = base();
  s.template_id = "sequence-film";
  s.scenes[0].component = "footage";
  assert.throws(() => validateSpec(s));
  s.scenes[0].props.asset_id = "00000000-0000-4000-8000-000000000001";
  assert.equal(validateSpec(s).scenes[0].component, "footage");
  s.scenes[0].effects = ["duotone"];
  assert.throws(() => validateSpec(s));
  s.scenes[0].effects = [];
  s.scenes[0].sfx = [{ kind: "tick", frame: 15, gain: 0.2 }];
  assert.throws(() => validateSpec(s));
});
test("no arbitrary imports or props", () => {
  for (const [k, v] of [
    ["imports", ["fs"]],
    ["url", "http://evil"],
  ])
    assert.throws(() => validateSpec({ ...base(), [k]: v }));
  const s = base();
  s.scenes[0].props.style = { background: "url(x)" };
  assert.throws(() => validateSpec(s));
});
test("only registered components", () => {
  const s = base();
  s.scenes[0].component = "../../x";
  assert.throws(() => validateSpec(s));
});
test("UUID media references only", () => {
  const s = base();
  s.scenes[0].props.asset_id = "https://evil";
  assert.throws(() => validateSpec(s));
});
test("duplicate scene ids rejected", () => {
  const s = base();
  s.scenes.push(structuredClone(s.scenes[0]));
  assert.throws(() => validateSpec(s));
});
test("first scene and max duration bounds", () => {
  const s = base();
  s.scenes[0].transition = "fade";
  s.scenes[0].transition_frames = 15;
  assert.throws(() => validateSpec(s));
  s.scenes = Array.from({ length: 5 }, (_, i) => ({
    ...base().scenes[0],
    id: "s" + i,
    duration_frames: 900,
  }));
  assert.throws(() => validateSpec(s));
});
test("brand CSS injection blocked", () =>
  assert.throws(() =>
    validateBrand({ id: "golfkuponger", version: 1, background: "url(x)" }),
  ));
test("numeric strings and nonfinite values blocked", () => {
  for (const v of ["123", Infinity, NaN]) {
    const s = base();
    s.scenes[0].props.value = v;
    assert.throws(() => validateSpec(s));
  }
});
test("template version pinned", () =>
  assert.throws(() => validateSpec({ ...base(), template_version: 999 })));
