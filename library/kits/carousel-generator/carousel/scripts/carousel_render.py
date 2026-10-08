"""Render each slide: overlay the text/graphics template on the AI background -> PNG.

Uses headless Chromium (Playwright) to render template.html at exactly
CANVAS_W x CANVAS_H (default 1080x1350, Instagram 4:5), once per slide, with that
slide's copy substituted and its background embedded as a data URI.

One-time setup:
    pip install playwright
    playwright install chromium

Usage: python carousel_render.py <run_dir>
"""
import base64
import json
import sys
from pathlib import Path

import carousel_config as cfg


_MIME = {".png": "image/png", ".svg": "image/svg+xml", ".webp": "image/webp", ".gif": "image/gif"}


def _data_uri(path: Path) -> str:
    mime = _MIME.get(path.suffix.lower(), "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def _asset_uri(path) -> str:
    """Data URI for an optional asset path (absolute, or relative to carousel/ or work/<kit>/)."""
    if not path:
        return ""
    p = cfg.resolve(path)
    return _data_uri(p) if p and p.exists() else ""


def _esc(x) -> str:
    return (x or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _notes(content) -> str:
    notes = content.get("note") or []
    if isinstance(notes, str):
        notes = [notes]
    if not notes:
        return ""
    return "".join(f'<div class="cnote">{_esc(n)}</div>' for n in notes)


def build_content(content) -> str:
    """Turn a slide's `content` spec into on-brand HTML (charts/stats/dial/chips)."""
    if not content:
        return ""
    t = content.get("type")

    # SVG chart types (line / column / meter / dumbbell) live in carousel_charts.py
    import carousel_charts as charts
    if t in charts.RENDERERS:
        return charts.RENDERERS[t](content)

    if t == "bars":
        items = content["items"]
        mx = max((i["value"] for i in items), default=1) * 1.12 or 1
        unit = content.get("unit", "")
        rows = ""
        for i in items:
            hi = " hi" if i.get("highlight") else ""
            w = max(3, round(i["value"] / mx * 100))
            val = f'{i["value"]:,g}{unit}'   # thousands-comma'd, per the house number spec
            rows += (f'<div class="bar-row"><div class="bar-lab">{_esc(i["label"])}</div>'
                     f'<div class="bar-track"><div class="bar-fill{hi}" style="width:{w}%"></div></div>'
                     f'<div class="bar-val{hi}">{_esc(val)}</div></div>')
        title = f'<div class="ctitle">{_esc(content["title"])}</div>' if content.get("title") else ""
        return f'<div class="card">{title}<div class="bars">{rows}</div>{_notes(content)}</div>'

    if t == "stats":
        import carousel_charts as charts
        tiles = "".join(
            f'<div class="stat"><div class="v">{_esc(str(i["value"]))}</div>'
            f'<div class="l">{_esc(i["label"])}</div>'
            f'{charts.sparkline(i.get("spark"))}'
            f'{f"""<div class="d">{_esc(i["delta"])}</div>""" if i.get("delta") else ""}'
            f'</div>' for i in content["items"])
        title = f'<div class="ctitle">{_esc(content["title"])}</div>' if content.get("title") else ""
        return f'<div class="card">{title}<div class="stats">{tiles}</div>{_notes(content)}</div>'

    if t == "dial":
        on = set(content.get("on", []))
        segs = "".join(
            f'<div class="seg{" on" if idx in on else ""}">{_esc(s)}</div>'
            for idx, s in enumerate(content["segments"]))
        cap = ""
        if content.get("left") or content.get("right"):
            cap = (f'<div class="dial-cap"><span>{_esc(content.get("left",""))}</span>'
                   f'<span>{_esc(content.get("right",""))}</span></div>')
        title = f'<div class="ctitle">{_esc(content["title"])}</div>' if content.get("title") else ""
        return f'<div class="card">{title}<div class="dial">{segs}</div>{cap}{_notes(content)}</div>'

    if t == "chips":
        chips = "".join(f'<span class="chip">{_esc(c)}</span>' for c in content["items"])
        return f'<div class="chips">{chips}</div>'

    if t == "image":
        import carousel_config as cfg
        src = content.get("src")
        p = cfg.resolve(src) if src else None
        uri = _data_uri(p) if p and p.exists() else ""
        cap = ""
        if content.get("caption") or content.get("source"):
            t_ = f'<span class="t">{_esc(content.get("caption",""))}</span>' if content.get("caption") else "<span></span>"
            s_ = f'<span class="s">{_esc(content.get("source",""))}</span>' if content.get("source") else ""
            cap = f'<div class="cap">{t_}{s_}</div>'
        return f'<figure class="shot"><img src="{uri}" alt="">{cap}</figure>'

    if t == "hero":
        # transparent illustration floating on the background, big + centered
        import carousel_config as cfg
        src = content.get("src")
        p = cfg.resolve(src) if src else None
        uri = _data_uri(p) if p and p.exists() else ""
        cap = f'<div class="hcap">{_esc(content["caption"])}</div>' if content.get("caption") else ""
        return f'<div class="heroimg"><img src="{uri}" alt="">{cap}</div>'

    return ""


def _slide_html(template: str, slide: dict, plan: dict) -> str:
    bg = slide.get("bg_file")
    bg_uri = _asset_uri(bg) if bg else ""
    repl = {
        "__BG__": bg_uri,
        "__STAGECLASS__": "hero" if slide.get("layout") == "hero" else "",
        "__TOPIC_TAG__": _esc(slide.get("topic_tag", "")),
        "__BRAND_LABEL__": _esc(plan.get("brand_label", "")),
        "__HEADLINE__": _esc(slide.get("headline", "")),
        "__HERO_WORD__": _esc(slide.get("hero_word", "")),
        # the quote may carry <br> line breaks; everything else stays escaped
        "__SUBTITLE__": _esc(slide.get("subtitle", "")).replace("&lt;br&gt;", "<br>"),
        "__HANDLE__": _esc(slide.get("handle") or plan.get("handle", cfg.DEFAULT_HANDLE)),
        "__INDEX__": str(slide["index"]),
        "__TOTAL__": str(len(plan["slides"])),
        # celestial template: flora layer, sticker glyph, badge
        "__FLORA__": _asset_uri(slide.get("flora")),
        "__QUOTETOP__": str(slide.get("quote_top", 300)),
        "__HEADTOP__": str(slide.get("head_top", 690)),
        "__CONTENTBOTTOM__": str(slide.get("content_bottom", 110)),
        "__GLYPH__": _esc(slide.get("glyph", "")),
        "__GX__": str(slide.get("glyph_x", 880)),
        "__GY__": str(slide.get("glyph_y", 250)),
        "__BADGE1__": _esc(slide.get("badge1", "")),
        "__BADGE2__": _esc(slide.get("badge2", "")),
        "__BADGE3__": _esc(slide.get("badge3", "")),
        "__BADGEX__": str(slide.get("badge_x", 96)),
        "__BADGEY__": str(slide.get("badge_y", 250)),
        # archival template: the three metadata pairs + headline geometry
        "__META1__": _esc(slide.get("meta1", plan.get("meta1", ""))),
        "__META2__": _esc(slide.get("meta2", plan.get("meta2", ""))),
        "__META3__": _esc(slide.get("meta3", plan.get("meta3", ""))),
        "__SEAM__": str(slide.get("seam", 560)),
        "__HEAD_OVERFLOW__": str(slide.get("head_overflow", 1.12)),
        "__HEAD_CROSS__": str(slide.get("head_cross", 0.30)),
        # midnight template: bottom call-to-action + the 3-part footer
        "__CTA_PILL__": _esc(slide.get("cta_pill", "")),
        "__CTA_SOFT__": _esc(slide.get("cta_soft", "")),
        "__MICROCOPY__": _esc(slide.get("microcopy", "")),
        "__TAGLINE__": _esc(slide.get("tagline", plan.get("tagline", ""))),
        # extra fields used by alternate templates (e.g. 90s film)
        "__KICKER__": _esc(slide.get("kicker", "")),
        "__HERO_PHRASE__": _esc(slide.get("hero_phrase", "")),
        "__TIMESTAMP__": _esc(slide.get("timestamp", plan.get("timestamp", ""))),
        "__FILMTAG__": _esc(slide.get("filmtag", plan.get("filmtag", ""))),
        "__CAPTION__": _esc(slide.get("caption", "")),
    }
    html = template
    for k, v in repl.items():
        html = html.replace(k, v)
    # raw-HTML injections (not escaped): main content + optional corner mascot
    html = html.replace("__CONTENT__", build_content(slide.get("content")))
    html = html.replace("__MASCOT__", _mascot(slide.get("mascot")))
    return html


def _mascot(m) -> str:
    """Optional decorative mascot overlay: {src, pos: right|br|bl, h: px}."""
    if not m:
        return ""
    import carousel_config as cfg
    src = m.get("src")
    p = cfg.resolve(src) if src else None
    uri = _data_uri(p) if p and p.exists() else ""
    if not uri:
        return ""
    pos = m.get("pos", "br")
    h = int(m.get("h", 300))
    return f'<img class="mascot {pos}" style="height:{h}px" src="{uri}" alt="">'


def render(run_dir):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Playwright is required to render slides.\n"
            "  pip install playwright && playwright install chromium"
        )

    run_dir = Path(run_dir)
    plan_path = run_dir / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    out_dir = run_dir / "slides"
    out_dir.mkdir(parents=True, exist_ok=True)
    tpl_name = plan.get("template")
    tpl_path = (Path(__file__).resolve().parent / tpl_name) if tpl_name else cfg.TEMPLATE
    template = tpl_path.read_text(encoding="utf-8")

    # charts follow the plan's style: "midnight" (default) or "archival"
    import carousel_charts
    carousel_charts.use_theme(plan.get("theme")
                             or ("archival" if "archival" in (tpl_name or "") else "midnight"))

    slides = plan["slides"]
    with sync_playwright() as p:
        browser = cfg.launch_browser(p)
        page = browser.new_page(
            viewport={"width": cfg.CANVAS_W, "height": cfg.CANVAS_H},
            device_scale_factor=cfg.RENDER_SCALE,
        )
        for slide in slides:
            idx = slide["index"]
            html = _slide_html(template, slide, plan)
            page.set_content(html, wait_until="networkidle")
            page.evaluate("() => document.fonts.ready.then(() => true)")  # webfonts loaded
            page.wait_for_timeout(220)  # let fonts settle
            # ensure the frame is composited before the screenshot
            page.evaluate("() => new Promise(r => requestAnimationFrame("
                          "() => requestAnimationFrame(r)))")
            out = out_dir / f"slide{idx:02d}.png"
            page.screenshot(path=str(out), clip={
                "x": 0, "y": 0, "width": cfg.CANVAS_W, "height": cfg.CANVAS_H})
            slide["out_file"] = str(out)
            print(f"[slide {idx}] rendered -> {out}")
        browser.close()

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"\nRendered {len(slides)} slide(s) -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python carousel_render.py <run_dir>")
        raise SystemExit(1)
    render(sys.argv[1])
