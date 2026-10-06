export type MotionPreset = "legacy" | "soft" | "snappy" | "weighty" | "editorial";
export type BeatAwareSpec = {
  fps: number;
  beat_map?: { enabled: boolean; beat_frames: number[] };
};
export function beatPulse(spec: BeatAwareSpec, frame: number): number;
export function motionStyle(
  kind: MotionPreset,
  frame: number,
  fps: number,
  beat?: number,
): { opacity?: number; transform?: string };
