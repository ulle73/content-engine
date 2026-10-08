> Källa: <https://hyperframes.heygen.com/guides/pr-to-video> · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07

# Turn a pull request into a video

*Show what changed, why it matters, and what happens next.*

Give HyperFrames a pull request. It reads the diff, commits, files, and contributors—there is no website capture.

Video: https://static.heygen.ai/hyperframes-oss/docs/images/showcase/full-prvideo.mp4

*A real pull request becomes a 32-second explanation with code, before-and-after behavior, and sound.*

## Make the request

Send the pull request and name the audience:

```text
Using /hyperframes, explain https://github.com/owner/repo/pull/123 to product
and engineering teammates.
```

The agent reads the actual pull request, proposes the angle, and confirms its
release state before presenting a proposed change as shipped behavior.

## Who needs to understand it?

- **Users** — lead with the visible change, show the before and after, and name any action they must take.
- **Contributors** — explain the architecture change, important tradeoff, and code path reviewers need to understand.
- **Social audience** — make one clear feature reveal with visible proof and only the implementation detail that explains it.

The same pull request needs a different story for users, contributors, or a social audience.

## Before it builds

Confirm:

- the intended pull request and audience;
- whether the angle is a changelog, feature reveal, fix, or refactor;
- whether the change is proposed, merged, or released;
- the visible before and after;
- any breaking change or migration step.

The video should explain the change, not read the pull request description aloud.

## Verify the proof

- The pull request and target branch are correct.
- Proposed, merged, and released are not confused.
- User-facing claims match the actual behavior.
- Code excerpts show only the relevant lines and remain readable.
- Tests and refactoring are not presented as product features.
- Contributor names and release details are accurate.

Ask the agent when the explanation or evidence must change. Use
Studio for a precise timing, code-framing, or
caption correction.

- [Finish and share](export-and-share.md) — Check the final project, render through your preferred surface, and review the file.

## Related topics

- [Prompt for code changes and pull requests](../prompting/code-and-prs.md)
- [Create a custom video from several sources](general-video.md)
