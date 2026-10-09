import json

from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..media_storage import MediaError, download_url, local_path
from . import discord, service


@csrf_exempt
@require_POST
def discord_interaction(request):
    """Interactions forwarded by the owner's n8n Discord bot (see engine/review/discord.py)."""
    if not discord.secret_ok(request.headers.get("X-Content-Engine-Secret", "")):
        return JsonResponse({"error": "forbidden"}, status=403)
    if len(request.body) > 64 * 1024:
        return JsonResponse({"error": "too large"}, status=400)
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "invalid json"}, status=400)
    return JsonResponse(discord.handle(data if isinstance(data, dict) else {}))


@require_GET
def video(request, token):
    """The review video behind a signed link: Discord attachment source and the 'Öppna videon' link."""
    try:
        review = service.review_from_token(token)
    except service.ReviewError:
        return HttpResponse("Länken är ogiltig.", status=404)
    asset = review.asset
    if asset.storage_backend == "r2":
        try:
            return redirect(download_url(asset))
        except MediaError:
            return HttpResponse("Videon kunde inte öppnas just nu.", status=503)
    path = local_path(asset.storage_key)
    if not path.is_file():
        return HttpResponse("Filen saknas.", status=404)
    return FileResponse(path.open("rb"), content_type=asset.mime_type)
