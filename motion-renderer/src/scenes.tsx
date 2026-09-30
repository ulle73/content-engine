import React from "react";
import { Img, OffthreadVideo } from "remotion";
import { Lottie } from "@remotion/lottie";
import { makeStar } from "@remotion/shapes";
import { Fit } from "./text";
import { clamp, enter, number, safe } from "./math";
import { mark } from "./lottie";
import type { SceneContext, Asset } from "./types";

const abs = (
  x: number,
  y: number,
  width: number,
  height?: number,
): React.CSSProperties => ({
  position: "absolute",
  left: x,
  top: y,
  width,
  height,
});
function Media({
  asset,
  style,
  fit = "cover",
  duotone = false,
}: {
  asset?: Asset;
  style: React.CSSProperties;
  fit?: "cover" | "contain";
  duotone?: boolean;
}) {
  if (!asset) return null;
  const s = {
    ...style,
    objectFit: fit,
    filter: duotone ? "grayscale(1) sepia(.3)" : undefined,
  };
  return asset.kind === "video" ? (
    <OffthreadVideo src={asset.src} muted style={s} />
  ) : (
    <Img src={asset.src} style={s} />
  );
}

export function SceneContents(c: SceneContext) {
  const { scene, frame: f, width: w, height: h, brand: b, assets, fps } = c;
  const p = scene.props;
  const s = safe(w, h);
  const min = Math.min(w, h);
  const big = min * 0.16;
  const small = min * 0.036;
  const labelSize = min * 0.03;
  const title = (
    text = p.headline,
    y = s.y,
    max = big,
    height = s.h * 0.38,
    animation = "none",
    width = s.w,
    x = s.x,
  ) => (
    <div style={abs(x, y, width, height)}>
      <Fit
        text={text}
        width={width}
        height={height}
        max={max}
        frame={f}
        animation={animation}
        font={b.font_family}
      />
    </div>
  );
  const body = (
    text = p.body,
    y = s.y + s.h * 0.72,
    height = s.h * 0.23,
    width = s.w,
    x = s.x,
  ) => (
    <div style={{ ...abs(x, y, width, height), opacity: enter(f, 14) }}>
      <Fit
        text={text}
        width={width}
        height={height}
        max={small * 1.25}
        weight={400}
        font={b.font_family}
        style={{ letterSpacing: "-.015em", color: b.muted }}
      />
    </div>
  );
  const eyebrow = p.eyebrow ? (
    <div
      style={{
        ...abs(s.x, s.y - labelSize * 2, s.w),
        fontSize: labelSize,
        fontWeight: 600,
        letterSpacing: ".12em",
        textTransform: "uppercase",
        opacity: enter(f),
      }}
    >
      {p.eyebrow}
    </div>
  ) : null;
  const logo = b.logo_asset_id ? assets[b.logo_asset_id] : undefined;
  const a = p.asset_id ? assets[p.asset_id] : undefined;
  const second = p.secondary_asset_id
    ? assets[p.secondary_asset_id]
    : undefined;
  const main = scene.component;
  const items = p.items;
  const prog = enter(f, 8, 42);
  const total = items.reduce((a, d) => a + Math.max(0, d.value), 0) || 1;
  const formatted =
    number(p.value * prog, main === "percentage" ? 1 : 0) +
    (p.unit ? " " + p.unit : "");
  const duotone = scene.effects.includes("duotone");
  const label = (text: string, x: number, y: number, width = s.w) => (
    <div style={abs(x, y, width)}>
      <Fit
        text={text}
        width={width}
        height={small * 2.8}
        max={small}
        weight={500}
        font={b.font_family}
      />
    </div>
  );
  const rule = (
    <div
      style={{
        ...abs(s.x, s.y + s.h * 0.62, s.w, 3),
        background: b.muted,
        opacity: 0.4,
        transformOrigin: "left",
        transform: `scaleX(${enter(f, 14, 30)})`,
      }}
    />
  );
  const glyph = makeStar({ points: 8, innerRadius: 40, outerRadius: 70 });
  let content: React.ReactNode;
  if (
    [
      "kinetic-words",
      "line-reveal",
      "letter-cascade",
      "typewriter",
      "tracking",
      "blur-reveal",
      "mask-rise",
      "brush-write",
      "outline-fill",
      "word-highlight",
      "split-flap",
    ].includes(main)
  ) {
    content = (
      <>
        {title(p.headline, s.y + s.h * 0.08, big, s.h * 0.62, main)}
        {body()}
        <svg
          width="160"
          height="160"
          style={{
            position: "absolute",
            right: s.x,
            top: s.y + s.h * 0.76,
            opacity: 0.25,
            transform: `rotate(${f * 0.8}deg)`,
          }}
        >
          <path d={glyph.path} fill={b.accent} transform="translate(8,8)" />
        </svg>
      </>
    );
  } else
    switch (main) {
      case "footage": {
        if (!a) throw new Error("Footage asset missing");
        const hasTitle = Boolean(p.headline);
        const mediaTop = hasTitle ? h * 0.24 : 0;
        content = (
          <>
            <Media
              asset={a}
              fit="contain"
              style={abs(0, mediaTop, w, h - mediaTop)}
            />
            {hasTitle &&
              title(p.headline, s.y, big * 0.65, h * 0.16, "line-reveal")}
          </>
        );
        break;
      }
      case "number-emphasis":
      case "counter":
      case "currency":
        content = (
          <>
            {title(p.headline, s.y, big * 0.58, s.h * 0.2, "line-reveal")}
            <div style={abs(s.x, s.y + s.h * 0.25, s.w, s.h * 0.34)}>
              <Fit
                text={
                  main === "number-emphasis"
                    ? number(p.value) + (p.unit ? " " + p.unit : "")
                    : formatted
                }
                width={s.w}
                height={s.h * 0.34}
                max={big * 2.5}
                font={b.font_family}
                style={{
                  fontVariantNumeric: "tabular-nums",
                  letterSpacing: "-.05em",
                }}
              />
            </div>
            {rule}
            {body()}
            <div
              style={{
                ...abs(s.x, s.y + s.h * 0.94, s.w, 8),
                background: b.accent,
                transformOrigin: "left",
                transform: `scaleX(${prog})`,
              }}
            />
          </>
        );
        break;
      case "percentage":
      case "donut": {
        const radius = min * 0.23;
        const cx = w / 2;
        const cy = s.y + s.h * 0.6;
        const circ = 2 * Math.PI * radius;
        let offset = 0;
        content = (
          <>
            {title(p.headline, s.y, big * 0.6, s.h * 0.22, "line-reveal")}
            <svg width={w} height={h} style={abs(0, 0, w, h)}>
              <circle
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke={b.accent}
                strokeWidth={min * 0.035}
                opacity=".25"
              />
              {main === "percentage" ? (
                <circle
                  cx={cx}
                  cy={cy}
                  r={radius}
                  fill="none"
                  stroke={b.muted}
                  strokeWidth={min * 0.035}
                  strokeDasharray={`${((circ * p.value) / 100) * prog} ${circ}`}
                  transform={`rotate(-90 ${cx} ${cy})`}
                />
              ) : (
                items.map((item, i) => {
                  const part = item.value / total;
                  const result = (
                    <circle
                      key={i}
                      cx={cx}
                      cy={cy}
                      r={radius}
                      fill="none"
                      stroke={i % 2 ? b.accent : b.muted}
                      opacity={1 - i * 0.045}
                      strokeWidth={min * 0.055}
                      strokeDasharray={`${Math.max(0, circ * part * prog - 8)} ${circ}`}
                      strokeDashoffset={-offset * circ}
                      transform={`rotate(-90 ${cx} ${cy})`}
                    />
                  );
                  offset += part;
                  return result;
                })
              )}
            </svg>
            {main === "percentage" ? (
              <div
                style={abs(
                  cx - radius,
                  cy - radius * 0.4,
                  radius * 2,
                  radius * 0.8,
                )}
              >
                <Fit
                  text={number(p.value * prog, 1) + "%"}
                  width={radius * 2}
                  height={radius * 0.8}
                  max={big}
                  font={b.font_family}
                  style={{ textAlign: "center" }}
                />
              </div>
            ) : (
              label(
                items.map((d) => `${d.label} ${number(d.value)}`).join("  /  "),
                s.x,
                s.y + s.h * 0.92,
                s.w,
              )
            )}
          </>
        );
        break;
      }
      case "ranking":
      case "list":
      case "steps":
      case "timeline": {
        const row = Math.min(
          s.h * 0.14,
          (s.h * 0.68) / Math.max(items.length, 1),
        );
        const top = s.y + s.h * 0.29;
        content = (
          <>
            {title(p.headline, s.y, big * 0.66, s.h * 0.22, "line-reveal")}
            {main === "timeline" && (
              <div
                style={{
                  ...abs(s.x + small * 0.65, top, 3, row * (items.length - 1)),
                  background: b.accent,
                  transformOrigin: "top",
                  transform: `scaleY(${prog})`,
                }}
              />
            )}
            {items.map((item, i) => {
              const ip = enter(f, 12 + i * 8, 22);
              return (
                <div
                  key={i}
                  style={{
                    ...abs(s.x, top + row * i, s.w, row * 0.85),
                    opacity: ip,
                    transform: `translateX(${(1 - ip) * 60}px)`,
                    display: "flex",
                    alignItems: "center",
                    gap: small * 0.8,
                    borderBottom:
                      main === "timeline" ? "none" : `2px solid ${b.accent}`,
                  }}
                >
                  <span
                    style={{
                      fontSize: small * 1.6,
                      fontWeight: 800,
                      color: b.muted,
                      minWidth: small * 1.7,
                    }}
                  >
                    {main === "ranking" ? "#" : ""}
                    {i + 1}
                  </span>
                  <Fit
                    text={item.label}
                    width={s.w - small * 3.5}
                    height={row * 0.75}
                    max={small * 1.6}
                    font={b.font_family}
                  />
                  {main === "ranking" && item.value !== 0 && (
                    <span style={{ fontSize: small, marginLeft: "auto" }}>
                      {number(item.value)}
                    </span>
                  )}
                </div>
              );
            })}
          </>
        );
        break;
      }
      case "bars":
      case "sparkline": {
        const top = s.y + s.h * 0.32;
        const chartH = s.h * 0.5;
        const max = Math.max(1, ...items.map((d) => d.value));
        content = (
          <>
            {title(p.headline, s.y, big * 0.6, s.h * 0.23, "line-reveal")}
            {main === "bars" ? (
              items.map((item, i) => {
                const row = chartH / Math.max(1, items.length);
                return (
                  <div key={i} style={abs(s.x, top + i * row, s.w, row * 0.85)}>
                    <div
                      style={{
                        fontSize: small * 0.9,
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <span>{item.label}</span>
                      <span>{number(item.value)}</span>
                    </div>
                    <div
                      style={{
                        height: row * 0.24,
                        marginTop: row * 0.12,
                        background: b.muted,
                        width: `${(Math.max(0, item.value) / max) * 100 * enter(f, 10 + i * 5, 35)}%`,
                      }}
                    />
                  </div>
                );
              })
            ) : (
              <>
                <svg
                  width={s.w}
                  height={chartH}
                  style={abs(s.x, top, s.w, chartH)}
                >
                  <line
                    x1="0"
                    y1={chartH - 2}
                    x2={s.w}
                    y2={chartH - 2}
                    stroke={b.accent}
                    strokeWidth="3"
                  />
                  <polyline
                    points={items
                      .map(
                        (d, i) =>
                          `${(i / Math.max(1, items.length - 1)) * s.w},${chartH * (0.9 - (0.75 * d.value) / max)}`,
                      )
                      .join(" ")}
                    fill="none"
                    stroke={b.muted}
                    strokeWidth="7"
                    pathLength="1"
                    strokeDasharray="1"
                    strokeDashoffset={1 - prog}
                  />
                </svg>
                {label(
                  items.map((d) => d.label).join("   /   "),
                  s.x,
                  top + chartH + 20,
                )}
              </>
            )}
            {body(p.body, s.y + s.h * 0.91, s.h * 0.1)}
          </>
        );
        break;
      }
      case "comparison":
      case "stat-wall":
      case "recap": {
        const cols =
          main === "comparison"
            ? 2
            : s.portrait
              ? 2
              : Math.min(3, Math.max(items.length, 1));
        const rows = Math.ceil(items.length / cols) || 1;
        const cw = s.w / cols;
        const ch = (s.h * 0.63) / rows;
        content = (
          <>
            {title(p.headline, s.y, big * 0.62, s.h * 0.23, "line-reveal")}
            {items.map((item, i) => {
              const x = s.x + (i % cols) * cw;
              const y = s.y + s.h * 0.32 + Math.floor(i / cols) * ch;
              const ip = enter(f, 10 + i * 8, 35);
              return (
                <div
                  key={i}
                  style={{
                    ...abs(x, y, cw * 0.92, ch * 0.9),
                    opacity: enter(f, 10 + i * 8),
                  }}
                >
                  <Fit
                    text={number(item.value * ip)}
                    width={cw * 0.92}
                    height={ch * 0.48}
                    max={big * 1.1}
                    font={b.font_family}
                  />
                  <div style={{ marginTop: small * 0.3 }}>
                    <Fit
                      text={item.label}
                      width={cw * 0.92}
                      height={ch * 0.32}
                      max={small * 1.1}
                      weight={400}
                      font={b.font_family}
                    />
                  </div>
                </div>
              );
            })}
          </>
        );
        break;
      }
      case "quote":
      case "testimonial":
        content = (
          <>
            <div
              style={{
                ...abs(s.x, s.y - small, s.w),
                fontSize: big * 2,
                color: b.accent,
                lineHeight: 1,
                fontFamily: "Georgia,serif",
              }}
            >
              {"\u201c"}
            </div>
            {title(
              p.headline,
              s.y + s.h * 0.2,
              big * 0.7,
              s.h * 0.47,
              "blur-reveal",
            )}
            {label(p.attribution, s.x, s.y + s.h * 0.82, a ? s.w * 0.7 : s.w)}
            {main === "testimonial" && a && (
              <Media
                asset={a}
                fit="cover"
                style={{
                  ...abs(
                    s.x + s.w - small * 4,
                    s.y + s.h * 0.8,
                    small * 4,
                    small * 4,
                  ),
                  borderRadius: "50%",
                }}
              />
            )}
          </>
        );
        break;
      case "product":
      case "spotlight":
      case "split-media":
      case "mosaic":
      case "device": {
        const horizontal = !s.portrait;
        const imageX = horizontal ? s.x + s.w * 0.48 : s.x;
        const imageY = horizontal ? s.y : s.y + s.h * 0.31;
        const imageW = horizontal ? s.w * 0.52 : s.w;
        const imageH = horizontal ? s.h * 0.84 : s.h * 0.48;
        const titleW = horizontal ? s.w * 0.42 : s.w;
        content = (
          <>
            {title(
              p.headline,
              s.y,
              big * 0.7,
              horizontal ? s.h * 0.5 : s.h * 0.24,
              "line-reveal",
              titleW,
            )}
            {a && (
              <div
                style={{
                  ...abs(imageX, imageY, imageW, imageH),
                  overflow: "hidden",
                  transform: `translateY(${(1 - enter(f, 8, 25)) * 45}px)`,
                  opacity: enter(f, 8, 25),
                  border:
                    main === "device" ? `10px solid ${b.muted}` : undefined,
                  borderRadius: main === "device" ? min * 0.045 : undefined,
                }}
              >
                <Media
                  asset={a}
                  duotone={duotone}
                  fit={
                    main === "product" || main === "device"
                      ? "contain"
                      : "cover"
                  }
                  style={{ width: "100%", height: "100%" }}
                />
              </div>
            )}
            {main === "mosaic" && second && (
              <Media
                asset={second}
                style={{
                  ...abs(
                    imageX + imageW * 0.45,
                    imageY + imageH * 0.53,
                    imageW * 0.55,
                    imageH * 0.48,
                  ),
                  border: `5px solid ${b.background}`,
                }}
              />
            )}
            {body(
              p.body,
              horizontal ? s.y + s.h * 0.57 : s.y + s.h * 0.85,
              horizontal ? s.h * 0.35 : s.h * 0.13,
              titleW,
            )}
          </>
        );
        break;
      }
      case "before-after": {
        const top = s.y + s.h * 0.3;
        const mh = s.h * 0.57;
        const reveal = clamp((f - 18) / 55);
        content = (
          <>
            {title(p.headline, s.y, big * 0.62, s.h * 0.22, "line-reveal")}
            <div style={{ ...abs(s.x, top, s.w, mh), overflow: "hidden" }}>
              <Media
                asset={a}
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  clipPath: `inset(0 ${(1 - reveal) * 100}% 0 0)`,
                }}
              >
                <Media
                  asset={second}
                  style={{ width: "100%", height: "100%" }}
                />
              </div>
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  bottom: 0,
                  left: `${reveal * 100}%`,
                  width: 5,
                  background: b.muted,
                }}
              />
            </div>
            {body(p.body, s.y + s.h * 0.92, s.h * 0.1)}
          </>
        );
        break;
      }
      case "countdown":
        content = (
          <>
            {title(p.headline, s.y, big * 0.65, s.h * 0.25)}
            <div style={abs(s.x, s.y + s.h * 0.32, s.w, s.h * 0.5)}>
              <Fit
                text={String(Math.max(0, Math.ceil(p.value - f / fps)))}
                width={s.w}
                height={s.h * 0.5}
                max={big * 3}
                font={b.font_family}
              />
            </div>
          </>
        );
        break;
      case "logo-sting":
      case "end-card":
        content = (
          <>
            {logo && (
              <Media
                asset={logo}
                fit="contain"
                style={{
                  ...abs(s.x, s.y, s.w, s.h * 0.42),
                  opacity: enter(f, 0, 24),
                  transform: `scale(${0.8 + 0.2 * enter(f, 0, 28)})`,
                }}
              />
            )}
            {title(
              p.headline,
              logo ? s.y + s.h * 0.5 : s.y + s.h * 0.15,
              big * 0.72,
              s.h * 0.3,
              "mask-rise",
            )}
            {body(p.cta || p.body, s.y + s.h * 0.85, s.h * 0.15)}
          </>
        );
        break;
      case "offer":
      case "cta":
        content = (
          <>
            {title(
              p.headline,
              s.y + s.h * 0.05,
              big,
              s.h * 0.44,
              "kinetic-words",
            )}
            {p.value !== 0 &&
              label(
                number(p.value) + (p.unit ? " " + p.unit : ""),
                s.x,
                s.y + s.h * 0.52,
              )}
            {body(p.body, s.y + s.h * 0.63, s.h * 0.18)}
            <div
              style={{
                ...abs(s.x, s.y + s.h * 0.87, s.w, small * 2.4),
                borderTop: `3px solid ${b.muted}`,
                paddingTop: small * 0.5,
                opacity: enter(f, 26),
              }}
            >
              <Fit
                text={p.cta}
                width={s.w}
                height={small * 2}
                max={small * 1.4}
                font={b.font_family}
              />
            </div>
          </>
        );
        break;
      case "announcement":
        content = (
          <>
            <div
              style={{
                ...abs(s.x, s.y, s.w, small * 1.8),
                background: b.muted,
                color: b.background,
                padding: small * 0.2,
                transformOrigin: "left",
                transform: `scaleX(${enter(f)})`,
                fontSize: small,
                fontWeight: 700,
              }}
            >
              {p.eyebrow || "NYHET"}
            </div>
            {title(
              p.headline,
              s.y + s.h * 0.2,
              big * 0.85,
              s.h * 0.45,
              "line-reveal",
            )}
            {body(p.body, s.y + s.h * 0.76, s.h * 0.22)}
          </>
        );
        break;
      case "lottie-mark":
        content = (
          <>
            {title(p.headline, s.y, big * 0.65, s.h * 0.25)}
            <Lottie
              animationData={mark}
              style={{
                ...abs(
                  s.x + s.w * 0.15,
                  s.y + s.h * 0.26,
                  s.w * 0.7,
                  s.h * 0.55,
                ),
              }}
            />
            {body(p.body, s.y + s.h * 0.86, s.h * 0.12)}
          </>
        );
        break;
      case "perspective-stack":
        content = (
          <>
            {title(p.headline, s.y, big * 0.65, s.h * 0.26, "line-reveal")}
            {items.slice(0, 4).map((item, i) => {
              const ip = enter(f, 10 + i * 8, 30);
              return (
                <div
                  key={i}
                  style={{
                    ...abs(s.x, s.y + s.h * (0.35 + i * 0.15), s.w, s.h * 0.12),
                    borderBottom: `3px solid ${b.muted}`,
                    transformOrigin: "left",
                    transform: `perspective(1000px) rotateY(${(1 - ip) * 45}deg) translateZ(${-i * 20}px)`,
                    opacity: ip,
                  }}
                >
                  <Fit
                    text={item.label}
                    width={s.w}
                    height={s.h * 0.12}
                    max={small * 2}
                    font={b.font_family}
                  />
                </div>
              );
            })}
          </>
        );
        break;
      case "hero":
        content = (
          <>
            {title(
              p.headline,
              s.y + s.h * 0.08,
              big * 1.18,
              s.h * 0.53,
              "line-reveal",
            )}
            {rule}
            {body(p.body, s.y + s.h * 0.72, s.h * 0.23)}
          </>
        );
        break;
      default:
        throw new Error("Unregistered scene component: " + main);
    }
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        color: b.foreground,
        fontFamily: b.font_family,
      }}
    >
      {main === "announcement" ? null : eyebrow}
      {content}
    </div>
  );
}
