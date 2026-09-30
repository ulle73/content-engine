import "@fontsource/inter/400.css";
import "@fontsource/inter/700.css";
import "@fontsource/inter/900.css";
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Composition,
  OffthreadVideo,
  Sequence,
  registerRoot,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { Background } from "./backgrounds";
import { EffectLayers, contentEffectStyle } from "./effects";
import { SceneContents } from "./scenes";
import { transitionStyle } from "./transitions";
import { clamp, dimensions, timeline } from "./math";
import type { Inputs, Spec, Brand } from "./types";

const emptyProps = {
  headline: "Motion",
  eyebrow: "",
  body: "Content Engine",
  value: 0,
  unit: "",
  items: [],
  asset_id: null,
  secondary_asset_id: null,
  cta: "",
  attribution: "",
  alignment: "left" as const,
};
const defaultSpec: Spec = {
  version: 1,
  template_id: "custom-storyboard",
  template_version: 1,
  aspect_ratio: "9:16",
  fps: 30,
  seed: 42,
  brand_id: "workspace",
  scenes: [
    {
      id: "intro",
      component: "hero",
      duration_frames: 120,
      props: emptyProps,
      background: "solid",
      transition: "cut",
      transition_frames: 0,
      effects: [],
      sfx: [],
    },
  ],
  audio: {
    enabled: false,
    gain: 0.7,
    music: "none",
    music_asset_id: null,
    fade_frames: 15,
    ducking: 0.3,
  },
  end_card_asset_id: null,
};
const defaultBrand: Brand = {
  id: "workspace",
  version: 1,
  name: "Content Engine",
  background: "#111814",
  foreground: "#ffffff",
  accent: "#68766f",
  muted: "#dfe7e3",
  paper: "#f6f8f7",
  ink: "#111814",
  font_family: "Inter, Arial, sans-serif",
  logo_asset_id: null,
};

export function MotionVideo({ spec, brand, assets }: Inputs) {
  const f = useCurrentFrame();
  const [w, h] = dimensions(spec.aspect_ratio);
  const times = timeline(spec.scenes);
  const duration = times.at(-1)!.end;
  const music = spec.audio.music_asset_id
    ? assets[spec.audio.music_asset_id]?.src
    : spec.audio.music === "none"
      ? null
      : staticFile("audio/" + spec.audio.music + ".wav");
  const finalStart = times.at(-1)!.start;
  const fade = Math.max(1, spec.audio.fade_frames);
  return (
    <AbsoluteFill style={{ background: brand.background }}>
      {spec.scenes.map((scene, i) => {
        const time = times[i];
        const next = times[i + 1];
        const local = f - time.start;
        const entering = scene.transition_frames
          ? clamp(local / scene.transition_frames)
          : 1;
        const outgoing =
          next && f >= next.start
            ? transitionStyle(
                spec.scenes[i + 1].transition,
                (f - next.start) /
                  Math.max(1, spec.scenes[i + 1].transition_frames),
                true,
              )
            : {};
        const context = {
          scene,
          frame: local,
          width: w,
          height: h,
          fps: spec.fps,
          brand,
          assets,
          seed: spec.seed + i * 7,
        };
        const isEnd = i === spec.scenes.length - 1 && spec.end_card_asset_id;
        return (
          <Sequence
            key={scene.id}
            from={time.start}
            durationInFrames={scene.duration_frames}
            name={scene.id}
          >
            <AbsoluteFill
              style={{
                overflow: "hidden",
                ...transitionStyle(scene.transition, entering),
                ...outgoing,
              }}
            >
              {isEnd ? (
                <AbsoluteFill
                  style={{
                    background: "#000000",
                    justifyContent: "center",
                    alignItems: "center",
                  }}
                >
                  {assets[spec.end_card_asset_id!] && (
                    <OffthreadVideo
                      src={assets[spec.end_card_asset_id!].src}
                      volume={spec.audio.enabled ? spec.audio.gain * 0.8 : 0}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "contain",
                      }}
                    />
                  )}
                </AbsoluteFill>
              ) : (
                <>
                  <Background {...context} />
                  <AbsoluteFill style={contentEffectStyle(context)}>
                    <SceneContents {...context} />
                  </AbsoluteFill>
                  <EffectLayers {...context} />
                </>
              )}
            </AbsoluteFill>
          </Sequence>
        );
      })}
      {spec.audio.enabled && music && (
        <Audio
          src={music}
          loop
          loopVolumeCurveBehavior="extend"
          volume={(frame) => {
            const envelope = Math.min(
              1,
              frame / fade,
              (duration - frame) / fade,
            );
            const cueDuck = spec.scenes.some((s, i) =>
              s.sfx.some(
                (c) =>
                  Math.abs(frame - times[i].start - c.frame) < spec.fps * 0.35,
              ),
            );
            const duck =
              (spec.end_card_asset_id && frame >= finalStart) || cueDuck
                ? spec.audio.ducking
                : 1;
            return spec.audio.gain * 0.22 * clamp(envelope) * duck;
          }}
        />
      )}
      {spec.audio.enabled &&
        spec.scenes.flatMap((scene, i) =>
          scene.sfx.map((cue, j) => (
            <Sequence
              key={`${scene.id}-${j}`}
              from={times[i].start + cue.frame}
              durationInFrames={Math.min(
                scene.duration_frames - cue.frame,
                spec.fps * 2,
              )}
              layout="none"
            >
              <Audio
                src={staticFile("audio/" + cue.kind + ".wav")}
                volume={
                  (spec.audio.gain * cue.gain * 0.55) /
                  Math.max(
                    1,
                    scene.sfx.filter(
                      (c) => Math.abs(c.frame - cue.frame) < spec.fps * 0.5,
                    ).length,
                  )
                }
              />
            </Sequence>
          )),
        )}
    </AbsoluteFill>
  );
}
const RemotionRoot = () => (
  <Composition
    id="Motion"
    component={MotionVideo}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={120}
    defaultProps={{ spec: defaultSpec, brand: defaultBrand, assets: {} }}
    calculateMetadata={({ props }) => {
      const [width, height] = dimensions(props.spec.aspect_ratio);
      return {
        width,
        height,
        fps: props.spec.fps,
        durationInFrames: timeline(props.spec.scenes).at(-1)!.end,
      };
    }}
  />
);
registerRoot(RemotionRoot);
