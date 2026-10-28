// Exempel: Blender-klipp med alfa (WebM VP9) ovanpå en befintlig film i Remotion.
// <OffthreadVideo transparent> extraherar bildrutor som PNG så att alfan följer med (Remotion ≥ 4.0.0,
// https://www.remotion.dev/docs/offthreadvideo#transparent). Filerna ligger i publicDir (se render.mjs).
import React from 'react';
import { AbsoluteFill, Composition, OffthreadVideo, Sequence, registerRoot, staticFile } from 'remotion';

const FPS = 30;

const Overlay = ({ film, filmFran, lager }) => (
  <AbsoluteFill style={{ backgroundColor: '#082f27' }}>
    <OffthreadVideo src={staticFile(film)} trimBefore={Math.round(filmFran * FPS)} muted />
    {lager.map((l) => (
      <Sequence key={l.src} from={Math.round(l.start * FPS)} layout="none">
        <AbsoluteFill>
          <OffthreadVideo src={staticFile(l.src)} transparent muted />
        </AbsoluteFill>
      </Sequence>
    ))}
  </AbsoluteFill>
);

const Root = () => (
  <Composition
    id="Blender3dOverlay"
    component={Overlay}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={150}
    defaultProps={{
      film: 'film.mp4',
      filmFran: 0,
      lager: [
        { src: 'golfboll.webm', start: 0 },
        { src: 'titel.webm', start: 1.2 },
      ],
    }}
    calculateMetadata={({ props }) => ({ durationInFrames: props.langd ? Math.round(props.langd * FPS) : 150 })}
  />
);

registerRoot(Root);
