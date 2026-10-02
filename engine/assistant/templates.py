"""Prompt recipes are data, not executable Python/Jinja or privileged system prompts."""
import re
import uuid
from dataclasses import asdict, dataclass

from django.db import transaction
from django.utils.text import slugify

from engine.models import AssistantTemplate, Company

from .contracts import TemplateRequest


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    title: str
    instructions: str
    kind: str = "auto"
    version: int = 1
    key: str = ""


BUILTINS = (
    PromptTemplate("animated-scroll", "Animerad scroll", "Planera {{brief}} som mjuka sammanhängande övergångar mellan bifogade bilder i deras ordning. Fyra bilder blir tre klipp. Bevara produktens identitet, riktning och kamerarörelse. Fråga om bilderna visar motiv som inte går att förena trovärdigt. Ingen text eller logga genereras in i AI-klippen.", "sequence"),
    PromptTemplate("product-reel", "Produktfilm", "Skapa en tydlig produktfilm utifrån {{brief}}. Bevara produktens identitet. En huvudhandling per klipp, en tydlig avslutning. Fråga om viktigt material saknas.", "video"),
    PromptTemplate("motion-message", "Animerat budskap", "Gör {{brief}} till ett kort budskap med rubrik, kort beskrivning och uppmaning. Använd originalmaterial för exakt logga och text. Hitta inte på fakta.", "motion"),
    PromptTemplate("social-post", "Inlägg i vår tonalitet", "Skriv ett konkret inlägg för {{company_name}} utifrån {{brief}} och företagets verifierade underlag. Följ tonaliteten {{voice}}. Hitta inte på erbjudanden, priser eller resultat.", "text"),
    PromptTemplate("story-film", "Film i flera scener", "Strukturera {{brief}} som en sammanhängande berättelse med en huvudhandling per scen. Förklara vilka bilder som behövs och bevara samma motiv mellan scenerna.", "sequence"),
)
VARIABLES = {"brief", "company_name", "profile", "voice", "current"}
PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def catalog(company):
    latest = {}
    for row in company.assistant_templates.order_by("key", "-version"):
        latest.setdefault(row.key, PromptTemplate(str(row.pk), row.title, row.instructions, row.kind, row.version, row.key))
    return [asdict(item) for item in (*BUILTINS, *latest.values())]


def resolve(company, template_id):
    if not template_id:
        return None
    for item in BUILTINS:
        if item.id == template_id:
            return asdict(item)
    try:
        template_id = uuid.UUID(str(template_id))
    except ValueError:
        raise ValueError("Promptmallen finns inte i detta företag.") from None
    row = AssistantTemplate.objects.filter(company=company, pk=template_id).first()
    if not row:
        raise ValueError("Promptmallen finns inte i detta företag.")
    return asdict(PromptTemplate(str(row.pk), row.title, row.instructions, row.kind, row.version, row.key))


def render(snapshot, values):
    if not snapshot:
        return ""
    return PLACEHOLDER.sub(lambda match: str(values.get(match[1], ""))[:6000], snapshot["instructions"])


@transaction.atomic
def save(company, user, data):
    data = TemplateRequest.model_validate(data)
    if company.owner_id != user.pk:
        raise ValueError("Företaget kunde inte öppnas.")
    unknown = set(PLACEHOLDER.findall(data.instructions)) - VARIABLES
    if unknown:
        raise ValueError("Okända mallfält: " + ", ".join(sorted(unknown)))
    Company.objects.select_for_update().get(pk=company.pk)
    key = data.key or slugify(data.title)[:65] or "promptmall"
    latest = company.assistant_templates.filter(key=key).order_by("-version").first()
    return AssistantTemplate.objects.create(company=company, key=key, version=latest.version + 1 if latest else 1,
                                            title=data.title, instructions=data.instructions, kind=data.kind)
