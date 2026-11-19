"""Mallmotor step 5: Godkänn and Drive (engine/smsfilm/publicera.py, scripts/drive_upload.py).

n8n and Google are replaced by fakes: no file leaves the test. The flow "CE – Publicera till CONTENT" itself was
checked by hand on 2026-11-19 (a few-KB file sent with another folder id still landed in CONTENT/01 Publicerat).
"""

from __future__ import annotations

import io
import json
import threading
import unittest
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from engine.models import Company, MediaAsset
from engine.smsfilm import publicera
from engine.smsfilm.models import Publicering, SmsFilmJob, SmsFilmOutput
from engine.smsfilm.spec import SmsFilmError

DRIVE = publicera.drive()


def _output(company, *, fmt="4x5", mime="image/jpeg", data=b"jpegdata", stad="Göteborg"):
    asset = MediaAsset.objects.create(company=company, kind="image" if mime.startswith("image") else "video",
                                      storage_key=f"x/{fmt}.jpg", byte_size=len(data), sha256="0" * 64, mime_type=mime)
    job = SmsFilmJob.objects.create(company=company, kind="mall", status="done", mall_id="golfkuponger-golfare-i-stad",
                                    varden={"stad": stad}, formats=[fmt], output_asset=asset)
    return SmsFilmOutput.objects.create(job=job, typ="bild", format=fmt, bredd=1080, hojd=1350, asset=asset)


class FakeGoogle:
    """Stands in for n8n (publicera_session) and Google (status, put_stream)."""

    def __init__(self, data=b"jpegdata"):
        self.data, self.sessions, self.puts, self.fail_next_put, self.expired = data, [], [], False, set()
        self.received = {}

    def publicera_session(self, namn, size):
        url = f"https://www.googleapis.com/upload/drive/v3/files?upload_id=s{len(self.sessions)}"
        self.sessions.append((namn, size))
        self.received[url] = b""
        return url

    def status(self, url, size):
        if url in self.expired:
            raise DRIVE.DriveFel("Uppladdningssessionen har gått ut.", sessionen_slut=True)
        got = self.received.get(url, b"")
        return {"id": "FILEID" + url[-2:] + "xxxxxxxx", "name": "x"} if len(got) == size else len(got)

    def put_stream(self, url, stream, size, mime, *, offset=0):
        stream.read(offset)
        rest = stream.read()
        self.puts.append((url, offset, len(rest)))
        if self.fail_next_put:
            self.fail_next_put = False
            self.received[url] = self.data[:3]   # Google got the first 3 bytes, then the connection broke
            raise DRIVE.DriveFel("Uppladdningen avbröts (TimeoutError).")
        self.received[url] = self.received.get(url, b"")[:offset] + rest
        return {"id": "FILEID" + url[-2:] + "xxxxxxxx", "name": "x"}


class Steg5Publicering(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pub", password="test")
        self.company = Company.objects.create(owner=self.user, name="GK", review_channel_id="123")
        self.output = _output(self.company)
        self.google = FakeGoogle()
        patches = [mock.patch.object(DRIVE, n, getattr(self.google, n)) for n in ("publicera_session", "status", "put_stream")]
        patches.append(mock.patch("engine.smsfilm.publicera.open_asset", lambda asset: _open(self.google.data)))
        self.discord = mock.patch("engine.review.discord.post", return_value={"message_id": "1"})
        patches.append(self.discord)
        self.mocks = [p.start() for p in patches]
        self.addCleanup(mock.patch.stopall)

    def test_steg5_filnamn_och_versioner(self):
        a = publicera.godkann(self.output, self.user, kampanj="Golfare i stad", stad="Göteborg", variant="A")
        b = publicera.godkann(self.output, self.user, kampanj="golfare-i-stad", stad="goteborg", variant="a")
        self.assertEqual((a.filnamn, b.filnamn), ("golfare-i-stad_goteborg_a_4x5_v01.jpg", "golfare-i-stad_goteborg_a_4x5_v02.jpg"))
        other = publicera.godkann(self.output, self.user, kampanj="golfare-i-stad", stad="Örebro", variant="a")
        self.assertEqual(other.filnamn, "golfare-i-stad_orebro_a_4x5_v01.jpg")
        for bad in ("", "  ", "!!!"):
            with self.assertRaises(SmsFilmError):
                publicera.godkann(self.output, self.user, kampanj=bad, stad="x", variant="a")

    def test_steg5_forslag_fran_mallen(self):
        self.assertEqual(publicera.forslag(self.output), {"kampanj": "golfare-i-stad", "stad": "goteborg", "variant": "a"})

    def test_steg5_uppladdning_och_discord(self):
        pub = publicera.ladda_upp(publicera.godkann(self.output, self.user, kampanj="k", stad="s", variant="a"))
        self.assertEqual((pub.status, pub.lank.startswith("https://drive.google.com/file/d/")), ("klar", True))
        self.assertEqual(self.google.sessions, [("k_s_a_4x5_v01.jpg", len(self.google.data))])
        payload = self.mocks[-1].call_args.args[0]
        self.assertEqual(payload["channel_id"], "123")
        self.assertIn("k_s_a_4x5_v01.jpg", payload["message"]["content"])
        # a finished row is never uploaded again
        publicera.ladda_upp(pub)
        self.assertEqual(len(self.google.puts), 1)
        self.assertEqual(len(self.google.sessions), 1)

    def test_steg5_avbruten_uppladdning_fortsatter_med_samma_url(self):
        self.google.fail_next_put = True
        pub = publicera.ladda_upp(publicera.godkann(self.output, self.user, kampanj="k", stad="s", variant="a"))
        self.assertEqual(pub.status, "fel")
        url = Publicering.objects.get(pk=pub.pk).upload_url
        pub = publicera.ladda_upp(Publicering.objects.get(pk=pub.pk))
        self.assertEqual(pub.status, "klar")
        self.assertEqual(len(self.google.sessions), 1)                 # no new session, no duplicate in Drive
        self.assertEqual(self.google.puts[-1][:2], (url, 3))           # continued from byte 3
        self.assertEqual(self.google.received[url], self.google.data)

    def test_steg5_utgangen_session_ger_ny(self):
        self.google.fail_next_put = True
        pub = publicera.ladda_upp(publicera.godkann(self.output, self.user, kampanj="k", stad="s", variant="a"))
        self.google.expired.add(Publicering.objects.get(pk=pub.pk).upload_url)
        pub = publicera.ladda_upp(Publicering.objects.get(pk=pub.pk))
        self.assertEqual((pub.status, len(self.google.sessions)), ("klar", 2))

    def test_steg5_discord_fel_stoppar_inte_publiceringen(self):
        from engine.review.service import ReviewError

        self.mocks[-1].side_effect = ReviewError("nere")
        pub = publicera.ladda_upp(publicera.godkann(self.output, self.user, kampanj="k", stad="s", variant="a"))
        self.assertEqual((pub.status, pub.discord_skickad), ("klar", False))

    def test_steg5_vyerna(self):
        self.client.force_login(self.user)
        url = reverse("engine:sms_film_godkann", kwargs={"workspace_id": self.company.pk, "output_id": self.output.pk})
        self.assertEqual(self.client.get(url).json()["forslag"]["stad"], "goteborg")
        r = self.client.post(url, json.dumps({"kampanj": "golfare-i-stad", "stad": "Göteborg", "variant": "a"}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["publicering"]["filnamn"], "golfare-i-stad_goteborg_a_4x5_v01.jpg")
        self.google.fail_next_put = True
        r = self.client.post(url, json.dumps({"kampanj": "golfare-i-stad", "stad": "Göteborg", "variant": "a"}),
                             content_type="application/json")
        self.assertEqual((r.status_code, r.json()["publicering"]["status"]), (502, "fel"))
        igen = reverse("engine:sms_film_publicera_igen", kwargs={"workspace_id": self.company.pk, "pub_id": r.json()["publicering"]["id"]})
        r = self.client.post(igen)
        self.assertEqual((r.status_code, r.json()["publicering"]["filnamn"]), (200, "golfare-i-stad_goteborg_a_4x5_v02.jpg"))
        self.assertEqual(self.client.post(url, "[]", content_type="application/json").status_code, 400)
        # another company's file and publication are out of reach
        other_user = get_user_model().objects.create_user(username="annan", password="test")
        other = Company.objects.create(owner=other_user, name="Annat")
        self.client.force_login(other_user)
        self.assertEqual(self.client.post(reverse("engine:sms_film_godkann", kwargs={"workspace_id": other.pk, "output_id": self.output.pk}),
                                          "{}", content_type="application/json").status_code, 404)
        self.assertEqual(self.client.post(reverse("engine:sms_film_publicera_igen", kwargs={"workspace_id": other.pk,
                                                                                           "pub_id": Publicering.objects.first().pk})).status_code, 404)


class Steg5N8nAnropet(TestCase):
    def test_steg5_inget_mapp_id_skickas(self):
        with mock.patch.dict("os.environ", {"GK_DRIVE_UPLOAD_SECRET": "s", "GK_DRIVE_UPLOAD_URL": "https://n8n.example/webhook/x"}), \
                mock.patch.object(DRIVE, "_post_json", return_value="https://www.googleapis.com/upload/drive/v3/x") as post:
            DRIVE.publicera_session("k_s_a_4x5_v01.jpg", 10)
        url, secret, body, _ = post.call_args.args
        self.assertEqual((url, secret, body), ("https://n8n.example/webhook/content-engine-publicera", "s",
                                               {"namn": "k_s_a_4x5_v01.jpg", "storlek": 10}))


@unittest.skipUnless(connection.vendor == "postgresql", "radlås provas mot Postgres (CI)")
class Steg5SamtidigaGodkannanden(TransactionTestCase):
    def test_steg5_tva_samtidiga_ger_olika_versioner(self):
        user = get_user_model().objects.create_user(username="par", password="test")
        company = Company.objects.create(owner=user, name="GK")
        output = _output(company)
        versioner, fel = [], []
        start = threading.Barrier(2)

        def godkann():
            try:
                start.wait()
                versioner.append(publicera.godkann(output, user, kampanj="k", stad="s", variant="a").version)
            except Exception as exc:  # noqa: BLE001
                fel.append(exc)
            finally:
                connection.close()

        trader = [threading.Thread(target=godkann) for _ in range(2)]
        for t in trader:
            t.start()
        for t in trader:
            t.join()
        self.assertEqual(fel, [])
        self.assertEqual(sorted(versioner), [1, 2])


class _open:
    def __init__(self, data):
        self.stream = io.BytesIO(data)

    def __enter__(self):
        return self.stream

    def __exit__(self, *exc):
        return False
