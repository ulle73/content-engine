"""Intent-first creation, existing services, zero real provider calls."""
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import test_media as media_test
from .creative_controls import CreativeControls, apply_controls, creation_catalog
from .creative_director import build_plan, parse_brief
from .creative_registry import get_model
from .forms import MediaCreationForm
from .media import create_job, default_brief, store_asset
from .models import ContentRun, MediaAsset, MediaGeneration

picture = media_test.picture


class CreatorTests(TestCase):
    url = media_test.MediaTests.url
    def setUp(self):
        media_test.MediaTests.setUp(self)
        self.run.model = 'creative-studio'
        self.run.context['media_only'] = True
        self.run.draft['photo_brief'] = ''
        self.run.save()
        self.start = store_asset(self.company, picture(), alt_text='Startbild TEST')
        self.end = store_asset(self.company, picture(), alt_text='Slutbild TEST')

    def data(self, **changes):
        return {'token': str(uuid.uuid4()), 'kind': 'video',
                'brief': 'Kameran n\u00e4rmar sig golfbollen. Bollen lyfter.',
                'shape': 'portrait', 'priority': 'balanced', 'count': '1',
                'source_asset': str(self.start.pk), 'end_asset': str(self.end.pk),
                **changes}

    def test_empty_studio_does_not_invent_a_multi_scene_prompt(self):
        self.assertEqual(default_brief(self.run, 'video'), '')
        self.run.draft['photo_brief'] = 'Min inspiration'
        self.assertEqual(default_brief(self.run, 'video'), 'Min inspiration')

    def test_new_studio_routes_video_without_generation(self):
        response = self.client.post(reverse('engine:media_new', kwargs={'workspace_id': self.company.pk}),
            {'token': str(uuid.uuid4()), 'kind': 'video', 'source_asset': self.start.pk})
        self.assertEqual(response.status_code, 302)
        self.assertIn('?kind=video&source='+str(self.start.pk), response.url)
        self.assertEqual(MediaGeneration.objects.count(), 0)
        self.assertEqual(self.client.get(response.url).status_code, 200)

    def test_invalid_studio_reference_creates_no_empty_run(self):
        before = ContentRun.objects.count()
        response = self.client.post(reverse('engine:media_new', kwargs={'workspace_id': self.company.pk}),
            {'token': str(uuid.uuid4()), 'kind': 'video', 'source_asset': 'not-a-uuid'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ContentRun.objects.count(), before)

    def test_local_preview_has_no_generation_storage_or_provider_side_effect(self):
        data = self.data(duration_seconds='8', camera='push_in', ending='match_end')
        with patch('engine.media.create_job', side_effect=AssertionError('must not create job')), \
             patch('engine.media_providers.estimate_video', side_effect=AssertionError('no estimate')), \
             patch('httpx.Client.send', side_effect=AssertionError('no network')):
            result = self.client.post(self.url('creation_preview'), data)
        self.assertEqual(result.status_code, 200, result.content)
        payload = result.json()
        self.assertEqual(payload['duration'], 8)
        self.assertEqual(payload['model_id'], 'bytedance/seedance-2.5')
        self.assertIn('END FRAME:', payload['prompt'])
        self.assertIn('hold the closing composition', payload['prompt'])
        self.assertFalse(payload['paid_generation_started'])
        self.assertEqual(MediaGeneration.objects.count(), 0)
        self.assertEqual(MediaAsset.objects.count(), 2)

    def test_preview_matches_the_saved_shared_compiler_plan(self):
        data = self.data(duration_seconds='8', camera='push_in', recipe_id='premium_product_reveal')
        result = self.client.post(self.url('creation_preview'), data)
        self.assertEqual(result.status_code, 200, result.content)
        form = MediaCreationForm(data, company=self.company)
        self.assertTrue(form.is_valid(), form.errors)
        job = create_job(self.run, token=form.cleaned_data['token'], **form.job_options())
        self.assertEqual(job.prompt, result.json()['prompt'])
        self.assertEqual(job.brief, data['brief'])
        self.assertEqual(job.parameters['creator']['controls']['camera'], 'push_in')
        self.assertEqual(job.parameters['creative']['brief']['user_intent'], data['brief'])

    def test_invalid_choice_keeps_intent_frames_and_selected_model(self):
        data = self.data(model_override='kling-video/v2.5-turbo/pro', duration_seconds='8')
        response = self.client.post(self.url('media_generate'), data)
        self.assertEqual(response.status_code, 422)
        form = response.context['creator_form']
        self.assertEqual(form['brief'].value(), data['brief'])
        self.assertEqual(form['source_asset'].value(), data['source_asset'])
        self.assertEqual(form['end_asset'].value(), data['end_asset'])
        self.assertEqual(form['model_override'].value(), data['model_override'])
        self.assertEqual(MediaGeneration.objects.count(), 0)
        self.assertContains(response, 'Auto', status_code=422)

    def test_end_image_without_start_fails_before_generation(self):
        response = self.client.post(self.url('creation_preview'), self.data(source_asset=''))
        self.assertEqual(response.status_code, 422)
        self.assertIn('end_asset', response.json()['errors'])
        self.assertFalse(MediaGeneration.objects.exists())

    def test_cross_company_expired_and_non_image_references_are_rejected(self):
        other = self.company.__class__.objects.create(owner=self.user, name='Other')
        foreign = store_asset(other, picture())
        expired = store_asset(self.company, picture())
        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save()
        for asset_id in [foreign.pk, expired.pk, 'not-a-uuid']:
            with self.subTest(asset=asset_id):
                response = self.client.post(self.url('creation_preview'), self.data(source_asset=str(asset_id)))
                self.assertEqual(response.status_code, 422)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_form_catalog_is_derived_from_verified_contracts(self):
        for item in creation_catalog('video')['models']:
            model = get_model('higgsfield', item['id'])
            contract = model.request_contract(item['mode'])
            self.assertEqual(item['audio'], bool(model.audio_support and contract.audio_parameter))
            self.assertEqual(item['roles'], [r.value for r in contract.supported_reference_roles])
            for duration in item['durations']:
                self.assertTrue(contract.supports_duration(duration))

    def test_retry_restores_settings_instead_of_silently_using_defaults(self):
        form = MediaCreationForm(self.data(duration_seconds='8', camera='orbit', brief='Visa bollen.',
            subject_motion='lift', ending='match_end', shape='landscape', priority='quality',
            recipe_id='premium_product_reveal', model_override='bytedance/seedance-2.0'), company=self.company)
        self.assertTrue(form.is_valid(), form.errors)
        job = create_job(self.run, token=form.cleaned_data['token'], **form.job_options())
        response = self.client.get(self.url('media'), {'retry': str(job.pk)})
        self.assertEqual(response.status_code, 200)
        restored = response.context['creator_form']
        for name in ('brief', 'source_asset', 'end_asset', 'camera', 'subject_motion', 'ending',
                     'duration_seconds', 'shape', 'priority', 'recipe_id', 'model_override'):
            self.assertEqual(str(restored[name].value()), str(form[name].value()), name)
        self.assertFalse(response.context['restore_creator'])

    def test_reference_search_pages_the_existing_library_and_excludes_foreign(self):
        MediaAsset.objects.bulk_create([MediaAsset(company=self.company, kind='image', purpose='content',
            storage_key=f'test-{i}', byte_size=1, mime_type='image/png', sha256='0'*64, alt_text=f'Fler bilder {i}') for i in range(65)])
        first = self.client.get(self.url('creation_references')).json()
        second = self.client.get(self.url('creation_references'), {'page': first['next_page']}).json()
        self.assertEqual(len(first['assets']), 60)
        self.assertEqual(len(second['assets']), 7)
        self.assertEqual(len({a['id'] for a in first['assets'] + second['assets']}), 67)
        query = self.client.get(self.url('creation_references'), {'q': 'Slutbild TEST'}).json()
        self.assertEqual([a['id'] for a in query['assets']], [str(self.end.pk)])
        self.assertEqual(self.client.get(self.url('creation_references'), {'page': 'bad'}).status_code, 400)
        self.assertEqual(self.client.post(self.url('creation_references')).status_code, 405)

    def test_inline_upload_uses_real_media_storage_and_is_available_immediately(self):
        response = self.client.post(self.url('media_upload'),
            {'file': SimpleUploadedFile('upload.png', picture()), 'alt_text': 'Ny startbild'}, HTTP_X_CREATOR_UPLOAD='1')
        self.assertEqual(response.status_code, 201, response.content)
        asset = MediaAsset.objects.get(pk=response.json()['id'], company=self.company)
        self.assertEqual(asset.kind, 'image')
        result = self.client.post(self.url('creation_preview'), self.data(source_asset=str(asset.pk)))
        self.assertEqual(result.status_code, 200)

    def test_invalid_inline_upload_creates_no_asset(self):
        response = self.client.post(self.url('media_upload'),
            {'file': SimpleUploadedFile('fake.png', b'not an image')}, HTTP_X_CREATOR_UPLOAD='1')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MediaAsset.objects.count(), 2)

    def test_handoff_preserves_copy_and_prefills_both_existing_workflows(self):
        for target, route in [('motion', 'motion_list'), ('sequence', 'sequence_list')]:
            with self.subTest(target=target):
                text = 'Min id\u00e9 till ' + target
                response = self.client.post(self.url('creation_handoff'), {'workflow': target, 'brief': text})
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse('engine:'+route, kwargs={'workspace_id': self.company.pk}), response.url)
                self.run.refresh_from_db()
                self.assertEqual(self.run.draft['photo_brief'], text)
                self.assertEqual(self.run.draft['facebook'], 'FB')
                self.assertEqual(self.run.draft['instagram'], 'IG')
                destination = self.client.get(response.url)
                self.assertEqual(destination.status_code, 200)
                self.assertContains(destination, text)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_sent_run_is_not_editable_and_preview_requires_csrf(self):
        self.run.delivery_status = 'sent'
        self.run.save()
        self.assertEqual(self.client.post(self.url('creation_preview'), self.data()).status_code, 409)
        self.assertEqual(self.client.post(self.url('creation_handoff'), {'workflow': 'sequence', 'brief': 'test'}).status_code, 409)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.user)
        self.assertEqual(secure.post(self.url('creation_preview'), self.data()).status_code, 403)

    def test_control_instructions_are_model_specific_without_changing_intent(self):
        intent = 'Visa golfbollen.'
        for model in ['kling-video/v2.5-turbo/pro', 'bytedance/seedance-2.5']:
            plan = build_plan(self.run, intent, kind='video', source=self.start, model_override=model,
                controls={'camera': 'orbit', 'subject_motion': 'lift', 'ending': 'close_up'})
            self.assertEqual(plan.brief.user_intent, intent)
            self.assertIn('smooth orbit around the subject', plan.prompt)
            self.assertIn('subject lifts smoothly', plan.prompt)
            self.assertIn('Finish in a clear close-up', plan.prompt)
            self.assertIn('PHYSICS:' if 'seedance' in model else 'ALLOW MOTION/CHANGE:', plan.prompt)

    def test_contradictory_camera_and_invalid_options_fail_closed(self):
        brief = parse_brief('Kameran st\u00e5r stilla vid golfbollen.', kind='video')
        with self.assertRaisesRegex(ValueError, 's\u00e4ger emot'):
            apply_controls(brief, {'camera': 'push_in'})
        with self.assertRaises(ValueError):
            CreativeControls.model_validate({'camera': 'invented'})
        with self.assertRaises(ValueError):
            CreativeControls.model_validate({'arbitrary': 'provider payload'})
        with self.assertRaises(ValueError):
            apply_controls(brief, {'ending': 'match_end'})


    def test_sequence_handoff_creates_canonical_images_in_the_selected_order(self):
        from .models import SequenceProject
        result = self.client.post(self.url('creation_handoff'), self.data(workflow='sequence'))
        self.assertEqual(result.status_code, 302)
        page = self.client.get(result.url)
        self.assertEqual([image.pk for image in page.context['seed_images']], [self.start.pk, self.end.pk])
        response = self.client.post(reverse('engine:sequence_list', kwargs={'workspace_id': self.company.pk}), {
            'run_id': str(self.run.pk), 'title': 'Min film', 'brief': 'Fortsatt id\u00e9', 'format': 'reel',
            'platform': 'instagram', 'image_ids': [str(self.start.pk), str(self.end.pk)]})
        self.assertEqual(response.status_code, 302)
        project = SequenceProject.objects.get()
        self.assertEqual(list(project.anchors.order_by('position').values_list('asset_id', flat=True)), [self.start.pk, self.end.pk])
        self.assertEqual(project.source_run_id, self.run.pk)
        self.assertFalse(MediaGeneration.objects.exists())

    def test_motion_extracts_only_explicit_monthly_numbers_from_the_same_intent(self):
        text = 'September wrapped: 877 inl\u00f6sen och 721515 kr.'
        result = self.client.post(self.url('creation_handoff'), {'workflow': 'motion', 'brief': text, 'shape': 'landscape'})
        page = self.client.get(result.url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['template_id'], 'monthly-wrapped')
        form = page.context['form']
        self.assertEqual(form['count'].value(), 877)
        self.assertEqual(form['total'].value(), 721515)
        self.assertEqual(form['month'].value(), 'September')
        self.assertEqual(form['aspect_ratio'].value(), '16:9')
        self.assertIn(form['area'].value(), (None, ''))
        self.assertFalse(MediaGeneration.objects.exists())

    def test_active_job_does_not_silently_replace_newly_submitted_intent(self):
        existing = create_job(self.run, token=uuid.uuid4(), kind='video', brief='Original idea')
        response = self.client.post(self.url('media_generate'), self.data())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context['creator_form']['brief'].value(), self.data()['brief'])
        existing.refresh_from_db()
        self.assertEqual(existing.brief, 'Original idea')
        self.assertEqual(MediaGeneration.objects.count(), 1)

    def test_conflicting_explicit_duration_audio_and_resolution_are_not_silently_rewritten(self):
        for intent, controls in [
            ('Skapa 5 sekunder video', {'duration_seconds': 8}),
            ('Video utan ljud', {'audio': 'native'}),
            ('Video i 1080p', {'resolution': '720p'}),
        ]:
            with self.subTest(intent=intent), self.assertRaises(ValueError):
                build_plan(self.run, intent, kind='video', controls=controls)

    def test_motion_handoff_carries_validated_images_to_existing_template_fields(self):
        response = self.client.post(self.url('creation_handoff'), self.data(workflow='motion'))
        page = self.client.get(response.url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['form']['asset_id'].value(), self.start.pk)
        self.assertEqual(page.context['form']['secondary_asset_id'].value(), self.end.pk)
        self.assertTrue(page.context['references_supported'])
        self.assertFalse(MediaGeneration.objects.exists())

    def test_motion_handoff_reports_when_a_template_cannot_use_images(self):
        response = self.client.post(self.url('creation_handoff'), self.data(workflow='motion',
            brief='September wrapped: 877 inlösen och 721515 kr.'))
        page = self.client.get(response.url)
        self.assertEqual(page.status_code, 200)
        self.assertFalse(page.context['references_supported'])
        self.assertContains(page, 'inte de valda bilderna')
        self.assertIsNone(page.context['form']['area'].value())

    def test_motion_image_handoff_is_company_scoped(self):
        other = self.company.__class__.objects.create(owner=self.user, name='Other')
        foreign = store_asset(other, picture())
        endpoint = reverse('engine:motion_list', kwargs={'workspace_id': self.company.pk})
        for image_id in ['bad-uuid', str(foreign.pk)]:
            self.assertEqual(self.client.get(endpoint, {'image_ids': image_id}).status_code, 404)
