from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .models import Company, ContentRun, MediaGeneration, PromptEntry
from .prompt_library import save_prompt


class PromptUITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='library-user')
        self.other = get_user_model().objects.create_user(username='library-other')
        self.company = Company.objects.create(owner=self.user, name='Golf')
        self.foreign = Company.objects.create(owner=self.other, name='Other')
        self.client.force_login(self.user)
        try:
            self.url = reverse('engine:prompt_library', kwargs={'workspace_id': self.company.pk})
        except Exception:
            self.fail('Prompt Library UI route is missing')

    def url_for(self, name, **kwargs):
        return reverse('engine:' + name, kwargs={'workspace_id': self.company.pk, **kwargs})

    def test_paste_save_redirects_to_empty_input_and_preserves_original(self):
        text = '  Drone film\r\nKeep signs.  \n'
        result = self.client.post(self.url, {'action': 'save', 'text': text}, follow=True)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(PromptEntry.objects.get().original_text, text)
        self.assertEqual(result.context['form']['text'].value(), None)
        self.assertContains(result, 'Spara prompt')

    def test_library_and_cards_escape_untrusted_text(self):
        save_prompt(self.user, self.company.pk, '<script>alert("x")</script>')
        result = self.client.get(self.url)
        self.assertNotContains(result, '<script>alert("x")</script>')
        self.assertContains(result, '&lt;script&gt;')
        self.assertContains(result, 'aria-label="Bibliotek"')

    def test_company_boundaries_and_csrf(self):
        foreign_url = reverse('engine:prompt_library', kwargs={'workspace_id': self.foreign.pk})
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        self.assertEqual(self.client.post(foreign_url, {'text': 'forbidden'}).status_code, 404)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.url, {'text': 'forbidden'}).status_code, 403)
        self.assertEqual(PromptEntry.objects.count(), 0)

    def test_detail_edit_cannot_replace_original(self):
        prompt, _ = save_prompt(self.user, self.company.pk, 'Original')
        url = self.url_for('prompt_detail', prompt_id=prompt.pk)
        self.assertEqual(self.client.post(url, {'text': 'Edited', 'title': 'My shot'}, follow=True).status_code, 200)
        prompt.refresh_from_db()
        self.assertEqual((prompt.original_text, prompt.text), ('Original', 'Edited'))

    def test_foreign_prompt_cannot_be_read_or_mutated(self):
        prompt, _ = save_prompt(self.other, self.foreign.pk, 'Secret')
        for name in ('prompt_detail', 'prompt_favorite', 'prompt_archive'):
            self.assertEqual(self.client.post(self.url_for(name, prompt_id=prompt.pk), {'text': 'attack'}).status_code, 404)
        self.assertEqual(self.client.get(self.url_for('prompt_detail', prompt_id=prompt.pk)).status_code, 404)

    def test_bulk_preview_saves_nothing_then_confirms_exact_parts(self):
        raw = '  First\n---PROMPT---\nSecond  '
        preview = self.client.post(self.url, {'action': 'preview', 'text': raw})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(PromptEntry.objects.count(), 0)
        self.assertEqual(preview.context['parts'], ['  First\n', 'Second  '])
        token = preview.context['preview_token']
        result = self.client.post(self.url, {'action': 'confirm', 'preview_token': token}, follow=True)
        self.assertEqual(result.status_code, 200)
        self.assertSetEqual(set(PromptEntry.objects.values_list('original_text', flat=True)), {'  First\n', 'Second  '})
        self.client.post(self.url, {'action': 'confirm', 'preview_token': token})
        self.assertEqual(PromptEntry.objects.count(), 2)

    def test_bulk_preview_rejects_tampered_token_and_other_user(self):
        preview = self.client.post(self.url, {'action': 'preview', 'text': 'First\n---PROMPT---\nSecond'})
        token = preview.context['preview_token']
        self.assertEqual(self.client.post(self.url, {'action': 'confirm', 'preview_token': token + 'x'}).status_code, 400)
        other_company = Company.objects.create(owner=self.user, name='Same owner different company')
        url = reverse('engine:prompt_library', kwargs={'workspace_id': other_company.pk})
        self.assertEqual(self.client.post(url, {'action': 'confirm', 'preview_token': token}).status_code, 400)
        self.assertEqual(PromptEntry.objects.count(), 0)

    def test_invalid_prompt_returns_actionable_form_without_saving(self):
        result = self.client.post(self.url, {'action': 'save', 'text': ' '})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(PromptEntry.objects.count(), 0)

    def test_favorite_and_archive_require_post(self):
        prompt, _ = save_prompt(self.user, self.company.pk, 'Original')
        for name in ('prompt_favorite', 'prompt_archive'):
            self.assertEqual(self.client.get(self.url_for(name, prompt_id=prompt.pk)).status_code, 405)
        self.client.post(self.url_for('prompt_favorite', prompt_id=prompt.pk), {'favorite': '1'})
        self.client.post(self.url_for('prompt_favorite', prompt_id=prompt.pk), {'favorite': '1'})
        prompt.refresh_from_db()
        self.assertTrue(prompt.favorite)
        self.client.post(self.url_for('prompt_archive', prompt_id=prompt.pk))
        self.assertEqual(self.client.get(self.url).context['entries'], [])

    def test_save_from_existing_generation_never_calls_provider(self):
        run = ContentRun.objects.create(workspace=self.company, author=self.user, context={}, model='test')
        job = MediaGeneration.objects.create(run=run, kind='video', provider='higgsfield', brief='User request', prompt='Compiled original')
        result = self.client.post(self.url_for('prompt_save_generation', job_id=job.pk), follow=True)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(PromptEntry.objects.get().generation_id, job.pk)
        self.assertContains(result, 'Compiled original')

    def test_query_favorites_and_kind_filters(self):
        prompt, _ = save_prompt(self.user, self.company.pk, 'Drone golf video')
        PromptEntry.objects.filter(pk=prompt.pk).update(favorite=True)
        save_prompt(self.user, self.company.pk, 'Portrait photo')
        result = self.client.get(self.url, {'q': 'drone', 'favorites': '1', 'kind': 'video'})
        self.assertContains(result, 'Drone golf video')
        self.assertNotContains(result, 'Portrait photo')
