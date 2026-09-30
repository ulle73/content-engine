import React from "react";
import { noise2D } from "@remotion/noise";
import { seeded } from "./math";
import type { SceneContext } from "./types";

export function Background({
  scene,
  frame,
  width: w,
  height: h,
  brand: b,
  seed,
}: SceneContext) {
  const t = frame / 90;
  const mode = scene.background;
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: b.background,
        overflow: "hidden",
      }}
    >
      {mode === "radial" && (
        <div
          style={{
            position: "absolute",
            inset: "-25%",
            background: `radial-gradient(ellipse at ${60 + Math.sin(t) * 10}% ${30 + Math.cos(t) * 12}%, ${b.accent}aa 0%, transparent 62%)`,
            transform: `scale(${1 + Math.sin(t) * 0.06})`,
          }}
        />
      )}
      {mode === "mesh" && (
        <>
          <div
            style={{
              position: "absolute",
              width: "110%",
              height: "80%",
              left: "-30%",
              top: "-25%",
              borderRadius: "50%",
              background: b.accent,
              filter: "blur(95px)",
              opacity: 0.45,
              transform: `translate(${Math.sin(t) * 40}px,${Math.cos(t) * 35}px)`,
            }}
          />
          <div
            style={{
              position: "absolute",
              width: "80%",
              height: "70%",
              right: "-45%",
              bottom: "-30%",
              borderRadius: "50%",
              background: b.muted,
              filter: "blur(100px)",
              opacity: 0.15,
              transform: `translateY(${Math.sin(t) * 50}px)`,
            }}
          />
        </>
      )}
      {mode === "grid" && (
        <div
          style={{
            position: "absolute",
            inset: -100,
            opacity: 0.16,
            backgroundImage: `linear-gradient(${b.muted} 1px, transparent 1px),linear-gradient(90deg,${b.muted} 1px,transparent 1px)`,
            backgroundSize: "90px 90px",
            transform: `translate(${(frame * 0.18) % 90}px,${(frame * 0.1) % 90}px)`,
          }}
        />
      )}
      {mode === "checker" && (
        <div
          style={{
            position: "absolute",
            inset: -150,
            opacity: 0.12,
            backgroundImage: `conic-gradient(${b.accent} 25%,transparent 0 50%,${b.accent} 0 75%,transparent 0)`,
            backgroundSize: "240px 240px",
            transform: `translateX(${(frame * 0.2) % 240}px) rotate(-8deg)`,
          }}
        />
      )}
      <svg
        width={w}
        height={h}
        style={{ position: "absolute", inset: 0 }}
        aria-hidden
      >
        {mode === "orbits" && (
          <g
            transform={`translate(${w * 0.83},${h * 0.6}) rotate(${frame * 0.13})`}
            fill="none"
            stroke={b.accent}
            strokeWidth="3"
            opacity=".4"
          >
            {[0.2, 0.36, 0.54, 0.73, 0.95].map((r, i) => (
              <ellipse
                key={i}
                cx="0"
                cy="0"
                rx={w * r}
                ry={w * r * 0.66}
                transform={`rotate(${i * 19})`}
              />
            ))}
          </g>
        )}
        {mode === "particles" &&
          Array.from({ length: 26 }, (_, i) => {
            const x =
              (seeded(seed, i) * w +
                frame * (0.2 + seeded(seed, i + 80) * 0.5)) %
              w;
            const y = (seeded(seed, i + 30) * h - frame * 0.35 + h * 2) % h;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={3 + seeded(seed, i + 50) * 7}
                fill={b.muted}
                opacity={0.07 + seeded(seed, i + 60) * 0.15}
              />
            );
          })}
        {mode === "rays" && (
          <g
            transform={`translate(${w * 0.88},${h * 0.2}) rotate(${frame * 0.15})`}
            fill={b.accent}
            opacity=".26"
          >
            {Array.from({ length: 12 }, (_, i) => (
              <path
                key={i}
                d={`M0 0 L${w * 1.5} -60 L${w * 1.5} 60Z`}
                transform={`rotate(${i * 30})`}
              />
            ))}
          </g>
        )}
        {mode === "waves" &&
          Array.from({ length: 5 }, (_, i) => (
            <path
              key={i}
              d={`M-100 ${h * (0.5 + i * 0.11)} Q ${w * 0.3} ${h * (0.3 + i * 0.12) + Math.sin(t + i) * 90} ${w * 0.6} ${h * (0.6 + i * 0.1)} T ${w + 100} ${h * (0.58 + i * 0.1)} L${w + 100} ${h + 100} L-100 ${h + 100}Z`}
              fill={i % 2 ? b.background : b.accent}
              opacity={0.18 + i * 0.055}
            />
          ))}
        {mode === "topography" &&
          Array.from({ length: 14 }, (_, i) => {
            let d = "";
            for (let j = 0; j <= 30; j++) {
              const x = (j * w) / 30;
              const y =
                h * 0.35 + i * 45 + noise2D(seed + i, j * 0.07, t * 0.08) * 100;
              d += `${j ? "L" : "M"}${x} ${y} `;
            }
            return (
              <path
                key={i}
                d={d}
                fill="none"
                stroke={b.muted}
                strokeWidth="2"
                opacity=".13"
              />
            );
          })}
      </svg>
    </div>
  );
}
