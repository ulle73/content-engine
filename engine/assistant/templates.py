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
    PromptTemplate("golf-photo-golfer", "Golfbild · naturlig golfare", "Skapa en trovärdig redaktionell golfbild för {{company_name}} utifrån {{brief}}. Prioritera naturlig personanatomi, synlig kontakt mellan båda händer och ett korrekt sammanhängande klubbgrepp/skaft/huvud, naturlig svensk golfmiljö, kameravinkel där kritiska relationer syns, mjukt verkligt ljus och återhållen efterbehandling. Använd företagets verifierade fakta från {{current}} endast som faktaunderlag. Följ golfrealism-guiden i docs/2026-10-28-golf-photo-realism-guide.md. Kräv inte specifik klubba eller golfbana utan bildreferens; inga AI-genererade loggor eller text.", "image"),
    PromptTemplate("golf-photo-swing", "Golfbild · korrekt svingfas", "Skapa en naturlig sportfotografisk golfbild för {{company_name}} från {{brief}}. Identifiera exakt svingfas innan bildgenerering: address, backswing, precis efter bollträff eller finish. Säkerställ rimliga höft-/torso-/arm-/fotpositioner, en enda sammanhängande golfklubba, båda händerna på greppet, rätt bollstatus och fysisk markkontakt. Välj inspektionsvänlig vinkel och realistisk slutartidskänsla. Se docs/2026-10-28-golf-photo-realism-guide.md. För avancerad sving: använd pose-referens när tillgänglig. Bevara användarens konstnärliga avsikt; inga uppfunna varumärkesdetaljer.", "image"),
    PromptTemplate("golf-photo-course", "Golfbild · nordisk golfbana", "Skapa ett trovärdigt nordiskt golfbanefoto för {{company_name}} utifrån {{brief}}. Beskriv relevanta gräszoner separat: green, collar, fairway, semiruff och ruff med rimliga klipphöjder, mjuka övergångar, naturlig topografi, vegetation och säsongsanpassad diskret färgvariation. Gräsdetaljer avtar med avståndet. Använd neutralt naturligt ljus, undvik neonfärgat eller plastigt gräs, överdriven HDR och konstruerade perfekt symmetriska ytor. Se docs/2026-10-28-golf-photo-realism-guide.md. Påstå inte att en genererad plats föreställer en riktig specifik bana utan en verklig banreferens.", "image"),
    PromptTemplate("golf-photo-equipment", "Golfbild · korrekt utrustning", "Skapa ett tekniskt trovärdigt golfutrustningsfoto för {{company_name}} enligt {{brief}}. Identifiera utrustningstyp och beskriv synliga sammanhängande delar och fästpunkter. Klubb: ett grepp, ett rakt obrutet skaft, en plausibel hosel och ett korrekt klubbhuvud. Standbag: exakt två rimligt fästa stödben. Trehjulig handvagn: ett framhjul, två bakhjul och rimlig baginfästning. Fotografera från tydlig trekvartsvinkel med synliga kontakt- och skuggpunkter. Se docs/2026-10-28-golf-photo-realism-guide.md. För en specifik kommersiell produkt behövs riktig produktreferens, annars får den inte utges för att vara exakt.", "image"),
    PromptTemplate("golf-photo-campaign", "Golfbild · trovärdig kampanj", "Skapa en professionell men fotografiskt trovärdig golfkampanjbild för {{company_name}} utifrån {{brief}} och tonaliteten {{voice}}. Välj naturlig golfhandling och en sammanhängande svensk miljö, med riktiga material, korrekt utrustning och diskret gräsvariation. Komponera avsiktligt utrymme för separat textlager, men generera ingen logga, UI eller rubrik i själva bilden. Naturligt ljus och färg, återhållen retusch, inte hyperpolerad generisk AI-reklam. Följ docs/2026-10-28-golf-photo-realism-guide.md. Förfalska inte dokumentära anspråk eller produktidentitet.", "image"),
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
