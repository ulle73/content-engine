"""Turns the dashboard form into the template's conversation.json and estimates the film's length.

The timing functions are ports of library/templates/imessage-samtal/build.mjs (readTime, typingTime, schedule,
intro, outro) so the dashboard can show and limit the length before anything is rendered. build.mjs stays the
authority: the worker runs it and reports the real length back.
"""

import math
import re
import uuid

from ..media import describe_file, store_asset
from ..media_storage import MediaError

MAX_MESSAGES = 30
MAX_TEXT = 400
MAX_SECONDS = 180
MAX_UPLOADS = 20
OUTRO_LEN = 3.1
GLASSES_SRC = "assets/thug-glasogon.png"
CLOCK_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")
CONTROL_RE = re.compile(r"[\u0000-\u0008\u000b-\u001f\u007f]")


class SmsFilmError(ValueError):
    pass


# --- timing (ports of build.mjs) ------------------------------------------------------------------------------

def _chars(s):
    return len(s) if isinstance(s, str) else 0


def read_time(m):
    n = _chars(m.get("text"))
    text = max(5 / 6, n / 12) + 0.9 if n else 0
    if m.get("image"):
        return text + 0.8 if n else 1.5
    return text


def typing_time(m, speed=1):
    n = _chars(m.get("text"))
    base = min(2.4, max(0.6, n * 0.065)) if m.get("side") == "sent" else min(2.6, max(1.1, 0.8 + n * 0.04))
    return base / speed


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def schedule(conv):
    """Start time per message and total length (with outro), like build.mjs. Returns (starts, total)."""
    msgs = conv.get("messages") or []
    if not 1 <= len(msgs) <= 100:
        raise SmsFilmError("Lägg till minst ett meddelande.")
    first = 0.6
    intro = conv.get("intro") or {}
    if intro.get("lockscreen"):
        notify = 0.5
        need = notify + read_time(msgs[0]) + 0.3
        first = round(max(3, need) - 0.3, 2)
    speed = conv["typingSpeed"] if _num(conv.get("typingSpeed")) and conv["typingSpeed"] > 0 else 1
    sent_speed = conv["sentTypingSpeed"] if _num(conv.get("sentTypingSpeed")) and conv["sentTypingSpeed"] > 0 else None
    starts, ends, prev, prev_start = [], [], None, 0.0
    for i, m in enumerate(msgs):
        no_typing = m.get("typing") is False or (i == 0 and intro.get("lockscreen"))
        typing = 0 if no_typing else typing_time(m, sent_speed if m.get("side") == "sent" and sent_speed else speed)
        if prev is None:
            start = max(first, typing)
        else:
            start = max(prev_start + read_time(prev), prev_start + 0.4 + typing)
        start = math.ceil(start * 100 - 1e-6) / 100
        ov = m.get("overlay")
        if ov and m.get("image"):
            at = start + (ov.get("after") if _num(ov.get("after")) else 1)
            ends.append(at + (ov.get("duration") or 1.6) + (ov.get("hold") if _num(ov.get("hold")) else 2.5))
        starts.append(start)
        prev, prev_start = m, start
    hold = conv["endHold"] if _num(conv.get("endHold")) else 0
    min_end = max([prev_start + max(read_time(prev), 2.2, hold) + 0.4, *ends])
    duration = math.ceil(min_end * 2) / 2
    total = round(duration + (OUTRO_LEN if conv.get("outro") == "spotlight" else 0), 2)
    return starts, total


# --- form → conversation --------------------------------------------------------------------------------------

def _text(value, label, limit, *, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise SmsFilmError(f"{label}: ogiltigt värde.")
    value = CONTROL_RE.sub("", value.replace("\r\n", "\n")).strip()
    if required and not value:
        raise SmsFilmError(f"{label}: fyll i texten.")
    if len(value) > limit:
        raise SmsFilmError(f"{label}: högst {limit} tecken.")
    return value


def _fraction(value, default, lo, hi):
    return min(hi, max(lo, float(value))) if _num(value) else default


def _extension(asset):
    return asset.storage_key.rsplit(".", 1)[-1].lower()


class _Images:
    """Resolves {"file": "f3"} (a new upload) or {"asset": "<uuid>"} (an earlier upload) to a template path."""

    def __init__(self, company, files):
        self.company, self.files, self.ids, self._stored = company, files or {}, [], {}

    def path(self, ref, label):
        if not ref:
            return None
        if not isinstance(ref, dict):
            raise SmsFilmError(f"{label}: ogiltig bild.")
        if ref.get("file"):
            key = str(ref["file"])
            if key not in self._stored:
                upload = self.files.get(key)
                if upload is None:
                    raise SmsFilmError(f"{label}: bilden kom inte med. Välj den igen.")
                if len(self._stored) >= MAX_UPLOADS:
                    raise SmsFilmError(f"Högst {MAX_UPLOADS} bilder per film.")
                data = upload.read()
                try:
                    if describe_file(data)["kind"] != "image":
                        raise SmsFilmError(f"{label}: välj en bild (JPEG, PNG eller WebP).")
                    self._stored[key] = store_asset(self.company, data, alt_text=f"SMS-film: {label}", purpose="content")
                except MediaError as exc:
                    raise SmsFilmError(f"{label}: {exc}") from exc
            asset = self._stored[key]
        elif ref.get("asset"):
            from ..models import MediaAsset

            try:
                asset_id = uuid.UUID(str(ref["asset"]))
            except ValueError as exc:
                raise SmsFilmError(f"{label}: ogiltig bild.") from exc
            asset = MediaAsset.objects.filter(pk=asset_id, company=self.company, kind="image").first()
            if asset is None:
                raise SmsFilmError(f"{label}: bilden finns inte längre. Välj en ny.")
        else:
            return None
        if str(asset.pk) not in self.ids:
            self.ids.append(str(asset.pk))
        return f"assets/upload/{asset.pk}.{_extension(asset)}", {"asset": str(asset.pk)}


def build(form, files, company):
    """Validates the submitted form. Returns (conversation, image_asset_ids, saved_form, total_seconds).

    saved_form is the form with every new upload replaced by its stored asset id, so the film can be reopened.
    """
    if not isinstance(form, dict):
        raise SmsFilmError("Formuläret kom inte fram. Ladda om sidan och försök igen.")
    images = _Images(company, files)
    saved = {}
    contact = _text(form.get("contact"), "Kontaktens namn", 40) or "Alex"
    clock = _text(form.get("clock"), "Klockan", 5) or "9:41"
    if not CLOCK_RE.match(clock):
        raise SmsFilmError("Klockan: skriv t.ex. 9:41.")
    chat_date = _text(form.get("chatDate"), "Datum i chatten", 40) or "Idag"
    conv = {"contact": contact, "clock": clock, "date": chat_date}
    saved.update(contact=contact, clock=clock, chatDate=chat_date)

    avatar = images.path(form.get("avatar"), "Profilbild")
    if avatar:
        conv["avatar"], saved["avatar"] = avatar
    conv["keyboard"] = saved["keyboard"] = form.get("keyboard") is not False
    if form.get("sounds") is False:
        conv["sounds"] = False
    saved["sounds"] = form.get("sounds") is not False

    messages = []
    notification = _text(form.get("notification"), "Notisen", MAX_TEXT)
    saved["notification"] = notification
    if notification:
        lock_date = _text(form.get("lockDate"), "Datum på låsskärmen", 40)
        intro = {"lockscreen": True}
        if lock_date:
            intro["date"] = lock_date
        wallpaper = images.path(form.get("wallpaper"), "Låsskärmens bakgrund")
        if wallpaper:
            intro["wallpaper"], saved["wallpaper"] = wallpaper
        conv["intro"] = intro
        saved["lockDate"] = lock_date
        messages.append({"side": "recv", "text": notification})

    raw = form.get("messages")
    if not isinstance(raw, list):
        raise SmsFilmError("Lägg till minst ett meddelande.")
    if len(raw) + len(messages) > MAX_MESSAGES:
        raise SmsFilmError(f"Högst {MAX_MESSAGES} meddelanden per film.")
    saved_messages = []
    for i, item in enumerate(raw, start=1):
        label = f"Meddelande {i}"
        if not isinstance(item, dict) or item.get("side") not in ("sent", "recv"):
            raise SmsFilmError(f"{label}: välj vänster eller höger.")
        text = _text(item.get("text"), label, MAX_TEXT)
        m, s = {"side": item["side"]}, {"side": item["side"], "text": text}
        if text:
            m["text"] = text
        image = images.path(item.get("image"), f"{label}, bild")
        if image:
            m["image"], s["image"] = image
        if not text and not image:
            raise SmsFilmError(f"{label}: skriv en text eller välj en bild.")
        glasses = item.get("glasses") if isinstance(item.get("glasses"), dict) else {}
        if glasses.get("on"):
            if not image:
                raise SmsFilmError(f"{label}: gangsterglasögonen behöver en bild att landa på.")
            g = {"x": _fraction(glasses.get("x"), 0.5, 0, 1), "y": _fraction(glasses.get("y"), 0.3, 0, 1),
                 "width": _fraction(glasses.get("width"), 0.6, 0.1, 1.5), "rotate": _fraction(glasses.get("rotate"), 0, -45, 45)}
            m["overlay"] = {"src": GLASSES_SRC, **g, "after": 1.0, "duration": 1.6, "hold": 2.5}
            s["glasses"] = {"on": True, **g}
        messages.append(m)
        saved_messages.append(s)
    if not messages:
        raise SmsFilmError("Lägg till minst ett meddelande.")
    conv["messages"] = messages
    saved["messages"] = saved_messages
    if form.get("outro"):
        conv["outro"] = "spotlight"
        conv["endHold"] = 2
    saved["outro"] = bool(form.get("outro"))
    conv["typingSpeed"] = 1.4
    conv["sentTypingSpeed"] = 0.7

    _, total = schedule(conv)
    if total > MAX_SECONDS:
        raise SmsFilmError(f"Filmen blir {total:.0f} sekunder. Högst {MAX_SECONDS} sekunder – ta bort några meddelanden.")
    return conv, images.ids, saved, total


# --- slutmallar (library/templates/golfkuponger-slutmallar) ----------------------------------------------------

SLUTMALLAR = {
    "alla": "Alla portaler",
    "epassi": "Epassi",
    "benify": "Benify",
    "sp": "Söderberg & Partners",
    "edenred": "Edenred",
}
SLUTMALL_RAD1 = 40
SLUTMALL_RAD2 = 48
SLUTMALL_LEN = 7.7  # render.mjs reports the real length; this is only the estimate shown before rendering
SLUTMALL_EFFEKTER = {
    "small": "Smäll",
    "studs": "Studs",
    "tona": "Tona in",
    "glid": "Glid upp",
    "skriv": "Skrivmaskin",
    "avtack": "Avtäck",
}
# Same keys and limits as STIL in slutmall.html: (label, unit, min, max, default). skak's default depends on the effect.
SLUTMALL_STIL = {
    "logga": ("Loggans storlek", "%", 50, 160, 100),
    "ikoner": ("Portalikonernas storlek", "%", 50, 160, 100),
    "rad1": ("Rad 1, storlek", "%", 50, 160, 100),
    "rubrik": ("Rad 2, största storlek", "%", 50, 160, 100),
    "cta": ("Uppmaningens storlek", "%", 50, 160, 100),
    "bredd": ("Textens bredd", "px", 560, 950, 778),
    "hojd": ("Flytta allt nedåt", "px", -120, 300, 0),
    "luft_logga": ("Luft under loggan", "px", -30, 240, 0),
    "luft_rad1": ("Luft under rad 1", "px", -30, 160, 0),
    "luft_rubrik": ("Luft under rad 2", "px", -20, 160, 0),
    "luft_cta": ("Luft ovanför ikonerna", "px", -20, 200, 0),
    "luft_ikoner": ("Luft mellan ikonerna", "px", -8, 60, 0),
    "tempo": ("Tempo", "%", 50, 200, 100),
    "skak": ("Skakning", "%", 0, 200, None),
}
SLUTMALL_SKAK = {"small": 100, "studs": 40}  # other effects: 0


def slutmall_default(key, effekt):
    if key == "skak":
        return SLUTMALL_SKAK.get(effekt, 0)
    return SLUTMALL_STIL[key][4]


def _slutmall_stil(raw, effekt):
    """Keeps known keys only, as whole numbers clamped to their limits. Missing keys use the template's default."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SmsFilmError("Stilvalen kom inte fram. Ladda om sidan och försök igen.")
    stil = {}
    for key, (_, _, lo, hi, _) in SLUTMALL_STIL.items():
        value = raw.get(key)
        if _num(value):
            value = int(round(min(hi, max(lo, float(value)))))
            if value != slutmall_default(key, effekt):
                stil[key] = value
    return stil


def build_slutmall(form):
    """Validates the end-card form. Returns (saved_form, estimated_seconds). render.mjs checks the same limits."""
    if not isinstance(form, dict):
        raise SmsFilmError("Formuläret kom inte fram. Ladda om sidan och försök igen.")
    mall = form.get("mall")
    if mall not in SLUTMALLAR:
        raise SmsFilmError("Välj vilken slutmall som ska användas.")
    rad1 = _text(form.get("rad1"), "Rad 1", SLUTMALL_RAD1)
    rad2 = _text(form.get("rad2"), "Rad 2", SLUTMALL_RAD2, required=True)
    if "\n" in rad1 or "\n" in rad2:
        raise SmsFilmError("Raderna får inte innehålla radbrytningar.")
    effekt = form.get("effekt") or "small"
    if effekt not in SLUTMALL_EFFEKTER:
        raise SmsFilmError("Välj en effekt för texten.")
    stil = _slutmall_stil(form.get("stil"), effekt)
    return {"kind": "slutmall", "mall": mall, "rad1": rad1, "rad2": rad2, "effekt": effekt, "stil": stil}, SLUTMALL_LEN
