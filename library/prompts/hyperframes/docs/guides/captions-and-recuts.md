> Källa: <https://hyperframes.heygen.com/guides/captions-and-recuts> · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07

# Add captions or repackage talking-head footage

*Add captions, add designed overlays, or change the spoken edit.*

Video: https://static.heygen.ai/hyperframes-oss/docs/images/showcase/captions-recut-demo-v1.mp4

A verbatim rail, an embedded climax word, kinetic emphasis, a lower third and a
pull-quote. The footage underneath is never re-edited — the overlays carry all
of it.

## Make the request

Name the file and the change you want:

```text
Using /hyperframes, add clear animated captions to assets/interview.mp4.
Keep the footage and its spoken edit unchanged.
```

Ask for designed information cards instead when the footage needs titles,
quotes, statistics, lower thirds, or picture-in-picture.

## What should change?

This page covers two workflows. `/hyperframes` picks between them from what you
ask for, and you can name one directly if you already know which you want.

- **Words on screen** — `/embedded-captions`. Readable, timed words over the clip.
  Plain subtitles, or cinematic captions set behind the subject.
- **Designed cards on screen** — `/talking-head-recut`. Titles, pull-quotes, data
  callouts, lower thirds, picture-in-picture, synced to the transcript.
- **Change the footage itself** — neither of these. Use
  [General Video](general-video.md) when pauses, selected moments, or the
  spoken order must change.

Both leave the clip and its audio untouched: the first adds words, the second adds
graphics, and the footage plays the same underneath either way.

Captions and designed overlays work best on a clear, single-subject clip with audible speech. Both keep the original footage and audio intact.

If you need to remove pauses, choose different moments, or reorder the speech, use [General Video](general-video.md).

## Before it builds

Confirm:

- **Captions:** the intended format and any names or terms the transcript may miss. HyperFrames can recommend a visual treatment after it sees the clip.
- **Designed overlays:** the format, layout, visual style, and how often a title, quote, statistic, or side panel should appear.
- **Either path:** where the speaker, existing text, and important action leave safe room for graphics.

## Review what matters

- Names, product terms, and numbers are correct.
- Captions follow the spoken words.
- Graphics avoid faces and important parts of the footage.
- The video works with sound and muted.
- The final caption or graphic clears before the video ends.

For direct placement changes, use [Captions in Studio](https://hyperframes.heygen.com/studio/captions) to
inspect synchronization and save position, scale, or rotation corrections. Ask
the agent or edit the caption source for corrected words and durable timing or
style changes.

- [Finish and share](export-and-share.md) — Review the chosen caption, overlay, or recut path, then render and watch the final file.

## Related topics

- [Edit captions in Studio](https://hyperframes.heygen.com/studio/captions)
- [Work with voice, music, sound, and captions](voice-and-audio.md)
- [Change the spoken edit with a custom video workflow](general-video.md)
