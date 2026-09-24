import io
import uuid
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .media import store_asset
from .models import Company, MediaGeneration, SequenceBridgeVersion, SequenceClipVersion, SequenceProject
from .sequence import (
    add_anchor,
    create_clip,
    create_sequence_project,
    create_transition_bridge,
    prepare_anchor_chain_version,
    prepare_transition_bridge_version,
    select_clip_version,
)


def picture(rgb=(24, 92, 58)):
    out = io.BytesIO()
    Image.new("RGB", (96, 64), rgb).save(out, "PNG")
    return out.getvalue()


class _Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
class SequenceWorkspaceF1Tests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media_root = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        self.media_root.enable()
        self.addCleanup(self.media_root.disable)

        self.user = get_user_model().objects.create_user(
            username="sequence-ui@example.test",
            password="test-only-password",
        )
        self.company = Company.objects.create(
            owner=self.user,
            name="Golfkuponger",
            profile="Golfkuponger profile",
            voice="Premium",
            current="Aktuellt",
            source="Test",
        )
        self.client.force_login(self.user)

    def asset(self, rgb=(24, 92, 58)):
        return store_asset(self.company, picture(rgb))

    def build_workspace_project(self):
        project = create_sequence_project(
            self.company,
            author=self.user,
            title="Premium scroll story",
            brief="Fyra anchors med ett separat continuity bridge.",
            format="scroll_story",
            platform="web",
        )
        k0 = add_anchor(project, self.asset((10, 40, 25)), position=0, label="Opening anchor", locked=True)
        k1 = add_anchor(project, self.asset((20, 70, 40)), position=1, label="Left ending anchor", locked=True)
        k2 = add_anchor(project, self.asset((40, 100, 60)), position=2, label="Right opening anchor", locked=False)
        k3 = add_anchor(project, self.asset((60, 130, 75)), position=3, label="Closing anchor", locked=True)
        left = create_clip(
            project,
            k0,
            k1,
            position=0,
            recipe_id="scroll_transition_bridge",
            label="Left scene",
        )
        right = create_clip(
            project,
            k2,
            k3,
            position=2,
            recipe_id="scroll_transition_bridge",
            label="Right scene",
        )
        bridge = create_transition_bridge(
            project,
            left,
            right,
            label="Continuity bridge",
        )

        selected = prepare_anchor_chain_version(left, token=uuid.uuid4())
        MediaGeneration.objects.filter(pk=selected.generation_id).update(status="completed")
        SequenceClipVersion.objects.filter(pk=selected.pk).update(status="ready")
        selected.refresh_from_db()
        select_clip_version(left, selected)

        bridge_version = prepare_transition_bridge_version(bridge, token=uuid.uuid4())
        SequenceBridgeVersion.objects.filter(pk=bridge_version.pk).update(status="queued")
        return project, (k0, k1, k2, k3), left, right, bridge

    def test_sequence_list_is_company_scoped_and_shows_counts(self):
        project, _, _, _, _ = self.build_workspace_project()
        outsider = get_user_model().objects.create_user(username="sequence-ui-other")
        other = Company.objects.create(owner=outsider, name="Other")
        create_sequence_project(other, author=outsider, title="Secret sequence")

        response = self.client.get(reverse("engine:sequence_list", kwargs={"workspace_id": self.company.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium scroll story")
        self.assertNotContains(response, "Secret sequence")
        self.assertContains(response, "<b>4</b> anchors", html=True)
        self.assertContains(response, "<b>2</b> clips", html=True)
        self.assertContains(response, "<b>1</b> bridges", html=True)
        self.assertContains(response, "Scroll story")
        self.assertContains(response, "Webb")
        self.assertContains(
            response,
            reverse("engine:sequence_workspace", kwargs={"workspace_id": self.company.pk, "project_id": project.pk}),
        )

    def test_create_empty_project_is_provider_free_and_redirects_to_workspace(self):
        with patch("engine.media.providers.estimate_video") as estimate, patch("engine.media.providers.start_video") as start:
            response = self.client.post(
                reverse("engine:sequence_list", kwargs={"workspace_id": self.company.pk}),
                {
                    "title": "Ny produktfilm",
                    "brief": "Premium produktfilm i tre steg.",
                    "format": "product_film",
                    "platform": "meta_ads",
                },
            )
        estimate.assert_not_called()
        start.assert_not_called()
        project = SequenceProject.objects.get(company=self.company, title="Ny produktfilm")
        self.assertRedirects(
            response,
            reverse("engine:sequence_workspace", kwargs={"workspace_id": self.company.pk, "project_id": project.pk}),
            fetch_redirect_response=False,
        )
        self.assertEqual((project.format, project.platform), ("product_film", "meta_ads"))
        self.assertEqual(project.anchors.count(), 0)
        self.assertEqual(project.clips.count(), 0)
        self.assertEqual(project.bridges.count(), 0)

    def test_invalid_project_create_preserves_form_and_creates_nothing(self):
        response = self.client.post(
            reverse("engine:sequence_list", kwargs={"workspace_id": self.company.pk}),
            {
                "title": "",
                "brief": "Behåll detta i formuläret",
                "format": "scroll_story",
                "platform": "web",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SequenceProject.objects.filter(company=self.company).exists())
        self.assertContains(response, "Sequence-projektet behöver en titel")
        self.assertContains(response, "Behåll detta i formuläret")
        self.assertContains(response, 'value="scroll_story" selected', html=False)

    def test_workspace_is_company_scoped(self):
        outsider = get_user_model().objects.create_user(username="sequence-ui-outsider")
        other = Company.objects.create(owner=outsider, name="Other")
        foreign = create_sequence_project(other, author=outsider, title="Foreign")
        response = self.client.get(
            reverse("engine:sequence_workspace", kwargs={"workspace_id": self.company.pk, "project_id": foreign.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_workspace_renders_anchor_clip_bridge_order_lock_state_and_versions(self):
        project, _, _, _, _ = self.build_workspace_project()
        response = self.client.get(
            reverse("engine:sequence_workspace", kwargs={"workspace_id": self.company.pk, "project_id": project.pk})
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()

        ordered = [
            "Opening anchor",
            "Left scene",
            "Left ending anchor",
            "Continuity bridge",
            "Right opening anchor",
            "Right scene",
            "Closing anchor",
        ]
        positions = [body.index(value) for value in ordered]
        self.assertEqual(positions, sorted(positions))

        self.assertContains(response, "Låst")
        self.assertContains(response, "Upplåst")
        self.assertContains(response, "Kandidater")
        self.assertContains(response, "V1")
        self.assertContains(response, "Completed")
        self.assertContains(response, "scroll_transition_bridge")
        self.assertContains(response, "4 anchors · 3 segment")
        self.assertContains(response, 'role="list"')
        self.assertContains(response, 'aria-label="Sekvensens ordning"')

    def test_workspace_is_read_safe_and_exposes_no_generation_or_anchor_mutation_actions(self):
        project, _, _, _, _ = self.build_workspace_project()
        response = self.client.get(
            reverse("engine:sequence_workspace", kwargs={"workspace_id": self.company.pk, "project_id": project.pk})
        )
        self.assertContains(response, "Översikt utan dolda mutationer")
        self.assertContains(response, "Read-safe")
        self.assertNotContains(response, "Regenerera")
        self.assertNotContains(response, "Starta betald generation")
        self.assertNotContains(response, "Byt anchor")
        self.assertNotContains(response, 'name="source_asset"')
        self.assertNotContains(response, 'name="end_asset"')

    def test_empty_workspace_renders_safe_empty_state(self):
        project = create_sequence_project(self.company, author=self.user, title="Tom sekvens")
        response = self.client.get(
            reverse("engine:sequence_workspace", kwargs={"workspace_id": self.company.pk, "project_id": project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projektet är tomt")
        self.assertContains(response, "Anchor-kontroller kommer i F2")
        self.assertContains(response, "<strong>0</strong>", count=4, html=True)

    def test_sequences_are_media_subnavigation_without_adding_seventh_primary_destination(self):
        project = create_sequence_project(self.company, author=self.user, title="Nav sequence")
        for url_name, kwargs in (
            ("sequence_list", {"workspace_id": self.company.pk}),
            ("sequence_workspace", {"workspace_id": self.company.pk, "project_id": project.pk}),
        ):
            response = self.client.get(reverse(f"engine:{url_name}", kwargs=kwargs))
            parser = _Links(response.content.decode())
            for link_class in ("app-nav-link", "mobile-nav-link"):
                links = [
                    link
                    for link in parser.links
                    if link_class in link.get("class", "").split()
                ]
                self.assertEqual(len(links), 6)
                active = [link for link in links if link.get("aria-current") == "page"]
                self.assertEqual(len(active), 1)
                self.assertEqual(
                    active[0]["href"],
                    reverse("engine:media_library", kwargs={"workspace_id": self.company.pk}),
                )
            self.assertContains(response, ">Sekvenser<", html=False)
            self.assertContains(
                response,
                reverse("engine:sequence_list", kwargs={"workspace_id": self.company.pk}),
            )

    def test_sequence_workspace_styles_use_native_overflow_and_mobile_stack(self):
        project = create_sequence_project(self.company, author=self.user, title="Styled sequence")
        response = self.client.get(
            reverse("engine:sequence_workspace", kwargs={"workspace_id": self.company.pk, "project_id": project.pk})
        )
        self.assertContains(response, 'href="/static/css/sequence-screen.css"')
        stylesheet = self.client.get("/static/css/sequence-screen.css")
        self.assertEqual(stylesheet.status_code, 200)
        css = b"".join(stylesheet.streaming_content).decode("utf-8")
        self.assertIn(".sequence-track-shell", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("@media (max-width: 720px)", css)
        self.assertIn(".sequence-track { width: 100%; display: grid", css)
