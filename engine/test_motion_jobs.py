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


    def test_preview_records_motion_provenance(self):
        spec = dict(self.spec)
        spec["scenes"] = [dict(spec["scenes"][0], motion_preset="snappy")]
        spec["beat_map"] = {
            "enabled": True,
            "bpm": 120.0,
            "offset_frames": 0,
            "beat_frames": [0, 15, 30, 45, 60, 75],
            "source": "manual",
        }
        p = self.service().create_project(
            self.company, self.user, title="Harness", spec=spec, key="harness-project"
        )
        job = self.service().queue_render(
            self.company, self.user, p.id, mode="preview", expected_revision=1, key="harness-preview"
        )
        motion = job.generation.parameters["motion"]
        self.assertEqual(motion["motion_presets"], ["snappy"])
        self.assertEqual(motion["beat_map"]["bpm"], 120.0)
        self.assertEqual(motion["aspect_ratio"], "9:16")

    def test_completed_preview_can_be_critic_improved_as_new_revision(self):
        p = self.project(key="critic-project")
        job = self.service().queue_render(
            self.company, self.user, p.id, mode="preview", expected_revision=1, key="critic-preview"
        )
        job.generation.status = "completed"
        job.generation.save(update_fields=["status"])
        try:
            report = self.service().critique_render(self.company, job.id)
        except AttributeError as exc:
            self.fail(f"Motion service must expose critique_render: {exc}")
        self.assertTrue(report["visual_review_required"])

        try:
            improved = self.service().improve_from_critique(
                self.company,
                self.user,
                job.id,
                expected_revision=1,
                key="critic-improve",
            )
        except AttributeError as exc:
            self.fail(f"Motion service must expose improve_from_critique: {exc}")
        improved.refresh_from_db()
        self.assertEqual(improved.current_revision, 2)
        old = improved.revisions.get(number=1).spec
        new = improved.revisions.get(number=2).spec
        self.assertEqual(old["scenes"][0]["props"], new["scenes"][0]["props"])
        self.assertNotEqual(old["scenes"][0].get("motion_preset", "legacy"), new["scenes"][0]["motion_preset"])


    def test_mcp_registers_critic_read_and_safe_fix_tools(self):
        from engine.motion import mcp as motion_mcp

        class FakeMCP:
            def __init__(self):
                self.titles = []

            def tool(self, **kwargs):
                self.titles.append(kwargs.get("title"))
                return lambda fn: fn

        fake = FakeMCP()
        motion_mcp.register(
            fake,
            company_for=lambda ref: self.company,
            run_for=lambda company_ref, run_id: None,
            user_for=lambda: self.user,
            safe_call=lambda fn, *args, **kwargs: fn(*args, **kwargs),
        )
        self.assertIn("Critique motion preview", fake.titles)
        self.assertIn("Improve motion from critic", fake.titles)
