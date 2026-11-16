from functools import wraps

from django.shortcuts import get_object_or_404

from .models import Company


def company_required(view):
    @wraps(view)
    def wrapped(request, workspace_id, *args, **kwargs):
        request.workspace = get_object_or_404(Company.accessible(request.user), pk=workspace_id)
        return view(request, workspace_id, *args, **kwargs)

    return wrapped
