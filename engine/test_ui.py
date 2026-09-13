from datetime import timedelta
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AdAccount, Company, CompetitorAd, ContentRun


class UIElements(HTMLParser):
    def __init__(self, response):
        super().__init__()
        self.elements = []
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def by_id(self, element_id):
        return next(attrs for _, attrs in self.elements if attrs.get("id") == element_id)


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

        self.assertContains(response, 'href="/static/css/app.css"')
        self.assertContains(response, 'href="/static/css/responsive-v2.css"')
        self.assertContains(response, 'class="app-sidebar"')
        self.assertContains(response, 'class="app-topbar"')
        self.assertContains(response, "Inspiration")

        self.assertEqual(self.client.get("/static/css/app.css").status_code, 200)
        self.assertEqual(self.client.get("/static/css/responsive-v2.css").status_code, 200)

    def test_workspace_shell_loads_htmx_and_editorial_workspace_styles(self):
        response = self.client.get(
            reverse("engine:home", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, "htmx.org@2.0.10")
        self.assertContains(response, 'href="/static/css/workspace-v3.css"')
        self.assertContains(response, 'href="/static/css/product-polish.css"')
        self.assertEqual(self.client.get("/static/css/workspace-v3.css").status_code, 200)
        self.assertEqual(self.client.get("/static/css/product-polish.css").status_code, 200)

    def test_workspace_shell_has_mobile_header_and_bottom_navigation(self):
        response = self.client.get(
            reverse("engine:home", kwargs={"workspace_id": self.workspace.pk})
        )

        self.assertContains(response, 'class="mobile-header"')
        self.assertContains(response, 'class="mobile-bottom-nav"')
        self.assertContains(response, 'aria-label="Mobil navigation"')
        self.assertContains(response, ">Resultat<")
        self.assertContains(response, ">Inspiration<")
        self.assertContains(response, ">Skapa<")
        self.assertContains(response, ">Inställningar<")
        self.assertContains(response, ">Kostnader<")

    def test_responsive_styles_include_touch_targets_safe_area_and_mobile_cards(self):
        stylesheet = self.client.get("/static/css/responsive-v2.css")
        css = b"".join(stylesheet.streaming_content).decode("utf-8")

        self.assertIn(".mobile-bottom-nav", css)
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(".mobile-table", css)
        self.assertIn("@media (max-width: 720px)", css)

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
        self.assertContains(settings, 'settings-page-premium')
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
        self.assertContains(review, 'premium-review-progress')
        self.assertContains(media, 'class="engine media-workspace"')

    def test_missing_or_expired_company_details_open_before_generation(self):
        url = reverse("engine:home", kwargs={"workspace_id": self.workspace.pk})
        response = self.client.get(url)
        self.assertIn("open", UIElements(response).by_id("company-context"))
        self.assertContains(response, "Fyll i företagsuppgifter")
        self.assertNotContains(response, 'data-busy-label="Tar fram idéer…"')
        self.workspace.profile = "Vi hjälper nya golfare."
        self.workspace.current = "Träning varje vecka."
        self.workspace.source = "Träningsprogrammet"
        self.workspace.valid_until = timezone.localdate() - timedelta(days=1)
        self.workspace.save()
        response = self.client.get(url)
        self.assertIn("open", UIElements(response).by_id("company-context"))
        self.assertContains(response, "Uppdatera företagsuppgifter")

    def test_ready_company_shows_one_generation_action_and_preserves_paid_channel(self):
        self.workspace.profile = "Golfträning"
        self.workspace.current = "Höstkurser"
        self.workspace.source = "Kursplanen"
        self.workspace.valid_until = timezone.localdate() + timedelta(days=1)
        self.workspace.save()
        response = self.client.get(reverse("engine:home", kwargs={"workspace_id": self.workspace.pk}), {"channel": "paid"})
        self.assertNotIn("open", UIElements(response).by_id("company-context"))
        self.assertContains(response, 'name="channel" value="paid"', count=1)
        self.assertContains(response, "Ge mig tre idéer", count=1)
        self.assertContains(response, reverse("engine:ideas", kwargs={"workspace_id": self.workspace.pk}))
        for name in ("profile", "voice", "current", "source", "valid_until"):
            self.assertContains(response, f'name="{name}"')

    def test_invalid_company_form_is_visible_and_preserves_input(self):
        response = self.client.post(reverse("engine:home", kwargs={"workspace_id": self.workspace.pk}), {
            "profile": "Min profil", "current": "Nytt erbjudande", "voice": "Vår röst",
            "source": "Vår webbplats", "valid_until": "invalid-date",
        })
        self.assertIn("open", UIElements(response).by_id("company-context"))
        self.assertContains(response, "Min profil")
        self.assertContains(response, 'class="errorlist"')

    def test_navigation_has_five_distinct_destinations_and_one_active_item_per_menu(self):
        response = self.client.get(reverse("engine:own_performance", kwargs={"workspace_id": self.workspace.pk}))
        elements = UIElements(response).elements
        for link_class in ("app-nav-link", "mobile-nav-link"):
            links = [attrs for tag, attrs in elements if tag == "a" and link_class in attrs.get("class", "").split()]
            self.assertEqual(len(links), 5)
            self.assertEqual(len({link["href"] for link in links}), 5)
            active = [link for link in links if link.get("aria-current") == "page"]
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["href"], reverse("engine:own_performance", kwargs={"workspace_id": self.workspace.pk}))

    def test_advanced_settings_remain_available_in_closed_disclosure(self):
        response = self.client.get(reverse("engine:settings", kwargs={"workspace_id": self.workspace.pk}))
        elements = UIElements(response)
        self.assertNotIn("open", elements.by_id("advanced"))
        self.assertEqual(elements.by_id("scraping")["id"], "scraping")
        self.assertContains(response, 'id="daily"')
        self.assertContains(response, 'name="logo"')

    def test_review_retains_delivery_guard_and_paid_has_no_send_action(self):
        run = ContentRun.objects.create(workspace=self.workspace, author=self.user, context={}, model="test", draft={"facebook": "Text", "instagram": "Text"})
        self.workspace.postiz_channels = [{"id": "channel-1", "name": "Golf", "identifier": "facebook"}]
        self.workspace.save()
        url = reverse("engine:review", kwargs={"workspace_id": self.workspace.pk, "run_id": run.pk})
        response = self.client.get(url)
        for name in ("facebook", "instagram", "channels", "reviewed"):
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, 'name="action" value="save"')
        self.assertContains(response, 'name="action" value="send"')
        run.channel = "paid"
        run.save()
        response = self.client.get(url)
        self.assertNotContains(response, 'value="send"')
        self.assertContains(response, 'name="headline"')
        run.channel = "organic"
        run.delivery_status = "unknown"
        run.save()
        response = self.client.get(url)
        self.assertNotContains(response, 'value="send"')
        self.assertContains(response, 'name="checked_postiz"')
        self.assertContains(response, 'value="reset"')

    def test_media_generation_is_optional_but_variant_and_retry_links_open_it(self):
        run = ContentRun.objects.create(workspace=self.workspace, author=self.user, context={}, model="test", draft={})
        url = reverse("engine:media", kwargs={"workspace_id": self.workspace.pk, "run_id": run.pk})
        response = self.client.get(url)
        self.assertNotIn("open", UIElements(response).by_id("generate"))
        for name in ("token", "kind", "brief", "shape", "count"):
            self.assertContains(response, f'name="{name}"')
        response = self.client.get(url, {"kind": "video"})
        self.assertIn("open", UIElements(response).by_id("generate"))
        self.assertContains(response, 'name="kind" value="video"')


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
        self.assertContains(response, "Konkurrentens annonsresultat är inte tillgängliga.")

        other = Company.objects.create(owner=self.user, name="Annat bolag")
        cross_company_url = reverse(
            "engine:ad_detail",
            kwargs={"workspace_id": other.pk, "ad_id": self.ad.pk},
        )
        self.assertEqual(self.client.get(cross_company_url).status_code, 404)
