> Källa: <https://hyperframes.heygen.com/guides/product-launch-video> · HyperFrames (HeyGen), Apache-2.0 · kopierad 2026-10-07

# Create a product or website video

*Turn a product URL or launch brief into a promo, product tour, or social video.*

Give HyperFrames the real URL when the product, website, or brand should appear in the result.

Video: https://static.heygen.ai/hyperframes-oss/docs/images/showcase/product-launch-huly-v5.mp4

Built by running this workflow on a real site. The screens are captured from
huly.io, not mocked — which is the point: you give it a URL and it works from
what is actually there.

## Make the request

Give the agent the real product URL and the result you want:

```text
Using /hyperframes, make a 30-second launch video for https://example.com.
```

The agent inspects the product, proposes a direction, and confirms anything
important that the request did not settle. Add an audience, required claim, or
final action when one must be exact; you do not need to specify every scene.

## What should the video do?

- **Launch video** — turn real product evidence into a persuasive story with one clear action at the end.
- **Product tour** — show one complete task through the product's real screens, from the first action to the result.
- **Short social video** — prove one useful point quickly, show the evidence, and stop after the payoff.

A tour features the product as it exists. A launch video rearranges the same evidence into a persuasive story. A social video proves one point and ends.

If you already have approved wording, paste the script and say whether it must remain verbatim. Say **do not capture the website** when the video should use only the supplied brief.

Use a [faceless explainer](faceless-explainer.md) instead when there is no product to show and the visuals should be invented.

## What HyperFrames builds from

Real screens

The interface and product states worth showing.

Product language

Claims, features, proof, and the final action.

Brand system

Color, type, imagery, motion, and sound.

HyperFrames can animate captured product material or rebuild only the part that needs to move. A raw screen recording is not the default.

## Review the result

- Every product claim is current.
- The shown states are realistic and use no private material.
- The important interface remains readable while the video plays.
- The opening proves the product quickly and the ending asks for one clear action.

Ask the agent for a broader story revision. Use Studio for a direct visual or
timing change. Render from the agent, Studio, or the CLI when the result is ready.

- [Finish and share](export-and-share.md) — Check the final project, render it from your preferred surface, and review the file.

## Related topics

- [Create a faceless explainer when there is no product to show](faceless-explainer.md)
- [Edit the finished project in Studio](https://hyperframes.heygen.com/studio)
- [Prompt for product-launch videos](../prompting/product-launch.md)
