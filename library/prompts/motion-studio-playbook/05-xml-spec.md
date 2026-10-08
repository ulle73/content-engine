# XML-spec – strukturerad brief i sex block

**Vad:** en briefmall där varje del av beställningen har sin egen tagg. Modellen tappar mindre när
indata, riktning, struktur, byggregler, fallgropar och första steget är tydligt separerade.
**När:** allt som är längre än en enradare – särskilt UI-animation, produktfilmer och loopar.

## Mall

```xml
<inputs>
What to ask me for before starting (assets, colours, music, facts). List them; ask in one message.
</inputs>

<direction>
The look and feel in 4–8 sentences: reference style, palette, type, motion character.
What is banned (e.g. glows on UI chrome, bouncy easing, dead time, template look).
</direction>

<structure>
Tempo (BPM / seconds), number of beats or scenes, and the sequence of states/events in order.
</structure>

<build>
Numbered technical rules: canvas size, render contract, springs/track(), beat grid,
how sound is placed, motion blur, the preview-before-render step.
</build>

<gotchas>
Known failure modes for this kind of film and how to avoid them.
</gotchas>

<start>
The very first thing to do and where to stop for my approval.
</start>
```

## Ifyllt exempel – "en form klipper aldrig" (Golfkuponger, 1:1-loop)

```xml
<inputs>
Ask me for: the order of UI states (default below), accent colour (default #0f7a50 on cream #f6f8f7),
and a royalty-free or self-generated track around 110–125 BPM.
</inputs>

<direction>
Premium Scandinavian UI motion. ONE rounded rectangle is the hero and the film never cuts: every
state is that same element changing size, corner radius and colour while its content swaps with a
short blur. A cursor causes every change with real clicks, drags and typing. Calm cream canvas,
dark green components, Inter. Springs with at most a small overshoot. The camera reframes so each
state fills the frame. The last frame equals the first, so it loops.
Avoid: particles, glow, gradients on UI, mismatched icon strokes, moments where nothing moves.
</direction>

<structure>
~120 BPM, 8 bars, an event on every beat:
button "Sök Golfkuponger" → search field, cursor types "golf" → result row expands →
amount slider dragged to [belopp] (stretches if pulled past max) → confirm → check mark →
the shape becomes the app's code card → it unfolds into a map with club pins →
toast "Klar för säsongen" → collapses back into the button.
</structure>

<build>
1. One HTML file, 1080x1080. window.seek(t) computes every style from t (01-render-contract.md).
2. Closed-form springs; values that retarget use track() from springs.mjs.
3. Leading and trailing edges of the slider/indicator ride different springs, so the shape stretches.
4. Drags are direct manipulation: while held, the value follows the cursor; on release it springs
   back from its current position and velocity (springFrom).
5. Beat grid from beat_grid.py; start on a downbeat; every UI sound placed on its measured peak.
6. Render 4 subframes per frame, blend for motion blur, never across a hard cut (there are none).
7. Before the full render: one frame per beat on a contact sheet; fix anything off-grid or cramped.
</build>

<gotchas>
Text swapping inside a morphing container needs its own enter/exit timing or it overlaps.
No will-change on anything the camera scales (blurry text). Last frame must match the first frame
in position AND velocity, cursor included. Numbers on screen only from the fact bank.
</gotchas>

<start>
Ask me for the inputs, then show the state list placed on the beat grid. No code before I say go.
</start>
```
