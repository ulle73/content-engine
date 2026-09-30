import io
import struct
import wave
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from engine.models import Company, ContentRun
from engine.media import describe_file, store_asset, select_asset
from engine.media_storage import MediaError


def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        audio.writeframes(struct.pack("<h", 1000) * 44100)
    return output.getvalue()


class MotionAudioTests(TestCase):
    def test_actual_wav_metadata(self):
        metadata = describe_file(wav_bytes())
        self.assertEqual(metadata["kind"], "audio")
        self.assertEqual(metadata["mime_type"], "audio/wav")
        self.assertAlmostEqual(metadata["duration_seconds"], 1, places=2)

    def test_fake_audio_is_rejected(self):
        with self.assertRaises(MediaError):
            describe_file(b"RIFFxxxxWAVE" + b"bad" * 40)
        with self.assertRaises(MediaError):
            describe_file(b"ID3" + b"bad" * 40)

    def test_audio_is_regular_owned_asset_but_not_a_post_image(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            user = get_user_model().objects.create_user(username="audio-owner")
            company = Company.objects.create(owner=user, name="Golfkuponger")
            asset = store_asset(company, wav_bytes())
            self.assertEqual(asset.kind, "audio")
            self.assertEqual(asset.company_id, company.id)
            run = ContentRun.objects.create(
                workspace=company, author=user, model="test", context={}, ideas=[], draft={}
            )
            with self.assertRaises(MediaError):
                select_asset(run, asset)
