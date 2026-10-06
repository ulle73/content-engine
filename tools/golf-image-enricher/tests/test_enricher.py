import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import enrich


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


class EnricherTests(unittest.TestCase):
    def test_validate_preserves_non_image_fields_and_existing_images(self):
        before = [
            {"name": "A", "active": True, "url": "https://a.test", "slug": "a"},
            {"name": "B", "active": True, "url": "https://b.test", "images": [{"url": "x", "width": 1600, "height": 900}]},
        ]
        after = copy.deepcopy(before)
        after[0]["images"] = [{"url": "y", "width": 1800, "height": 1000}]
        self.assertEqual(enrich.validate_output(before, after), [])
        after[1]["images"] = []
        self.assertTrue(any("existing images changed" in x for x in enrich.validate_output(before, after)))

    def test_wp_original_variant(self):
        u = "https://x.test/wp-content/uploads/course-1536x1024.jpg"
        self.assertEqual(enrich.original_variant(u), "https://x.test/wp-content/uploads/course.jpg")

    def test_wix_original_variant(self):
        u = (
            "https://static.wixstatic.com/media/abc123~mv2.jpg/"
            "v1/fill/w_1600,h_1068,q_85/abc123~mv2.jpg"
        )
        self.assertEqual(
            enrich.original_variant(u),
            "https://static.wixstatic.com/media/abc123~mv2.jpg",
        )

    def test_generic_background_attribute_candidate(self):
        body = '<div data-background-image="/course-wide.jpg" class="hero golf"></div>'
        cands, _ = enrich.extract_candidates("https://club.test/", body)
        self.assertTrue(any(c.url == "https://club.test/course-wide.jpg" for c in cands))

    def test_end_to_end_against_local_http_server(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            site = td / "site"
            site.mkdir()
            # Approved landscape photo.
            Image.new("RGB", (1800, 1000), (80, 140, 80)).save(site / "fairway.jpg", quality=90)
            # Rejected small logo.
            Image.new("RGB", (500, 300), (255, 255, 255)).save(site / "logo.jpg", quality=90)
            (site / "index.html").write_text(
                '<html><body><a href="/banan.html">Banan</a><img src="/logo.jpg" alt="logo"></body></html>',
                encoding="utf-8",
            )
            (site / "banan.html").write_text(
                '<html><body><img src="/fairway.jpg" alt="Golfbana fairway hål 1"></body></html>',
                encoding="utf-8",
            )

            old = os.getcwd()
            os.chdir(site)
            try:
                server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                port = server.server_address[1]
                club = {"name": "Test GK", "url": f"http://127.0.0.1:{port}/index.html", "active": True}
                result = enrich.process_club(0, club, max_pages=4, max_probes=10, max_images=5)
                self.assertEqual(result.status, "ok")
                self.assertEqual(len(result.images), 1)
                self.assertEqual(result.images[0]["width"], 1800)
                self.assertEqual(result.images[0]["height"], 1000)
                self.assertTrue(result.images[0]["url"].endswith("fairway.jpg"))
            finally:
                server.shutdown()
                server.server_close()
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()