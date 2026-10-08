# Parallella kapitel – storyboard + animationsguide för underagenter

**Vad:** mönstret från musikvideon *I'm Upping My P(doom)* (JohnHeibel/PDoomVideo, se
`library/external/PDoomVideo/README.md`), med egna ord: huvudagenten skriver först två dokument –
en **storyboard** och en **animationsguide** – och låter sedan en underagent per kapitel bygga
parallellt. Varje underagent äger bara sin egen fil; huvudagenten äger delade filer, övergångar och
kritikloopen.
**När:** filmer över ~45 s, musikvideor, explainers med många scener – där en agent annars tappar
detaljnivån mot slutet.

## Prompt till huvudagenten

```text
We will build this film with parallel chapter agents.
1. Write STORYBOARD.md: the idea in one paragraph, the cast (look + role), what ties the film
   together (recurring set, palette arc, how transitions are motivated, camera rule), then one
   section per chapter: time range, palette, and shot list ("something happens in every shot").
2. Write ANIMATION_GUIDE.md for the chapter agents: how a chapter file works (one file per chapter,
   registered with its start/end time, each shot is a pure function of time that paints the whole
   frame), the canvas and safe zones, the shared drawing/motion API, the style rules, the performance
   budget per frame, and exactly how to check your work (contact sheets and strips of your own times).
   Rules: only edit your own chapter file; shared helpers are read-only – write private helpers or
   report a bug; no Math.random/timers; beats fall at [t0 + n * period].
3. Build the shared engine and one reference chapter yourself, render a sheet, fix the guide.
4. Spawn one agent per remaining chapter with: the guide, the storyboard section, its time range
   and the reference chapter. They render their own sheets and iterate until their shots read well.
5. Integrate: check every chapter boundary with a strip, run the critique loop on the whole film,
   then render and mix.
```

## Varför det fungerar

- Rena funktioner av tiden gör att kapitel kan renderas och granskas var för sig, i valfri ordning.
- Guiden är det enda delade "minnet" – därför står stil, API och kontrollsteg där, inte i chatten.
- Ägarskap per fil förhindrar att agenterna skriver över varandra.
