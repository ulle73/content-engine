import type { CSSProperties } from "react";
import { clamp, smooth } from "./math";

/** Masks apply only to the incoming frame; outgoing content continues underneath. */
export function transitionStyle(
  kind: string,
  progress: number,
  outgoing = false,
): CSSProperties {
  const p = smooth(progress);
  const q = 1 - p;
  if (outgoing) {
    if (kind === "push") return { transform: `translateX(${-p * 100}%)` };
    if (kind === "whip")
      return {
        transform: `translateX(${-p * 100}%)`,
        filter: `blur(${Math.sin(p * Math.PI) * 14}px)`,
      };
    if (kind === "zoom")
      return { transform: `scale(${1 + p * 0.4})`, opacity: q };
    if (kind === "blur") return { filter: `blur(${p * 25}px)`, opacity: q };
    return {};
  }
  switch (kind) {
    case "cut":
      return {};
    case "fade":
      return { opacity: p };
    case "wipe":
      return { clipPath: `inset(0 ${q * 100}% 0 0)` };
    case "push":
      return { transform: `translateX(${q * 100}%)` };
    case "whip":
      return {
        transform: `translateX(${q * 100}%)`,
        filter: `blur(${Math.sin(p * Math.PI) * 14}px)`,
      };
    case "zoom":
      return { transform: `scale(${0.78 + 0.22 * p})`, opacity: p };
    case "iris":
      return { clipPath: `circle(${p * 150}% at 50% 50%)` };
    case "diagonal":
      return {
        clipPath: `polygon(0 0, ${p * 200}% 0, ${p * 200 - 100}% 100%, 0 100%)`,
      };
    case "blinds":
      return {
        maskImage: `repeating-linear-gradient(90deg,#000 0 ${p * 100}px,transparent ${p * 100}px 100px)`,
      };
    case "split":
      return { clipPath: `inset(0 ${q * 50}% 0 ${q * 50}%)` };
    case "brush":
      return {
        clipPath: `polygon(0 0,${p * 110}% 0,${clamp(p * 1.1 - 0.04) * 100}% 20%,${clamp(p * 1.1 + 0.02) * 100}% 38%,${clamp(p * 1.1 - 0.07) * 100}% 56%,${clamp(p * 1.1 + 0.03) * 100}% 76%,${p * 110}% 100%,0 100%)`,
      };
    case "blur":
      return { opacity: p, filter: `blur(${q * 25}px)` };
    case "flash":
      return {
        opacity: p,
        filter: `brightness(${1 + Math.sin(p * Math.PI) * 1.5})`,
      };
    default:
      throw new Error("Unregistered transition");
  }
}
