import base64
import hashlib
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


class SetupState(models.Model):
    """Single transaction lock for first-admin registration."""

    completed = models.BooleanField(default=False)


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    profile = models.TextField(blank=True)
    voice = models.TextField(blank=True)
    current = models.TextField(blank=True)
    source = models.CharField(max_length=500, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    postiz_ciphertext = models.TextField(blank=True, default="")
    postiz_channels = models.JSONField(default=list)

    @staticmethod
    def cipher():
        key = hashlib.sha256(settings.POSTIZ_ENCRYPTION_SECRET.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    @property
    def postiz_key(self):
        return self.cipher().decrypt(self.postiz_ciphertext.encode()).decode() if self.postiz_ciphertext else ""

    @postiz_key.setter
    def postiz_key(self, value):
        self.postiz_ciphertext = self.cipher().encrypt(value.encode()).decode() if value else ""


class ContentRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Company, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    context = models.JSONField()
    ideas = models.JSONField(default=list)
    selected = models.PositiveSmallIntegerField(null=True)
    draft = models.JSONField(default=dict)
    model = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=20, default="draft")
    delivery_result = models.JSONField(default=list)

    @property
    def title(self):
        return (
            self.ideas[self.selected]["title"]
            if self.selected is not None and self.selected < len(self.ideas)
            else "Sparat utkast"
        )
