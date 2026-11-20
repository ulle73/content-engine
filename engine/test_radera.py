"""Radera i Dina filer (engine/smsfilm/radera.py). n8n and Google are replaced by a fake; the flow
"CE – Papperskorg i CONTENT" was checked by hand against Drive on 2026-11-20 (trash, trash again, refuse a file outside
CONTENT/01 Publicerat)."""

from __future__ import annotations

import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from engine.models import Company, MediaAsset
from engine.smsfilm import publicera, radera, service
from engine.smsfilm.models import Publicering, SmsFilmJob, SmsFilmOutput
from engine.smsfilm.spec import SmsFilmError

DRIVE = publicera.drive()


def _jobb(company, *, status="done", formats=("9x16", "4x5")):
    job = SmsFilmJob.objects.create(company=company, kind="mall", status=status, mall_id="golfkuponger-golfare-i-stad",
                                    varden={"stad": "Göteborg"}, formats=list(formats))
    for fmt in formats:
        asset = MediaAsset.objects.create(company=company, kind="image", storage_backend="local", storage_key=f"t/{job.pk}-{fmt}.jpg",
                                          byte_size=4, sha256="0" * 64, mime_type="image/jpeg")
        SmsFilmOutput.objects.create(job=job, typ="bild", format=fmt, bredd=1080, hojd=1920, asset=asset)
    return job


def _publicerad(output, version=1, status="klar"):
    return Publicering.objects.create(company=output.job.company, output=output, kampanj="golfare-i-stad", stad="goteborg",
                                      variant="a", format=output.format, version=version, filnamn=f"f_v{version:02d}.jpg",
                                      status=status, drive_id=f"DRIVEID{version:02d}xxxxxxxxxxxxxxxx" if status == "klar" else "")


class RaderaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("jonas", password="pw")
        self.company = Company.objects.create(owner=self.user, name="GK")
        self.job = _jobb(self.company)
        self.out = self.job.outputs.get(format="9x16")

    def test_lista_doljer_men_behaller_allt(self):
        radera.radera(self.job, lista=True)
        self.job.refresh_from_db()
        self.assertIsNotNone(self.job.dold_at)
        self.assertNotIn(self.job, list(service.jobs_for(self.company)))
        self.assertEqual(MediaAsset.objects.filter(company=self.company).count(), 2)

    def test_content_engine_raderar_jobb_och_filer_men_behaller_versionerna(self):
        pub = _publicerad(self.out)
        with mock.patch("engine.smsfilm.radera.delete_file") as delete_file:
            res = radera.radera(self.job, content_engine=True)
        self.assertTrue(res["content_engine"])
        self.assertFalse(SmsFilmJob.objects.filter(pk=self.job.pk).exists())
        self.assertEqual(SmsFilmOutput.objects.count(), 0)
        self.assertEqual(MediaAsset.objects.filter(company=self.company).count(), 0)
        self.assertEqual(delete_file.call_count, 2)
        pub.refresh_from_db()
        self.assertIsNone(pub.output_id)  # the version stays counted

    def test_fil_som_anvands_pa_annat_stalle_ligger_kvar(self):
        asset = self.out.asset
        MediaAsset.objects.filter(pk=asset.pk).update(used_at="2026-11-20T00:00:00Z")
        with mock.patch("engine.smsfilm.radera.delete_file"):
            radera.radera(self.job, content_engine=True)
        self.assertTrue(MediaAsset.objects.filter(pk=asset.pk).exists())

    def test_drive_lagger_publicerade_filer_i_papperskorgen(self):
        klar = _publicerad(self.out, 1)
        fel = _publicerad(self.out, 2, status="fel")
        with mock.patch.object(DRIVE, "papperskorg", return_value="papperskorg") as korg:
            res = radera.radera(self.job, lista=False, i_drive_ocksa=True)
        korg.assert_called_once_with(klar.drive_id)
        self.assertEqual(res["drive"], [klar.filnamn])
        klar.refresh_from_db(); fel.refresh_from_db()
        self.assertEqual(klar.status, "raderad")
        self.assertEqual(fel.status, "fel")
        self.assertTrue(SmsFilmJob.objects.filter(pk=self.job.pk, dold_at__isnull=True).exists())

    def test_drivefel_raderar_inget_i_content_engine(self):
        _publicerad(self.out)
        with mock.patch.object(DRIVE, "papperskorg", side_effect=DRIVE.DriveFel("n8n kunde inte nås.")), \
                self.assertRaises(SmsFilmError):
            radera.radera(self.job, content_engine=True, i_drive_ocksa=True)
        self.assertTrue(SmsFilmJob.objects.filter(pk=self.job.pk).exists())

    def test_pagaende_jobb_kan_inte_raderas(self):
        job = _jobb(self.company, status="rendering", formats=("9x16",))
        with self.assertRaises(SmsFilmError):
            radera.radera(job, content_engine=True)

    def test_inget_valt_ger_fel(self):
        with self.assertRaises(SmsFilmError):
            radera.radera(self.job, lista=False)

    def test_raderad_utdata_laddas_inte_upp_igen(self):
        pub = _publicerad(self.out, status="fel")
        with mock.patch("engine.smsfilm.radera.delete_file"):
            radera.radera(self.job, content_engine=True)
        pub.refresh_from_db()
        pub = publicera.ladda_upp(pub)
        self.assertEqual(pub.status, "fel")
        self.assertIn("raderad", pub.fel)


class RaderaViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("jonas", password="pw")
        self.company = Company.objects.create(owner=self.user, name="GK")
        self.client.force_login(self.user)
        self.job = _jobb(self.company)

    def url(self, job):
        return reverse("engine:sms_film_radera", kwargs={"workspace_id": self.company.pk, "job_id": job.pk})

    def test_post_doljer(self):
        res = self.client.post(self.url(self.job), json.dumps({"lista": True}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["resultat"]["dold"])

    def test_bara_drive_ger_tillbaka_jobbet(self):
        with mock.patch.object(DRIVE, "papperskorg", return_value="papperskorg"):
            res = self.client.post(self.url(self.job), json.dumps({"drive": True}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["job"]["id"], str(self.job.pk))

    def test_annat_foretags_jobb_finns_inte(self):
        other = Company.objects.create(owner=get_user_model().objects.create_user("x", password="pw"), name="X")
        job = _jobb(other, formats=("9x16",))
        res = self.client.post(self.url(job), json.dumps({"lista": True}), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(SmsFilmJob.objects.filter(pk=job.pk, dold_at__isnull=True).exists())

    def test_get_ar_inte_tillatet(self):
        self.assertEqual(self.client.get(self.url(self.job)).status_code, 405)
