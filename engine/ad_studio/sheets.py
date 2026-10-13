"""Images the assistant shows in chat so decisions are visual, not abstract.

- picker_sheet:  numbered candidates ("ta 2 och 5")
- storyboard:    the agreed ad, scene by scene, before anything is rendered
- review_sheet:  keyframes of a rendered preview with safe-zone guides for QA

Everything is drawn locally with Pillow. No provider calls, no cost.
"""

from __future__ import annotations

import io
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont, ImageOps

from engine.media_storage import open_asset
from engine.motion.brand import PRESETS

FONT_DIR = Path(__file__).resolve().parent / "fonts"

# 9:16 safe zones (fractions of height/width) used by brand skill and review.
SAFE_TOP = 0.14
SAFE_BOTTOM = 0.35
SAFE_LEFT = 0.06
SAFE_RIGHT = 0.14


def _font(size: int, bold: bool = False):
    name = "Inter-Bold.ttf" if bold else "Inter-Regular.ttf"
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default(size=size)


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def brand_colors(preset: str = "golfkuponger", company=None) -> dict:
    from engine.motion.brand import brand_id_for, tokens_for

    if company is not None and preset == brand_id_for(company):
        tokens = tokens_for(company)
    else:
        tokens = PRESETS.get(preset, PRESETS["workspace"])
    return {k: _hex(v) for k, v in tokens.items() if isinstance(v, str) and v.startswith("#")}


def _video_frame(file, at_fraction: float = 0.35) -> Image.Image:
    with av.open(file) as container:
        stream = container.streams.video[0]
        frames = stream.frames or 0
        target = int(frames * at_fraction) if frames else 0
        last = None
        for index, frame in enumerate(container.decode(video=0)):
            last = frame
            if index >= target:
                break
        if last is None:
            raise ValueError("Videon saknar läsbara bilder.")
        return last.to_image().convert("RGB")


def load_asset_image(asset, max_side: int = 900) -> Image.Image:
    with open_asset(asset) as file:
        if asset.kind == "video":
            image = _video_frame(file)
        else:
            image = Image.open(io.BytesIO(file.read()))
            image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((max_side, max_side))
    return image


def _placeholder(size, label: str) -> Image.Image:
    colors = brand_colors()
    image = Image.new("RGB", size, colors["background"])
    draw = ImageDraw.Draw(image)
    draw.text((size[0] // 2, size[1] // 2), label, font=_font(22), fill=colors["muted"], anchor="mm")
    return image


def _cover(image: Image.Image, size) -> Image.Image:
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)


def _wrap(draw, text: str, font, width: int) -> list[str]:
    lines = []
    for paragraph in text.replace(" / ", "\n").split("\n"):
        words, current = paragraph.split(), ""
        for word in words:
            trial = f"{current} {word}".strip()
            if draw.textlength(trial, font=font) <= width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def _dashed_hline(draw, y, x0, x1, fill, dash=10):
    for x in range(x0, x1, dash * 2):
        draw.line([(x, y), (min(x + dash, x1), y)], fill=fill, width=2)


def _safe_guides(draw, box, color=(255, 196, 0)):
    x0, y0, x1, y1 = box
    h, w = y1 - y0, x1 - x0
    _dashed_hline(draw, y0 + int(h * SAFE_TOP), x0, x1, color)
    _dashed_hline(draw, y1 - int(h * SAFE_BOTTOM), x0, x1, color)
    xl, xr = x0 + int(w * SAFE_LEFT), x1 - int(w * SAFE_RIGHT)
    for y in range(y0, y1, 20):
        draw.line([(xl, y), (xl, min(y + 10, y1))], fill=color, width=2)
        draw.line([(xr, y), (xr, min(y + 10, y1))], fill=color, width=2)


def _to_jpeg(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, "JPEG", quality=85, optimize=True)
    return out.getvalue()


# ---- reference video ------------------------------------------------------

def reference_video_sheet(asset, frames: int = 6) -> bytes:
    """Evenly sample a company-owned reference video into one local JPEG sheet."""
    if getattr(asset, "kind", "") != "video":
        raise ValueError("Referensen måste vara en video.")
    if type(frames) is not int or not 3 <= frames <= 12:
        raise ValueError("Välj 3–12 referensbilder.")

    samples: list[tuple[Image.Image, float]] = []
    try:
        with open_asset(asset) as file:
            with av.open(file) as container:
                stream = next(iter(container.streams.video), None)
                if stream is None:
                    raise ValueError("Videon saknar ett läsbart videospår.")
                duration = float(getattr(asset, "duration_seconds", 0) or 0)
                if duration <= 0 and stream.duration is not None and stream.time_base is not None:
                    duration = float(stream.duration * stream.time_base)
                if duration <= 0 and stream.frames and stream.average_rate:
                    duration = float(stream.frames / stream.average_rate)
                end = max(0.001, duration * 0.98) if duration > 0 else 0
                targets = [end * i / (frames - 1) for i in range(frames)] if end else []
                target_index = 0
                last: tuple[Image.Image, float] | None = None
                for index, frame in enumerate(container.decode(video=0)):
                    timestamp = (
                        float(frame.time)
                        if frame.time is not None
                        else index / float(stream.average_rate or 30)
                    )
                    image = frame.to_image().convert("RGB")
                    last = (image, timestamp)
                    if targets:
                        while target_index < len(targets) and timestamp >= targets[target_index]:
                            samples.append((image.copy(), timestamp))
                            target_index += 1
                    elif len(samples) < frames:
                        samples.append((image.copy(), timestamp))
                    if targets and target_index >= len(targets):
                        break
                if last is None:
                    raise ValueError("Videon saknar läsbara bilder.")
                while len(samples) < frames:
                    samples.append((last[0].copy(), last[1]))
    except ValueError:
        raise
    except (av.error.FFmpegError, OSError) as exc:
        raise ValueError("Referensvideon kunde inte läsas.") from exc

    colors = brand_colors()
    cols = min(3, frames)
    rows = (frames + cols - 1) // cols
    pad, tile_w, tile_h, caption_h, header_h = 16, 320, 180, 30, 58
    sheet = Image.new(
        "RGB",
        (pad + cols * (tile_w + pad), header_h + rows * (tile_h + caption_h + pad)),
        colors["paper"],
    )
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 15), "Referensvideo · kreativa mekaniker", font=_font(24, bold=True), fill=colors["ink"])
    for index, (image, timestamp) in enumerate(samples[:frames]):
        row, col = divmod(index, cols)
        x = pad + col * (tile_w + pad)
        y = header_h + row * (tile_h + caption_h + pad)
        sheet.paste(_cover(image, (tile_w, tile_h)), (x, y))
        draw.rounded_rectangle([x + 8, y + 8, x + 80, y + 38], 8, fill=colors["ink"])
        draw.text(
            (x + 44, y + 23),
            f"{timestamp:.1f} s",
            font=_font(15, bold=True),
            fill=colors["foreground"],
            anchor="mm",
        )
        draw.text((x, y + tile_h + 6), f"Bild {index + 1}", font=_font(15, bold=True), fill=colors["ink"])
    return _to_jpeg(sheet)


# ---- picker ---------------------------------------------------------------

def picker_sheet(items: list[tuple[object, str]], title: str = "") -> bytes:
    """items: [(asset_or_None, caption)]. Tiles are numbered 1..n in order."""
    colors = brand_colors()
    cols = 4 if len(items) > 4 else max(1, len(items))
    tile_w, tile_h, cap_h, pad = 240, 427, 54, 16  # 9:16, same shape as the ad
    rows = (len(items) + cols - 1) // cols
    header = 56 if title else pad
    sheet = Image.new("RGB", (pad + cols * (tile_w + pad), header + rows * (tile_h + cap_h + pad)), colors["paper"])
    draw = ImageDraw.Draw(sheet)
    if title:
        draw.text((pad, 16), title[:90], font=_font(26, bold=True), fill=colors["ink"])
    for index, (asset, caption) in enumerate(items):
        r, c = divmod(index, cols)
        x, y = pad + c * (tile_w + pad), header + r * (tile_h + cap_h + pad)
        try:
            image = _cover(load_asset_image(asset), (tile_w, tile_h)) if asset is not None else None
        except Exception:
            image = None
        sheet.paste(image or _placeholder((tile_w, tile_h), "Kan inte visas"), (x, y))
        draw.ellipse([x + 10, y + 10, x + 62, y + 62], fill=colors["background"], outline=colors["foreground"], width=3)
        draw.text((x + 36, y + 36), str(index + 1), font=_font(28, bold=True), fill=colors["foreground"], anchor="mm")
        if asset is not None and getattr(asset, "kind", "") == "video":
            draw.rounded_rectangle([x + tile_w - 78, y + 12, x + tile_w - 10, y + 42], 8, fill=colors["ink"])
            draw.text((x + tile_w - 44, y + 27), "VIDEO", font=_font(16, bold=True), fill=colors["foreground"], anchor="mm")
        for i, line in enumerate(_wrap(draw, caption, _font(17), tile_w)[:2]):
            draw.text((x, y + tile_h + 6 + i * 22), line, font=_font(17), fill=colors["ink"])
    return _to_jpeg(sheet)


# ---- storyboard -----------------------------------------------------------

PANEL_W, PANEL_H = 270, 480


def _fit_text(draw, text: str, width: int, start: int = 26, minimum: int = 15):
    """Largest bold size where every line fits inside the safe width. Returns (font, lines, fits)."""
    for size in range(start, minimum - 1, -1):
        font = _font(size, bold=True)
        lines = _wrap(draw, text, font, width)
        if all(draw.textlength(line, font=font) <= width for line in lines):
            return font, lines, True
    return font, lines, False


def _panel(scene, image: Image.Image | None, colors, warnings: list[str]) -> Image.Image:
    if scene.purpose == "cta" and image is None:
        panel = Image.new("RGB", (PANEL_W, PANEL_H), colors["background"])
    else:
        panel = _cover(image, (PANEL_W, PANEL_H)) if image else _placeholder((PANEL_W, PANEL_H), "Ingen bild vald")
        shade = Image.new("RGB", panel.size, (0, 0, 0))
        panel = Image.blend(panel, shade, 0.28)
    draw = ImageDraw.Draw(panel)
    text = scene.on_screen_text
    if text:
        inner = int(PANEL_W * (1 - SAFE_RIGHT)) - 24
        font, lines, fits = _fit_text(draw, text, inner)
        if not fits:
            warnings.append(f"Scen '{scene.id}': ett ord är för långt för safe zone. Korta texten eller dela ordet.")
        line_h = int(font.size * 1.25)
        top = int(PANEL_H * 0.42) - len(lines) * line_h // 2
        for i, line in enumerate(lines):
            draw.text((18, top + i * line_h), line, font=font, fill=colors["foreground"])
    _safe_guides(draw, (0, 0, PANEL_W, PANEL_H))
    return panel


def storyboard(brief, assets_by_id: dict, problems: list[str], company=None) -> bytes:
    colors = brand_colors(brief.brand_preset, company=company)
    scenes = brief.scenes
    pad, info_h = 16, 120
    header_h = 120
    width = pad + max(1, len(scenes)) * (PANEL_W + pad)
    footer_h = 30 + 24 * 6
    sheet = Image.new("RGB", (max(width, 900), header_h + PANEL_H + info_h + footer_h), colors["paper"])
    draw = ImageDraw.Draw(sheet)

    engine = brief.engine.engine if brief.engine else "motor ej vald"
    template = brief.engine.remotion_template_id if brief.engine and brief.engine.remotion_template_id else ""
    total = sum(s.duration_s for s in scenes)
    draw.text((pad, 14), (brief.angle.title if brief.angle else brief.message or "Storyboard")[:70],
              font=_font(30, bold=True), fill=colors["ink"])
    draw.text((pad, 56), (brief.message or "")[:110], font=_font(18), fill=colors["ink"])
    draw.text((pad, 84), f"{engine} {template}  ·  {total:g} s  ·  {', '.join(brief.formats)}  ·  "
              f"rubrik: {brief.copy_.headline or '—'}"[:120], font=_font(16), fill=colors["accent"])

    warnings: list[str] = []
    t = 0.0
    for i, scene in enumerate(scenes):
        x, y = pad + i * (PANEL_W + pad), header_h
        image = None
        asset = assets_by_id.get(scene.asset_id) if scene.asset_id else None
        if asset is not None:
            try:
                image = load_asset_image(asset)
            except Exception:
                image = None
        sheet.paste(_panel(scene, image, colors, warnings), (x, y))
        iy = y + PANEL_H + 8
        draw.text((x, iy), f"{i + 1}. {scene.id.upper()} · {scene.purpose}", font=_font(17, bold=True), fill=colors["ink"])
        draw.text((x, iy + 24), f"{t:g}–{t + scene.duration_s:g} s · {scene.transition_in}", font=_font(15), fill=colors["accent"])
        for j, line in enumerate(_wrap(draw, scene.motion or scene.voiceover, _font(14), PANEL_W)[:3]):
            draw.text((x, iy + 46 + j * 18), line, font=_font(14), fill=colors["ink"])
        t += scene.duration_s

    fy = header_h + PANEL_H + info_h
    problems = [*problems, *warnings]
    if problems:
        draw.text((pad, fy), "Måste åtgärdas före låsning:", font=_font(17, bold=True), fill=(170, 30, 30))
        for i, problem in enumerate(problems[:6]):
            draw.text((pad, fy + 26 + i * 24), "• " + problem[:130], font=_font(15), fill=(170, 30, 30))
    else:
        draw.text((pad, fy + 6), "Skiss. Exakt utseende syns i preview-renderingen. Gula linjer = safe zones för Reels/Stories. Inga regelbrott.",
                  font=_font(15), fill=colors["accent"])
    used = fy + (30 + 24 * min(len(problems), 6) if problems else 40)
    return _to_jpeg(sheet.crop((0, 0, sheet.width, used)))


# ---- render review --------------------------------------------------------

def review_sheet(keyframes: list[tuple[str, int, object]], fps: int, title: str) -> bytes:
    """keyframes: [(scene_id, frame, asset)] from MotionRender.storyboard."""
    colors = brand_colors()
    pad, cap = 16, 40
    w, h = 270, 480
    sheet = Image.new("RGB", (pad + max(1, len(keyframes)) * (w + pad), 60 + h + cap + pad), colors["ink"])
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 16), title[:90], font=_font(24, bold=True), fill=colors["foreground"])
    for i, (scene_id, frame, asset) in enumerate(keyframes):
        x = pad + i * (w + pad)
        try:
            image = _cover(load_asset_image(asset), (w, h))
        except Exception:
            image = _placeholder((w, h), "Saknas")
        tile_draw = ImageDraw.Draw(image)
        _safe_guides(tile_draw, (0, 0, w, h))
        sheet.paste(image, (x, 60))
        draw.text((x, 60 + h + 8), f"{i + 1}. {scene_id} · {frame / fps:.1f} s", font=_font(16, bold=True),
                  fill=colors["foreground"])
    return _to_jpeg(sheet)
