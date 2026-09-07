import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the first owner using BOOTSTRAP_ADMIN_EMAIL/PASSWORD; never changes an existing account."

    def handle(self, **options):
        email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL")
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
        if not email or not password:
            raise CommandError("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD securely.")
        if get_user_model().objects.filter(email=email).exists():
            self.stdout.write("Owner already exists; unchanged.")
            return
        if get_user_model().objects.exists():
            raise CommandError("An owner already exists. Use the existing invitation flow.")
        if len(password) < 16:
            raise CommandError("Use a password of at least 16 characters.")
        user = get_user_model().objects.create_superuser(email=email, password=password, name="Administratör")
        workspace = user.workspace_memberships.first().workspace
        workspace.name = "Gullbringa Golf"
        workspace.timezone = "Europe/Stockholm"
        workspace.approval_workflow_mode = "required_internal"
        workspace.save()
        self.stdout.write("Owner and company created. No source facts or social accounts were invented.")
