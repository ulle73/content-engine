# Remotion in the shared studio

The model picker now offers Remotion. It routes through the existing Motion
adapter and closed `MotionSpec`; the renderer never executes assistant-generated
JavaScript or React. A prepared project opens a video workbench beside the chat
on desktop and below it on narrow screens.

The workbench lists completed videos across the conversation, identifying both
the originating plan and immutable project revision. Preview approval is enabled
only while viewing that plan's current render. Existing backend revision and
approval checks still gate final rendering. Failed previews can be retried with
a fresh idempotency key.

## Editing contract

Direct edits use `edit_motion`, an edit UUID, the expected Motion revision and
typed `MotionSceneEdit` values. Text, CTA and scene duration can change. Images,
audio, transitions, effects and the existing brand snapshot remain intact. Each
save creates an immutable revision and clears preview approval. Footage timing
and Sequence-generated projects remain editable through their existing film flow.

Timestamped comments send a normal assistant turn with `motion_source_render`.
The server checks company and conversation ownership, completed output and the
original attachments before supplying that exact rendered spec as the editing
base. The planner receives scene IDs and timestamp ranges and can propose only
the typed text/timing fields. The review displays actual scene differences before
preparation. A comment without edits or a clarifying question is blocked. Broader
animation/layout changes require further authoring features; this is not a free
form video editor.

Direct editing revisions belong to one project. A newly confirmed chat plan
creates its own project, with earlier videos retained in the conversation's
version selector. Unsaved editor values and comments survive status refreshes
within the page; server-saved plans and revisions survive page reloads.

## Verification and costs

669 Django tests passed (5 PostgreSQL-only skips on SQLite), including eight
new scene-edit/source-version/retry checks. Ruff and JavaScript syntax checks
passed. Browser acceptance used an isolated SQLite/media fixture, mocked AI
planning and real Remotion preview files. The initial preview was played through,
then text/timing edits were saved and rendered again; old-version approval was
disabled as expected. No paid Higgsfield generation was run.

Existing local rendering remains required. No always-on paid Render worker is
created. The Motion media-generation estimate is zero; AI conversation/analysis
usage is priced separately. Real provider interpretation of comments was not
part of the fixture acceptance test.

Run tests on Windows with ffmpeg available on PATH, for example the existing
`data/test-tools` directory, and `--settings=engine.test_settings`. That settings
module isolates the database and prevents loading production credentials.
