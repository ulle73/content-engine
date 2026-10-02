# Expanded video catalog

Content Engine now exposes 15 video models through the existing Higgsfield REST
adapter. The reviewed addition is in `engine/higgsfield_video_profiles.json`;
`engine/model_catalog.py` turns those profiles into the same contracts used by
the Creative Director, Sequence Engine and studio. Page loads make no provider
catalog calls. Higgsfield's app/MCP catalog is broader and has different IDs;
its IDs must never be substituted for REST endpoints.

The new families are Kling 3.0 Standard/Pro/4K, Kling 2.6 Pro, Wan 3.0/Prime/2.7,
LTX 2.5 Fast/Pro, MiniMax H3 and Happy Horse 1.1/1.0. Each mode's exact production
endpoint, parameters and source URL were checked against the model-specific API
reference on 2026-10-03, starting at https://open.higgsfield.ai/explore. MiniMax H3
is marked preview in its documentation, labelled in the UI and excluded from
automatic routing and recommendations.

## Add a model

1. Verify the model's REST API reference, authentication, output lifecycle and
   every supported mode. App availability alone is insufficient.
2. Add its display name and mode-specific endpoint, image field names, durations,
   resolution choices, aspect ratio behavior, audio type and safe defaults to
   the JSON file. Do not infer end-frame support from a family name.
3. Add dated source links and planning rates. Use undiscounted rates; resolution
   tiers must not be priced at the cheapest tier. Wan 3.0 uses $0.05/$0.10/$0.20
   per second. Wan 2.7 uses $0.10/$0.15; Prime uses the conservative maximum
   $0.28/s across modes and resolutions. LTX planning prices are limited to the
   documented default 720p tier; higher resolutions require an account quote.
   These are hints, not account quotations.
4. Quality/speed/cost tiers are editorial ranking hints, not verified benchmarks.
   Raise them only with evidence; a preview model must remain opt-in.
5. Add contract tests with correct payloads and incompatible inputs. A new audio
   field or output lifecycle needs an adapter change before enabling the profile.

## Price and approval boundaries

The picker shows a labelled 10-second example, and the actual plan prices all
clips together. Current account availability and pricing are checked through
non-billable `/estimate/` before a paid start. Public rates never authorize
billing. The estimator accepts the existing numeric USD total, an unambiguous
USD-per-generation/second account tariff, or an exact reviewed tariff description.
Unknown ranges, changed descriptions and missing totals block paid work. Account
tariffs round upward. The server's per-clip ceiling and the studio's order-wide
budget still apply; a changed price needs a fresh user review.

The local development environment has no dedicated GK API credential. Contract,
price-boundary and approval tests therefore use fixtures/mocks. No real paid
generation is part of this verification.
