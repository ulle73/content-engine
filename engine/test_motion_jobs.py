from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from engine.models import Company
from engine import test_motion_schema as fixture_module


class MotionJobTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="motion", password="test")
        self.other = get_user_model().objects.create_user(username="other", password="test")
        self.company = Company.objects.create(owner=self.user, name="Golfkuponger")
        self.other_company = Company.objects.create(owner=self.other, name="Other")
        self.spec = fixture_module.MotionContractTests().spec()

    def service(self):
        from engine.motion import service

        return service

    def project(self, key="project-create-1"):
        return self.service().create_project(self.company, self.user, title="September", spec=self.spec, key=key)

    def test_service_exists(self):
        import importlib.util

        self.assertIsNotNone(importlib.util.find_spec("engine.motion.service"), "durable motion services missing")

    def test_create_is_idempotent(self):
        a = self.project()
        b = self.project()
        self.assertEqual(a.id, b.id)
        self.assertEqual(a.run.workspace_id, self.company.id)
        self.assertEqual(a.revisions.count(), 1)

    def test_idempotency_payload_conflict(self):
        self.project()
        with self.assertRaises(ValueError):
            self.service().create_project(
                self.company, self.user, title="Changed", spec=self.spec, key="project-create-1"
            )

    def test_owner_and_company_isolation(self):
        p = self.project()
        with self.assertRaises(ValueError):
            self.service().get_project(self.other_company, str(p.id))
        with self.assertRaises(ValueError):
            self.service().create_project(self.company, self.other, title="X", spec=self.spec, key="denied-create-1")

    def test_immutable_revision_and_optimistic_lock(self):
        p = self.project()
        old = p.revisions.get(number=1)
        data = dict(self.spec, seed=43)
        p = self.service().update_project(
            self.company, self.user, p.id, spec=data, expected_revision=1, key="update-project-1"
        )
        self.assertEqual(p.current_revision, 2)
        old.refresh_from_db()
        self.assertEqual(old.spec["seed"], 42)
        with self.assertRaises(ValueError):
            self.service().update_project(
                self.company, self.user, p.id, spec=data, expected_revision=1, key="update-project-2"
            )

    def test_final_requires_same_revision_preview(self):
        p = self.project()
        with self.assertRaises(ValueError):
            self.service().queue_render(
                self.company, self.user, p.id, mode="final", expected_revision=1, key="final-render-1"
            )

    def test_preview_queue_and_claim(self):
        p = self.project()
        a = self.service().queue_render(
            self.company, self.user, p.id, mode="preview", expected_revision=1, key="preview-render-1"
        )
        b = self.service().queue_render(
            self.company, self.user, p.id, mode="preview", expected_revision=1, key="preview-render-1"
        )
        self.assertEqual(a.id, b.id)
        from engine.motion.jobs import claim_job

        job = claim_job()
        self.assertEqual(job.id, a.id)
        self.assertEqual(job.generation.status, "running")
        self.assertIsNone(claim_job())

    def test_cancel_fences_worker(self):
        p = self.project()
        s = self.service()
        job = s.queue_render(self.company, self.user, p.id, mode="preview", expected_revision=1, key="preview-render-1")
        from engine.motion.jobs import claim_job, heartbeat

        leased = claim_job()
        token = leased.lease_token
        s.cancel_render(self.company, job.id)
        with self.assertRaises(ValueError):
            heartbeat(job.id, token, 0.5)
        job.refresh_from_db()
        self.assertEqual(job.generation.status, "canceled")

    def test_expired_lease_retries_and_fences_stale_token(self):
        p = self.project()
        self.service().queue_render(
            self.company, self.user, p.id, mode="preview", expected_revision=1, key="preview-render-1"
        )
        from engine.motion.jobs import claim_job, heartbeat

        first = claim_job()
        old_token = first.lease_token
        type(first).objects.filter(id=first.id).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        second = claim_job()
        self.assertEqual(first.id, second.id)
        self.assertNotEqual(old_token, second.lease_token)
        self.assertEqual(second.attempts, 2)
        with self.assertRaises(ValueError):
            heartbeat(second.id, old_token, 0.5)

    def test_active_render_deduplicated_even_with_new_key(self):
        p = self.project()
        s = self.service()
        a = s.queue_render(self.company, self.user, p.id, mode="preview", expected_revision=1, key="preview-render-1")
        b = s.queue_render(self.company, self.user, p.id, mode="preview", expected_revision=1, key="preview-render-2")
        self.assertEqual(a.id, b.id)

    def test_retry_budget_exhausted(self):
        p = self.project()
        self.service().queue_render(
            self.company, self.user, p.id, mode="preview", expected_revision=1, key="preview-render-1"
        )
        from engine.motion.jobs import claim_job

        for _ in range(3):
            job = claim_job()
            type(job).objects.filter(id=job.id).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(claim_job())
        job.refresh_from_db()
        self.assertEqual(job.generation.status, "failed")
