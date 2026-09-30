/** Original synthesized audio, no third-party recordings. Peak-bounded PCM WAV. */
import { writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
export const audioKinds = [
  "tick",
  "impact",
  "whoosh",
  "rise",
  "sting",
  "pluck",
  "pulse",
  "chime",
  "bed",
];
export function buildAudio(directory) {
  mkdirSync(directory, { recursive: true });
  const sr = 44100;
  for (const kind of audioKinds) {
    const duration =
      kind === "bed"
        ? 8
        : kind === "pulse"
          ? 2
          : kind === "sting"
            ? 1.1
            : kind === "rise"
              ? 1.4
              : kind === "whoosh"
                ? 0.45
                : kind === "chime"
                  ? 1.1
                  : kind === "impact"
                    ? 0.55
                    : kind === "pluck"
                      ? 0.35
                      : 0.075;
    const count = Math.round(duration * sr);
    const pcm = Buffer.alloc(count * 2);
    let noise = 9317;
    for (let i = 0; i < count; i++) {
      const t = i / sr;
      const progress = t / duration;
      let sample = 0;
      noise = (Math.imul(noise, 1664525) + 1013904223) >>> 0;
      const n = noise / 2147483648 - 1;
      const sine = (hz) => Math.sin(2 * Math.PI * hz * t);
      if (kind === "tick")
        sample = (sine(1100) * 0.7 + sine(1600) * 0.25) * Math.exp(-t * 95);
      if (kind === "impact")
        sample =
          (Math.sin(2 * Math.PI * (65 * t - 24 * t * t)) * 0.8 + n * 0.09) *
          Math.exp(-t * 9);
      if (kind === "whoosh")
        sample = n * Math.sin(Math.PI * progress) ** 2 * 0.55;
      if (kind === "rise")
        sample =
          Math.sin(2 * Math.PI * (180 * t + 180 * t * t)) *
          Math.sin(Math.PI * progress) *
          0.45;
      if (kind === "pluck")
        sample = (sine(440) + sine(880) * 0.3) * Math.exp(-t * 16) * 0.55;
      if (kind === "chime")
        sample = (sine(880) * 0.6 + sine(1320) * 0.3) * Math.exp(-t * 4);
      if (kind === "sting") {
        for (const [j, hz] of [293.665, 369.994, 440].entries()) {
          const dt = t - j * 0.13;
          if (dt >= 0)
            sample +=
              Math.sin(2 * Math.PI * hz * dt) * Math.exp(-dt * 5) * 0.28;
        }
      }
      if (kind === "pulse") {
        const dt = t % 0.5;
        sample = (sine(110) * 0.65 + sine(220) * 0.15) * Math.exp(-dt * 15);
      }
      if (kind === "bed") {
        const chord = Math.floor(t / 2) % 4;
        const roots = [146.832, 130.813, 110, 130.813];
        const root = roots[chord];
        sample =
          (sine(root) * 0.55 + sine(root * 1.5) * 0.22 + sine(root * 2) * 0.1) *
          (0.55 + 0.12 * Math.sin(2 * Math.PI * t * 0.5));
        const at = t % 2;
        sample *= Math.min(1, at / 0.08, (2 - at) / 0.08);
      }
      const fade = Math.min(1, t / 0.003, (duration - t) / 0.025);
      sample = Math.max(-0.8, Math.min(0.8, sample)) * fade * 0.6;
      pcm.writeInt16LE(Math.round(sample * 32767), i * 2);
    }
    const header = Buffer.alloc(44);
    header.write("RIFF");
    header.writeUInt32LE(36 + pcm.length, 4);
    header.write("WAVE", 8);
    header.write("fmt ", 12);
    header.writeUInt32LE(16, 16);
    header.writeUInt16LE(1, 20);
    header.writeUInt16LE(1, 22);
    header.writeUInt32LE(sr, 24);
    header.writeUInt32LE(sr * 2, 28);
    header.writeUInt16LE(2, 32);
    header.writeUInt16LE(16, 34);
    header.write("data", 36);
    header.writeUInt32LE(pcm.length, 40);
    writeFileSync(
      path.join(directory, kind + ".wav"),
      Buffer.concat([header, pcm]),
    );
  }
}
if (process.argv[1] === new URL(import.meta.url).pathname)
  buildAudio(new URL("./public/audio/", import.meta.url).pathname);
