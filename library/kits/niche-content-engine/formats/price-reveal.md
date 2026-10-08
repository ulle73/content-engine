# Format: Price reveal

Ur `niche-content-engine` (`.claude/skills/niche-content-engine/references/formats.md`). Exemplen gäller en takläggare —
byt till din bransch (t.ex. golf/friskvård).

| | |
|---|---|
| Hook (första 3 s) | "Here's what a {service} actually costs in {city} right now." |
| Kropp | what drives the price, range (only the user's real numbers), what's a rip-off |
| Ord | 100–140 (≈ 35–60 s talat) |
| Bäst för | leads — highest intent |

## Prompt

```
Använd /niche-content-engine. Nisch: <bransch, stad>. Målgrupp: <vem>.
Skriv 1–3 manus i formatet "Price reveal" (hook: "Here's what a {service} actually costs in {city} right now.").
Följ references/script-rules.md: hook ≤ 12 ord på 3 s, 90–160 ord, en riktig fackdetalj,
inga påhittade siffror/recensioner, inga hakparenteser, CTA med unikt kommentarsord kopplat till en riktig leverans.
Skriv manusen på svenska. Leverera enligt references/output-template.md (on-screen text, B-roll, caption).
```

Blandningsregel per batch om 5: minst 2 lead-format (price reveal, signs you need it, red flags, timely),
minst 1 förtroende/story-format, högst 1 nyhet, inget format mer än två gånger.
