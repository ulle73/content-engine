from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openai import APIError

from .forms import BrandForm, CompanyForm, validate_context
from .generation import generate
from .models import Company, CompetitorPost, ContentEvent, ContentRun
from .ownership import company_required


@login_required
def index(request):
    companies = Company.objects.filter(owner=request.user).order_by("name")
    form = CompanyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        company = form.save(commit=False)
        company.owner = request.user
        company.save()
        return redirect("engine:home", workspace_id=company.pk)
    return render(request, "engine/companies.html", {"companies": companies, "form": form})


@login_required
@company_required
def home(request, workspace_id):
    workspace = request.workspace
    context = workspace
    form = BrandForm(request.POST or None, instance=context)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Företagsunderlaget är sparat.")
        return redirect("engine:home", workspace_id=workspace_id)
    runs = ContentRun.objects.filter(workspace=workspace).order_by("-created_at")[:10]
    return render(request, "engine/home.html", {"form": form, "runs": runs, "workspace": workspace})


@login_required
@company_required
@require_POST
def ideas(request, workspace_id):
    context = request.workspace
    try:
        validate_context(context)
        from .signals import classify, inspiration, rank_ideas

        signal_id = request.POST.get("signal_id")
        if signal_id:
            signal_post = get_object_or_404(
                CompetitorPost, pk=signal_id, competitor__company=request.workspace, competitor__active=True
            )
            classify(signal_post, request.workspace)
        snapshot = {
            "company": request.workspace.name,
            "profile": context.profile,
            "voice": context.voice,
            "current": context.current,
            "source": context.source,
            "valid_until": context.valid_until.isoformat(),
            "captured_at": timezone.now().isoformat(),
            "recent_posts": [
                item.get("facebook", "")
                for item in ContentRun.objects.filter(workspace=request.workspace)
                .exclude(draft={})
                .order_by("-created_at")
                .values_list("draft", flat=True)[:10]
            ],
        }
        snapshot["competitor_signals"] = inspiration(request.workspace, signal_id)
        output = generate(snapshot)
        ranked = rank_ideas(output["ideas"], snapshot)
        new_run = ContentRun.objects.create(
            workspace=request.workspace,
            author=request.user,
            context=snapshot,
            ideas=ranked,
            model=settings.OPENAI_MODEL,
        )
        ContentEvent.objects.create(
            run=new_run,
            action="ranked",
            data={
                "ranker_version": "heuristic-v1",
                "ideas": ranked,
                "signal_ids": [s["id"] for s in snapshot["competitor_signals"]],
            },
        )
        messages.success(request, "Tre idéer är klara. Välj vilken du vill skriva.")
    except ValueError as exc:
        messages.error(request, str(exc))
    except APIError as exc:
        messages.error(
            request,
            f"AI-anropet misslyckades ({getattr(exc, 'status_code', None) or 'anslutning'}). Inga nya idéer sparades.",
        )
    return redirect("engine:home", workspace_id=workspace_id)


@login_required
@company_required
@require_POST
def draft(request, workspace_id, run_id, idea_index):
    run = get_object_or_404(ContentRun, pk=run_id, workspace=request.workspace)
    if run.draft:
        return redirect("engine:review", workspace_id=workspace_id, run_id=run.id)
    if idea_index >= len(run.ideas):
        from django.http import Http404

        raise Http404
    try:
        current = request.workspace
        validate_context(current)
        if (
            any(run.context[key] != getattr(current, key) for key in ["profile", "voice", "current", "source"])
            or run.context["valid_until"] != current.valid_until.isoformat()
        ):
            raise ValueError("Underlaget har ändrats. Skapa nya idéer så att texten bygger på rätt uppgifter.")
        if date.fromisoformat(run.context["valid_until"]) < timezone.localdate():
            raise ValueError("Underlaget har gått ut. Uppdatera det och skapa nya idéer.")
        output = generate(run.context, idea=run.ideas[idea_index])
        with transaction.atomic():
            locked = ContentRun.objects.select_for_update().get(pk=run.pk, workspace=request.workspace)
            if not locked.draft:
                locked.draft = output
                locked.selected = idea_index
                locked.save(update_fields=["draft", "selected"])
                ContentEvent.objects.create(
                    run=locked, idea_index=idea_index, action="selected", data={"idea": run.ideas[idea_index]}
                )
                ContentEvent.objects.create(
                    run=locked, idea_index=idea_index, action="draft_created", data={"initial_draft": output}
                )
        messages.success(request, "Utkastet är sparat. Granska texten, välj bild och för över till Postiz.")
        return redirect("engine:review", workspace_id=workspace_id, run_id=run.id)
    except ValueError as exc:
        messages.error(request, str(exc))
    except APIError as exc:
        messages.error(
            request,
            f"AI-anropet misslyckades ({getattr(exc, 'status_code', None) or 'anslutning'}). Idéerna finns kvar.",
        )
    return redirect("engine:home", workspace_id=workspace_id)


@login_required
@company_required
def connect(request, workspace_id):
    from .postiz import PostizError, list_channels

    context = request.workspace
    if request.method == "POST":
        key = request.POST.get("api_key", "").strip() or context.postiz_key
        try:
            channels = list_channels(key)
            if request.POST.get("action") == "save":
                chosen = request.POST.getlist("channels")
                context.postiz_key = key
                context.postiz_channels = [c for c in channels if c["id"] in chosen]
                context.save(update_fields=["postiz_ciphertext", "postiz_channels"])
                messages.success(request, "Företagets Postiz-koppling är sparad.")
                return redirect("engine:home", workspace_id=workspace_id)
            # Persist the verified credential encrypted, never send it back to HTML.
            if key != context.postiz_key:
                context.postiz_channels = []
            context.postiz_key = key
            context.save(update_fields=["postiz_ciphertext", "postiz_channels"])
            return render(
                request,
                "engine/connect.html",
                {"channels": channels, "workspace": request.workspace, "connected": True},
            )
        except PostizError as exc:
            messages.error(request, str(exc))
    return render(
        request, "engine/connect.html", {"workspace": request.workspace, "connected": bool(context.postiz_key)}
    )


@login_required
@company_required
def review(request, workspace_id, run_id):
    from .postiz import PostizError, make_payload
    from .postiz import request as postiz_request

    run = get_object_or_404(ContentRun, pk=run_id, workspace=request.workspace)
    brand = request.workspace
    if request.method == "POST" and request.POST.get("action") == "reset":
        if run.delivery_status == "unknown" and request.POST.get("checked_postiz"):
            ContentRun.objects.filter(pk=run.pk, delivery_status="unknown").update(delivery_status="draft")
            messages.success(request, "Överföringen är återställd efter din kontroll i Postiz.")
        else:
            messages.error(request, "Kontrollera först att inget utkast skapats i Postiz.")
        return redirect("engine:review", workspace_id=workspace_id, run_id=run.id)
    if request.method == "POST":
        facebook = request.POST.get("facebook", "").strip()
        instagram = request.POST.get("instagram", "").strip()
        action = request.POST.get("action")
        try:
            if run.delivery_status != "draft":
                raise ValueError("Utkastet har redan skickats eller inväntar kontroll i Postiz. Redigera där.")
            if not facebook or not instagram or len(instagram) > 2200 or len(facebook) > 63206:
                raise ValueError("Båda texter behövs. Instagram får vara högst 2200 tecken och Facebook högst 63206.")
            run.draft.update(facebook=facebook, instagram=instagram)
            with transaction.atomic():
                current_run = ContentRun.objects.select_for_update().get(pk=run.pk)
                if current_run.delivery_status != "draft":
                    raise ValueError("Överföringen har redan startat. Kontrollera Postiz.")
                previous_draft = current_run.draft
                current_run.draft = run.draft
                current_run.save(update_fields=["draft"])
                if previous_draft != run.draft:
                    ContentEvent.objects.create(
                        run=run,
                        idea_index=run.selected,
                        action="edited",
                        data={"before": previous_draft, "after": run.draft},
                    )
            if action == "send":
                validate_context(brand)
                if run.context["valid_until"] < timezone.localdate().isoformat() or any(
                    run.context[k] != getattr(brand, k) for k in ["current", "source", "profile"]
                ):
                    raise ValueError(
                        "Underlaget har ändrats eller gått ut. Skapa ett nytt inlägg från de aktuella uppgifterna."
                    )
                if not request.POST.get("reviewed"):
                    raise ValueError("Bekräfta att texten och bildrättigheterna har kontrollerats.")
                chosen = request.POST.getlist("channels")
                channels = [c for c in brand.postiz_channels if c["id"] in chosen]
                photo = request.FILES.get("photo")
                if photo and (photo.size > 8 * 1024 * 1024 or photo.content_type not in {"image/jpeg", "image/png"}):
                    raise ValueError("Välj en JPEG- eller PNG-bild under 8 MB.")
                # Validate before any write to the external service.
                make_payload(channels, facebook, instagram, [{}] if photo else [])
                if not brand.postiz_key:
                    raise ValueError("Anslut Postiz först.")
                claimed = ContentRun.objects.filter(pk=run.pk, delivery_status="draft").update(
                    delivery_status="sending", draft=run.draft
                )
                if not claimed:
                    raise ValueError("Överföringen har redan startat. Kontrollera Postiz.")
                ContentEvent.objects.create(
                    run=run, idea_index=run.selected, action="approved", data={"draft": run.draft, "channels": channels}
                )
                try:
                    media = []
                    if photo:
                        uploaded = postiz_request(
                            brand.postiz_key,
                            "POST",
                            "/upload",
                            files={"file": (photo.name, photo.read(), photo.content_type)},
                        )
                        media = [{"id": uploaded["id"], "path": uploaded["path"]}]
                    result = postiz_request(
                        brand.postiz_key, "POST", "/posts", json=make_payload(channels, facebook, instagram, media)
                    )
                    if (
                        not isinstance(result, list)
                        or len(result) != len(channels)
                        or not all(r.get("postId") for r in result)
                    ):
                        raise PostizError("Postiz-svaret gick inte att bekräfta. Kontrollera utkasten i Postiz.")
                    ContentRun.objects.filter(pk=run.pk).update(delivery_status="sent", delivery_result=result)
                    ContentEvent.objects.create(
                        run=run, idea_index=run.selected, action="postiz_draft", data={"posts": result}
                    )
                    messages.success(request, "Utkastet finns i Postiz. Slutgranska och schemalägg där.")
                except (PostizError, KeyError):
                    ContentRun.objects.filter(pk=run.pk).update(delivery_status="unknown")
                    raise PostizError(
                        "Överföringen kunde inte bekräftas. Kontrollera utkastet i Postiz; ingen automatisk omsändning görs."
                    )
            else:
                messages.success(request, "Ändringarna är sparade.")
            return redirect("engine:review", workspace_id=workspace_id, run_id=run.id)
        except (ValueError, PostizError) as exc:
            messages.error(request, str(exc))
        run.refresh_from_db()
    return render(request, "engine/review.html", {"run": run, "brand": brand, "workspace": request.workspace})
