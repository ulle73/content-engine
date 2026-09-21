"""Company-scoped prompt storage and bounded, multilingual concept retrieval.

No paid model calls on save. Analysis is explicitly heuristic; model contracts
always come from the separate verified model registry, never from this library.
"""
import hashlib
import re
import unicodedata
from urllib.parse import urlsplit

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import Company, MediaGeneration, PromptEntry, PromptTerm

MAX_TEXT = 50_000
ANALYSIS_VERSION = "concepts-v1"
CONCEPTS = {
    "drone": {"drone", "dronare", "aerial", "flygning", "flyger"},
    "golf": {"golf", "golfbana", "golfbanan", "golfcourse", "green", "fairway"},
    "cinematic": {"cinematic", "filmisk", "filmiskt", "cinematisk"},
    "preservation": {"preserve", "retain", "unchanged", "bevara", "bevaras", "oforandrad", "behall"},
    "landscape": {"landscape", "landskap", "mountain", "berg", "nature", "natur"},
    "portrait": {"portrait", "portratt", "face", "ansikte"},
    "product": {"product", "produkt", "packshot", "presentkort", "giftcard"},
    "mist": {"mist", "fog", "dimma", "morgondimma"},
    "light": {"light", "lighting", "ljus", "belysning", "sunrise", "soluppgang"},
    "motion": {"motion", "movement", "moving", "rorelse", "rora", "animation", "animera", "animate"},
    "realistic": {"realistic", "photorealistic", "realistisk", "realistiskt", "fotorealistisk"},
}
STOP_WORDS = set("a an the of in on for and to with by is it as at this that en ett av pa i till med och ar som den det de over under".split())


def normalize(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def words(value: str) -> set[str]:
    return {word for word in re.findall(r"[^\W_]+", normalize(value)) if 1 < len(word) <= 80 and word not in STOP_WORDS}


def concepts(value: str) -> set[str]:
    tokens = words(value)
    result = {name for name, alternatives in CONCEPTS.items() if tokens & alternatives}
    if re.search(r"\b(push[ -]?in|dolly[ -]?in|in[ao]kning)\b", normalize(value)):
        result.add("push_in")
    if re.search(r"\b(slow motion|slow-motion|slowly|langsamt)\b", normalize(value)):
        result.add("slow_motion")
    return result


def analyze_prompt(text: str) -> dict:
    tokens = words(text)
    detected = sorted(concepts(text))
    kind = "i2v" if tokens & {"animate", "animera", "i2v"} else "video" if tokens & {"video", "reel", "t2v"} else "image" if tokens & {"photo", "photograph", "bild", "image"} else "unknown"
    language = "sv" if tokens & {"behall", "dronare", "golfbanan", "dimma", "langsamt", "skapa"} else "unknown"
    return {"analysis_version": ANALYSIS_VERSION, "evidence_level": "HEURISTIC", "kind": kind,
            "language": language, "model": "unknown", "tags": detected,
            "mechanisms": [item for item in detected if item in {"push_in", "slow_motion", "preservation", "light", "motion", "drone"}]}


def _owned_company(user, company_id):
    if not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Logga in f\u00f6rst.")
    company = Company.objects.filter(pk=company_id, owner=user).first()
    if company is None:
        raise PermissionDenied("F\u00f6retaget kunde inte \u00f6ppnas.")
    return company


def _text(text):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT or "\x00" in text:
        raise ValidationError("Klistra in en prompt med 1\u201350 000 tecken.")
    return text  # Deliberately no strip/newline/unicode normalization on stored text.


def _source(url):
    if not url:
        return ""
    if not isinstance(url, str) or len(url) > 2000 or any(ord(c) < 32 for c in url):
        raise ValidationError("Ange en giltig HTTPS-l\u00e4nk utan inloggningsuppgifter.")
    URLValidator(schemes=["https"])(url)
    parts = urlsplit(url)
    if parts.username is not None or parts.password is not None:
        raise ValidationError("K\u00e4lll\u00e4nken f\u00e5r inte inneh\u00e5lla inloggningsuppgifter.")
    return url


def _tags(tags):
    if tags is None:
        return []
    if not isinstance(tags, (list, tuple)) or len(tags) > 20:
        raise ValidationError("Ange h\u00f6gst 20 etiketter.")
    result = []
    for tag in tags:
        if not isinstance(tag, str) or not 1 <= len(tag.strip()) <= 64 or any(ord(c) < 32 for c in tag):
            raise ValidationError("Varje etikett ska ha 1\u201364 tecken.")
        if tag.strip() not in result:
            result.append(tag.strip())
    return result


def _reindex(prompt):
    tokens = {"word:" + word for word in words(prompt.text + " " + prompt.title + " " + prompt.notes)}
    tokens |= {"concept:" + item for item in concepts(prompt.text)}
    tokens |= {"tag:" + normalize(tag) for tag in prompt.metadata.get("tags", []) + prompt.metadata.get("user_tags", [])}
    # Max input length bounds index work. Extra-long tokens are not useful search terms.
    tokens = {value for value in tokens if len(value) <= 80}
    prompt.terms.all().delete()
    PromptTerm.objects.bulk_create([PromptTerm(prompt=prompt, value=value) for value in sorted(tokens)], batch_size=500)


@transaction.atomic
def save_prompt(user, company_id, text: str, *, title="", source_url="", notes="", tags=None):
    company = _owned_company(user, company_id)
    _text(text)
    if not isinstance(title, str) or len(title) > 160 or not isinstance(notes, str) or len(notes) > 4000:
        raise ValidationError("Rubriken f\u00e5r vara h\u00f6gst 160 tecken och anteckningen 4 000.")
    source_url, tags = _source(source_url), _tags(tags)
    metadata = {**analyze_prompt(text), "user_tags": tags}
    prompt, created = PromptEntry.objects.get_or_create(company=company, original_hash=hashlib.sha256(text.encode()).hexdigest(),
        defaults={"author": user, "original_text": text, "text": text, "title": title,
                  "source_url": source_url, "notes": notes, "metadata": metadata})
    if created:
        _reindex(prompt)
    elif prompt.archived_at is not None:
        prompt.archived_at = None
        prompt.save(update_fields=["archived_at", "updated_at"])
    return prompt, created


def get_prompt(user, company_id, prompt_id):
    company = _owned_company(user, company_id)
    return PromptEntry.objects.get(pk=prompt_id, company=company, archived_at__isnull=True)


@transaction.atomic
def edit_prompt(user, company_id, prompt_id, **changes):
    company = _owned_company(user, company_id)
    allowed = {"text", "title", "notes", "source_url", "tags", "favorite"}
    if set(changes) - allowed:
        raise ValidationError("Original och ursprung kan inte skrivas \u00f6ver.")
    prompt = PromptEntry.objects.select_for_update().get(pk=prompt_id, company=company, archived_at__isnull=True)
    if "text" in changes:
        prompt.text = _text(changes["text"])
    for key, maximum in (("title", 160), ("notes", 4000)):
        if key in changes:
            if not isinstance(changes[key], str) or len(changes[key]) > maximum:
                raise ValidationError("Textf\u00e4ltet \u00e4r f\u00f6r l\u00e5ngt.")
            setattr(prompt, key, changes[key])
    if "source_url" in changes:
        prompt.source_url = _source(changes["source_url"])
    if "favorite" in changes:
        if not isinstance(changes["favorite"], bool):
            raise ValidationError("Favorit ska vara ja eller nej.")
        prompt.favorite = changes["favorite"]
    metadata = dict(prompt.metadata)
    metadata.update(analyze_prompt(prompt.text))
    metadata["user_tags"] = _tags(changes.get("tags", metadata.get("user_tags", [])))
    prompt.metadata = metadata
    prompt.save()
    _reindex(prompt)
    return prompt


@transaction.atomic
def archive_prompt(user, company_id, prompt_id):
    company = _owned_company(user, company_id)
    PromptEntry.objects.filter(pk=prompt_id, company=company).update(archived_at=timezone.now(), updated_at=timezone.now())


def search_prompts(user, company_id, *, query="", tag="", favorites=False, kind="", limit=40):
    company = _owned_company(user, company_id)
    limit = max(1, min(int(limit), 100))
    if not isinstance(query, str) or len(query) > 1000:
        raise ValidationError("S\u00f6kningen f\u00e5r vara h\u00f6gst 1 000 tecken.")
    entries = PromptEntry.objects.filter(company=company, archived_at__isnull=True)
    if favorites:
        entries = entries.filter(favorite=True)
    if kind in {"image", "video", "i2v", "unknown"}:
        entries = entries.filter(metadata__kind=kind)
    if query.strip():
        query_words = ["word:" + w for w in sorted(words(query))[:30]]
        query_concepts = ["concept:" + c for c in concepts(query)]
        entries = entries.filter(terms__value__in=query_words + query_concepts).annotate(
            concept_hits=Count("terms", filter=Q(terms__value__in=query_concepts), distinct=True),
            word_hits=Count("terms", filter=Q(terms__value__in=query_words), distinct=True),
        ).order_by("-concept_hits", "-word_hits", "-favorite", "-created_at", "-id")
    else:
        entries = entries.order_by("-favorite", "-created_at", "-id")
    if tag:
        entries = entries.filter(terms__value="tag:" + normalize(_tags([tag])[0]))
    return list(entries.defer("original_text").distinct()[:limit])


def retrieve_inspiration(user, company_id, query: str, *, limit=3):
    entries = search_prompts(user, company_id, query=query, limit=min(max(1, limit), 5))
    return [{"id": str(p.pk), "text": p.text[:1200], "mechanisms": p.metadata.get("mechanisms", []),
             "tags": p.metadata.get("tags", []), "trust": "untrusted_inspiration", "origin": p.origin} for p in entries]


def preview_bulk(text: str):
    if not isinstance(text, str) or len(text) > 100_000:
        raise ValidationError("Klistra in h\u00f6gst 100 000 tecken \u00e5t g\u00e5ngen.")
    parts = re.split(r"(?m)^---PROMPT---(?:\r?\n|$)", text)
    if len(parts) > 20:
        raise ValidationError("Spara h\u00f6gst 20 promptar \u00e5t g\u00e5ngen.")
    return [_text(part) for part in parts]


@transaction.atomic
def save_from_generation(user, company_id, generation_id):
    company = _owned_company(user, company_id)
    job = MediaGeneration.objects.select_related("run").get(pk=generation_id, run__workspace=company)
    prompt, created = save_prompt(user, company.pk, job.prompt)
    if prompt.generation_id is None:
        prompt.generation = job
    if created:
        prompt.origin = "generation"
    safe_keys = {"model", "duration", "aspect_ratio", "resolution", "sound", "generate_audio", "shape"}
    prompt.metadata = {**prompt.metadata, "generation": {
        "id": str(job.pk), "run_id": str(job.run_id), "user_request": job.brief,
        "parameters": {k: v for k, v in job.parameters.items() if k in safe_keys},
        "estimated_usd": job.usage.get("estimated_usd"),
        "structured_brief": job.parameters.get("creative", {}).get("brief", {}),
        "asset_ids": [str(value) for value in job.assets.values_list("pk", flat=True)[:8]],
    }}
    prompt.save()
    return prompt, created
