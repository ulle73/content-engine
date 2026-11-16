"""Give a colleague access to a company's dashboard (e.g. Nicholas for SMS films).

    python manage.py add_company_member nicholas --company Golfkuponger
    python manage.py add_company_member nicholas --company Golfkuponger --email nicholas@example.com

Creates the user if missing and prints a one-time password; an existing user keeps their password.
Members can work in the dashboard; only the owner changes the Postiz connection and market switch.
"""

import secrets
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from engine.models import Company


def find_company(ref):
    try:
        return Company.objects.get(pk=uuid.UUID(ref))
    except (ValueError, Company.DoesNotExist):
        pass
    matches = list(Company.objects.filter(name__iexact=ref)[:2])
    if len(matches) != 1:
        raise CommandError(f"Hittar inget entydigt företag som heter {ref!r}. Använd företagets UUID.")
    return matches[0]


class Command(BaseCommand):
    help = "Ger en kollega åtkomst till ett företags dashboard. Skapar användaren om den saknas."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--company", required=True, help="Företagets namn eller UUID")
        parser.add_argument("--email", default="")
        parser.add_argument("--remove", action="store_true", help="Ta bort åtkomsten i stället")

    @transaction.atomic
    def handle(self, *args, username, company, email, remove, **options):
        company = find_company(company)
        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if remove:
            if user:
                company.members.remove(user)
            self.stdout.write(f"{username} har inte längre åtkomst till {company.name}.")
            return
        if user and user.pk == company.owner_id:
            raise CommandError(f"{username} äger redan {company.name}.")
        password = None
        if not user:
            password = secrets.token_urlsafe(12)
            user = User.objects.create_user(username=username, email=email, password=password)
        company.members.add(user)
        self.stdout.write(self.style.SUCCESS(f"{username} har åtkomst till {company.name}."))
        if password:
            self.stdout.write(f"Lösenord (visas bara nu): {password}")
