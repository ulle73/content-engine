import {spring} from "remotion";

const clamp = (value, min = 0, max = 1) =>
  Math.max(min, Math.min(max, value));

const PRESETS = Object.freeze({
  soft: {config: {damping: 26, stiffness: 120, mass: 1}, y: 18, scale: 0.988, beat: 0.002},
  snappy: {config: {damping: 18, stiffness: 240, mass: 0.65}, y: 12, scale: 0.982, beat: 0.006},
  weighty: {config: {damping: 22, stiffness: 90, mass: 1.45}, y: 24, scale: 0.985, beat: 0.002},
  editorial: {config: {damping: 24, stiffness: 145, mass: 0.95}, y: 16, scale: 0.99, beat: 0.004},
});

export function beatPulse(spec, frame) {
  const map = spec?.beat_map;
  if (!map?.enabled || !Array.isArray(map.beat_frames) || map.beat_frames.length === 0) return 0;
  const fps = Number(spec.fps) || 30;
  const window = Math.max(2, Math.round(fps * 0.12));
  let distance = Infinity;
  for (const beat of map.beat_frames) {
    distance = Math.min(distance, Math.abs(frame - beat));
    if (beat > frame + window) break;
  }
  if (distance > window) return 0;
  const normalized = 1 - distance / window;
  return normalized * normalized;
}

export function motionStyle(kind, frame, fps, beat = 0) {
  if (kind === "legacy") return {};
  const preset = PRESETS[kind];
  if (!preset) throw new Error("Unregistered motion preset");
  const progress = spring({
    frame: Math.max(0, frame),
    fps,
    config: preset.config,
  });
  const p = clamp(progress);
  const opacity = clamp(p * 1.08);
  const y = (1 - p) * preset.y;
  const scale = preset.scale + (1 - preset.scale) * p + clamp(beat) * preset.beat;
  return {
    opacity,
    transform: `translateY(${y.toFixed(3)}px) scale(${scale.toFixed(5)})`,
  };
}
