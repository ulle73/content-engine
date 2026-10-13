import uuid

from django.db import models


class IdeaCard(models.Model):
    """A hit someone posted (or we posted ourselves) pitched as a short idea for our own version.

    Found by the daily job (engine/ideas/service.py), broken down as a ReferenceVideo and pitched in one sentence. Only
    the best reach Discord, and only a few a week: the owner reads a short summary, opens the original and answers
    👍 Skapa / 👎 / betyg / kommentar. 👍 turns the pitch into a plan and a list of what the company must supply.
    """

    STATUSES = [
        ("pitched", "Föreslagen"),      # pitched, waiting for its turn (or below the bar)
        ("sent", "Skickad"),            # card in Discord, waiting for a verdict
        ("approved", "Skapa"),          # 👍 – plan and material list being made / made
        ("rejected", "Nej"),
        ("skipped", "Inte bra nog"),    # never sent: below the fit bar or too old
        ("failed", "Misslyckades"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("engine.Company", on_delete=models.CASCADE, related_name="idea_cards")
    reference = models.ForeignKey("engine.ReferenceVideo", null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="idea_cards")
    # "ad:<library id>" or "<platform>:<post id>": one card per source and company.
    source_key = models.CharField(max_length=120)
    source_url = models.URLField(max_length=2000)
    own = models.BooleanField(default=False)
    # The numbers that make it a hit: {kind, views, baseline_views, ratio, days_running, active, eu_reach, advertiser}.
    signal = models.JSONField(default=dict, blank=True)
    why = models.CharField(max_length=300)          # "Timeplan: 328 000 visningar, 9,4× kontots normala"
    summary = models.CharField(max_length=300, blank=True)   # what the original is, one sentence
    spin = models.TextField(blank=True)             # our version, one or two sentences
    fit = models.PositiveSmallIntegerField(null=True, blank=True)  # 1–10: how good an idea it is for us
    fit_note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="pitched")
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    feedback = models.JSONField(default=list, blank=True)   # [{kind, text, rating, by, at}]
    adaptation_id = models.CharField(max_length=20, blank=True)
    needs = models.JSONField(default=list, blank=True)      # what the company must supply, one line each
    error = models.TextField(blank=True)
    discord_channel_id = models.CharField(max_length=32, blank=True)
    discord_message_id = models.CharField(max_length=32, blank=True)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["company", "source_key"], name="unique_idea_source")]

    def __str__(self):
        return self.why
