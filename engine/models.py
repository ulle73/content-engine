import uuid

from apps.common.encryption import EncryptedTextField
from django.conf import settings
from django.db import models


class BrandContext(models.Model):
    workspace = models.OneToOneField("workspaces.Workspace", on_delete=models.CASCADE)
    profile = models.TextField(blank=True)
    voice = models.TextField(blank=True)
    current = models.TextField(blank=True)
    source = models.CharField(max_length=500, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    postiz_key = EncryptedTextField(blank=True, default="")
    postiz_channels = models.JSONField(default=list)


class ContentRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    context = models.JSONField()
    ideas = models.JSONField(default=list)
    selected = models.PositiveSmallIntegerField(null=True)
    draft = models.JSONField(default=dict)
    post = models.OneToOneField("composer.Post", null=True, on_delete=models.SET_NULL)
    model = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=20, default="draft")
    delivery_result = models.JSONField(default=list)
