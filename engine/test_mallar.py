"""Mallmotorn (docs/designs/mallmotor.md). Testnamnen anger vilket byggsteg de hör till.

Steg 1: mallformatet mall/v1 och den statiska kontrollen (library/tools/mallformat.py, build_catalog.py --check).
Sidkontrollen (kontrollera_mallar.mjs) körs i CI-jobbet "mallar" med Node och Chrome.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
TESTMALL = ROOT / "library" / "templates" / "_mall" / "testmall"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mallformat = _load("mallformat", ROOT / "library" / "tools" / "mallformat.py")


def _testmall() -> dict:
    return json.loads((TESTMALL / "mall.json").read_text(encoding="utf-8"))


def _reglage(data: dict, nyckel: str) -> dict:
    return next(r for r in data["reglage"] if r["nyckel"] == nyckel)


class Steg1Mallformat(SimpleTestCase):
    def test_steg1_schemat_ar_ett_giltigt_json_schema(self):
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(json.loads(mallformat.SCHEMA_PATH.read_text(encoding="utf-8")))

    def test_steg1_testmallen_godkanns(self):
        self.assertEqual(mallformat.kontrollera_fil(TESTMALL / "mall.json"), [])

    def test_steg1_alla_mallar_i_biblioteket_godkanns(self):
        self.assertEqual(mallformat.mall_problems(), [])

    def test_steg1_build_catalog_check_kontrollerar_mallar(self):
        build_catalog = _load("build_catalog_mallar", ROOT / "library" / "tools" / "build_catalog.py")
        _items, problems = build_catalog.load_manifests()
        self.assertEqual([p for p in problems if "mall" in p.lower()], [])

    def test_steg1_trasiga_mallar_stoppas(self):
        def bryt(andring):
            data = _testmall()
            andring(data)
            return mallformat.kontrollera(data, mappnamn="testmall", mapp=TESTMALL)

        fall = {
            "saknar typ": lambda d: d.pop("typ"),
            "fel schema": lambda d: d.update(schema="mall/v2"),
            "okänd reglagetyp": lambda d: _reglage(d, "rubrik").update(typ="reglage"),
            "standard över max": lambda d: _reglage(d, "rubrik_storlek").update(standard=500),
            "min inte mindre än max": lambda d: _reglage(d, "rubrik_storlek").update(min=200),
            "standard inte bland valen": lambda d: _reglage(d, "typsnitt").update(standard="comic"),
            "för lång standardtext": lambda d: _reglage(d, "rubrik").update(standard="x" * 41),
            "ogiltig färg": lambda d: _reglage(d, "bakgrundsfarg").update(standard="grön"),
            "bild med standardfil": lambda d: _reglage(d, "bakgrund").update(standard="bakgrund.jpg"),
            "reserverad nyckel": lambda d: _reglage(d, "rubrik").update(nyckel="format"),
            "dubblerad nyckel": lambda d: _reglage(d, "bana").update(nyckel="rubrik"),
            "utdata i saknat format": lambda d: d["utdata"][0].update(format=["4x5", "1x1"]),
            "video ur bildmall": lambda d: d["utdata"].append({"typ": "video", "filtyp": "mp4", "format": ["4x5"]}),
            "standard_per okänt reglage": lambda d: d["standard_per"]["format"]["4x5"].update(finns_inte=1),
            "standard_per utanför gränsen": lambda d: d["standard_per"]["format"]["9x16"].update(rubrik_y=2),
            "standard_per saknat format": lambda d: d["standard_per"]["format"].update({"16x9": {"rubrik_y": 0.5}}),
            "fel id": lambda d: d.update(id="annan-mall"),
            "sidan finns inte": lambda d: d.update(sida="saknas.html"),
            "pekar på foto i repot": lambda d: d.update(beskrivning="library/templates/x/foto.png"),
        }
        for namn, andring in fall.items():
            with self.subTest(namn):
                self.assertNotEqual(bryt(andring), [], f"{namn} borde ha stoppats")

    def test_steg1_formatstorlekarna_stammer_med_safezones(self):
        js = (ROOT / "edit-renderer" / "src" / "safezones.js").read_text(encoding="utf-8")
        hittade = {
            f"{a}x{b}": (int(w), int(h))
            for a, b, w, h in re.findall(r"'(\d+):(\d+)': \{ W: (\d+), H: (\d+),", js)
        }
        self.assertEqual(hittade, mallformat.FORMAT_STORLEK)

    def test_steg1_testmallen_har_referensbilder(self):
        for fmt in _testmall()["format"]:
            with self.subTest(fmt):
                self.assertTrue((TESTMALL / "referens" / f"{fmt}.png").is_file())

    def test_steg1_kontrollen_andrar_inte_originalet(self):
        data = _testmall()
        kopia = copy.deepcopy(data)
        mallformat.kontrollera(data)
        self.assertEqual(data, kopia)


SLUTMALL = ROOT / "library" / "templates" / "golfkuponger-slutmallar"


def _slutmall() -> dict:
    return json.loads((SLUTMALL / "mall.json").read_text(encoding="utf-8"))


class Steg2Slutmallar(SimpleTestCase):
    def test_steg2_slutmallens_mall_json_godkanns(self):
        self.assertEqual(mallformat.kontrollera_fil(SLUTMALL / "mall.json"), [])

    def test_steg2_gransen_stammer_med_spec_tills_steg_3(self):
        # Steg 3 tar bort kopian i spec.py; fram till dess måste de vara lika.
        from engine.smsfilm import spec

        data = _slutmall()
        reglage = {r["nyckel"]: r for r in data["reglage"]}
        self.assertEqual([v["varde"] for v in reglage["mall"]["val"]], list(spec.SLUTMALLAR))
        self.assertEqual([v["varde"] for v in reglage["effekt"]["val"]], list(spec.SLUTMALL_EFFEKTER))
        self.assertEqual((reglage["text1"]["max_langd"], reglage["text2"]["max_langd"]), (spec.SLUTMALL_RAD1, spec.SLUTMALL_RAD2))
        self.assertEqual(sorted(data["format"]), sorted(spec.SLUTMALL_FORMAT))
        for nyckel, (_namn, enhet, lo, hi, _std) in spec.SLUTMALL_STIL.items():
            with self.subTest(nyckel):
                r = reglage[nyckel]
                self.assertEqual((r["min"], r["max"], r["enhet"]), (lo, hi, enhet))
                for effekt in spec.SLUTMALL_EFFEKTER:
                    std = mallformat.standardvarden(data, "9x16", {"effekt": effekt})[nyckel]
                    self.assertEqual(std, spec.slutmall_default(nyckel, effekt), effekt)

    def test_steg2_standard_per_beror_pa_ett_val(self):
        data = _slutmall()
        self.assertEqual(mallformat.standardvarden(data, "9x16")["skak"], 100)
        self.assertEqual(mallformat.standardvarden(data, "4x5", {"effekt": "studs"})["skak"], 40)
        self.assertEqual(mallformat.standardvarden(data, "9x16", {"effekt": "tona"})["skak"], 0)

    def test_steg2_trasig_standard_per_stoppas(self):
        fall = {
            "beror på textreglage": lambda d: d["standard_per"].update(text1={"x": {"skak": 1}}),
            "okänt val": lambda d: d["standard_per"]["effekt"].update(okand={"skak": 1}),
            "värde utanför gränsen": lambda d: d["standard_per"]["effekt"]["small"].update(skak=999),
            "beror på sig själv": lambda d: d["standard_per"]["effekt"]["small"].update(effekt="studs"),
            "tom krävd text": lambda d: next(r for r in d["reglage"] if r["nyckel"] == "text2").update(standard=" "),
        }
        for namn, andring in fall.items():
            with self.subTest(namn):
                data = _slutmall()
                andring(data)
                self.assertNotEqual(mallformat.kontrollera(data, mappnamn=SLUTMALL.name, mapp=SLUTMALL), [], namn)

    def test_steg2_slutmallen_har_referensbilder(self):
        for fmt in _slutmall()["format"]:
            with self.subTest(fmt):
                self.assertTrue((SLUTMALL / "referens" / f"{fmt}.png").is_file())