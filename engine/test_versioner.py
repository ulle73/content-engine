import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from . import versionsarkiv as va


def _gor_video(path: Path, farg: str = "red", sek: float = 1.0) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={farg}:s=108x192:d={sek}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


class VersionsarkivTest(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.work = self.tmp / "work"
        (self.work / "film-a" / "resultat").mkdir(parents=True)
        (self.work / "film-a" / "film.json").write_text('{"texter": []}', encoding="utf-8")
        self.p = mock.patch.object(va, "WORK", self.work)
        self.p.start()
        self.v1 = _gor_video(self.work / "film-a" / "resultat" / "film-a-9x16.mp4", "red")

    def tearDown(self):
        self.p.stop()
        for f in self.tmp.rglob("*"):
            try:
                f.chmod(0o666)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_spara_las_och_hoppa_over_dubbletter(self):
        meta = va.spara("film-a", [self.v1], andring="första")
        self.assertEqual(meta["namn"], "v01")
        mapp = Path(meta["mapp"])
        for namn in ("film-9x16.mp4", "poster.jpg", "kontakt.jpg", "meta.json", "granskning.json", "kalla/film.json"):
            self.assertTrue((mapp / namn).is_file(), namn)
        self.assertIsNone(va.spara("film-a", [self.v1]))            # samma film → ingen ny version
        v2 = _gor_video(self.work / "film-a" / "resultat" / "film-a-9x16.mp4", "blue")
        self.assertEqual(va.spara("film-a", [v2], andring="blå")["namn"], "v02")
        self.assertEqual([v["nr"] for v in va.versioner("film-a")], [1, 2])
        self.assertEqual(va.kontroll(), [])

    def test_kommentar_status_aterstall_och_kontroll(self):
        self.assertEqual(len(va.kontroll()), 1)                     # resultat utan version
        va.spara("film-a", [self.v1])
        k = va.kommentera("film-a", "v01", "Texten för tidigt", tid=2.5)
        va.satt_status("film-a", 1, "godkänd")
        v = va.version("film-a", "v01")
        self.assertEqual(v["granskning"]["status"], "godkänd")
        self.assertEqual(v["granskning"]["kommentarer"][0]["tid"], 2.5)
        self.assertIn("Texten för tidigt", va.uppdrag("film-a", 1))
        va.markera_kommentar("film-a", 1, k["id"])
        self.assertTrue(va.version("film-a", 1)["granskning"]["kommentarer"][0]["klar"])
        dst = va.aterstall("film-a", "v01")
        self.assertTrue((dst / "film.json").is_file())
        with self.assertRaises(va.ArkivFel):
            va.aterstall("film-a", "v01")                           # skriver aldrig över
        with self.assertRaises(va.ArkivFel):
            va.satt_status("film-a", 1, "kanske")

    def test_vyer(self):
        va.spara("film-a", [self.v1], andring="första")
        user = get_user_model().objects.create_user("jonas", password="x")
        self.assertEqual(self.client.get("/versioner/").status_code, 302)   # kräver inloggning
        self.client.force_login(user)
        self.assertContains(self.client.get("/versioner/"), "film-a")
        self.assertContains(self.client.get("/versioner/film-a/"), "v01")
        self.assertContains(self.client.get("/versioner/film-a/jamfor/?v=v01"), "film-9x16.mp4")
        r = self.client.get("/versioner/film-a/v01/fil/film-9x16.mp4", HTTP_RANGE="bytes=0-15")
        self.assertEqual(r.status_code, 206)
        self.assertEqual(len(r.content), 16)
        self.assertEqual(self.client.get("/versioner/film-a/v01/fil/meta.json").status_code, 404)
        self.assertEqual(self.client.get("/versioner/film-a/v09/fil/poster.jpg").status_code, 404)
        r = self.client.post("/versioner/film-a/v01/kommentar/", json.dumps({"text": "Bra", "tid": 1.2}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        r = self.client.post("/versioner/film-a/v01/status/", json.dumps({"status": "godkänd"}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(va.version("film-a", 1)["granskning"]["status"], "godkänd")
        self.assertContains(self.client.get("/versioner/film-a/v01/uppdrag/"), "Bra")

    def test_utan_arkiv_404(self):
        user = get_user_model().objects.create_user("jonas", password="x")
        self.client.force_login(user)
        with mock.patch.object(va, "WORK", self.tmp / "finns-inte"):
            self.assertEqual(self.client.get("/versioner/").status_code, 404)
