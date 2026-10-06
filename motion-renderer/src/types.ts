export type Ratio = "9:16" | "4:5" | "1:1" | "16:9";
export type MotionPreset = "legacy" | "soft" | "snappy" | "weighty" | "editorial";
export type Datum = { label: string; value: number };
export type SceneProps = {
  headline: string;
  eyebrow: string;
  body: string;
  value: number;
  unit: string;
  items: Datum[];
  asset_id: string | null;
  secondary_asset_id: string | null;
  cta: string;
  attribution: string;
  alignment: "left" | "center";
};
export type Cue = { kind: string; frame: number; gain: number };
export type SceneSpec = {
  id: string;
  component: string;
  duration_frames: number;
  transition: string;
  transition_frames: number;
  motion_preset: MotionPreset;
  background: string;
  effects: string[];
  props: SceneProps;
  sfx: Cue[];
};
export type BeatMap = {
  enabled: boolean;
  bpm: number | null;
  offset_frames: number;
  beat_frames: number[];
  source: "none" | "profile" | "built-in-pulse" | "manual";
};
export type ReferenceProfile = {
  source_asset_id: string | null;
  label: string;
  motion_intensity: "low" | "medium" | "high";
  camera_style: "locked" | "push" | "orbit" | "dolly" | "handheld" | "macro" | "aerial" | "mixed";
  transition_family: "cuts" | "soft" | "dynamic" | "mixed";
  typography_behavior: "none" | "minimal" | "kinetic" | "editorial" | "bold";
  beat_density: "sparse" | "medium" | "dense";
  motion_preset: MotionPreset;
  color_behavior: "brand" | "natural" | "muted" | "high-contrast";
  bpm: number | null;
  notes: string;
};
export type Spec = {
  version: 1;
  template_id: string;
  template_version: number;
  aspect_ratio: Ratio;
  fps: number;
  seed: number;
  brand_id: string;
  scenes: SceneSpec[];
  audio: {
    enabled: boolean;
    gain: number;
    music: "none" | "bed" | "pulse";
    music_asset_id: string | null;
    fade_frames: number;
    ducking: number;
  };
  beat_map: BeatMap;
  reference_profile: ReferenceProfile | null;
  end_card_asset_id: string | null;
};
export type Brand = {
  id: string;
  version: number;
  name: string;
  background: string;
  foreground: string;
  accent: string;
  muted: string;
  paper: string;
  ink: string;
  font_family: string;
  logo_asset_id: string | null;
};
export type Asset = {
  src: string;
  kind: "image" | "video" | "audio";
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
};
export type Inputs = {
  spec: Spec;
  brand: Brand;
  assets: Record<string, Asset>;
};
export type SceneContext = {
  scene: SceneSpec;
  frame: number;
  width: number;
  height: number;
  fps: number;
  brand: Brand;
  assets: Record<string, Asset>;
  seed: number;
};
