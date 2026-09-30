import io
import struct
import wave
import tempfile
import math
from array import array
import av
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from engine.models import Company, ContentRun
from engine.media import describe_file, store_asset, select_asset
from engine.media_storage import MediaError
from engine.motion.outputs import validate_audio
from engine.motion.schema import validate_spec


def encoded_audio(amplitude):
    """Actual AAC bytes, including encoder padding, rather than mocked levels."""
    data = io.BytesIO()
    with av.open(data, "w", format="mp4") as container:
        stream = container.add_stream("aac", rate=48000)
        stream.layout = "stereo"
        for offset in range(0, 48000, 4800):
            frame = av.AudioFrame(format="flt", layout="stereo", samples=4800)
            frame.sample_rate = 48000
            frame.pts = offset
            samples = array("f", (amplitude * math.sin(2 * math.pi * 440 * (offset + i // 2) / 48000) for i in range(9600)))
            frame.planes[0].update(samples.tobytes())
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return data.getvalue()


def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        audio.writeframes(struct.pack("<h", 1000) * 44100)
    return output.getvalue()


class MotionAudioTests(TestCase):
    def audio_spec(self, enabled):
        return validate_spec({"template_id": "kinetic-text", "scenes": [{"id": "intro", "component": "hero", "duration_frames": 30}], "audio": {"enabled": enabled}})

    def test_full_aac_track_accepts_intentional_silence_and_music(self):
        silent = validate_audio(encoded_audio(0), self.audio_spec(False), 1)
        self.assertEqual(silent["audio_intent"], "silent")
        self.assertEqual(silent["audio_peak"], 0)
        music = validate_audio(encoded_audio(0.2), self.audio_spec(True), 1)
        self.assertGreater(music["audio_rms"], 0.01)
        self.assertLess(music["audio_peak"], 0.98)

    def test_missing_music_unintended_audio_and_clipping_are_blocked(self):
        with self.assertRaisesMessage(ValueError, "saknas"):
            validate_audio(encoded_audio(0), self.audio_spec(True), 1)
        with self.assertRaisesMessage(ValueError, "tyst"):
            validate_audio(encoded_audio(0.2), self.audio_spec(False), 1)
        with self.assertRaisesMessage(ValueError, "dista"):
            validate_audio(encoded_audio(2), self.audio_spec(True), 1)

    def test_truncated_soundtrack_is_blocked(self):
        with self.assertRaisesMessage(ValueError, "slutar före"):
            validate_audio(encoded_audio(0.2), self.audio_spec(True), 3)

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
