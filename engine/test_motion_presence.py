import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from engine.motion.jobs import worker_available
from engine.motion.models import MotionWorkerSession


class MotionPresenceTests(TestCase):
    def setUp(self):
        self.token = "local-pull-worker-test-token-0123456789"
        self.environment = patch.dict("os.environ", {
            "MOTION_WORKER_TOKEN": self.token, "MOTION_WORKER_MODE": "pull", "MOTION_WORKER_URL": "",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def post(self, route, data, authenticated=True):
        return self.client.post(
            "/internal/motion/" + route, data, content_type="application/json",
            HTTP_AUTHORIZATION="Bearer " + (self.token if authenticated else "wrong"),
        )

    def test_only_authenticated_worker_can_enable_pull_rendering_and_disconnect(self):
        worker = str(uuid.uuid4())
        self.assertFalse(worker_available())
        self.assertEqual(self.post("claim/", {"worker_id": worker}, False).status_code, 401)
        self.assertFalse(worker_available())
        self.assertEqual(self.post("claim/", {"worker_id": worker}).status_code, 200)
        self.assertTrue(worker_available())
        self.assertEqual(self.post("disconnect/", {"worker_id": worker}).status_code, 200)
        self.assertFalse(worker_available())

    def test_crashed_worker_expires_and_invalid_identity_cannot_enable_rendering(self):
        worker = uuid.uuid4()
        MotionWorkerSession.objects.create(id=worker, expires_at=timezone.now() - timedelta(seconds=1))
        self.assertFalse(worker_available())
        self.assertEqual(self.post("claim/", {"worker_id": "invalid"}).status_code, 409)
        self.assertFalse(worker_available())
        self.post("claim/", {"worker_id": str(uuid.uuid4())})
        self.assertEqual(MotionWorkerSession.objects.count(), 1)

    def test_presence_without_credentials_does_not_enable_rendering(self):
        MotionWorkerSession.objects.create(id=uuid.uuid4(), expires_at=timezone.now() + timedelta(seconds=90))
        with patch.dict("os.environ", {"MOTION_WORKER_TOKEN": ""}):
            self.assertFalse(worker_available())
