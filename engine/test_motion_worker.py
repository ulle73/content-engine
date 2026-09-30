"""Real bytes/storage and HTTP checks; no mocked renderer or storage success."""

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from engine.models import Company, MediaAsset
from engine.motion import service
from engine.motion.jobs import claim_job

TOKEN = "isolated-motion-worker-token-0123456789"


class MotionWorkerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp = tempfile.TemporaryDirectory()
        filename = Path(cls.tmp.name) / "fixture.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=c=green:s=360x640:r=30",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=44100",
                "-t",
                "1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(filename),
            ],
            check=True,
        )
        cls.video = filename.read_bytes()
        image = Image.new("RGB", (360, 640), "green")
        out = io.BytesIO()
        image.save(out, "PNG")
        cls.png = out.getvalue()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.env = patch.dict(
            os.environ, {"MOTION_WORKER_TOKEN": TOKEN, "MEDIA_STORAGE": "local", "MOTION_WORKER_URL": ""}
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.storage = override_settings(MEDIA_ROOT=Path(self.tmp.name) / "media")
        self.storage.enable()
        self.addCleanup(self.storage.disable)
        self.user = get_user_model().objects.create_user(username="worker-owner", password="test")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger")
        self.spec = {
            "template_id": "custom-storyboard",
            "scenes": [{"id": "intro", "component": "hero", "duration_frames": 30, "props": {"headline": "Test"}}],
        }
        self.project = service.create_project(
            self.company, self.user, title="Test", spec=self.spec, key="worker-project"
        )
        self.job = service.queue_render(
            self.company, self.user, self.project.id, mode="preview", expected_revision=1, key="worker-preview"
        )
        self.claimed = claim_job()

    def post(self, action, data=None):
        return self.client.post(
            "/internal/motion/" + action + "/",
            data=json.dumps(data or {}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer " + TOKEN,
        )

    def test_worker_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("engine.motion.worker_api"), "Worker API is not implemented")

    def test_unauthenticated_request_cannot_claim(self):
        self.assertEqual(self.client.post("/internal/motion/claim/").status_code, 401)
        self.assertEqual(
            self.client.post("/internal/motion/claim/", HTTP_AUTHORIZATION="Bearer wrong").status_code, 401
        )

    def test_input_manifest_contains_only_revision_assets(self):
        from engine.motion.outputs import manifest

        data = manifest(self.claimed)
        self.assertEqual(data["render_id"], str(self.job.id))
        self.assertEqual(data["assets"], [])
        self.assertNotIn("storage_key", json.dumps(data))
        self.assertNotIn("owner", data)
        self.assertEqual(data["spec_hash"], self.claimed.revision.spec_hash)

    def test_completed_preview_reuses_real_assets_on_retry(self):
        from engine.motion.outputs import save_keyframe, save_output

        frame = save_keyframe(self.job.id, self.claimed.lease_token, "intro", 21, self.png)
        again = save_keyframe(self.job.id, self.claimed.lease_token, "intro", 21, self.png)
        self.assertEqual(frame.id, again.id)
        asset = save_output(self.job.id, self.claimed.lease_token, self.video)
        self.assertEqual(asset.id, save_output(self.job.id, self.claimed.lease_token, self.video).id)
        self.job.refresh_from_db()
        self.job.generation.refresh_from_db()
        self.assertEqual(self.job.generation.status, "completed")
        self.assertEqual(self.job.storyboard.count(), 1)
        self.assertEqual(asset.company, self.company)
        self.assertEqual(asset.provider, "remotion")
        self.assertEqual(asset.sha256, hashlib.sha256(self.video).hexdigest())
        self.assertIsNone(asset.expires_at)
        self.assertEqual(MediaAsset.objects.count(), 2)
        service.approve_preview(self.company, self.user, self.project.id, render_id=self.job.id, expected_revision=1)
        self.project.refresh_from_db()
        self.assertEqual(self.project.approved_preview_id, self.job.id)

    def test_preview_requires_all_storyboard_frames(self):
        from engine.motion.outputs import save_output

        with self.assertRaises(ValueError):
            save_output(self.job.id, self.claimed.lease_token, self.video)
        self.assertEqual(MediaAsset.objects.count(), 0)

    def test_keyframe_exact_scene_and_frame_are_enforced(self):
        from engine.motion.outputs import save_keyframe

        for scene, frame in [("nonexistent", 21), ("intro", 0), ("intro", 22)]:
            with self.subTest(scene=scene, frame=frame), self.assertRaises(ValueError):
                save_keyframe(self.job.id, self.claimed.lease_token, scene, frame, self.png)

    def test_output_quality_rejects_wrong_timing_and_dimensions(self):
        from engine.motion.outputs import validate_output

        bad = dict(self.claimed.revision.spec)
        bad["aspect_ratio"] = "16:9"
        with self.assertRaises(ValueError):
            validate_output(self.video, bad, "preview")
        bad = json.loads(json.dumps(self.claimed.revision.spec))
        bad["scenes"][0]["duration_frames"] = 60
        with self.assertRaises(ValueError):
            validate_output(self.video, bad, "preview")
        with self.assertRaises(ValueError):
            validate_output(b"not video", bad, "preview")

    def test_canceled_worker_cannot_store_or_heartbeat(self):
        from engine.motion.outputs import save_keyframe

        service.cancel_render(self.company, self.job.id)
        with self.assertRaises(ValueError):
            save_keyframe(self.job.id, self.claimed.lease_token, "intro", 21, self.png)
        response = self.post(
            "heartbeat", {"render_id": str(self.job.id), "lease": str(self.claimed.lease_token), "progress": 0.5}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(MediaAsset.objects.count(), 0)

    def test_active_motion_job_is_not_sent_to_higgsfield(self):
        from engine.media import advance_job

        result = advance_job(self.job.generation)
        self.assertEqual(result.status, "running")
        self.assertEqual(result.provider, "remotion")
        self.assertEqual(result.provider_id, "")

    def test_motion_reference_prevents_physical_deletion(self):
        from engine.motion.outputs import save_keyframe
        from engine.media import remove_asset
        from engine.media_storage import MediaError, open_asset

        asset = save_keyframe(self.job.id, self.claimed.lease_token, "intro", 21, self.png)
        with self.assertRaises(MediaError):
            remove_asset(asset)
        with open_asset(asset) as f:
            self.assertEqual(f.read(), self.png)

    def test_worker_asset_access_is_job_scoped(self):
        from engine.media import store_asset

        asset = store_asset(self.company, self.png)
        response = self.client.get(
            f"/internal/motion/assets/{self.job.id}/{asset.id}/",
            HTTP_AUTHORIZATION="Bearer " + TOKEN,
            HTTP_X_MOTION_LEASE=str(self.claimed.lease_token),
        )
        self.assertEqual(response.status_code, 404)

    def test_multipart_keyframe_endpoint(self):
        response = self.client.post(
            f"/internal/motion/keyframe/{self.job.id}/",
            {"file": SimpleUploadedFile("frame.png", self.png, "image/png"), "scene_id": "intro", "frame": "21"},
            HTTP_AUTHORIZATION="Bearer " + TOKEN,
            HTTP_X_MOTION_LEASE=str(self.claimed.lease_token),
        )
        self.assertEqual(response.status_code, 200, response.content[:500])
        self.assertEqual(response.json()["kind"], "image")
