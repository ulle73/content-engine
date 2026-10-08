---
workflow: product-launch-video
flow: automation
storyboard: yes
message: "Din chef kan betala din golf – använd friskvårdsbidraget på Golfkuponger."
destination: instagram-feed
aspect: 1080x1080
language: sv
audience: "Anställda i Sverige som spelar golf och har (eller kan få) friskvårdsbidrag"
length: 30s
angle: hook-question
narration: no
---

## Intent

Reklam för friskvård hos Golfkuponger med kroken "Vill du att din chef ska betala din golf?".
Användaren bad: "kom på ett perfekt förslag ... reklam för friskvård, kolla experiment-site temat på shopify,
använd bilder där ifrån, använd text eller så, använd logos för friskvårdsportaler".
Godkänt manus (30 s, 1:1): Kroken → Svaret (5 000 kr/år skattefritt, arbetsgivaren bestämmer) →
Vad det täcker (greenfee, range, lektioner, simulator) → 300+ klubbar (Bro Hof Slott, Halmstad GK,
Falsterbo GK, Österåker GK) → Köp via förmånsportal (Benifex, ePassi, Söderberg & Partners, Edenred)
eller direkt → Avslut med logga + golfkuponger.se.

## Assets

- Källa: experiment-site-temat (opublicerat), förhandsvisning https://golfkuponger.se/?preview_theme_id=201846882645
- Hero: https://cdn.shopify.com/s/files/1/1030/3484/7573/files/Fridfull_golfbana_i_nordisk_skog_1.png
- Klubbbilder: https://golfkuponger.se/cdn/shop/t/5/assets/1.png (Bro Hof Slott), 2.png (Halmstad GK), 3.png (Falsterbo GK), 4.png (Österåker GK)
- Logga: https://golfkuponger.se/cdn/shop/t/5/assets/golfkuponger_logo.png
- Portallogotyper (visas på sajten): Benifex, ePassi, Söderberg & Partners, Edenred (cdn/shop/files/*_300x200*)

## Customizations

- Count-up 0 → 5 000 kr i svarsscenen.
- Musik: egen bakgrundslåt genererad lokalt med ACE-Step (host-ljud, ingen HeyGen-BGM), assets/bgm.wav.
- Ingen speakerröst (Kokoro saknar svenska) – texten bär budskapet.

## Notes

- Alla påståenden ska komma från sajten: max 5 000 kr skattefritt/år, arbetsgivaren bestämmer beloppet, 300+ klubbar, giltig 12 mån.
- Gratis prioriteras: inga betal-API:er.
- Brandtokens: Inter, mörkgrönt/vitt, guld från loggan.
