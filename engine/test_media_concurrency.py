"""Real independent PostgreSQL transactions, also run by the existing CI job."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from . import test_media as fixtures
from .media import advance_job, create_job
from .models import ContentRun, MediaGeneration


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True)
@skipUnlessDBFeature("has_select_for_update")
class MediaConcurrencyTests(TransactionTestCase):
    setUp = fixtures.MediaTests.setUp

    def parallel(self, operation):
        barrier = Barrier(2)
        def worker(_):
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, range(2)))

    def test_concurrent_create_keeps_one_active_job_per_run(self):
        def create():
            run = ContentRun.objects.select_related("workspace").get(pk=self.run.pk)
            return create_job(run, token=uuid.uuid4(), kind="image", brief="Golf").pk
        results = self.parallel(create)
        self.assertEqual(results[0], results[1])
        self.assertEqual(MediaGeneration.objects.count(), 1)

    @patch("engine.media.providers.generate_images", return_value=([fixtures.picture()], {}))
    def test_concurrent_submit_calls_paid_provider_once(self, generate):
        job = create_job(self.run, token=uuid.uuid4(), kind="image", brief="Golf")
        def advance():
            return advance_job(MediaGeneration.objects.select_related("run__workspace").get(pk=job.pk)).pk
        self.parallel(advance)
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.assets.count(), 1)
        generate.assert_called_once()
