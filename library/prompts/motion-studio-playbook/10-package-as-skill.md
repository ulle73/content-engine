# Paketera som skill

**Vad:** mall för att göra ett arbetsflöde som fungerade (en film, en annonsstil, en karusellstil)
till en återanvändbar Claude Code-skill, så att nästa beställning börjar från det som redan bevisats.
**När:** efter en lyckad produktion som vi vill kunna upprepa med nytt innehåll.

## Prompt

```text
Package what we just made as a reusable Claude Code skill.
1. Look back at what actually worked (final files, the brief, the fixes from the critique loop).
   Separate what is general (method, engine, rules) from what was specific (copy, assets).
2. Create .claude/skills/<name>/ with:
   - SKILL.md (frontmatter name + a description listing the words people will use to ask for it)
   - templates/  a runnable starter with the engine and one worked example, content as variables
   - references/ the style guide, motion vocabulary, traps we hit and how we fixed them
   - scripts/    render, review, beat grid, sound – repo-relative paths, output to work/<name>/
3. In SKILL.md: when to use it, the max 3 questions to ask, the steps with approval gates, the
   render contract, the critique loop, and a "known traps" table. Style rules are DEFAULTS the
   user can override, never blockers. Facts come from the fact bank.
4. Add an entry to the right library LIBRARY.json (type "skill") and run
   python library/tools/build_catalog.py --check.
5. Prove it: start from a fresh request with different content, follow only SKILL.md, render,
   and fix the skill (not the output) wherever it was unclear.
```

## SKILL.md-skelett

```markdown
---
name: <kort-namn>
description: <Vad den gör i en mening>. Använd när någon ber om <ord 1>, <ord 2>, <ord 3> … även om de inte nämner skillen.
---

# <Namn>

Utgångsläge, inte regler: allt här kan brytas när idén blir bättre av det. Fakta från faktabanken.

## Fråga först (max 3, alltid med förslag)
1. …

## Flöde
1. Brief → 2. Stillbilder (godkänn) → 3. Bygg → 4. Kritikloop → 5. Master + format

## Motor
Renderkontrakt, filstruktur, kommandon.

## Kända fällor
| Symptom | Orsak | Fix |
|---|---|---|
```
