"""Session-based link -> proposals -> explicit approval workflow for the existing technique bank."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .ad_studio import library as catalog
from .ownership import company_required
from .techniques import service
from .techniques.models import StoredTechnique, TechniqueImport


@login_required
@company_required
@require_http_methods(["GET", "POST"])
def techniques(request, workspace_id):
    company = request.workspace
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "suggest":
                batch = service.propose(company, request.user, request.POST.get("url", ""))
                messages.info(request, "Granska förslagen. Inget har lagts till i teknikbanken ännu.")
                response = redirect("engine:techniques", workspace_id=workspace_id)
                response["Location"] += "?review=" + str(batch.pk)
                return response
            if action == "approve":
                batch_id = request.POST.get("import_id", "")
                selected = [int(x) for x in request.POST.getlist("selected")]
                result = service.approve(company, request.user, batch_id, selected)
                messages.success(request, str(len(result.get("added", result["saved"]))) + " tekniker finns i biblioteket.")
                return redirect("engine:techniques", workspace_id=workspace_id)
            raise ValueError("Okänd åtgärd.")
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
            return redirect("engine:techniques", workspace_id=workspace_id)
    import_id = request.GET.get("review", "")
    batch = None
    if import_id:
        try:
            batch = service.owned(company, import_id)
        except (ValueError, TypeError):
            messages.error(request, "Förslaget finns inte.")
    saved = list(StoredTechnique.objects.filter(company=company)[:100])
    batches = list(TechniqueImport.objects.filter(company=company)[:12])
    base_count = sum(item.get("type") == "technique" for item in catalog.items())
    return render(request, "engine/techniques.html", {
        "workspace": company, "batch": batch, "saved": saved,
        "batches": batches, "base_count": base_count,
    })
