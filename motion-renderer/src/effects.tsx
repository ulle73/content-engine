import React from "react";
import { evolvePath } from "@remotion/paths";
import { clamp, enter } from "./math";
import type { SceneContext } from "./types";

export function EffectLayers({
  scene,
  frame,
  width: w,
  height: h,
  brand: b,
  seed,
}: SceneContext) {
  const effects = new Set(scene.effects);
  const id = `grain-${scene.id}`;
  const path = `M${w * 0.08} ${h * 0.8} C${w * 0.28} ${h * 0.55},${w * 0.67} ${h * 0.93},${w * 0.91} ${h * 0.62}`;
  const draw = evolvePath(clamp(frame / 45), path);
  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {effects.has("vignette") && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse,transparent 25%,rgba(0,0,0,.36))",
          }}
        />
      )}
      {effects.has("glow") && (
        <div
          style={{
            position: "absolute",
            left: "55%",
            top: "18%",
            width: w * 0.55,
            height: w * 0.55,
            borderRadius: "50%",
            boxShadow: `0 0 130px 40px ${b.accent}66`,
            opacity: 0.65,
            transform: `scale(${0.9 + 0.1 * Math.sin(frame / 30)})`,
          }}
        />
      )}
      {effects.has("scanline") && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: `${clamp(frame / 90) * 100}%`,
            height: 2,
            background: b.muted,
            opacity: frame < 90 ? 0.25 : 0,
          }}
        />
      )}
      {effects.has("frame") && (
        <svg width={w} height={h}>
          <rect
            x={w * 0.045}
            y={h * 0.045}
            width={w * 0.91}
            height={h * 0.91}
            rx="2"
            fill="none"
            stroke={b.muted}
            strokeWidth="3"
            pathLength="1"
            strokeDasharray="1"
            strokeDashoffset={1 - enter(frame, 4, 45)}
            opacity=".45"
          />
        </svg>
      )}
      {effects.has("svg-path") && (
        <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
          <path
            d={path}
            stroke={b.muted}
            fill="none"
            strokeWidth="4"
            {...draw}
          />
        </svg>
      )}
      {effects.has("grain") && (
        <svg
          width={w}
          height={h}
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.045,
            mixBlendMode: "screen",
          }}
        >
          <filter id={id}>
            <feTurbulence
              type="fractalNoise"
              baseFrequency=".65"
              numOctaves="2"
              seed={seed}
            />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter={`url(#${id})`} />
        </svg>
      )}
    </div>
  );
}

export function contentEffectStyle(c: SceneContext): React.CSSProperties {
  const effects = new Set(c.scene.effects);
  const { frame, brand: b } = c;
  const transforms: string[] = [];
  if (effects.has("parallax"))
    transforms.push(
      `translate(${Math.sin(frame / 70) * 12}px,${Math.cos(frame / 75) * 8}px)`,
    );
  if (effects.has("glitch") && frame > 7 && frame < 13)
    transforms.push(`translateX(${frame % 2 ? 10 : -10}px)`);
  return {
    transform: transforms.join(" ") || undefined,
    filter: effects.has("shadow")
      ? "drop-shadow(0px 12px 12px rgba(0,0,0,.28))"
      : undefined,
    textShadow:
      effects.has("glitch") && frame > 7 && frame < 13
        ? `6px 0 ${b.accent}`
        : undefined,
  };
}
