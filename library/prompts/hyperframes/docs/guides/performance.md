> Källa: <https://hyperframes.heygen.com/guides/performance> · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07

# Fix a slow preview or render

*Find the expensive part of a composition and make it cheaper.*

A finished render can be smooth even when preview stutters. Preview must draw each frame in real time; render can take as long as it needs to capture the same frames.

Video: https://static.heygen.ai/hyperframes-oss/docs/images/showcase/render-performance-demo-v2.mp4

Real numbers, not estimates: 25.0s against 9.8s, taken as the median of three
runs at 1920x1080 over 300 frames. One CSS declaration is the whole difference,
and a pixel comparison confirms the picture did not change.

## Start with the symptom

| What you see | Check first |
| --- | --- |
| Preview stutters in one scene | Large blurs, masks, shadows, or many animated layers in that scene |
| Preview pauses the first time an image appears | Oversized source images or image decoding |
| The whole page becomes slow | Script work, layout thrashing, or too many DOM nodes |
| Render is slow but the result is correct | Source-video extraction, frame capture, or encoding |
| WebM takes much longer than MP4 | VP9 encoding; transparent WebM is CPU-heavy |

## Reduce expensive browser work

- Use fewer large `backdrop-filter` and `filter: blur()` layers.
- Avoid animating dozens of shadowed elements at once.
- Replace a static blur or texture stack with a pre-rendered image.
- Size images near their actual delivery dimensions. A very large JPEG still decodes into a very large bitmap.
- Keep work inside animation callbacks small. Do not repeatedly read layout and write styles in the same frame.

For a 1920×1080 composition, a 3840×2160 source already provides enough detail for a 2× display. Larger sources usually add memory and decode work without improving the frame.

## Measure instead of guessing

1. Run `npx hyperframes preview`.
2. Open Chrome DevTools and select **Performance**.
3. Record the part that stutters.
4. Inspect the longest tasks:
   - **Paint** or **Composite Layers** points to filters, shadows, masks, or large layers.
   - **Layout** or **Recalculate Style** points to layout work.
   - **Script** points to author code.

Change one expensive feature, record again, and keep the version that moves the bottleneck.

## Make a fast review render

If the composition is intentionally too heavy for real-time playback, review an encoded file:

```bash
npx hyperframes render --quality draft --output review.mp4
```

Use `standard` or `high` for delivery. Draft changes capture and encoder quality; it does not change the composition's timing.

## Tune transparent WebM only when needed

WebM uses the CPU-heavy VP9 encoder. The default is suitable for most work. To trade more encoding time for compression quality:

```bash
npx hyperframes render --format webm --vp9-cpu-used 2 --output overlay.webm
```

`--vp9-cpu-used` accepts integers from `-8` to `8`; higher values are faster with a larger quality/size tradeoff.

## Related topics

- [Diagnose a failed or stalled render](troubleshooting.md)
- [Render from the command line](rendering.md)
- [Render at 4K](4k-rendering.md)
