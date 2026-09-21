"""Prompt Library contract: original bytes, tenant scope and bounded retrieval."""
from django.test import TestCase
from . import models


class PromptSchemaTests(TestCase):
    def test_prompt_library_is_a_real_company_scoped_model(self):
        self.assertTrue(hasattr(models, "PromptEntry"), "Prompt Library model is missing")
        self.assertEqual(models.PromptEntry._meta.get_field("company").remote_field.model, models.Company)
        self.assertEqual(models.PromptEntry._meta.get_field("original_text").get_internal_type(), "TextField")
