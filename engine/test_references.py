import io
from datetime import timedelta
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

import av
import numpy as np
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from engine import ads
from engine.models import AdAccount, AdObservation, Company, CompetitorAd, ScrapeRequest
from engine.references import adapt, fetch, measure, service
from engine.references.models import ReferenceVideo


def synthetic_video(colors=((220, 30, 30), (0, 0, 0), (30, 60, 220)), seconds=(1.5, 1.0, 2.0), fps=25,
                    bpm=120.0) -> bytes:
    """Solid colour shots (hard cuts between them) with a click track at `bpm`."""
    buf = io.BytesIO()
    with av.open(buf, mode="w", format="mp4") as out:
        video = out.add_stream("libx264", rate=fps)
        video.width, video.height, video.pix_fmt = 180, 320, "yuv420p"
        audio = out.add_stream("aac", rate=44100)
        audio.layout = "mono"
        index = 0
        for color, length in zip(colors, seconds):
            for _ in range(round(length * fps)):
                image = np.zeros((320, 180, 3), dtype=np.uint8)
                image[:] = color
                image[150:170, 10 + (index % 40):30 + (index % 40)] = 255  # a little motion inside each shot
                frame = av.VideoFrame.from_ndarray(image, format="rgb24")
                frame.pts, frame.time_base = index, Fraction(1, fps)
                index += 1
                for packet in video.encode(frame):
                    out.mux(packet)
        for packet in video.encode(None):
            out.mux(packet)
        total = sum(seconds)
        samples = np.zeros(int(44100 * total), dtype=np.float32)
        beat = 60.0 / bpm
        t = 0.0
        while t < total:
            start = int(t * 44100)
            samples[start:start + 2000] = 0.6 * np.sin(np.linspace(0, 2000 * 2 * np.pi * 880 / 44100, 2000))
            t += beat
        for i in range(0, samples.size, 1024):
            chunk = samples[i:i + 1024].reshape(1, -1)
            frame = av.AudioFrame.from_ndarray(chunk, format="flt", layout="mono")
            frame.sample_rate, frame.pts = 44100, i
            for packet in audio.encode(frame):
                out.mux(packet)
        for packet in audio.encode(None):
            out.mux(packet)
    return buf.getvalue()


def split_streams(data: bytes, folder: Path) -> tuple[Path, Path]:
    """Video-only mp4 and audio-only m4a, like YouTube's separate (DASH) formats."""
    paths = folder / "video.137.mp4", folder / "video.140.m4a"
    for kind, path in zip(("video", "audio"), paths):
        with av.open(io.BytesIO(data)) as source, av.open(str(path), mode="w", format="mp4") as out:
            stream = source.streams.get(**{kind: 0})[0]
            copy = out.add_stream_from_template(stream)
            for packet in source.demux(stream):
                if packet.dts is not None:
                    packet.stream = copy
                    out.mux(packet)
    return paths


class MeasureTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.video = synthetic_video()
        cls.result = measure.measure(cls.video, title="Syntetisk")

    def test_cuts_are_frame_accurate(self):
        self.assertEqual(len(self.result["cuts"]), 2)
        self.assertAlmostEqual(self.result["cuts"][0], 1.5, delta=0.05)
        self.assertAlmostEqual(self.result["cuts"][1], 2.5, delta=0.05)
        self.assertEqual([s["id"] for s in self.result["scenes"]], ["s1", "s2", "s3"])
        self.assertEqual(self.result["summary"]["cuts_first_3s"], 2)

    def test_audio_tempo_and_loudness(self):
        audio = self.result["audio"]
        self.assertTrue(audio["has_audio"])
        self.assertAlmostEqual(audio["tempo_bpm"], 120, delta=6)
        self.assertLess(audio["peak_dbfs"], 0.5)

    def test_proxy_and_sheet(self):
        info = measure.probe(self.result["proxy"])
        self.assertTrue(info["has_audio"])
        self.assertLessEqual(max(info["width"], info["height"]), measure.PROXY_LONG_SIDE)
        self.assertTrue(self.result["sheet"].startswith(b"\xff\xd8"))

    def test_rejects_non_video(self):
        with self.assertRaises(measure.MeasureError):
            measure.measure(b"not a video")


class FetchTests(SimpleTestCase):
    def test_ad_library_ids(self):
        self.assertEqual(fetch.ad_library_id("https://www.facebook.com/ads/library/?id=2009689302964425"),
                         "2009689302964425")
        self.assertEqual(fetch.ad_library_id("https://www.facebook.com/ads/library/?active_status=all&id=42"), "42")
        self.assertEqual(fetch.ad_library_id("https://www.instagram.com/reel/abc/"), "")

    def test_only_public_https_links(self):
        for bad in ("ftp://x.se/a.mp4", "http://localhost/a.mp4", "https://127.0.0.1/a.mp4", "https://u:p@x.se/a",
                    "not a url"):
            with self.assertRaises(fetch.FetchError):
                fetch.check_url(bad)
        self.assertEqual(fetch.check_url(" https://www.tiktok.com/@a/video/1 "), "https://www.tiktok.com/@a/video/1")

    def test_yt_dlp_merges_only_with_ffmpeg(self):
        import yt_dlp
        seen = []

        class FakeYDL:
            def __init__(self, options):
                seen.append(options)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download):
                raise yt_dlp.utils.DownloadError("ERROR: [youtube] x: Requested format is not available.")

        url = "https://www.youtube.com/watch?v=x"
        with mock.patch.object(yt_dlp, "YoutubeDL", FakeYDL):
            for ffmpeg in ("/usr/bin/ffmpeg", None):
                with mock.patch.object(fetch.shutil, "which", return_value=ffmpeg), \
                        self.assertRaisesRegex(fetch.FetchError, "inte i något format"):
                    fetch._yt_dlp(url)
        self.assertEqual([o["format"] for o in seen], [fetch.FORMAT_MERGED, fetch.FORMAT_SEPARATE])
        self.assertIn("+", fetch.FORMAT_MERGED)
        self.assertNotIn("+", fetch.FORMAT_SEPARATE)
        self.assertIn("node", seen[0]["js_runtimes"])

    def test_separate_format_picks_combined_file_else_video_and_audio(self):
        import yt_dlp

        def fmt(format_id, ext, vcodec, acodec, height=None):
            return {"format_id": format_id, "ext": ext, "vcodec": vcodec, "acodec": acodec, "height": height,
                    "url": "https://example.com/" + format_id, "protocol": "https"}

        youtube = [fmt("251", "webm", "none", "opus"), fmt("140", "m4a", "none", "mp4a.40.2"),
                   fmt("248", "webm", "vp9", "none", 1080), fmt("137", "mp4", "avc1.640028", "none", 1080),
                   fmt("401", "mp4", "av01.0.12M.08", "none", 2160)]
        instagram = youtube + [fmt("dash-720", "mp4", "avc1.64001f", "mp4a.40.2", 720)]
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            select = ydl.build_format_selector(fetch.FORMAT_SEPARATE)

            def picked(formats):
                incomplete = all(f["vcodec"] == "none" or f["acodec"] == "none" for f in formats)
                return [f["format_id"] for f in select({"formats": formats, "incomplete_formats": incomplete,
                                                         "has_merged_format": False})]

            self.assertEqual(picked(youtube), ["137", "140"])  # H.264 up to 1080p, never the 4K AV1
            self.assertEqual(picked(instagram), ["dash-720"])  # a combined file wins: nothing to remux

    def _fetch_separate(self, data):
        """_yt_dlp without ffmpeg where yt-dlp delivers the video and audio of `data` as two files."""
        import yt_dlp
        seen = []

        class FakeYDL:
            def __init__(self, options):
                seen.append(options)
                self.folder = Path(options["outtmpl"]).parent

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download):
                split_streams(data, self.folder)
                return {"title": "Separat", "uploader": "Kanal"}

        with mock.patch.object(yt_dlp, "YoutubeDL", FakeYDL), mock.patch.object(fetch.shutil, "which",
                                                                                 return_value=None):
            fetched = fetch._yt_dlp("https://www.youtube.com/watch?v=x")
        self.assertEqual(seen[0]["format"], fetch.FORMAT_SEPARATE)
        return fetched

    def test_separate_video_and_audio_are_remuxed_without_reencoding(self):
        original = synthetic_video()
        fetched = self._fetch_separate(original)
        self.assertEqual((fetched.mime, fetched.title, fetched.author), ("video/mp4", "Separat", "Kanal"))

        def packets(data, kind):
            with av.open(io.BytesIO(data)) as container:
                stream = container.streams.get(**{kind: 0})[0]
                return stream.codec_context.name, [bytes(p) for p in container.demux(stream) if p.dts is not None]

        for kind in ("video", "audio"):
            self.assertEqual(packets(fetched.data, kind), packets(original, kind))  # stream copy, bit for bit
        info = measure.probe(fetched.data)
        self.assertTrue(info["has_audio"])
        self.assertAlmostEqual(info["duration_s"], 4.5, delta=0.1)

    def test_separate_streams_respect_max_bytes(self):
        original = synthetic_video()
        with mock.patch.object(fetch, "MAX_BYTES", len(original) // 2), \
                self.assertRaisesRegex(fetch.FetchError, "200 MB"):
            self._fetch_separate(original)


BREAKDOWN = {
    "observations": "Mörk väg, sedan tänds ljuset.", "summary": "Mörker till ljus.", "format": "före/efter",
    "hook": {"first_seconds": "Mörk väg", "type": "problem", "why_it_stops": "Man vill se."},
    "structure": ["Krok: mörker", "Bevis: ljus"],
    "scenes": [{"id": "s1", "start_s": 0, "end_s": 1, "shot": "POV", "camera": "statisk", "shows": "väg",
                "action": "kör", "purpose": "krok"}],
    "audio": {"voice": "ingen", "music": "spänd", "cut_to_music": "ja"},
    "text_style": "versaler", "pacing": "snabbt", "cta": "Köp nu", "why_it_works": ["kontrast"],
    "mechanics": ["av → på"], "do_not_copy": ["deras logga"], "production_needs": ["bil på natten"],
    "quality_score": 8, "quality_note": "Stark kontrast.",
}


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True, APP_URL="http://127.0.0.1:8765")
class ReferenceServiceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.video = synthetic_video()

    def setUp(self):
        self.tmp = TemporaryDirectory()
        override = override_settings(MEDIA_ROOT=Path(self.tmp.name))
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(self.tmp.cleanup)
        self.user = get_user_model().objects.create_user(username="ref-owner")
        self.company = Company.objects.create(owner=self.user, name="Faiv", profile="Extraljus.", current="Grillkit.")
        self.account = AdAccount.objects.create(company=self.company, name="Konkurrent",
                                                page_url="https://www.facebook.com/123", page_id="123")

    def fake_call(self, model, *, schema, operation, **kwargs):
        if schema.__name__ == "Breakdown":
            self.assertTrue(kwargs["videos"][0].startswith("data:video/mp4;base64,"))
            return schema.model_validate(BREAKDOWN), {"model": model, "cost_usd": 0.004, "usage": {}}
        plan = {
            "title": "Vår", "angle": "Se mer", "why_this_angle": "Mörker", "keep_from_reference": ["av → på"],
            "beat_the_reference": ["riktig produkt"], "hook": "Mörk väg", "music": "spänd", "end_card": "Logga",
            "duration_s": 12,
            "scenes": [{"ref_scene": "s1", "start_s": 0, "end_s": 2, "shows": "väg", "camera": "POV",
                        "on_screen_text": "5 års garanti", "material": "mediabank", "asset_id": "påhittat-id",
                        "fact_ids": ["F4"]}],
        }
        return schema.model_validate(plan), {"model": model, "cost_usd": 0.003, "usage": {}}

    def test_url_to_breakdown_and_our_version(self):
        url = "https://www.facebook.com/ads/library/?id=555"
        ad = CompetitorAd.objects.create(account=self.account, external_id="555", creative={"headline": "Ljus"},
                                         creative_hash="h", first_seen_at=timezone.now(), last_seen_at=timezone.now(),
                                         start_date=timezone.localdate() - timedelta(days=90), is_active=True)
        got = fetch.Fetched(self.video, "video/mp4", url)
        with mock.patch.object(fetch, "fetch", return_value=got), \
                mock.patch("engine.openrouter._call", side_effect=self.fake_call):
            ref = service.process(self.company, url, model="google/test-model")
            again = service.process(self.company, url)  # same file → same reference, no new paid call
            entry = service.plan_our_version(ref, angle="Se mer")
        self.assertEqual(again.pk, ref.pk)
        ref.refresh_from_db()
        self.assertEqual(ref.status, "analyzed")
        self.assertEqual(ref.competitor_ad_id, ad.pk)
        self.assertEqual(ref.source_kind, "meta_ad")
        self.assertEqual(ref.title, "Ljus")
        self.assertEqual(ref.measurements["summary"]["scene_count"], 3)
        self.assertEqual(len(ref.analyses), 1)
        self.assertEqual(ref.breakdown["model"], "google/test-model")
        self.assertEqual(float(ref.cost_usd), 0.007)
        self.assertTrue(ref.sheet_key and ref.proxy_key)
        # Invented asset ids and unverified facts never reach the plan silently.
        scene = entry["plan"]["scenes"][0]
        self.assertEqual(scene["asset_id"], "")
        self.assertEqual(scene["material"], "filma")
        self.assertTrue(any("F4" in w for w in entry["warnings"]))
        data = service.serialize(ref, full=True)
        self.assertEqual(data["adaptations"][0]["title"], "Vår")
        self.assertEqual(data["breakdown"]["hook"]["type"], "problem")

    def test_candidates_rank_long_running_ads_with_reach(self):
        now = timezone.now()
        short = CompetitorAd.objects.create(account=self.account, external_id="1", creative={}, creative_hash="a",
                                            first_seen_at=now, last_seen_at=now, is_active=True,
                                            start_date=timezone.localdate() - timedelta(days=5))
        long = CompetitorAd.objects.create(account=self.account, external_id="2", creative={}, creative_hash="b",
                                           first_seen_at=now, last_seen_at=now, is_active=True,
                                           start_date=timezone.localdate() - timedelta(days=120))
        request = ScrapeRequest.objects.create(state=ads.account_state(self.account), key="r", actor=ads.ACTOR,
                                               mode="discovery", max_cost_usd=.15, inputs={}, status="succeeded")
        AdObservation.objects.create(ad=long, request=request, observed_at=now,
                                     data={"metrics": {"eu_total_reach": 40670}})
        other = AdAccount.objects.create(company=self.company, name="Annan", page_url="https://www.facebook.com/7",
                                         page_id="7")
        CompetitorAd.objects.create(account=other, external_id="3", creative={}, creative_hash="c", first_seen_at=now,
                                    last_seen_at=now, is_active=True, start_date=timezone.localdate() - timedelta(days=4))
        rows = service.candidates(self.company)
        self.assertEqual([r["ad_id"] for r in rows], ["2", "3", "1"])  # each advertiser's best first
        self.assertEqual(rows[0]["eu_reach"], 40670)
        self.assertEqual(rows[0]["url"], "https://www.facebook.com/ads/library/?id=2")
        self.assertIsNone(rows[1]["eu_reach"])
        self.assertTrue(short.pk)

    def test_facts_follow_the_fact_bank(self):
        from engine.ad_studio.models import AdFact

        claim = next(f["claim"] for f in adapt.facts(self.company) if f["id"] == "F4")
        AdFact.objects.create(company=self.company, claim=claim, status="verified")
        statuses = {f["id"]: f["status"] for f in adapt.facts(self.company)}
        self.assertEqual(statuses["F4"], "verified")
        self.assertEqual(statuses["F1"], "unverified")

    def test_mcp_tools(self):
        from asgiref.sync import async_to_sync

        from engine import mcp_server

        tools = {tool.name: tool for tool in async_to_sync(mcp_server.mcp.list_tools)()}
        for name in ("analyze_reference_video", "list_reference_candidates", "list_references", "get_reference",
                     "view_reference_sheet", "reanalyze_reference", "plan_our_version"):
            self.assertIn(name, tools)
        self.assertTrue(tools["get_reference"].annotations.read_only_hint)

        def registered(name):
            return mcp_server.mcp._tool_manager.get_tool(name).fn

        token = SimpleNamespace(claims={"django_user_id": self.user.pk})
        got = fetch.Fetched(self.video, "video/mp4", "https://example.com/a.mp4")
        with mock.patch("engine.mcp_auth.get_access_token", return_value=token), \
                mock.patch.object(fetch, "fetch", return_value=got), \
                mock.patch("engine.openrouter._call", side_effect=self.fake_call):
            made = registered("analyze_reference_video")(str(self.company.pk), "https://example.com/a.mp4")
            self.assertEqual(made["status"], "analyzed")
            sheet = registered("view_reference_sheet")(str(self.company.pk), made["reference_id"])
            self.assertTrue(sheet.data.startswith(b"\xff\xd8"))
            listed = registered("list_references")(str(self.company.pk))
            self.assertEqual(listed[0]["reference_id"], made["reference_id"])
            other = Company.objects.create(owner=get_user_model().objects.create_user(username="x"), name="Annan")
            ReferenceVideo.objects.filter(pk=made["reference_id"]).update(company=other)
            with self.assertRaises(Exception):
                registered("get_reference")(str(self.company.pk), made["reference_id"])


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True, APP_URL="http://127.0.0.1:8765")
class PostOutlierTests(TestCase):
    def test_videos_far_above_their_accounts_normal_views_are_candidates(self):
        from engine.models import Competitor, CompetitorImport, CompetitorPost, CompetitorSnapshot

        user = get_user_model().objects.create_user(username="outlier")
        company = Company.objects.create(owner=user, name="Golfkuponger")
        account = Competitor.objects.create(company=company, name="Timeplan", platform="tiktok", username="timeplango")
        run = CompetitorImport.objects.create(competitor=account, actor="apidojo/tiktok-scraper", status="succeeded")
        now = timezone.now()
        for i, views in enumerate((900, 1100, 1000, 1200, 203376, 5000)):
            post = CompetitorPost.objects.create(
                competitor=account, shortcode=str(100 + i), url=f"https://www.tiktok.com/@timeplango/video/{100 + i}",
                published_at=now - timedelta(days=5 + i), format="reel")
            CompetitorSnapshot.objects.create(post=post, import_run=run, observed_at=now, views=views)
        rows = service.post_outliers(company)
        self.assertEqual([r["post_id"] for r in rows], ["104", "105"])
        self.assertGreater(rows[0]["ratio"], 100)
        self.assertIn("TikTok", rows[0]["why"])
        mixed = service.candidates(company)
        self.assertEqual(mixed[0]["kind"], "post")
        self.assertEqual(mixed[0]["url"], "https://www.tiktok.com/@timeplango/video/104")


class AdMetricsTests(SimpleTestCase):
    def test_reach_is_kept_outside_the_creative(self):
        account = SimpleNamespace(page_id="12345")
        row = {"adId": "98765", "advertiserPageId": "12345", "adText": "Hej", "euTotalReach": 40670,
               "snapshotUrl": "https://www.facebook.com/ads/library/?id=98765", "adCreationTime": "2026-09-21"}
        item = ads.normalize(row, account)
        self.assertEqual(ads.metrics(row)["eu_total_reach"], 40670)
        self.assertEqual(ads.metrics(row)["created_date"], "2026-09-21")
        self.assertNotIn("metrics", item)
        self.assertIsNone(ads.metrics({**row, "euTotalReach": True})["eu_total_reach"])
        without = ads.normalize({k: v for k, v in row.items() if k != "euTotalReach"}, account)
        self.assertEqual(item["creative_hash"], without["creative_hash"])


@override_settings(MEDIA_STORAGE="local", LOCAL_HTTP=True, APP_URL="http://127.0.0.1:8765")
class ReferenceDailyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="daily-ref")
        self.company = Company.objects.create(owner=self.user, name="Faiv")
        account = AdAccount.objects.create(company=self.company, name="K", page_url="https://www.facebook.com/9",
                                           page_id="9")
        now = timezone.now()
        for ext, days in (("old", 60), ("older", 200), ("new", 3), ("third", 30)):
            CompetitorAd.objects.create(account=account, external_id=ext, creative={}, creative_hash=ext,
                                        first_seen_at=now, last_seen_at=now, is_active=True,
                                        start_date=timezone.localdate() - timedelta(days=days))

    def test_units_take_the_longest_running_ads_within_the_daily_limit(self):
        from engine import daily_stages

        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "k", "REFERENCE_DAILY_LIMIT": "2"}):
            self.assertEqual([k for k, _ in daily_stages.reference_units(self.company)], ["older", "old"])
        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "k", "REFERENCE_DAILY_LIMIT": "0"}):
            self.assertEqual(daily_stages.reference_units(self.company), [])

    def test_ad_without_video_is_skipped_not_failed(self):
        from engine import daily_stages

        with mock.patch.object(fetch, "fetch", side_effect=fetch.FetchError("Ingen video hittades på länken.")):
            result = daily_stages.breakdown_reference(self.company, "https://www.facebook.com/ads/library/?id=1")
        self.assertEqual(result.status, "skipped")
        self.assertFalse(ReferenceVideo.objects.exists())
