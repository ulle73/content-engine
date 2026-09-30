import { readFileSync } from "node:fs";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
const schema = JSON.parse(
  readFileSync(new URL("./spec.schema.json", import.meta.url), "utf8"),
);
const ajv = new Ajv({
  strict: false,
  allErrors: true,
  coerceTypes: false,
  useDefaults: true,
});
addFormats(ajv);
const check = ajv.compile(schema);

export function validateSpec(input) {
  if (JSON.stringify(input).length > 150000)
    throw new Error("MotionSpec too large");
  const value = structuredClone(input);
  if (!check(value))
    throw new Error(
      "Invalid MotionSpec: " + ajv.errorsText(check.errors).slice(0, 350),
    );
  if (value.template_version !== 1)
    throw new Error("Unsupported template version");
  const ids = new Set();
  let end = 0;
  for (const [index, scene] of value.scenes.entries()) {
    if (ids.has(scene.id)) throw new Error("Duplicate scene ID");
    ids.add(scene.id);
    if (
      index === 0 &&
      (scene.transition !== "cut" || scene.transition_frames !== 0)
    )
      throw new Error("First scene must cut");
    if (scene.transition === "cut" && scene.transition_frames !== 0)
      throw new Error("Cut must have zero frames");
    if (
      scene.transition !== "cut" &&
      (scene.transition_frames < 1 ||
        scene.transition_frames >= Math.floor(scene.duration_frames / 2))
    )
      throw new Error("Invalid transition duration");
    if (
      index &&
      scene.transition_frames >=
        Math.floor(value.scenes[index - 1].duration_frames / 2)
    )
      throw new Error("Transition consumes previous scene");
    if (new Set(scene.effects).size !== scene.effects.length)
      throw new Error("Duplicate effects");
    if (scene.sfx.some((c) => c.frame >= scene.duration_frames))
      throw new Error("Sound cue outside scene");
    const ticks = scene.sfx
      .filter((c) => c.kind === "tick")
      .map((c) => c.frame)
      .sort((a, b) => a - b);
    if (ticks.some((v, i) => i && v - ticks[i - 1] < value.fps / 6))
      throw new Error("Counter ticks too frequent");
    if (
      ["bars", "donut", "percentage"].includes(scene.component) &&
      (scene.props.value < 0 || scene.props.items.some((i) => i.value < 0))
    )
      throw new Error("Non-negative values required");
    if (scene.component === "percentage" && scene.props.value > 100)
      throw new Error("Invalid percentage");
    end += scene.duration_frames - scene.transition_frames;
  }
  if (end > 120 * value.fps) throw new Error("Duration exceeds 120 seconds");
  return value;
}

export function validateBrand(brand) {
  if (
    !brand ||
    !["golfkuponger", "workspace"].includes(brand.id) ||
    brand.version !== 1
  )
    throw new Error("Invalid brand");
  for (const key of [
    "background",
    "foreground",
    "accent",
    "muted",
    "paper",
    "ink",
  ])
    if (!/^#[0-9a-fA-F]{6}$/.test(brand[key]))
      throw new Error("Invalid brand color");
  if (brand.font_family !== "Inter, Arial, sans-serif")
    throw new Error("Unregistered font");
  if (typeof brand.name !== "string" || brand.name.length > 200)
    throw new Error("Invalid brand name");
  return brand;
}
