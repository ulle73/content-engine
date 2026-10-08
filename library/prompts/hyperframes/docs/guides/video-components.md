> Källa: <https://hyperframes.heygen.com/guides/video-components> · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07

# Use images and video

*Import, place, replace, trim, and review images and footage in a HyperFrames project.*

Images and footage should enter the project once, remain easy to identify, and
behave the same in preview and the final render.

Video: https://static.heygen.ai/hyperframes-oss/docs/images/showcase/media-basics-demo-v1.mp4

Each step adds one attribute and shows the result. The last swaps the source
file; the crop, timing and placement around it stay exactly as they were.

## Import a file

In Studio:

1. Open **Assets**.
2. Choose **Import media**, or drop the file into the panel.
3. Preview it.
4. Drag it to the timeline.

Studio accepts common image formats, SVG, MP4, WebM, and MOV. Keep the source
inside the project before the final render.

## Place it deliberately

- Set the start and duration by watching the surrounding edit.
- Choose a crop that preserves the important content.
- Keep source audio only when it belongs in the mix.
- Avoid stretching low-resolution media beyond what it can support.
- Use a wrapper when animating the size or position of video; this keeps frame capture reliable.

For a source-level change, ask the agent in terms of the visible result:

```text
Use assets/product-tour.mp4 from 00:04 to 00:10.
Crop around the editor canvas, keep the source muted, and place it beneath
the existing caption layer.
```

## Change or replace the source

Studio’s Media section shows the current project path and controls Fit,
Position, playback, and audio. Assets imports files and adds new layers. It does
not currently provide a one-click source replacement in that Inspector.

To keep the existing layer, ask the agent to change its `src`, or edit the
element in Source. Then recheck the crop, clip length, transition, and any
motion tied to the old dimensions.

Replacing a file should not require rebuilding the whole scene. If the new
content also changes the story or several scenes, ask the agent to make the
broader revision.

## Avoid fragile sources

Temporary signed URLs, private browser sessions, and render-time network
requests can disappear or fail in another environment. Copy required media into
the project, keep filenames stable, and run `npx hyperframes check` before
rendering.

Continue to [Use Assets and Catalog](https://hyperframes.heygen.com/studio/assets-and-blocks) for the Studio
controls, or [Media effects](media-effects.md) when the source needs a
non-destructive visual treatment.

## The same edits in Studio

Everything above is done by editing attributes by hand. Studio writes the
same attributes when you drag, trim or reframe — it is the other way into
one file, not a second copy of the project.

Video: https://static.heygen.ai/hyperframes-oss/docs/images/showcase/studio-media-edit-loop-v4.mp4

*Current Studio, changing the real project: inspect the source, change Fit and Position, crop on the canvas, then import another local asset.*

## Related topics

- [Use Assets and Catalog in Studio](https://hyperframes.heygen.com/studio/assets-and-blocks)
- [Apply a media effect](media-effects.md)
- [Remove a human background](remove-background.md)
