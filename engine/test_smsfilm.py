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
from engine.smsfilm import mallar, service, spec
from engine.smsfilm.models import SmsFilmJob, SmsFilmOutput

TOKEN = "t" * 40


def png(color="red", size=(40, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def done_slutmall(company, user, fmt="9x16", duration=7.7, status="done"):
    """A rendered slutmall job whose output is a video in the company's media library."""
    files = {"f1": SimpleUploadedFile("a.png", png(), content_type="image/png")}
    _, ids, _, _ = spec.build({"messages": [{"side": "recv", "image": {"file": "f1"}}]}, files, company)
    asset = MediaAsset.objects.get(pk=ids[0])
    asset.kind = "video"
    asset.save(update_fields=["kind"])
    mall = mallar.hamta("golfkuponger-slutmallar")
    varden, formats = mallar.validera(mall, {"text2": "x"}, [fmt])
    job = service.create_job(company, user, title=f"Slut {fmt}", form={"kind": "mall"}, conversation={}, image_asset_ids=[],
                             duration_s=duration, dispatch_now=False, kind="slutmall", mall_id=mall["id"],
                             varden=varden, formats=formats)
    SmsFilmJob.objects.filter(pk=job.pk).update(status=status, output_asset=asset)
    SmsFilmOutput.objects.create(job=job, typ="video", format=fmt, bredd=1080, hojd=1920 if fmt == "9x16" else 1350,
                                 langd=duration, asset=asset)
    job.refresh_from_db()
    return job, asset


class SpecTests(TestCase):
    def setUp(self):
        self.user = user = get_user_model().objects.create_user(username="spec", password="test")
        self.company = Company.objects.create(owner=user, name="Spec AB")

    def test_slutmall_as_outro(self):
        job, asset = done_slutmall(self.company, self.user, duration=6.4)
        *_, base = spec.build({"messages": [{"side": "recv", "text": "Hej"}]}, {}, self.company)
        conv, _, saved, total = spec.build(
            {"messages": [{"side": "recv", "text": "Hej"}], "outro": True, "slutmall": str(job.pk)}, {}, self.company)
        self.assertEqual(conv["outro"], {"asset": str(asset.pk), "src": f"assets/outro/slutmall-{asset.pk}.mp4", "len": 6.4})
        self.assertEqual((saved["slutmall"], saved["outro"]), (str(job.pk), False))
        self.assertAlmostEqual(total, base + 6.4)
        self.assertEqual(spec.outro_len(conv), 6.4)

    def test_outro_len(self):
        self.assertEqual(spec.outro_len({"outro": "spotlight"}), spec.OUTRO_LEN)
        self.assertEqual(spec.outro_len({"outro": {"len": 5}}), 5)
        for conv in ({}, {"outro": None}, {"outro": {"len": -1}}, {"outro": {"len": "x"}}, {"outro": "annat"}):
            self.assertEqual(spec.outro_len(conv), 0, conv)

    def test_slutmall_outro_rejects_bad_choices(self):
        other_user = get_user_model().objects.create_user(username="annan", password="test")
        other = Company.objects.create(owner=other_user, name="Annat AB")
        wide, _ = done_slutmall(self.company, self.user, fmt="4x5")
        foreign, _ = done_slutmall(other, other_user)
        pending, _ = done_slutmall(self.company, self.user, status="queued")
        cases = {"inte-ett-id": "ogiltigt", str(wide.pk): "4:5", str(foreign.pk): "finns inte",
                 str(pending.pk): "finns inte"}
        for ref, message in cases.items():
            with self.assertRaisesMessage(spec.SmsFilmError, message, msg=ref):
                spec.build({"messages": [{"side": "recv", "text": "Hej"}], "slutmall": ref}, {}, self.company)

    def test_finished_slutmallar_and_serialize(self):
        done, _ = done_slutmall(self.company, self.user, fmt="4x5")
        done_slutmall(self.company, self.user, status="failed")
        listed = service.finished_slutmallar(self.company)
        self.assertEqual([j["id"] for j in listed], [str(done.pk)])
        self.assertEqual((listed[0]["format"], listed[0]["duration_s"]), ("4x5", 7.7))

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

    def test_embed_restricts_framing_and_preserves_access(self):
        url = reverse("engine:sms_film_embed", kwargs={"workspace_id": self.company.pk})
        response = self.client.get(url, HTTP_HOST="content.golfkuponger.se")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SMS-film")
        self.assertNotContains(response, "Huvudnavigation")
        self.assertEqual(response["Content-Security-Policy"], "frame-ancestors https://dashboard.golfkuponger.se")
        self.assertNotIn("X-Frame-Options", response)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertContains(response, url)
        self.assertEqual(self.client.get(self.url)["X-Frame-Options"], "DENY")
        other = get_user_model().objects.create_user(username="embed-other", password="test")
        self.client.force_login(other)
        self.assertEqual(self.client.get(url, HTTP_HOST="content.golfkuponger.se").status_code, 404)

    def test_embed_login_and_wrong_host(self):
        url = reverse("engine:sms_film_embed", kwargs={"workspace_id": self.company.pk})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        response = self.client.get(url, HTTP_HOST="content.golfkuponger.se")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logga in för att skapa SMS-film")
        self.assertContains(response, 'target="_blank"')
        self.assertEqual(response["Content-Security-Policy"], "frame-ancestors https://dashboard.golfkuponger.se")
        self.assertNotIn("X-Frame-Options", response)

    def test_embed_post_requires_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        url = reverse("engine:sms_film_embed", kwargs={"workspace_id": self.company.pk})
        args = {"HTTP_HOST": "content.golfkuponger.se", "HTTP_ORIGIN": "https://content.golfkuponger.se",
                "HTTP_ACCEPT": "application/json", "secure": True}
        self.assertEqual(client.post(url, {"form_json": "{}"}, **args).status_code, 403)
        client.get(url, **args)
        token = client.cookies["csrftoken"].value
        response = client.post(url, {"form_json": "{}"}, HTTP_X_CSRFTOKEN=token, **args)
        self.assertEqual(response.status_code, 400)

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

    def test_sms_job_with_slutmall_outro_gets_the_video(self):
        user = get_user_model().objects.get(username="w")
        slut, video = done_slutmall(self.company, user, duration=7.2)
        conv, ids, saved, total = spec.build({"messages": [{"side": "recv", "text": "Hej"}], "slutmall": str(slut.pk)},
                                             {}, self.company)
        job = service.create_job(self.company, user, title="Med slut", form=saved, conversation=conv,
                                 image_asset_ids=ids, duration_s=total, dispatch_now=False)
        payload = self.post("claim/", {"worker_id": "gh", "job_id": str(job.pk)}).json()["job"]
        self.assertEqual(payload["job_id"], str(job.pk))
        outro = payload["outro_asset"]
        self.assertEqual((outro["id"], outro["path"]), (str(video.pk), f"assets/outro/slutmall-{video.pk}.mp4"))
        got = self.client.get(outro["url"].replace("https://engine.test", ""), **self.auth,
                              HTTP_X_EDIT_LEASE=payload["lease"])
        self.assertEqual(got.status_code, 200)
        # The leased SMS job may fetch only its own slutmall, not other videos in the library.
        _, stranger = done_slutmall(self.company, user)
        other = self.client.get(f"/internal/sms-film/assets/{job.pk}/{stranger.pk}/", **self.auth,
                                HTTP_X_EDIT_LEASE=payload["lease"])
        self.assertEqual(other.status_code, 404)

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


class MallValideringTests(TestCase):
    """engine/smsfilm/mallar.py: the server checks a job's values against the template's mall.json."""

    def setUp(self):
        self.mall = mallar.hamta("golfkuponger-slutmallar")

    def test_defaults_are_frozen_and_follow_the_effect(self):
        varden, formats = mallar.validera(self.mall, {"mall": "epassi", "text2": " Det brinner *inne* ", "effekt": "studs"}, ["9x16"])
        self.assertEqual(formats, ["9x16"])
        self.assertEqual((varden["mall"], varden["text2"], varden["effekt"]), ("epassi", "Det brinner *inne*", "studs"))
        self.assertEqual((varden["text1"], varden["logga"], varden["bredd"], varden["skak"]), ("Friskvårdsbidrag kvar?", 100, 778, 40))
        varden, _ = mallar.validera(self.mall, {"text2": "x", "effekt": "tona"}, ["9x16", "4x5"])
        self.assertEqual(varden["skak"], 0)
        varden, _ = mallar.validera(self.mall, {"text2": "x", "effekt": "small", "skak": 0}, ["4x5"])
        self.assertEqual(varden["skak"], 0)   # "small" shakes by default, so 0 is a choice

    def test_rejects_what_mall_json_does_not_allow(self):
        fall = [({"text2": "x", "logga": 999}, ["9x16"]), ({"text2": "  "}, ["9x16"]), ({"text2": "x", "okand": 1}, ["9x16"]),
                ({"text2": "x", "text1": "a" * 41}, ["9x16"]), ({"text2": "x", "effekt": "explodera"}, ["9x16"]),
                ({"text2": "x", "mall": "okand"}, ["9x16"]), ({"text2": "x"}, ["16x9"]), ({"text2": "x"}, []),
                ({"text2": "x", "hojd": "mycket"}, ["9x16"]), (["text2", "x"], ["9x16"])]
        for raw, formats in fall:
            with self.assertRaises(spec.SmsFilmError, msg=(raw, formats)):
                mallar.validera(self.mall, raw, formats)

    def test_only_templates_with_a_mall_field_are_offered(self):
        ids = [m["id"] for m in mallar.for_formularet()]
        self.assertIn("golfkuponger-slutmallar", ids)
        self.assertNotIn("testmall", ids)
        with self.assertRaises(spec.SmsFilmError):
            mallar.hamta("testmall")

    def test_utdata_puts_9x16_first(self):
        self.assertEqual([u["format"] for u in mallar.utdata(self.mall, ["4x5", "9x16"])], ["9x16", "4x5"])

    def test_old_slutmall_jobs_are_migrated(self):
        import importlib

        from django.apps import apps

        migration = importlib.import_module("engine.migrations.0045_mallmotor")
        user = get_user_model().objects.create_user(username="mig", password="test")
        company = Company.objects.create(owner=user, name="Mig AB")
        asset = MediaAsset.objects.create(company=company, kind="video", storage_key="x/y.mp4", byte_size=1, sha256="0" * 64,
                                          mime_type="video/mp4")
        old = SmsFilmJob.objects.create(company=company, kind="slutmall", status="done", output_asset=asset, duration_s=3.1,
                                        form={"kind": "slutmall", "mall": "sp", "rad1": "", "rad2": "Hej", "effekt": "studs",
                                              "stil": {"logga": 130}})
        wide = SmsFilmJob.objects.create(company=company, kind="slutmall", status="failed",
                                         form={"mall": "alla", "rad2": "x", "format": "4x5"})
        migration.fyll_slutmallar(apps, None)
        old.refresh_from_db()
        wide.refresh_from_db()
        self.assertEqual((old.mall_id, old.formats, wide.formats), ("golfkuponger-slutmallar", ["9x16"], ["4x5"]))
        self.assertEqual({k: old.varden[k] for k in ("mall", "text1", "text2", "effekt", "logga", "skak", "bredd")},
                         {"mall": "sp", "text1": "", "text2": "Hej", "effekt": "studs", "logga": 130, "skak": 40, "bredd": 778})
        self.assertEqual(list(old.outputs.values_list("format", "typ", "asset_id")), [("9x16", "video", asset.pk)])
        self.assertFalse(wide.outputs.exists())
        # every frozen value is still valid against today's mall.json
        mallar.validera(mallar.hamta("golfkuponger-slutmallar"), old.varden, old.formats)
        migration.tom_slutmallar(apps, None)
        old.refresh_from_db()
        self.assertEqual((old.mall_id, old.varden), ("", {}))


@override_settings(APP_URL="https://engine.test")
@mock.patch.dict(os.environ, {"EDIT_WORKER_TOKEN": TOKEN, "GITHUB_DISPATCH_TOKEN": ""})
class SlutmallFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="s", password="test")
        self.company = Company.objects.create(owner=self.user, name="GK")
        self.client.force_login(self.user)
        self.url = reverse("engine:sms_film", kwargs={"workspace_id": self.company.pk})

    def create(self, form):
        return self.client.post(self.url, {"form_json": json.dumps(form)}, HTTP_ACCEPT="application/json")

    def test_page_offers_the_templates(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Generera video")
        self.assertContains(response, "mall-section")
        self.assertContains(response, 'value="mall:golfkuponger-slutmallar"')
        for text in ("Epassi", "Skrivmaskin", "Luft under loggan", "mall-data", "sm-klara-data"):
            self.assertContains(response, text)
        self.assertNotContains(response, "testmall")

    def test_finished_slutmall_is_listed_under_slut_and_reopens(self):
        job, asset = done_slutmall(self.company, self.user, duration=6.9)
        page = self.client.get(self.url)
        klara = json.loads(page.content.decode().split('id="sm-klara-data" type="application/json">', 1)[1].split("</script>", 1)[0])
        self.assertEqual([(j["id"], j["format"], j["duration_s"]) for j in klara], [(str(job.pk), "9x16", 6.9)])
        self.assertEqual(klara[0]["output_asset_id"], str(asset.pk))
        self.assertEqual([(o["format"], o["asset_id"]) for o in klara[0]["outputs"]], [("9x16", str(asset.pk))])
        response = self.create({"messages": [{"side": "recv", "text": "Hej"}], "slutmall": str(job.pk)})
        self.assertEqual(response.status_code, 201, response.content)
        film = SmsFilmJob.objects.get(kind="sms")
        self.assertEqual(film.form["slutmall"], str(job.pk))
        self.assertGreater(film.duration_s, 6.9)

    def test_4x5_slutmall_cannot_end_an_sms_film(self):
        job, _ = done_slutmall(self.company, self.user, fmt="4x5")
        response = self.create({"messages": [{"side": "recv", "text": "Hej"}], "slutmall": str(job.pk)})
        self.assertEqual(response.status_code, 400)
        self.assertIn("4:5", response.json()["error"])

    def test_old_preview_route_serves_only_the_spotlight_clip(self):
        url = lambda fil: reverse("engine:sms_film_slutmall", kwargs={"workspace_id": self.company.pk, "fil": fil})
        spotlight = self.client.get(url("spotlight-9x16.mp4"), HTTP_RANGE="bytes=0-15")
        self.assertEqual((spotlight.status_code, spotlight["Content-Type"]), (206, "video/mp4"))
        self.assertTrue(spotlight["Content-Range"].startswith("bytes 0-15/"))
        for bad in ("slutmall.html", "assets/anton.woff2", "render.mjs", "../views.py", "spotlight-4x5.mp4"):
            self.assertEqual(self.client.get(url(bad)).status_code, 404, bad)
        self.client.logout()
        self.assertEqual(self.client.get(url("spotlight-9x16.mp4")).status_code, 302)

    def test_mall_preview_serves_the_page_contract_files_only(self):
        url = lambda mall, fil: reverse("engine:sms_film_mall", kwargs={"workspace_id": self.company.pk, "mall": mall, "fil": fil})
        page = self.client.get(url("golfkuponger-slutmallar", "slutmall.html"))
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("X-Frame-Options", page)
        self.assertEqual(page["Content-Security-Policy"], "frame-ancestors 'self' https://dashboard.golfkuponger.se")
        for mall, fil, typ in (("golfkuponger-slutmallar", "mall.json", "application/json"),
                               ("golfkuponger-slutmallar", "assets/anton.woff2", "font/woff2"),
                               ("_mall", "sida.mjs", "text/javascript"), ("_mall", "safezones.js", "text/javascript")):
            response = self.client.get(url(mall, fil))
            self.assertEqual((response.status_code, response["Content-Type"]), (200, typ), fil)
        b"".join(self.client.get(url("_mall", "safezones.js")).streaming_content).decode().index("PLATFORM_ZONES")
        for mall, fil in (("golfkuponger-slutmallar", "render.mjs"), ("golfkuponger-slutmallar", "README.md"),
                          ("golfkuponger-slutmallar", "annan.html"), ("golfkuponger-slutmallar", "assets/../render.mjs"),
                          ("golfkuponger-slutmallar", "referens/9x16.png"), ("_mall", "render-bas.mjs"), ("_mall", "mall.schema.json"),
                          ("imessage-samtal", "mall.json"), ("..", "manage.py"), ("_mall", "../../manage.py")):
            self.assertEqual(self.client.get(url(mall, fil)).status_code, 404, f"{mall}/{fil}")
        self.client.logout()
        self.assertEqual(self.client.get(url("golfkuponger-slutmallar", "slutmall.html")).status_code, 302)

    def test_post_creates_slutmall_job_and_worker_payload(self):
        response = self.create({"kind": "mall", "mall": "golfkuponger-slutmallar", "format": ["9x16", "4x5"],
                                "varden": {"text1": "Friskvårdsbidrag kvar?", "text2": "Det brinner inne 31/12",
                                           "effekt": "studs", "logga": 130}})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["job"]["kind"], "slutmall")
        job = SmsFilmJob.objects.get()
        self.assertEqual((job.kind, job.title, job.mall_id, job.formats), ("slutmall", "Slutmall med svingloggan",
                                                                           "golfkuponger-slutmallar", ["9x16", "4x5"]))
        self.assertEqual((job.varden["logga"], job.varden["skak"]), (130, 40))
        auth = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}
        payload = self.client.post("/internal/sms-film/claim/", json.dumps({"worker_id": "gh"}),
                                   content_type="application/json", **auth).json()["job"]
        self.assertEqual(payload["kind"], "slutmall")
        self.assertEqual(payload["mall"]["id"], "golfkuponger-slutmallar")
        self.assertEqual([(u["typ"], u["format"]) for u in payload["mall"]["utdata"]], [("video", "9x16"), ("video", "4x5")])
        # a worker from before the multi-file protocol still gets the old shape
        self.assertEqual((payload["slutmall"]["rad2"], payload["slutmall"]["effekt"], payload["slutmall"]["stil"]["logga"]),
                         ("Det brinner inne 31/12", "studs", 130))
        self.assertNotIn("apple_pack_url", payload)
        self.assertEqual(payload["assets"], [])
        lease = {"HTTP_X_EDIT_LEASE": payload["lease"]}
        pack = self.client.get(f"/internal/sms-film/apple-pack/{job.pk}/", **auth, **lease)
        self.assertEqual(pack.status_code, 404)

        # multi-file protocol: one call per file, then klar/
        def fil(fmt, data=b"mp4-" , typ="video"):
            with mock.patch("engine.smsfilm.service.store_asset", side_effect=lambda c, d, **kw: MediaAsset.objects.create(
                    company=c, kind="video", storage_key=f"x/{len(d)}-{fmt}.mp4", byte_size=len(d), sha256="1" * 64,
                    mime_type="video/mp4")):
                return self.client.post(f"/internal/sms-film/fil/{job.pk}/", {
                    "file": SimpleUploadedFile("a.mp4", data + fmt.encode()),
                    "meta": json.dumps({"typ": typ, "format": fmt, "langd": 3.1})}, **auth, **lease)

        done = lambda: self.client.post(f"/internal/sms-film/klar/{job.pk}/", json.dumps({"duration_s": 3.1, "render_commit": "abc1234"}),
                                        content_type="application/json", **auth, **lease)
        self.assertEqual(fil("9x16").status_code, 200)
        self.assertEqual(done().status_code, 409)               # 4:5 has not arrived
        self.assertEqual(fil("1x1").status_code, 409)           # not one of the job's files
        self.assertEqual(fil("4x5", typ="bild").status_code, 409)
        self.assertEqual(fil("4x5").status_code, 200)
        self.assertEqual(fil("4x5", data=b"igen-").status_code, 200)   # a retry replaces the file
        self.assertEqual(done().status_code, 200)
        job.refresh_from_db()
        nio = job.outputs.get(format="9x16")
        self.assertEqual((job.status, job.output_asset_id, job.render_commit, job.outputs.count()), ("done", nio.asset_id, "abc1234", 2))
        reopen = self.client.get(self.url + f"?from={job.pk}")
        self.assertContains(reopen, "Det brinner inne 31/12")

    def test_bad_template_job_and_non_object_form(self):
        base = {"kind": "mall", "mall": "golfkuponger-slutmallar", "format": ["9x16"]}
        for form in ({**base, "varden": {"text2": ""}}, {**base, "varden": {"text2": "x", "logga": 999}},
                     {**base, "mall": "testmall", "varden": {}}, {**base, "format": [], "varden": {"text2": "x"}}):
            self.assertEqual(self.create(form).status_code, 400, form)
        self.assertEqual(self.create(["inte", "ett", "objekt"]).status_code, 400)
        self.assertFalse(SmsFilmJob.objects.exists())


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
