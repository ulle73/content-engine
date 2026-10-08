# Referensprompt – ta grammatiken, inte innehållet

**Vad:** gör en referensvideo man gillar till en stilguide och en klipplista som en ny film kan
byggas mot. Rytm, övergångar, kamera, typografibeteende och täthet lånas – logotyper, text,
karaktärer, musik och bilder lånas aldrig.
**När:** "gör en sån här fast för oss".

## Steg 1 – extrahera bildrutor (lokalt, gratis)

```bash
python library/prompts/motion-studio-playbook/review.py frames ref.mp4 --every 0.5 --out work/prompts/ref/frames
python library/prompts/motion-studio-playbook/review.py sheet ref.mp4 --every 0.5 --cols 6 --out work/prompts/ref/sheet.jpg
ffmpeg -i ref.mp4 -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep pts_time   # klippunkter
```

## Steg 2 – prompt

```text
Here are frames of a reference video, one every 0.5 s (contact sheet + folder), and its cut times.
Write two files. Describe the GRAMMAR, never copy the CONTENT (no logos, words, characters, music).

style_guide.md
- Palette logic (how many colours, what the accent is allowed to do), contrast, texture/grain.
- Type behaviour: classes and treatments (e.g. "condensed heavy grotesque, masked word-by-word"),
  sizes relative to frame height, how long text holds.
- Motion vocabulary: easing character (snappy/soft/springy), typical speeds, overshoot, stagger.
- Transitions: list each type used and how often; what carries across cuts (shape, line, word, colour).
- Camera: locked / push / orbit / whip; zoom behaviour.
- Rhythm: average and min/max shot length, events per second, where the peaks are.
- The ONE signature device that makes it recognisable.

shotlist.md – a table: # | start–end | what happens | transition in | transition out | text on screen (placeholder) | energy 1–5

Then propose how the same grammar carries OUR content: [brief / Golfkuponger message], as a new
shot list with the same timings. Ask before you write any code.
```

## Tips

- Samma struktur som stilarksprompten för stillbilder: `library/prompts/downloaded/style-master-sheet.md`.
- Spara `style_guide.md` + `shotlist.md` i `work/prompts/<projekt>/` och peka på dem i `05-xml-spec.md`.
