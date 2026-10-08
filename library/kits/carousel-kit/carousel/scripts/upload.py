"""DISABLED in the content-engine import: no automatic uploads to public file hosts.

The original kit uploaded your local style-reference image (and logos / subject photos) to
catbox.moe or 0x0.st so kie.ai could read it. That sends private files to third-party public
hosts, so it was removed. Only the PAID kie.ai path ever needed it; the free path never does.

To use the paid path anyway, host the image yourself somewhere you control and pass its URL:
  * set CAROUSEL_STYLE_REFERENCE_URL=https://... in the repo-root .env (style sheet), and/or
  * put http(s) URLs directly in plan.json (`style_reference`, `logo`, `subject_image`).
public_url() passes URLs through unchanged and refuses local files.
"""
from __future__ import annotations

import carousel_config as config


class UploadDisabled(SystemExit):
    pass


def public_url(path) -> str:
    """Return `path` if it already is a public URL; refuse to upload local files."""
    s = str(path)
    if s.startswith(("http://", "https://")):
        return s
    raise UploadDisabled(
        "Automatic upload of local files to public hosts is disabled in this kit.\n"
        f"  file: {s}\n"
        "kie.ai needs a PUBLIC image URL. Host the file yourself and set "
        "CAROUSEL_STYLE_REFERENCE_URL (style sheet) in .env, or use an http(s) URL in plan.json.\n"
        "Or stay on the free path (localbg / own photos / Wikimedia photos), which never uploads."
    )


def style_reference_url() -> str:
    if config.STYLE_REFERENCE_URL:
        return config.STYLE_REFERENCE_URL
    return public_url(config.STYLE_REFERENCE)


if __name__ == "__main__":
    print(style_reference_url())
