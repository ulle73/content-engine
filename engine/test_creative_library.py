"""Prompt Library contract: original bytes, tenant scope and bounded retrieval."""
from django.test import TestCase
from . import models


class PromptSchemaTests(TestCase):
    def test_prompt_library_is_a_real_company_scoped_model(self):
        self.assertTrue(hasattr(models, "PromptEntry"), "Prompt Library model is missing")
        self.assertEqual(models.PromptEntry._meta.get_field("company").remote_field.model, models.Company)
        self.assertEqual(models.PromptEntry._meta.get_field("original_text").get_internal_type(), "TextField")


class PromptServiceTests(TestCase):
    def setUp(self):
        import importlib.util
        from django.contrib.auth import get_user_model
        self.assertIsNotNone(importlib.util.find_spec('engine.prompt_library'), 'Prompt Library service is missing')
        from . import prompt_library
        self.library = prompt_library
        self.user = get_user_model().objects.create_user(username='prompt-owner')
        self.other = get_user_model().objects.create_user(username='other-owner')
        self.company = models.Company.objects.create(owner=self.user, name='Golf')
        self.foreign = models.Company.objects.create(owner=self.other, name='Other')

    def save(self, text, **kwargs):
        return self.library.save_prompt(self.user, self.company.pk, text, **kwargs)

    def test_preserves_whitespace_and_original_when_editing(self):
        original = '  Drone over a golf course.\r\n\r\nKeep signs exactly.  \n'
        prompt, created = self.save(original)
        self.assertTrue(created)
        self.library.edit_prompt(self.user, self.company.pk, prompt.pk, text='A new editable version')
        prompt.refresh_from_db()
        self.assertEqual(prompt.original_text, original)
        self.assertEqual(prompt.text, 'A new editable version')
        self.assertEqual(prompt.original_hash, __import__('hashlib').sha256(original.encode()).hexdigest())

    def test_model_save_rejects_original_mutation(self):
        from django.core.exceptions import ValidationError
        prompt, _ = self.save('Immutable original')
        prompt.original_text = 'Changed behind the service'
        with self.assertRaises(ValidationError):
            prompt.save()
        self.assertEqual(models.PromptEntry.objects.get(pk=prompt.pk).original_text, 'Immutable original')

    def test_duplicate_save_is_idempotent_and_does_not_undo_edits(self):
        prompt, _ = self.save('Saved once')
        self.library.edit_prompt(self.user, self.company.pk, prompt.pk, text='Edited once')
        again, created = self.save('Saved once')
        self.assertFalse(created)
        self.assertEqual(again.pk, prompt.pk)
        self.assertEqual(again.text, 'Edited once')
        self.assertEqual(models.PromptEntry.objects.count(), 1)

    def test_identical_text_can_belong_to_two_companies_without_leaking(self):
        self.save('Identical text')
        foreign, _ = self.library.save_prompt(self.other, self.foreign.pk, 'Identical text')
        found = self.library.search_prompts(self.user, self.company.pk, query='Identical')
        self.assertEqual(len(found), 1)
        self.assertNotEqual(found[0].pk, foreign.pk)

    def test_all_service_entry_points_enforce_company_ownership(self):
        from django.core.exceptions import PermissionDenied
        prompt, _ = self.save('Owned prompt')
        calls = [
            lambda: self.library.save_prompt(self.other, self.company.pk, 'Intrusion'),
            lambda: self.library.search_prompts(self.other, self.company.pk),
            lambda: self.library.get_prompt(self.other, self.company.pk, prompt.pk),
            lambda: self.library.edit_prompt(self.other, self.company.pk, prompt.pk, text='Intrusion'),
            lambda: self.library.archive_prompt(self.other, self.company.pk, prompt.pk),
        ]
        for call in calls:
            with self.subTest(call=call), self.assertRaises(PermissionDenied):
                call()

    def test_foreign_prompt_id_cannot_be_changed_in_own_company(self):
        from django.core.exceptions import ObjectDoesNotExist
        foreign, _ = self.library.save_prompt(self.other, self.foreign.pk, 'Not yours')
        with self.assertRaises(ObjectDoesNotExist):
            self.library.edit_prompt(self.user, self.company.pk, foreign.pk, favorite=True)
        foreign.refresh_from_db()
        self.assertFalse(foreign.favorite)

    def test_concept_search_finds_swedish_drone_golf_and_excludes_archived(self):
        prompt, _ = self.save('En filmisk dr\u00f6nare flyger \u00f6ver golfbanan i morgondimma.')
        self.save('A close-up portrait in a studio.')
        found = self.library.search_prompts(self.user, self.company.pk, query='cinematic drone golf')
        self.assertEqual(found[0].pk, prompt.pk)
        self.assertEqual(prompt.metadata['evidence_level'], 'HEURISTIC')
        self.library.archive_prompt(self.user, self.company.pk, prompt.pk)
        self.assertEqual(self.library.search_prompts(self.user, self.company.pk, query='drone golf'), [])

    def test_saved_again_restores_archive_without_replacing_original(self):
        prompt, _ = self.save('A stored prompt')
        self.library.archive_prompt(self.user, self.company.pk, prompt.pk)
        restored, created = self.save('A stored prompt')
        self.assertFalse(created)
        self.assertEqual(restored.pk, prompt.pk)
        self.assertIsNone(restored.archived_at)

    def test_edit_reindexes_search_and_tags_without_replacing_original(self):
        prompt, _ = self.save('A mountain landscape')
        self.library.edit_prompt(self.user, self.company.pk, prompt.pk,
                                 text='A calm ocean scene', tags=['Campaign A'], favorite=True)
        self.assertEqual(self.library.search_prompts(self.user, self.company.pk, query='mountain'), [])
        found = self.library.search_prompts(self.user, self.company.pk, query='ocean', tag='Campaign A', favorites=True)
        self.assertEqual([p.pk for p in found], [prompt.pk])
        prompt.refresh_from_db()
        self.assertEqual(prompt.original_text, 'A mountain landscape')

    def test_inspiration_is_bounded_and_scoped(self):
        for i in range(8):
            self.save(f'Drone over golf course {i}. ' + 'A long description. ' * 100)
        self.library.save_prompt(self.other, self.foreign.pk, 'SECRET drone golf')
        examples = self.library.retrieve_inspiration(self.user, self.company.pk, 'drone golf', limit=3)
        self.assertEqual(len(examples), 3)
        self.assertTrue(all(len(item['text']) <= 1200 for item in examples))
        self.assertNotIn('SECRET', str(examples))
        self.assertTrue(all(item['trust'] == 'untrusted_inspiration' for item in examples))

    def test_invalid_or_oversized_text_and_source_urls_are_rejected(self):
        from django.core.exceptions import ValidationError
        for text in ['', ' \r\n ', 'x' * 50001, 'bad\x00text']:
            with self.subTest(text=text[:20]), self.assertRaises(ValidationError):
                self.save(text)
        for url in ['javascript:alert(1)', 'https://user:password@example.com/prompt']:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                self.save('Example', source_url=url)
        self.assertEqual(models.PromptEntry.objects.count(), 0)

    def test_unknown_metadata_is_not_fabricated(self):
        prompt, _ = self.save('A thing in a place')
        self.assertEqual(prompt.metadata['kind'], 'unknown')
        self.assertEqual(prompt.metadata['model'], 'unknown')

    def test_bulk_splits_only_explicit_separator_and_keeps_segment_text(self):
        raw = '  Prompt one\n---PROMPT---\nPrompt two  '
        self.assertEqual(self.library.preview_bulk(raw), ['  Prompt one\n', 'Prompt two  '])
        self.assertEqual(self.library.preview_bulk('PROMPT 1\nOne\nPROMPT 2\nTwo'), ['PROMPT 1\nOne\nPROMPT 2\nTwo'])

    def test_generation_save_keeps_provenance_without_arbitrary_parameters(self):
        run = models.ContentRun.objects.create(workspace=self.company, author=self.user, context={}, model='test')
        job = models.MediaGeneration.objects.create(run=run, kind='video', provider='higgsfield',
            brief='User request', prompt='Compiled prompt', parameters={'model': 'verified-model', 'duration': 8, 'api_key': 'never-copy'},
            usage={'estimated_usd': '0.5'}, status='completed')
        prompt, _ = self.library.save_from_generation(self.user, self.company.pk, job.pk)
        self.assertEqual(prompt.original_text, 'Compiled prompt')
        self.assertEqual(prompt.generation_id, job.pk)
        self.assertEqual(prompt.metadata['generation']['user_request'], 'User request')
        self.assertNotIn('never-copy', str(prompt.metadata))

    def test_generation_save_rejects_foreign_generation(self):
        from django.core.exceptions import ObjectDoesNotExist
        run = models.ContentRun.objects.create(workspace=self.foreign, author=self.other, context={}, model='test')
        job = models.MediaGeneration.objects.create(run=run, kind='video', provider='higgsfield', brief='secret', prompt='secret')
        with self.assertRaises(ObjectDoesNotExist):
            self.library.save_from_generation(self.user, self.company.pk, job.pk)

    def test_bulk_update_cannot_overwrite_original(self):
        from django.core.exceptions import ValidationError
        prompt, _ = self.save('Original stays')
        with self.assertRaises(ValidationError):
            models.PromptEntry.objects.filter(pk=prompt.pk).update(original_text='Changed')

    def test_retrieval_uses_bounded_index_query_without_per_entry_reads(self):
        for i in range(6):
            self.save(f'Drone golf {i}')
        with self.assertNumQueries(2):
            result = self.library.retrieve_inspiration(self.user, self.company.pk, 'drone golf')
        self.assertEqual(len(result), 3)
