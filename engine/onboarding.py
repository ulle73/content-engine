import secrets

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render

from .models import Company, SetupState


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="E-post", max_length=150)

    def clean_username(self):
        return self.cleaned_data["username"].lower()


class FirstAdminForm(UserCreationForm):
    username = forms.EmailField(label="E-post", max_length=150)
    company = forms.CharField(label="Första företagets namn", max_length=200)
    setup_token = forms.CharField(label="Installationskod", widget=forms.PasswordInput, required=False)

    class Meta(UserCreationForm.Meta):
        fields = ("username", "company", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.LOCAL_HTTP:
            del self.fields["setup_token"]
        else:
            self.fields["setup_token"].required = True
            self.fields[
                "setup_token"
            ].help_text = "Finns i webbhotellets inställningar som SETUP_TOKEN. Ingen terminal behövs."

    def clean_username(self):
        return self.cleaned_data["username"].lower()

    def clean_setup_token(self):
        token = self.cleaned_data.get("setup_token", "")
        if not settings.SETUP_TOKEN or not secrets.compare_digest(token, settings.SETUP_TOKEN):
            raise forms.ValidationError("Installationskoden stämmer inte.")
        return token


class SignInView(LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailLoginForm

    def dispatch(self, request, *args, **kwargs):
        if not get_user_model().objects.exists():
            return redirect("setup")
        return super().dispatch(request, *args, **kwargs)


def setup(request):
    if get_user_model().objects.exists():
        return redirect("dashboard" if request.user.is_authenticated else "login")
    form = FirstAdminForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # A migration seeds this singleton; concurrent requests cannot both claim ownership.
            state = SetupState.objects.select_for_update().get(pk=1)
            if state.completed or get_user_model().objects.exists():
                return redirect("login")
            user = form.save(commit=False)
            user.email = user.username
            user.is_staff = user.is_superuser = True
            user.save()
            Company.objects.create(name=form.cleaned_data["company"], owner=user)
            state.completed = True
            state.save(update_fields=["completed"])
        login(request, user)
        return redirect("dashboard")
    return render(request, "registration/setup.html", {"form": form})
