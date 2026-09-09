# Editorial Workspace V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Content Engine feel like a focused editorial intelligence product instead of an admin dashboard, using Django templates plus HTMX rather than a React rewrite.

**Architecture:** Keep Django server-rendered pages as the source of truth. Add HTMX 2.0.10 progressively for detail-pane interactions and partial updates, with full-page fallbacks preserved. Introduce one final workspace stylesheet loaded after the existing CSS to define the editorial visual layer without changing scraper, learning, media, or publishing behavior.

**Tech Stack:** Django 5.2, Django templates, HTMX 2.0.10, existing minimal JavaScript, CSS.

**Spec:** User-approved direction from the 2026-09-09 Ads Intelligence screenshot review: two-pane intelligence workspace, visible creative previews, clearer hierarchy, fewer generic SaaS cards, mobile full-detail behavior, keep Django and avoid React unless client-state complexity genuinely requires it.

## Global Constraints

- Keep the existing Django server-rendered architecture.
- Do not introduce React, Next.js, Tailwind, a SPA router, worker queues, or a new frontend build pipeline.
- Use HTMX only as progressive enhancement; core navigation/actions must continue to work without HTMX.
- Preserve existing backend semantics, scraper cost protections, ML logic, Postiz flow, and media behavior.
- Keep the UI in Swedish.
- Preserve the light editorial direction: off-white/white surfaces, charcoal text, subdued green accent, thin borders, minimal shadows, compact density.
- Avoid generic KPI-card grids, gradients, glass, glow, excessive pill UI, and oversized rounded cards.
- Mobile must keep the approved sticky header and bottom navigation, with touch targets at least 44 px.

---

### Task 1: HTMX foundation and editorial workspace layer

**Files:**
- Modify: `templates/base.html`
- Create: `engine/static/css/workspace-v3.css`
- Modify: `engine/test_ui.py`

**Interfaces:**
- Consumes: existing `app.css` and `responsive-v2.css`.
- Produces: HTMX available globally and a final stylesheet that can safely override screen presentation without changing backend behavior.

- [ ] **Step 1: Write failing UI tests**

Add assertions that authenticated workspace pages load HTMX 2.0.10 and `/static/css/workspace-v3.css`, and that the static stylesheet is served.

- [ ] **Step 2: Verify the tests fail**

Run `python manage.py test engine.test_ui` and confirm the new assertions fail because the assets are not loaded yet.

- [ ] **Step 3: Add HTMX and the final stylesheet**

Load the official HTMX 2.0.10 CDN build with integrity/crossorigin in `base.html`, then load `workspace-v3.css` after `responsive-v2.css`.

- [ ] **Step 4: Build the editorial design layer**

Define global page width, typography scale, spacing, section hierarchy, table/list density, selected/focus states, responsive rules, and reusable two-pane workspace classes. Preserve the current mobile shell and safe-area behavior.

- [ ] **Step 5: Run UI tests**

Run `python manage.py test engine.test_ui` and require green.

### Task 2: Meta Ads intelligence as a two-pane HTMX workspace

**Files:**
- Modify: `engine/urls.py`
- Modify: `engine/ads_views.py`
- Modify: `templates/engine/ads.html`
- Create: `templates/engine/ad_detail.html`
- Modify: `engine/test_ui.py`

**Interfaces:**
- Consumes: `CompetitorAd.creative` including `image_url`, `video_url`, copy/headline/CTA/landing-page metadata and current classification.
- Produces: `ads_views.detail(request, workspace_id, ad_id)` returning the detail partial for a company-owned active ad; the Ads list targets `#ad-detail-panel` through HTMX while retaining normal links as fallback.

- [ ] **Step 1: Write failing tests for Ads workspace behavior**

Test that the paid intelligence page contains `ads-workspace`, `ad-detail-panel`, an HTMX-enabled row targeting the detail endpoint, and a creative image when `creative.image_url` exists. Test that the detail endpoint rejects cross-company ads and renders the expected headline for the owning company.

- [ ] **Step 2: Verify the tests fail**

Run the focused tests and confirm the workspace/detail assertions fail.

- [ ] **Step 3: Add the company-scoped detail endpoint**

Create a GET-only detail view that uses `company_required`, fetches only active ads belonging to `request.workspace`, computes `analysis_current`, `observed_days`, and the Ads Library URL, and renders only `engine/ad_detail.html`.

- [ ] **Step 4: Rebuild `ads.html`**

Replace the monotone table-first layout with: concise page header; insight tabs; one actionable editorial highlight when data exists; compact theme strip; left-side creative list with real image/video thumbnails when available; sticky right-side detail panel populated from the first ad and swapped through HTMX. Keep uncertainty/performance caveats concise and visible. Move watched-advertiser administration below the intelligence workspace.

- [ ] **Step 5: Build `ad_detail.html`**

Render large creative preview, observed facts, copy/headline/CTA/landing page, current classification, explicit unknowns, and the existing create/analyze action. Never imply competitor CTR/CPA/ROAS/conversions.

- [ ] **Step 6: Add mobile behavior**

At <=820 px, make the list single-column and make selecting an ad reveal the detail block directly below/over the list as a full-width editorial detail experience. Preserve no-JS fallback links.

- [ ] **Step 7: Run focused tests**

Run `python manage.py test engine.test_ui` and require green.

### Task 3: Apply the same editorial hierarchy across all primary screens

**Files:**
- Modify: `templates/engine/home.html`
- Modify: `templates/engine/intelligence.html`
- Modify: `templates/engine/own_performance.html`
- Modify: `templates/engine/review.html`
- Modify: `templates/engine/media.html`
- Modify: `templates/engine/settings.html`
- Modify: `templates/engine/companies.html`
- Modify: `templates/registration/login.html`
- Modify: `templates/registration/setup.html`
- Modify: `engine/static/css/workspace-v3.css`
- Modify: `engine/test_ui.py`

**Interfaces:**
- Consumes: existing context variables and form actions unchanged.
- Produces: consistent screen-specific visual hierarchy with no backend contract changes.

- [ ] **Step 1: Add structural UI tests for the primary workflows**

Assert that Overview exposes a prominent recommendation/create workspace, Organic and Own Results retain insight tabs, Review exposes an editor workspace, Media exposes the library/generator, and Settings exposes its operational sections. Tests should check stable structural class names, not brittle prose.

- [ ] **Step 2: Verify the new assertions fail where structure is missing**

Run `python manage.py test engine.test_ui`.

- [ ] **Step 3: Refine Overview**

Make the main question “Vad bör jag göra idag?” visually dominant, promote creation/recommendation, keep company context secondary, and make recent work a compact editorial activity list.

- [ ] **Step 4: Refine Organic and Own Results**

Use the same intelligence vocabulary as Ads: strong list rows, meaningful visual emphasis on the most important signal/result, compact mechanism/theme strips, and details that read as editorial analysis rather than raw admin data.

- [ ] **Step 5: Refine Create/Review and Media**

Keep the copy editor the primary work surface, make media preview/action a focused side rail on desktop and sequential sections on mobile, and reduce unnecessary box nesting. Keep Postiz as the final distribution step rather than duplicating its workflow.

- [ ] **Step 6: Refine Settings, company chooser, login/setup**

Turn settings into compact grouped rows/sections, retain technical details behind disclosure controls, make company choice feel like a workspace switcher, and keep authentication surfaces visually consistent with the product.

- [ ] **Step 7: Run UI tests**

Run `python manage.py test engine.test_ui` and require green.

### Task 4: Full verification and branch completion

**Files:**
- Create temporarily if needed: `.github/workflows/ui-v3-verify.yml`
- Delete the temporary workflow before merging if it is only for the feature branch.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: verified feature branch ready to fast-forward/merge into `main`.

- [ ] **Step 1: Run Django verification**

Run `python manage.py check`, `python manage.py collectstatic --noinput`, and `python manage.py test` with the social-media-skills submodule initialized.

- [ ] **Step 2: Inspect failures and fix only real regressions**

Do not weaken existing behavioral tests simply to make the redesign pass. Preserve copy contracts where existing tests intentionally depend on them.

- [ ] **Step 3: Compare branch against main**

Review changed files for accidental backend logic changes, unnecessary dependencies, and duplicate CSS rules.

- [ ] **Step 4: Merge only after green verification**

Fast-forward or create a merge commit into `main` after the full test suite passes.
