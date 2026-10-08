> Källa: <https://hyperframes.heygen.com/guides/music-to-video> · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07

# Create a music-driven video

*Cut footage, images, lyrics, and motion to a track’s beat grid.*

Start with a music file—or a video whose audio should control the edit. Narration is not added; the track is the spine.

Video: https://static.heygen.ai/hyperframes-oss/docs/images/showcase/full-music-v2.mp4

*A complete music-driven film. Its sections, visual treatments, and cuts follow the track.*

## Make the request

Attach the track and any media that must appear:

```text
Using /hyperframes, turn assets/song.wav and the photos in assets/tour into a
30-second music-driven video.
```

The agent analyzes the real track before planning the cut. Mention a required
section, lyric, image order, or delivery format when it cannot be chosen freely.

## What should the track drive?

- **Use your photos or video** — cut approved media to the track's phrases, energy, beats, and ending.
- **Make a lyric video** — verify the words first, then synchronize and design each line around the vocal.
- **Invent the visuals** — build the visual arc from typography, graphic elements, and motion when no media is supplied.

A complete video can also be built entirely from type, graphic templates, and
motion.

## The track sets the structure

HyperFrames maps the track’s phrases, energy, onsets, silences, rolls, drops, and hard stops before it plans the visuals.

A rhythmic track can support cuts on its real beat grid. Calm or loose music should flow by phrase and energy instead of forcing a cut onto every measured beat.

The visual treatments change at meaningful musical moments. More beats do not automatically mean more scenes.

## Review the rhythm

- The correct section of the track is used.
- Required media appears and lyrics match the vocal.
- The strongest visual changes land on meaningful musical changes.
- Important images and text remain long enough to understand.
- The ending reaches a musical landing or forms a deliberate loop.

For direct timing control, use the [Studio timeline](https://hyperframes.heygen.com/studio/timeline) to refine
cuts, holds, and the ending against the beat markers. Ask the agent when the
section, media plan, or overall treatment must change.

- [Finish and share](export-and-share.md) — Check the final project, render through your preferred surface, and review the file.

## Related topics

- [Edit cuts and holds on the Studio timeline](https://hyperframes.heygen.com/studio/timeline)
- [Work with voice, music, sound, and captions](voice-and-audio.md)
- [Prompt for music videos and slideshows](../prompting/music-and-slideshows.md)
