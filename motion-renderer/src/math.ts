/** Frame-only helpers. No clocks, uncontrolled randomness or CSS animations. */
export const clamp = (x: number, min = 0, max = 1) =>
  Math.max(min, Math.min(max, x));
export const ease = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
export const smooth = (x: number) => {
  const p = clamp(x);
  return p * p * (3 - 2 * p);
};
export const enter = (frame: number, delay = 0, duration = 20) =>
  ease((frame - delay) / duration);
export const seeded = (seed: number, index: number) => {
  const x = Math.sin(seed * 12.9898 + index * 78.233) * 43758.5453;
  return x - Math.floor(x);
};
export const number = (value: number, fraction = 0) =>
  new Intl.NumberFormat("sv-SE", { maximumFractionDigits: fraction }).format(
    value,
  );
export function timeline(
  scenes: { duration_frames: number; transition_frames: number; id: string }[],
) {
  let end = 0;
  return scenes.map((s) => {
    const start = end - s.transition_frames;
    end = start + s.duration_frames;
    return { id: s.id, start, end };
  });
}
export function dimensions(ratio: string): [number, number] {
  return ratio === "9:16"
    ? [1080, 1920]
    : ratio === "1:1"
      ? [1080, 1080]
      : [1920, 1080];
}
export function safe(width: number, height: number) {
  const portrait = height > width * 1.2;
  const x = width * 0.085;
  const y = height * (portrait ? 0.12 : 0.09);
  return {
    x,
    y,
    w: width - x * 2,
    h: height - y - height * (portrait ? 0.17 : 0.1),
    portrait,
  };
}
