"""Thin session-authenticated UI over the shared Prompt Library service."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import prompt_library as library
from .models import MediaGeneration, PromptEntry
from .ownership import company_required

PREVIEW_SALT = 'creative-prompt-bulk-v1'


class PromptForm(forms.Form):
    text = forms.CharField(label='Prompt', strip=False, max_length=100_000,
                           widget=forms.Textarea(attrs={'rows': 8, 'autofocus': True,
                           'placeholder': 'Klistra in din prompt h\u00e4r ...'}))
    title = forms.CharField(label='Rubrik', required=False, max_length=160)
    source_url = forms.URLField(label='K\u00e4lla (HTTPS)', required=False, max_length=2000)
    notes = forms.CharField(label='Anteckning', required=False, max_length=4000, widget=forms.Textarea(attrs={'rows': 3}))
    tags = forms.CharField(label='Egna etiketter (separera med komma)', required=False, max_length=1300)

    def clean_text(self):
        value = self.cleaned_data['text']
        if not value.strip():
            raise forms.ValidationError('Klistra in en prompt f\u00f6rst.')
        return value

    def service_data(self):
        data = self.cleaned_data.copy()
        data['tags'] = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]
        return data


def _entry(request, prompt_id):
    return get_object_or_404(PromptEntry, pk=prompt_id, company=request.workspace, archived_at__isnull=True)


def _failure(form, exc):
    form.add_error(None, '; '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))


@login_required
@company_required
def prompt_library(request, workspace_id):
    form = PromptForm(request.POST or None)
    status = 200
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'confirm':
            try:
                token = request.POST.get('preview_token', '')
                if len(token) > 200_000:
                    raise signing.BadSignature()
                preview = signing.loads(token, salt=PREVIEW_SALT, max_age=600)
                if preview['user'] != request.user.pk or preview['company'] != str(workspace_id):
                    raise signing.BadSignature()
                parts = library.preview_bulk(preview['text'])
                with transaction.atomic():
                    for part in parts:
                        library.save_prompt(request.user, workspace_id, part)
                messages.success(request, f'{len(parts)} promptar har sparats. Befintliga dubletter beh\u00e5lls utan omskrivning.')
                return redirect('engine:prompt_library', workspace_id=workspace_id)
            except (signing.BadSignature, KeyError, TypeError, ValidationError):
                form = PromptForm({})
                form.is_valid()
                form.add_error(None, 'F\u00f6rhandsgranskningen har g\u00e5tt ut eller kunde inte verifieras. Klistra in texten och granska igen.')
                status = 400
        elif form.is_valid():
            try:
                if action == 'preview':
                    parts = library.preview_bulk(form.cleaned_data['text'])
                    preview_token = signing.dumps({'user': request.user.pk, 'company': str(workspace_id),
                        'text': form.cleaned_data['text']}, salt=PREVIEW_SALT, compress=True)
                    return render(request, 'engine/prompt_bulk.html', {'workspace': request.workspace,
                        'parts': parts, 'preview_token': preview_token})
                if action != 'save':
                    raise ValidationError('V\u00e4lj Spara prompt eller F\u00f6rhandsgranska flera.')
                _, created = library.save_prompt(request.user, workspace_id, **form.service_data())
                messages.success(request, 'Prompten \u00e4r sparad. Klistra in n\u00e4sta!' if created else 'Prompten finns redan. Original och eventuella redigeringar \u00e4r kvar.')
                return redirect('engine:prompt_library', workspace_id=workspace_id)
            except ValidationError as exc:
                _failure(form, exc)
                status = 400
        else:
            status = 400
    try:
        entries = library.search_prompts(request.user, workspace_id, query=request.GET.get('q', ''),
            tag=request.GET.get('tag', ''), favorites=request.GET.get('favorites') == '1', kind=request.GET.get('kind', ''))
    except ValidationError as exc:
        entries = []
        if not form.is_bound:
            form = PromptForm({})
            form.is_valid()
        _failure(form, exc)
        status = 400
    return render(request, 'engine/prompt_library.html', {'workspace': request.workspace, 'entries': entries,
        'form': form, 'filters': request.GET}, status=status)


@login_required
@company_required
def prompt_detail(request, workspace_id, prompt_id):
    prompt = _entry(request, prompt_id)
    initial = {'text': prompt.text, 'title': prompt.title, 'source_url': prompt.source_url, 'notes': prompt.notes,
               'tags': ', '.join(prompt.metadata.get('user_tags', []))}
    form = PromptForm(request.POST or None, initial=initial)
    status = 200
    if request.method == 'POST':
        if form.is_valid():
            try:
                library.edit_prompt(request.user, workspace_id, prompt_id, **form.service_data())
                messages.success(request, '\u00c4ndringarna \u00e4r sparade. Originalet \u00e4r of\u00f6r\u00e4ndrat.')
                return redirect('engine:prompt_detail', workspace_id=workspace_id, prompt_id=prompt_id)
            except ValidationError as exc:
                _failure(form, exc)
        status = 400
    return render(request, 'engine/prompt_detail.html', {'workspace': request.workspace, 'prompt': prompt,
        'form': form}, status=status)


@login_required
@company_required
@require_POST
def prompt_favorite(request, workspace_id, prompt_id):
    _entry(request, prompt_id)
    library.edit_prompt(request.user, workspace_id, prompt_id, favorite=request.POST.get('favorite') == '1')
    return redirect('engine:prompt_library', workspace_id=workspace_id)


@login_required
@company_required
@require_POST
def prompt_archive(request, workspace_id, prompt_id):
    # Repeat removal is safe, but foreign IDs are never accepted.
    get_object_or_404(PromptEntry, pk=prompt_id, company=request.workspace)
    library.archive_prompt(request.user, workspace_id, prompt_id)
    messages.success(request, 'Prompten \u00e4r borttagen fr\u00e5n biblioteket. Sparade generationer p\u00e5verkas inte.')
    return redirect('engine:prompt_library', workspace_id=workspace_id)


@login_required
@company_required
@require_POST
def prompt_save_generation(request, workspace_id, job_id):
    get_object_or_404(MediaGeneration, pk=job_id, run__workspace=request.workspace)
    try:
        prompt, _ = library.save_from_generation(request.user, workspace_id, job_id)
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
        return redirect('engine:prompt_library', workspace_id=workspace_id)
    messages.success(request, 'Prompten och l\u00e4nken till generationen \u00e4r sparade.')
    return redirect('engine:prompt_detail', workspace_id=workspace_id, prompt_id=prompt.pk)
