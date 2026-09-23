from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.template.loader import render_to_string

from .models import AdAccount, Company, CompetitorAd, ContentRun


class AppShellTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ui@example.test",
            password="test-only-password",
        )
        self.workspace = Company.objects.create(owner=self.user, name="Sänk Dig Golf")
        self.client.force_login(self.user)

    def test_workspace_pages_use_shared_app_shell_and_stylesheets(self):
        response = self.client.get(
            reverse("engine:intelligence", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, 'href="/static/css/studio.css"')
        self.assertContains(response, 'src="/static/js/studio.js"')
        self.assertContains(response, 'class="app-sidebar"')
        self.assertContains(response, 'class="app-topbar"')
        self.assertContains(response, "Insikter")

        self.assertEqual(self.client.get("/static/css/studio.css").status_code, 200)

    def test_workspace_shell_loads_htmx_and_editorial_workspace_styles(self):
        response = self.client.get(
            reverse("engine:home", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, "htmx.org@2.0.10")
        self.assertContains(response, 'href="/static/css/studio.css"')
        self.assertEqual(response.content.count(b'rel="stylesheet"'), 1)

    def test_workspace_shell_has_mobile_header_and_bottom_navigation(self):
        response = self.client.get(
            reverse("engine:home", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, 'class="mobile-header"')
        self.assertContains(response, 'class="mobile-bottom-nav"')
        self.assertContains(response, 'aria-label="Mobil navigation"')
        self.assertContains(response, ">Översikt<")
        self.assertContains(response, ">Insikter<")
        self.assertContains(response, ">Skapa<")
        self.assertContains(response, ">Inställningar<")

    def test_responsive_styles_include_touch_targets_safe_area_and_mobile_cards(self):
        stylesheet = self.client.get("/static/css/studio.css")
        css = b"".join(stylesheet.streaming_content).decode("utf-8")

        self.assertIn(".mobile-bottom-nav", css)
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(".mobile-table", css)
        self.assertIn("@media (max-width: 600px)", css)

    def test_settings_exposes_mobile_friendly_operational_table(self):
        response = self.client.get(
            reverse("engine:settings", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, 'class="data-table mobile-table"')
        self.assertContains(response, "Scraping · kostnad och nytt värde")

    def test_primary_screens_expose_product_specific_layouts(self):
        home = self.client.get(reverse("engine:home", kwargs={"workspace_id": self.workspace.pk}))
        organic = self.client.get(reverse("engine:intelligence", kwargs={"workspace_id": self.workspace.pk}))
        performance = self.client.get(reverse("engine:own_performance", kwargs={"workspace_id": self.workspace.pk}))
        settings = self.client.get(reverse("engine:settings", kwargs={"workspace_id": self.workspace.pk}))
        companies = self.client.get(reverse("dashboard"))

        self.assertContains(home, 'class="engine overview-page"')
        self.assertContains(home, 'class="overview-command"')
        self.assertContains(organic, 'organic-insights-page')
        self.assertContains(performance, 'performance-page')
        self.assertContains(settings, 'class="engine settings-page"')
        self.assertContains(settings, 'class="settings-layout"')
        self.assertContains(companies, 'workspace-page-v3')

    def test_review_and_media_are_task_specific_workspaces(self):
        run = ContentRun.objects.create(
            workspace=self.workspace,
            author=self.user,
            context={"source": "test", "valid_until": "2099-01-01"},
            ideas=[],
            draft={"facebook": "Facebook text", "instagram": "Instagram text", "photo_brief": "", "checks": []},
            model="test-model",
        )
        review = self.client.get(reverse("engine:review", kwargs={"workspace_id": self.workspace.pk, "run_id": run.pk}))
        media = self.client.get(reverse("engine:media", kwargs={"workspace_id": self.workspace.pk, "run_id": run.pk}))

        self.assertContains(review, 'class="engine review-page"')
        self.assertContains(review, 'class="review-progress"')
        self.assertContains(media, 'class="engine media-workspace"')


class AdsWorkspaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ads-ui@example.test",
            password="test-only-password",
        )
        self.workspace = Company.objects.create(owner=self.user, name="Sänk Dig Golf")
        self.account = AdAccount.objects.create(
            company=self.workspace,
            name="Shot Scope",
            page_url="https://www.facebook.com/123456789",
            page_id="123456789",
            country="SE",
        )
        now = timezone.now()
        self.ad = CompetitorAd.objects.create(
            account=self.account,
            external_id="987654321",
            creative={
                "headline": "Play Smarter Like Radar",
                "text": "Get data on your game and make better decisions.",
                "format": "image",
                "image_url": "https://images.example.test/shot-scope.jpg",
                "video_url": None,
                "cta": "LEARN_MORE",
                "landing_page": "https://example.test/product",
                "platforms": ["FACEBOOK", "INSTAGRAM"],
                "variant_count": 8,
            },
            creative_hash="creative-hash",
            classification={
                "message": "Data hjälper golfaren fatta bättre beslut.",
                "hook": "Social proof och datadrivet löfte",
                "cta": "Learn more",
                "offer": "Produktdemo",
                "themes": ["Datadriven golf"],
                "mechanisms": ["Social proof"],
                "adaptation": "Visa ett konkret beslut en amatörgolfare kan förbättra med verifierad data.",
                "unknowns": ["Faktisk annonsperformance är okänd."],
            },
            classification_hash="stale-until-view-computes-current",
            first_seen_at=now,
            last_seen_at=now,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_paid_intelligence_uses_two_pane_workspace_with_creative_preview(self):
        response = self.client.get(
            reverse("engine:intelligence", kwargs={"workspace_id": self.workspace.pk}),
            {"channel": "paid"},
        )
        detail_url = reverse(
            "engine:ad_detail",
            kwargs={"workspace_id": self.workspace.pk, "ad_id": self.ad.pk},
        )

        self.assertContains(response, 'class="ads-workspace workspace-split"')
        self.assertContains(response, 'id="ad-detail-panel"')
        self.assertContains(response, f'hx-get="{detail_url}"')
        self.assertContains(response, "https://images.example.test/shot-scope.jpg")
        self.assertContains(response, "Play Smarter Like Radar")

    def test_ad_detail_is_company_scoped_and_renders_editorial_detail(self):
        detail_url = reverse(
            "engine:ad_detail",
            kwargs={"workspace_id": self.workspace.pk, "ad_id": self.ad.pk},
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="workspace-detail-panel ad-detail-panel"')
        self.assertContains(response, "Play Smarter Like Radar")
        self.assertContains(response, "CTR, CPA och ROAS är okända")

        other = Company.objects.create(owner=self.user, name="Annat bolag")
        cross_company_url = reverse(
            "engine:ad_detail",
            kwargs={"workspace_id": other.pk, "ad_id": self.ad.pk},
        )
        self.assertEqual(self.client.get(cross_company_url).status_code, 404)

    def test_original_precedes_analysis_and_adaptation_without_losing_long_copy(self):
        self.ad.creative["text"] = "ORIGINAL " + "Lång caption utan förkortning. " * 150
        self.ad.analysis_current = True
        html = render_to_string("engine/ad_detail.html", {"ad": self.ad, "workspace": self.workspace})
        self.assertIn(self.ad.creative["text"], html)
        self.assertLess(html.index("Originalannons"), html.index("Budskap och mekanism"))
        self.assertLess(html.index("Budskap och mekanism"), html.index("Sänk Dig Golfs idé"))
        self.assertIn('name="channel" value="paid"', html)
        self.assertIn(f'name="signal_id" value="{self.ad.pk}"', html)

    def test_organic_original_is_complete_and_escaped_before_interpretation(self):
        from types import SimpleNamespace
        caption = "<script>alert(1)</script> " + "Originalinlägg med lång text. " * 100
        post = SimpleNamespace(pk=1, competitor=self.account, caption=caption,
            url="https://example.test/original", classification={"why": "ANALYS", "adaptation": "EGEN IDE"})
        html = render_to_string("engine/signal_card.html", {
            "workspace": self.workspace, "signal": {"id": "1", "post": post, "analysis_current": True},
        })
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("Originalinlägg med lång text. " * 100, html)
        self.assertLess(html.index('class="source-caption"'), html.index("ANALYS"))
        self.assertLess(html.index("ANALYS"), html.index("EGEN IDE"))
