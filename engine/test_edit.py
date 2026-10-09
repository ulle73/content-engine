import io
import json
import uuid
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import av
import httpx
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from .edit import service
from .edit import spec as cut_spec
from .edit.models import EditJob
from .media import store_asset
from .models import Company, MediaAsset
from .review.models import Review

TOKEN = "w" * 40
AUTH = {"HTTP_AUTHORIZATION": "Bearer " + TOKEN}


def movie(seconds=1.0, size=(64, 96)):
    out = io.BytesIO()
    with av.open(out, mode="w", format="mp4") as container:
        stream = container.add_stream("libx264", rate=10)
        stream.width, stream.height, stream.pix_fmt = size[0], size[1], "yuv420p"
        for _ in range(max(1, int(seconds * 10))):
            for packet in stream.encode(av.VideoFrame.from_image(Image.new("RGB", size, "green"))):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return out.getvalue()


def picture():
    out = io.BytesIO()
    Image.new("RGB", (96, 160), "navy").save(out, "PNG")
    return out.getvalue()


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True, APP_URL="http://127.0.0.1:8765")
class EditTestCase(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        override = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        override.enable()
        self.addCleanup(override.disable)
        env = mock.patch.dict("os.environ", {"EDIT_WORKER_TOKEN": TOKEN}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        for name in ("GITHUB_DISPATCH_TOKEN", "CONTENT_N8N_DISCORD_URL", "CONTENT_N8N_SECRET"):
            patcher = mock.patch.dict("os.environ", {name: ""})
            patcher.start()
            self.addCleanup(patcher.stop)
        self.user = get_user_model().objects.create_user("editor", password="x")
        self.company = Company.objects.create(owner=self.user, name="FAIV", review_channel_id="555",
                                              brand={"background": "#0b0b0d", "accent": "#f2a900"})
        self.other = Company.objects.create(owner=self.user, name="Annat bolag")
        self.clip = store_asset(self.company, movie(3.0))
        self.still = store_asset(self.company, picture())
        self.foreign = store_asset(self.other, picture())
        self.music = MediaAsset.objects.create(company=self.company, kind="audio", origin="uploaded", provider="user",
                                               storage_backend="local", storage_key="x/music.wav", mime_type="audio/wav",
                                               byte_size=10, duration_seconds=30)

    def spec(self, **changes):
        data = {
            "schema": "cut/v1", "format": "9:16", "fps": 30, "title": "Grillkit i mörkret", "caption": "Nu finns det.",
            "recipe_id": "faiv-dark-to-light-reveal", "brand": "faiv",
            "scenes": [
                {"id": "s1", "purpose": "hook", "duration_s": 2.0, "asset_id": str(self.clip.pk), "trim_start_s": 0.5,
                 "fit": "cover", "text": "Mörkt *ute?*", "text_style": "hyperframes.registry.headline-slam",
                 "effects": ["hyperframes.registry.vignette", "hyperframes.registry.confetti", "no.such.effect"],
                 "transition_in": None},
                {"id": "s2", "purpose": "product", "duration_s": 3.0, "asset_id": str(self.still.pk),
                 "text": "Grillkit", "text_style": None, "effects": ["nextphase.persa.grade"],
                 "transition_in": "hyperframes.registry.flash-through-white"},
            ],
            "music_asset_id": str(self.music.pk),
            "cta": {"text": "Beställ idag", "url": "https://faiv.se"},
        }
        data.update(changes)
        return data


class CutSpecTests(EditTestCase):
    def test_valid_spec_is_normalized_with_warnings_for_unsupported_ids(self):
        spec, warnings = cut_spec.validate(self.company, self.spec())
        self.assertEqual(spec["duration_s"], 7.5)
        self.assertEqual(spec["brand"], "faiv")
        self.assertEqual(spec["scenes"][0]["asset_kind"], "video")
        self.assertEqual(spec["scenes"][1]["fit"], "cover")
        self.assertEqual(spec["cta"]["duration_s"], 2.5)
        joined = "\n".join(warnings)
        self.assertIn("hyperframes.registry.confetti stöds inte av klippmallen", joined)
        self.assertIn("no.such.effect finns inte i biblioteket", joined)
        self.assertIn("faiv-dark-to-light-reveal finns inte i library/recipes", joined)
        self.assertEqual(cut_spec.resolve("transitions", "hyperframes.registry.flash-through-white"), "flash")
        self.assertEqual(cut_spec.resolve("effects", "cut.effect.dark-to-light"), "dark-to-light")

    def assertInvalid(self, message, **changes):
        with self.assertRaisesRegex(cut_spec.CutSpecError, message):
            cut_spec.validate(self.company, self.spec(**changes))

    def test_strict_errors_in_swedish(self):
        self.assertInvalid("schema ska vara", schema="cut/v2")
        self.assertInvalid("format ska vara", format="21:9")
        self.assertInvalid("okänt fält extra", extra=1)
        self.assertInvalid("brand \"golfkuponger\" hör inte till FAIV", brand="golfkuponger")
        self.assertInvalid("title saknas", title=" ")
        scenes = self.spec()["scenes"]
        self.assertInvalid("finns inte i bolagets mediabank", scenes=[{**scenes[0], "asset_id": str(self.foreign.pk)}])
        self.assertInvalid("klippet är 3.0 s långt", scenes=[{**scenes[0], "trim_start_s": 2.0}])
        self.assertInvalid("trim_start_s gäller bara video", scenes=[{**scenes[1], "trim_start_s": 1}])
        self.assertInvalid("okänt fält speed", scenes=[{**scenes[1], "speed": 2}])
        self.assertInvalid("id ska vara unikt", scenes=[scenes[1], {**scenes[1]}])
        self.assertInvalid("här krävs ljud", music_asset_id=str(self.still.pk))
        long = [{**scenes[1], "id": f"s{i}", "duration_s": 20} for i in range(5)]
        self.assertInvalid("Max är 90 s", scenes=long)
        self.assertInvalid("cta.url ska börja med https", cta={"text": "Köp", "url": "faiv.se"})


class DispatchAndLimitTests(EditTestCase):
    def test_dispatch_calls_github_workflow_dispatch(self):
        job = service.create_job(self.company, self.spec(), dispatch_now=False)
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["auth"] = request.headers["Authorization"]
            seen["body"] = json.loads(request.content)
            return httpx.Response(204)

        env = {"GITHUB_DISPATCH_TOKEN": "ghp_test", "GITHUB_REPOSITORY": "ulle73/content-engine"}
        with mock.patch.dict("os.environ", env):
            self.assertTrue(service.dispatch(job, client=httpx.Client(transport=httpx.MockTransport(handler))))
        self.assertEqual(seen["url"],
                         "https://api.github.com/repos/ulle73/content-engine/actions/workflows/edit-render.yml/dispatches")
        self.assertEqual(seen["auth"], "Bearer ghp_test")
        self.assertEqual(seen["body"], {"ref": "main", "inputs": {"job_id": str(job.pk)}})
        job.refresh_from_db()
        self.assertIsNotNone(job.dispatched_at)
        self.assertEqual(job.status, "queued")

    def test_dispatch_failures_never_crash_and_keep_job_queued(self):
        job = service.create_job(self.company, self.spec())  # no token configured
        self.assertIn("GITHUB_DISPATCH_TOKEN saknas", job.dispatch_error)
        self.assertEqual(job.status, "queued")

        def broken(request):
            raise httpx.ConnectError("down")

        with mock.patch.dict("os.environ", {"GITHUB_DISPATCH_TOKEN": "ghp_test"}):
            self.assertFalse(service.dispatch(job, client=httpx.Client(transport=httpx.MockTransport(broken))))
            self.assertFalse(service.dispatch(job, client=httpx.Client(
                transport=httpx.MockTransport(lambda r: httpx.Response(404)))))
        job.refresh_from_db()
        self.assertIn("404", job.dispatch_error)
        self.assertIsNone(job.dispatched_at)

    def test_rate_limit_active_jobs_per_company(self):
        for _ in range(3):
            service.create_job(self.company, self.spec())
        with self.assertRaisesRegex(service.EditError, "redan 3 klippjobb"):
            service.create_job(self.company, self.spec())
        EditJob.objects.filter(company=self.company).update(status="done")
        service.create_job(self.company, self.spec())
        with mock.patch.dict("os.environ", {"EDIT_MAX_JOBS_PER_DAY": "4"}):
            EditJob.objects.filter(company=self.company).update(status="done")
            with self.assertRaisesRegex(service.EditError, "per dygn"):
                service.create_job(self.company, self.spec())


class WorkerApiTests(EditTestCase):
    def post(self, path, data=None, **extra):
        return self.client.post(f"/internal/edit/{path}", json.dumps(data or {}), content_type="application/json",
                                **{**AUTH, **extra})

    def claimed(self):
        job = service.create_job(self.company, self.spec())
        payload = self.post("claim/", {"worker_id": str(uuid.uuid4()), "job_id": str(job.pk)}).json()["job"]
        return job, payload

    def test_auth_required(self):
        self.assertEqual(self.client.post("/internal/edit/claim/", "{}", content_type="application/json").status_code, 401)
        bad = self.client.post("/internal/edit/claim/", "{}", content_type="application/json",
                               HTTP_AUTHORIZATION="Bearer " + "x" * 40)
        self.assertEqual(bad.status_code, 401)
        with mock.patch.dict("os.environ", {"EDIT_WORKER_TOKEN": "short"}):
            self.assertEqual(self.client.post("/internal/edit/claim/", "{}", content_type="application/json",
                                              HTTP_AUTHORIZATION="Bearer short").status_code, 401)
        self.assertEqual(self.client.get("/internal/edit/claim/", **AUTH).status_code, 405)

    def test_claim_returns_spec_brand_and_authorized_asset_urls(self):
        self.assertIsNone(self.post("claim/").json()["job"])
        job, payload = self.claimed()
        self.assertEqual(payload["job_id"], str(job.pk))
        self.assertEqual(payload["spec"]["title"], "Grillkit i mörkret")
        self.assertEqual(payload["brand"]["accent"], "#f2a900")
        self.assertEqual(payload["brand"]["name"], "FAIV")
        self.assertEqual({a["id"] for a in payload["assets"]}, {str(self.clip.pk), str(self.still.pk), str(self.music.pk)})
        clip = next(a for a in payload["assets"] if a["id"] == str(self.clip.pk))
        self.assertTrue(clip["url"].endswith(f"/internal/edit/assets/{job.pk}/{self.clip.pk}/"))
        self.assertIsNone(clip["download_url"])
        job.refresh_from_db()
        self.assertEqual((job.status, job.attempts), ("claimed", 1))
        self.assertIsNone(self.post("claim/").json()["job"])  # nothing else queued

        lease = {"HTTP_X_EDIT_LEASE": payload["lease"]}
        response = self.client.get(f"/internal/edit/assets/{job.pk}/{self.clip.pk}/", **AUTH, **lease)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content)[4:8], b"ftyp")
        self.assertEqual(self.client.get(f"/internal/edit/assets/{job.pk}/{self.foreign.pk}/", **AUTH, **lease).status_code, 404)
        wrong = self.client.get(f"/internal/edit/assets/{job.pk}/{self.clip.pk}/", **AUTH, HTTP_X_EDIT_LEASE=str(uuid.uuid4()))
        self.assertEqual(wrong.status_code, 409)

    def test_heartbeat_marks_rendering_and_extends_lease(self):
        job, payload = self.claimed()
        before = EditJob.objects.get(pk=job.pk).lease_expires_at
        response = self.post("heartbeat/", {"job_id": payload["job_id"], "lease": payload["lease"], "progress": 0.4,
                                            "stage": "rendering"})
        self.assertEqual(response.json()["status"], "rendering")
        job.refresh_from_db()
        self.assertEqual(job.progress, 0.4)
        self.assertGreaterEqual(job.lease_expires_at, before)
        self.assertEqual(self.post("heartbeat/", {"job_id": payload["job_id"], "lease": str(uuid.uuid4())}).status_code, 409)

    def upload(self, job, payload, **files):
        files.setdefault("file", SimpleUploadedFile("master.mp4", movie(2.0), "video/mp4"))
        data = {"warnings": json.dumps(["Effekten x hoppades över."]), "meta": json.dumps({"duration_s": 7.5}), **files}
        return self.client.post(f"/internal/edit/output/{job.pk}/", data, HTTP_X_EDIT_LEASE=payload["lease"], **AUTH)

    def test_output_stores_video_creates_review_and_posts_to_discord(self):
        job, payload = self.claimed()
        with mock.patch("engine.review.discord.send") as send:
            send.side_effect = lambda review: Review.objects.filter(pk=review.pk).update(discord_message_id="42")
            response = self.upload(job, payload)
        self.assertEqual(response.status_code, 200, response.content)
        job.refresh_from_db()
        self.assertEqual(job.status, "done")
        self.assertEqual(job.output_asset.kind, "video")
        self.assertEqual(job.output_asset.provider, "hyperframes")
        self.assertIn("Effekten x hoppades över.", job.warnings)
        review = job.review
        self.assertEqual(review.asset_id, job.output_asset_id)
        self.assertEqual(review.title, "Grillkit i mörkret")
        send.assert_called_once()
        self.assertEqual(send.call_args.args[0].pk, review.pk)
        manifest = send.call_args.args[0].manifest
        self.assertEqual(manifest["duration_s"], 7.5)
        self.assertEqual([s["id"] for s in manifest["scenes"]], ["s1", "s2", "cta"])
        self.assertEqual((manifest["scenes"][1]["start"], manifest["scenes"][1]["end"]), (2.0, 5.0))
        s1 = {i["id"]: i for i in manifest["scenes"][0]["items"]}
        self.assertEqual(s1["hyperframes.registry.headline-slam"]["type"], "text")
        self.assertEqual(s1["hyperframes.registry.vignette"]["type"], "effect")
        self.assertEqual(s1[str(self.clip.pk)]["type"], "asset")
        s2 = {i["id"]: i for i in manifest["scenes"][1]["items"]}
        self.assertEqual(s2["hyperframes.registry.flash-through-white"]["type"], "transition")
        self.assertEqual(s2["nextphase.persa.grade"]["type"], "grade")
        globals_ = {i["id"]: i["type"] for i in manifest["global"]}
        self.assertEqual(globals_["faiv-dark-to-light-reveal"], "template")
        self.assertEqual(globals_[str(self.music.pk)], "music")
        self.assertEqual(self.upload(job, payload).status_code, 409)  # lease is gone once done

    def test_preview_becomes_review_asset_and_master_is_kept(self):
        job, payload = self.claimed()
        with mock.patch("engine.review.discord.send"):
            response = self.upload(job, payload, preview=SimpleUploadedFile("preview.mp4", movie(1.0), "video/mp4"))
        self.assertEqual(response.status_code, 200, response.content)
        job.refresh_from_db()
        self.assertEqual(job.review.asset_id, job.preview_asset_id)
        self.assertNotEqual(job.output_asset_id, job.preview_asset_id)
        self.assertEqual(job.review.edit_jobs.get().output_asset_id, job.output_asset_id)

    def test_discord_failure_keeps_job_done_and_recover_retries(self):
        from .review.service import ReviewError

        job, payload = self.claimed()
        with mock.patch("engine.review.discord.send", side_effect=ReviewError("Discord-kopplingen är inte konfigurerad")):
            self.assertEqual(self.upload(job, payload).status_code, 200)
        job.refresh_from_db()
        self.assertEqual(job.status, "done")
        self.assertIn("Discord", job.discord_error)
        self.assertEqual(job.review.status, "pending")
        self.assertIn("görs om automatiskt", service.serialize(job)["next_step"])
        with mock.patch("engine.review.discord.send") as send:
            send.side_effect = lambda review: Review.objects.filter(pk=review.pk).update(discord_message_id="77")
            self.assertEqual(service.recover(redispatch=False)["discord"], 1)
        job.refresh_from_db()
        self.assertEqual(job.discord_error, "")
        self.assertTrue(service.serialize(job)["discord_posted"])

    def test_failed_retryable_requeues_then_fails(self):
        job, payload = self.claimed()
        response = self.post("failed/", {"job_id": payload["job_id"], "lease": payload["lease"], "code": "render_failed",
                                         "detail": "Chrome kraschade", "retryable": True})
        self.assertEqual(response.json()["status"], "queued")
        payload = self.post("claim/").json()["job"]
        response = self.post("failed/", {"job_id": payload["job_id"], "lease": payload["lease"], "code": "bogus"})
        self.assertEqual(response.json()["status"], "failed")
        job.refresh_from_db()
        self.assertEqual(job.error, "Videon kunde inte renderas.")
        self.assertEqual(job.attempts, 2)


class RecoveryAndMcpTests(EditTestCase):
    def test_recover_requeues_stale_leases_and_fails_after_three_attempts(self):
        job = service.create_job(self.company, self.spec())
        service.claim()
        EditJob.objects.filter(pk=job.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(service.recover(send_discord=False, redispatch=False)["requeued"], 1)
        job.refresh_from_db()
        self.assertEqual((job.status, job.lease_token), ("queued", None))
        EditJob.objects.filter(pk=job.pk).update(status="rendering", attempts=3,
                                                 lease_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(service.recover(send_discord=False, redispatch=False)["failed"], 1)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIn("tre gånger", job.error)

    def test_recover_redispatches_queued_jobs_once(self):
        service.create_job(self.company, self.spec())
        service.create_job(self.company, self.spec())
        with mock.patch.object(service, "dispatch", return_value=True) as dispatch:
            self.assertEqual(service.recover(send_discord=False)["dispatched"], 1)
        dispatch.assert_called_once()

    def test_mcp_tools_are_registered_and_create_jobs(self):
        from types import SimpleNamespace

        from asgiref.sync import async_to_sync

        from engine import mcp_server

        tools = {tool.name: tool for tool in async_to_sync(mcp_server.mcp.list_tools)()}
        self.assertIn("render_cut", tools)
        self.assertTrue(tools["get_cut_job"].annotations.read_only_hint)

        def registered(name):
            return mcp_server.mcp._tool_manager.get_tool(name).fn

        token = SimpleNamespace(claims={"django_user_id": self.user.pk})
        with mock.patch("engine.mcp_auth.get_access_token", return_value=token):
            created = registered("render_cut")(str(self.company.pk), self.spec())
            self.assertEqual(created["status"], "queued")
            self.assertTrue(created["warnings"])
            fetched = registered("get_cut_job")(str(self.company.pk), created["job_id"])
            self.assertEqual(fetched["job_id"], created["job_id"])
            from mcp.server.mcpserver.exceptions import ToolError

            with self.assertRaises(ToolError):
                registered("render_cut")(str(self.company.pk), self.spec(schema="x"))
