export type Ratio = "9:16" | "1:1" | "16:9";
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
  background: string;
  effects: string[];
  props: SceneProps;
  sfx: Cue[];
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
