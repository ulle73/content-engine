import io
import json
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from engine.models import Company, MediaAsset
from engine.smsfilm import service, spec
from engine.smsfilm.models import SmsFilmJob

TOKEN = "t" * 40


def png(color="red", size=(40, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


class SpecTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="spec", password="test")
        self.company = Company.objects.create(owner=user, name="Spec AB")

    def test_notification_becomes_first_message_and_lockscreen(self):
        conv, ids, saved, total = spec.build(
            {"notification": "Hej!", "messages": [{"side": "sent", "text": "Tja"}], "outro": True}, {}, self.company)
        self.assertEqual(conv["messages"][0], {"side": "recv", "text": "Hej!"})
        self.assertTrue(conv["intro"]["lockscreen"])
        self.assertEqual(conv["outro"], "spotlight")
        self.assertEqual(ids, [])
        self.assertGreater(total, spec.OUTRO_LEN)
        self.assertTrue(saved["outro"])

    def test_glasses_need_an_image(self):
        with self.assertRaises(spec.SmsFilmError):
            spec.build({"messages": [{"side": "recv", "text": "x", "glasses": {"on": True}}]}, {}, self.company)

    def test_upload_is_stored_and_glasses_clamped(self):
        files = {"f1": SimpleUploadedFile("a.png", png(), content_type="image/png")}
        conv, ids, saved, _ = spec.build({"messages": [
            {"side": "recv", "image": {"file": "f1"}, "glasses": {"on": True, "x": 2, "y": 0.4, "width": 9, "rotate": 90}},
        ]}, files, self.company)
        self.assertEqual(len(ids), 1)
        msg = conv["messages"][0]
        self.assertEqual(msg["image"], f"assets/upload/{ids[0]}.png")
        self.assertEqual((msg["overlay"]["x"], msg["overlay"]["width"], msg["overlay"]["rotate"]), (1, 1.5, 45))
        self.assertEqual(saved["messages"][0]["image"], {"asset": ids[0]})

    def test_too_long_is_rejected(self):
        messages = [{"side": "recv" if i % 2 else "sent", "text": "x" * 400} for i in range(29)]
        with self.assertRaisesMessage(spec.SmsFilmError, "sekunder"):
            spec.build({"messages": messages}, {}, self.company)

    def test_schedule_matches_reading_rule(self):
        starts, total = spec.schedule({"messages": [{"side": "recv", "text": "Hej"}, {"side": "sent", "text": "Tja"}]})
        self.assertEqual(len(starts), 2)
        self.assertGreaterEqual(starts[1] - starts[0], 5 / 6 + 0.9 - 0.01)
        self.assertEqual(total * 2, int(total * 2))


@mock.patch.dict(os.environ, {"GITHUB_DISPATCH_TOKEN": ""})
class ViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="nicholas", password="test")
        self.company = Company.objects.create(owner=self.user, name="GK")
        self.client.force_login(self.user)
        self.url = reverse("engine:sms_film", kwargs={"workspace_id": self.company.pk})

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SMS-film")
        self.assertContains(response, "sms-limits-data")

    def test_post_creates_job_and_status(self):
        form = {"title": "Test", "notification": "Hej", "messages": [{"side": "sent", "text": "Tja", "image": {"file": "f1"}}]}
        response = self.client.post(self.url, {"form_json": json.dumps(form),
                                               "f1": SimpleUploadedFile("a.png", png(), content_type="image/png")},
                                    HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        job = SmsFilmJob.objects.get()
        self.assertEqual(job.status, "queued")
        self.assertEqual(len(job.image_asset_ids), 1)
        self.assertIn("GITHUB_DISPATCH_TOKEN", job.dispatch_error)
        status = self.client.get(reverse("engine:sms_film_job", kwargs={"workspace_id": self.company.pk, "job_id": job.pk}))
        self.assertEqual(status.json()["job"]["status"], "queued")
        reopen = self.client.get(self.url + f"?from={job.pk}")
        self.assertContains(reopen, "Tja")

    def test_bad_form_returns_error(self):
        response = self.client.post(self.url, {"form_json": json.dumps({"messages": []})}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SmsFilmJob.objects.exists())

    def test_other_company_cannot_see_job(self):
        other = get_user_model().objects.create_user(username="other", password="test")
        other_company = Company.objects.create(owner=other, name="Other")
        job = SmsFilmJob.objects.create(company=other_company, created_by=other, title="x", form={},
                                        conversation={}, image_asset_ids=[], duration_s=5)
        response = self.client.get(reverse("engine:sms_film_job",
                                           kwargs={"workspace_id": self.company.pk, "job_id": job.pk}))
        self.assertEqual(response.status_code, 404)

    def test_active_limit(self):
        for _ in range(service.max_active()):
            SmsFilmJob.objects.create(company=self.company, created_by=self.user, title="x", form={},
                                      conversation={}, image_asset_ids=[], duration_s=5)
        response = self.client.post(self.url, {"form_json": json.dumps({"messages": [{"side": "sent", "text": "a"}]})},
                                    HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)


@override_settings(APP_URL="https://engine.test")
@mock.patch.dict(os.environ, {"EDIT_WORKER_TOKEN": TOKEN, "GITHUB_DISPATCH_TOKEN": ""})
class WorkerApiTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="w", password="test")
        self.company = Company.objects.create(owner=user, name="GK")
        files = {"f1": SimpleUploadedFile("a.png", png(), content_type="image/png")}
        conv, ids, saved, total = spec.build({"messages": [{"side": "recv", "text": "Hej", "image": {"file": "f1"}}]},
                                             files, self.company)
        self.job = service.create_job(self.company, user, title="Film", form=saved, conversation=conv,
                                      image_asset_ids=ids, duration_s=total, dispatch_now=False)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}

    def post(self, path, data, **extra):
        return self.client.post(f"/internal/sms-film/{path}", json.dumps(data), content_type="application/json",
                                **self.auth, **extra)

    def test_requires_token(self):
        response = self.client.post("/internal/sms-film/claim/", "{}", content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_full_cycle(self):
        payload = self.post("claim/", {"worker_id": "gh", "job_id": str(self.job.pk)}).json()["job"]
        self.assertEqual(payload["job_id"], str(self.job.pk))
        self.assertEqual(len(payload["assets"]), 1)
        lease = payload["lease"]
        asset_url = payload["assets"][0]["url"].replace("https://engine.test", "")
        image = self.client.get(asset_url, **self.auth, HTTP_X_EDIT_LEASE=lease)
        self.assertEqual(image.status_code, 200)
        self.assertEqual(b"".join(image.streaming_content)[:4], b"\x89PNG")
        wrong = self.client.get(asset_url, **self.auth, HTTP_X_EDIT_LEASE="00000000-0000-0000-0000-000000000000")
        self.assertEqual(wrong.status_code, 409)
        beat = self.post("heartbeat/", {"job_id": str(self.job.pk), "lease": lease, "progress": 0.5, "stage": "rendering"})
        self.assertEqual(beat.json()["status"], "rendering")
        output = f"/internal/sms-film/output/{self.job.pk}/"
        fields = {"meta": json.dumps({"duration_s": 12.5}), "warnings": json.dumps(["ok"])}
        # A file that is not a real video is rejected by the media check; the job keeps its lease.
        bad = self.client.post(output, {"file": SimpleUploadedFile("out.mp4", b"fake"), **fields},
                               **self.auth, HTTP_X_EDIT_LEASE=lease)
        self.assertEqual(bad.status_code, 409)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "rendering")
        # A stored video completes the job (store_asset stubbed: the test environment has no real MP4).
        video_asset = MediaAsset.objects.get(pk=self.job.image_asset_ids[0])
        video_asset.kind = "video"
        with mock.patch("engine.smsfilm.service.store_asset", return_value=video_asset):
            done = self.client.post(output, {"file": SimpleUploadedFile("out.mp4", b"mp4"), **fields},
                                    **self.auth, HTTP_X_EDIT_LEASE=lease)
        self.assertEqual(done.status_code, 200, done.content)
        self.job.refresh_from_db()
        self.assertEqual((self.job.status, self.job.duration_s, self.job.warnings), ("done", 12.5, ["ok"]))
        self.assertEqual(self.job.output_asset_id, video_asset.pk)
        late = self.post("heartbeat/", {"job_id": str(self.job.pk), "lease": lease, "progress": 1})
        self.assertEqual(late.status_code, 409)

    def test_fail_retryable_requeues_then_fails(self):
        for attempt in range(service.MAX_ATTEMPTS):
            payload = self.post("claim/", {"worker_id": "gh"}).json()["job"]
            self.assertEqual(payload["attempt"], attempt + 1)
            result = self.post("failed/", {"job_id": payload["job_id"], "lease": payload["lease"],
                                           "code": "render_failed", "detail": "boom", "retryable": True}).json()
        self.assertEqual(result["status"], "failed")
        self.job.refresh_from_db()
        self.assertIn("boom", self.job.error)

    def test_recover_requeues_expired_lease(self):
        payload = self.post("claim/", {"worker_id": "gh"}).json()["job"]
        SmsFilmJob.objects.filter(pk=payload["job_id"]).update(lease_expires_at="2000-01-01T00:00:00Z")
        self.assertEqual(service.recover(redispatch=False)["requeued"], 1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "queued")

class CommandTests(TestCase):
    def test_apple_pack_contains_all_files_without_owner(self):
        import tarfile
        import tempfile
        from pathlib import Path

        from django.core.management.base import CommandError

        from engine.management.commands.sms_film_apple_pack import FILES, build_pack

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            with self.assertRaises(CommandError):
                build_pack(cache)
            for name in FILES:
                (cache / name).parent.mkdir(parents=True, exist_ok=True)
                (cache / name).write_bytes(b"x")
            data = build_pack(cache)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            members = tar.getmembers()
        self.assertEqual(sorted(m.name for m in members), sorted(FILES))
        self.assertTrue(all(m.uid == 0 and m.uname == "" and m.mode == 0o644 for m in members))

    def test_sms_film_jobs_command_reports(self):
        from django.core.management import call_command

        out = io.StringIO()
        with mock.patch.object(service, "recover", return_value={"requeued": 1, "failed": 0, "redispatched": 2}) as rec:
            call_command("sms_film_jobs", "--no-dispatch", stdout=out)
        rec.assert_called_once_with(redispatch=False)
        self.assertIn("1 återköade", out.getvalue())


class MemberAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="jonas", password="test")
        self.company = Company.objects.create(owner=self.owner, name="Golfkuponger")
        self.stranger = User.objects.create_user(username="annan", password="test")

    def test_command_creates_member_who_can_open_sms_film(self):
        out = io.StringIO()
        call_command("add_company_member", "nicholas", "--company", "golfkuponger", stdout=out)
        self.assertIn("visas bara nu", out.getvalue())
        nicholas = get_user_model().objects.get(username="nicholas")
        self.assertTrue(self.company.can_access(nicholas))
        self.client.force_login(nicholas)
        self.assertContains(self.client.get(reverse("dashboard")), "Golfkuponger")
        url = reverse("engine:sms_film", kwargs={"workspace_id": self.company.pk})
        self.assertEqual(self.client.get(url).status_code, 200)
        out = io.StringIO()
        call_command("add_company_member", "nicholas", "--company", str(self.company.pk), stdout=out)
        self.assertNotIn("visas bara nu", out.getvalue())
        self.assertEqual(self.company.members.count(), 1)

    def test_non_member_gets_404(self):
        self.client.force_login(self.stranger)
        url = reverse("engine:sms_film", kwargs={"workspace_id": self.company.pk})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertNotContains(self.client.get(reverse("dashboard")), "Golfkuponger")
        self.assertFalse(self.company.can_access(self.stranger))

    def test_member_cannot_change_owner_settings(self):
        self.company.members.add(self.stranger)
        self.client.force_login(self.stranger)
        kw = {"workspace_id": self.company.pk}
        response = self.client.post(reverse("engine:connect", kwargs=kw), {"api_key": "x", "action": "save"})
        self.assertRedirects(response, reverse("engine:home", kwargs=kw), fetch_redirect_response=False)
        self.client.post(reverse("engine:market_action", kwargs=kw), {"action": "toggle"})
        self.company.refresh_from_db()
        self.assertEqual(self.company.postiz_ciphertext, "")
        self.assertTrue(self.company.market_intelligence_enabled)
