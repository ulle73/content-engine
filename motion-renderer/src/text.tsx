import React from "react";
import { clamp, enter } from "./math";
let canvas: HTMLCanvasElement | undefined;
/** Measure with the actual renderer font, then break every long token. */
function linesAt(
  text: string,
  size: number,
  width: number,
  font: string,
  weight: number,
) {
  if (typeof document === "undefined") return [text];
  canvas ||= document.createElement("canvas");
  const ctx = canvas.getContext("2d")!;
  ctx.font = `${weight} ${size}px ${font}`;
  const lines: string[] = [];
  for (const paragraph of text.split("\n")) {
    let line = "";
    for (const word of paragraph.split(/\s+/)) {
      const next = line ? `${line} ${word}` : word;
      if (ctx.measureText(next).width <= width) {
        line = next;
        continue;
      }
      if (line) {
        lines.push(line);
        line = "";
      }
      if (ctx.measureText(word).width <= width) {
        line = word;
        continue;
      }
      let part = "";
      for (const char of word) {
        if (part && ctx.measureText(part + char).width > width) {
          lines.push(part);
          part = "";
        }
        part += char;
      }
      line = part;
    }
    lines.push(line);
  }
  return lines;
}
export function fitText(
  text: string,
  width: number,
  height: number,
  max: number,
  font: string,
  weight = 800,
) {
  let lo = 12,
    hi = max;
  for (let i = 0; i < 12; i++) {
    const mid = (lo + hi) / 2;
    if (linesAt(text, mid, width, font, weight).length * mid * 1.12 <= height)
      lo = mid;
    else hi = mid;
  }
  const size = Math.floor(lo);
  return { size, lines: linesAt(text, size, width, font, weight) };
}
export function Fit({
  text,
  width,
  height,
  max = 150,
  font = "Inter, Arial, sans-serif",
  weight = 800,
  style = {},
  animation = "none",
  frame = 100,
  color = "inherit",
}: {
  text: string;
  width: number;
  height: number;
  max?: number;
  font?: string;
  weight?: number;
  style?: React.CSSProperties;
  animation?: string;
  frame?: number;
  color?: string;
}) {
  const fit = fitText(text, width, height, max, font, weight);
  let charIndex = 0;
  let wordIndex = 0;
  return (
    <div
      data-motion-text
      style={{
        width,
        fontFamily: font,
        fontWeight: weight,
        fontSize: fit.size,
        lineHeight: 1.12,
        letterSpacing: "-.035em",
        color,
        ...style,
      }}
    >
      {fit.lines.map((line, index) => {
        const p = enter(frame, index * 5, 20);
        const words = line.split(" ");
        return (
          <div
            key={index}
            style={{
              minHeight: fit.size * 1.12,
              overflow: ["line-reveal", "mask-rise", "brush-write"].includes(
                animation,
              )
                ? "hidden"
                : "visible",
            }}
          >
            <div
              style={{
                transform:
                  animation === "line-reveal"
                    ? `translateY(${(1 - p) * 110}%)`
                    : animation === "mask-rise"
                      ? `translateY(${(1 - enter(frame)) * 110}%)`
                      : undefined,
                filter:
                  animation === "blur-reveal"
                    ? `blur(${(1 - p) * 18}px)`
                    : undefined,
                opacity: animation === "blur-reveal" ? p : 1,
                letterSpacing:
                  animation === "tracking"
                    ? `${(1 - enter(frame)) * 0.18 - 0.035}em`
                    : undefined,
                clipPath:
                  animation === "brush-write"
                    ? `inset(0 ${(1 - p) * 100}% 0 0)`
                    : undefined,
                WebkitTextStroke:
                  animation === "outline-fill"
                    ? "1.5px currentColor"
                    : undefined,
                color:
                  animation === "outline-fill" && frame < 14
                    ? "transparent"
                    : undefined,
              }}
            >
              {["kinetic-words", "word-highlight"].includes(animation)
                ? words.map((word, i) => {
                    const wi = wordIndex++;
                    const wp = enter(frame, wi * 5, 18);
                    return (
                      <React.Fragment key={i}>
                        <span
                          style={{
                            display: "inline-block",
                            opacity: animation === "kinetic-words" ? wp : 1,
                            transform:
                              animation === "kinetic-words"
                                ? `translateY(${(1 - wp) * 40}px) scale(${0.85 + 0.15 * wp})`
                                : undefined,
                            textDecoration:
                              animation === "word-highlight" &&
                              Math.floor(frame / 12) %
                                Math.max(1, text.split(/\s/).length) ===
                                wi
                                ? "underline"
                                : undefined,
                            textUnderlineOffset: ".12em",
                          }}
                        >
                          {word}
                        </span>
                        {i < words.length - 1 ? " " : ""}
                      </React.Fragment>
                    );
                  })
                : ["letter-cascade", "typewriter", "split-flap"].includes(
                      animation,
                    )
                  ? Array.from(line).map((char, i) => {
                      const ci = charIndex++;
                      const cp = enter(
                        frame,
                        ci * (animation === "typewriter" ? 1.5 : 0.6),
                        16,
                      );
                      return (
                        <span
                          key={i}
                          style={{
                            display: char === " " ? "inline" : "inline-block",
                            whiteSpace: "pre",
                            opacity:
                              animation === "typewriter"
                                ? frame >= ci * 1.5
                                  ? 1
                                  : 0
                                : cp,
                            transform:
                              animation === "letter-cascade"
                                ? `translateY(${(1 - cp) * 35}px) rotate(${(1 - cp) * 8}deg)`
                                : animation === "split-flap"
                                  ? `perspective(500px) rotateX(${(1 - cp) * -90}deg)`
                                  : undefined,
                          }}
                        >
                          {char}
                        </span>
                      );
                    })
                  : line}
            </div>
          </div>
        );
      })}
    </div>
  );
}
