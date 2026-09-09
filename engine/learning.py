"""Own seven-day outcomes only; chronological, purged evaluation; shadow by default.

JSON model coefficients are portable and inspectable. No pickle, service or training queue.
Editorial choices/rejections and competitor observations are never performance labels.
"""
import math
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ContentEvent, ContentRun, LearningModel, OwnOutcome, Prediction
from .sync import fingerprint

FEATURE_VERSION = "idea-features-v1"
TARGETS = {"organic":"interactions_per_1000_impressions_7d", "paid":"clicks_per_1000_impressions_7d"}
NUMERIC = ("profile_relevance", "current_relevance", "own_current_facts", "signal_score", "signal_confidence",
           "signal_relative", "has_signal", "format_video", "format_carousel", "is_instruction", "is_question")


def features(idea, context):
    signal = next((s for s in context.get("competitor_signals", []) if s["id"] == idea.get("signal_id")), {})
    mechanisms = signal.get("classification", {}).get("mechanisms", [])
    numeric = {"profile_relevance":idea.get("profile_relevance", 0), "current_relevance":idea.get("current_relevance", 0),
        "own_current_facts":int(idea.get("source_field") == "current"), "signal_score":signal.get("score", 0),
        "signal_confidence":signal.get("confidence", 0), "signal_relative":min(signal.get("relative") or 0, 10),
        "has_signal":int(bool(signal)), "format_video":int(signal.get("format") in ("reel", "video")),
        "format_carousel":int(signal.get("format") == "carousel"), "is_instruction":int("instruktion" in mechanisms),
        "is_question":int("fråga" in mechanisms)}
    return {"numeric":numeric, "signal":signal, "context_hash":fingerprint(context),
            "idea_hash":fingerprint({k:v for k,v in idea.items() if k not in ("ranking", "learning")}),
            "available_at":context.get("captured_at"), "feature_version":FEATURE_VERSION}


def predict(model, values):
    a = model.artifact
    return max(0., a["intercept"] + sum(c*(values[k]-m)/s for k,c,m,s in
        zip(NUMERIC, a["coefficients"], a["mean"], a["scale"], strict=True)))


def record_predictions(run):
    """Freeze forecasts before user choice or publication; shadow does not change ranking."""
    channel = run.channel
    production = LearningModel.objects.filter(company=run.workspace, channel=channel, mode="production").order_by("-trained_at").first()
    shadow = LearningModel.objects.filter(company=run.workspace, channel=channel, mode="shadow").order_by("-trained_at").first()
    models = [m for m in (production, shadow) if m] or [None]
    rows = [(idea, features(idea, run.context)) for idea in run.ideas]
    if production:
        rows.sort(key=lambda row: -predict(production, row[1]["numeric"]))
    with transaction.atomic():
        ContentRun.objects.select_for_update().get(pk=run.pk)
        if run.predictions.exists():
            return
        for index, (idea, data) in enumerate(rows):
            idea["learning"] = {"mode":"production" if production else "shadow", "target":TARGETS[channel],
                                "model_version":production.version if production else "heuristic-only"}
            for model in models:
                Prediction.objects.create(run=run, idea_index=index, channel=channel, features=data,
                    feature_version=FEATURE_VERSION, model=model, model_version=model.version if model else "heuristic-only",
                    target=TARGETS[channel], value=predict(model, data["numeric"]) if model else None,
                    mode=model.mode if model else "shadow")
        run.ideas = [row[0] for row in rows]
        run.save(update_fields=["ideas"])


def record_outcome(run, *, source, external_id, published_at, window_end, observed_at, metrics, evidence):
    from .ads import safe_url
    if run.selected is None:
        raise ValueError("Välj ett verkligt producerat innehåll före resultatregistrering.")
    if source not in ("meta_export", "postiz_export", "manual_verified") or not external_id.strip() or not safe_url(evidence):
        raise ValueError("Ange källa, verkligt post-/annons-id och en spårbar resultatlänk.")
    if any(timezone.is_naive(t) for t in (published_at, window_end, observed_at)):
        raise ValueError("Resultattider måste ha tidszon.")
    if window_end != published_at+timedelta(days=7) or not window_end <= observed_at <= timezone.now()+timedelta(minutes=5):
        raise ValueError("Resultatet ska avse exakt de första sju dygnen och vara observerat efter fönstrets slut.")
    required = ("impressions", "likes", "comments") if run.channel == "organic" else ("impressions", "clicks")
    allowed = {"impressions", "likes", "comments", "clicks", "conversions", "spend", "revenue"}
    if not isinstance(metrics, dict) or not set(required).issubset(metrics) or not set(metrics).issubset(allowed):
        raise ValueError("Saknade resultat får inte ersättas med noll. Ange mätta impressions och likes/kommentarer eller klick.")
    for key, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            raise ValueError("Resultat måste vara ändliga, icke-negativa mätvärden.")
        if key not in ("spend", "revenue") and int(value) != value:
            raise ValueError("Antal måste vara heltal.")
    if metrics["impressions"] <= 0:
        raise ValueError("Minst en mätt impression behövs för den valda labeln.")
    numerator = metrics["likes"]+metrics["comments"] if run.channel == "organic" else metrics["clicks"]
    label = 1000*numerator/metrics["impressions"]
    with transaction.atomic():
        # Serialize own outcomes by company; one external object cannot label multiple ideas.
        from .models import Company
        Company.objects.select_for_update().get(pk=run.workspace_id)
        prediction = run.predictions.filter(idea_index=run.selected, created_at__lte=published_at,
            channel=run.channel, feature_version=FEATURE_VERSION).order_by("created_at", "pk").first()
        if not prediction:
            raise ValueError("Det saknas en fryst prediction från före publiceringen. Retroaktivt skapade features används inte för ML.")
        existing = OwnOutcome.objects.filter(prediction__run__workspace_id=run.workspace_id,
            prediction__channel=run.channel, external_id=external_id.strip(), window_end=window_end).first()
        if existing:
            if existing.prediction.run_id != run.pk or existing.metrics != metrics or existing.published_at != published_at:
                raise ValueError("Resultatet finns redan med annat innehåll eller andra mätvärden; skriv inte över historiska labels.")
            return existing
        if OwnOutcome.objects.filter(prediction__run=run).exists():
            raise ValueError("Det finns redan ett sjudygnsresultat för detta innehåll. Skapa inte dubbla träningslabels.")
        outcome = OwnOutcome.objects.create(prediction=prediction, source=source, external_id=external_id.strip(),
            published_at=published_at, window_end=window_end, observed_at=observed_at, metrics=metrics, label=label, evidence=evidence)
        ContentEvent.objects.create(run=run, idea_index=run.selected, action="own_outcome",
            data={"outcome_id":outcome.pk, "channel":run.channel, "target":prediction.target, "source":source,
                  "draft_hash":fingerprint(run.draft), "media_asset_id":str(run.media_asset_id) if run.media_asset_id else None})
        return outcome


def dataset(company, channel, cutoff=None):
    cutoff = cutoff or timezone.now()
    return list(OwnOutcome.objects.filter(prediction__run__workspace=company, prediction__channel=channel,
        prediction__feature_version=FEATURE_VERSION, prediction__target=TARGETS[channel], recorded_at__lte=cutoff,
        observed_at__lte=cutoff, window_end__lte=cutoff).select_related("prediction").order_by("prediction__created_at", "pk"))


def train(company, channel):
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    cutoff = timezone.now()
    rows = dataset(company, channel, cutoff)
    if len(rows) < 80:
        return {"status":"insufficient", "labels":len(rows), "required":80, "channel":channel}
    candidate = LearningModel.objects.filter(company=company, channel=channel, mode="shadow").order_by("-trained_at").first()
    if candidate:
        shadow = shadow_evaluation(candidate)
        if shadow["count"] < 20 or shadow["eligible"]:
            # Keep one candidate long enough to accumulate actual prospective evidence.
            return {"status":"cached", "model_version":candidate.version, "mode":"shadow", "shadow":shadow}
        candidate.mode = "rejected"
        candidate.save(update_fields=["mode"])
    version = fingerprint(["ridge-v1", channel, FEATURE_VERSION, [(r.pk,r.label) for r in rows]])
    existing = LearningModel.objects.filter(company=company, channel=channel, version=version).first()
    if existing:
        return {"status":"cached", "model_version":version, "mode":existing.mode}
    holdout = rows[-max(20, len(rows)//4):]
    # Purge labels that were unavailable when the earliest holdout prediction was made.
    boundary = holdout[0].prediction.created_at
    training = [r for r in rows[:-len(holdout)] if max(r.window_end, r.observed_at, r.recorded_at) < boundary]
    if len(training) < 40:
        return {"status":"insufficient_temporal_history", "labels":len(rows), "purged_train":len(training), "channel":channel}
    def matrix(items):
        return np.asarray([[r.prediction.features["numeric"][k] for k in NUMERIC] for r in items], dtype=float)
    scaler = StandardScaler().fit(matrix(training))
    model = Ridge(alpha=10.).fit(scaler.transform(matrix(training)), [r.label for r in training])
    actual = np.asarray([r.label for r in holdout])
    predicted = np.maximum(model.predict(scaler.transform(matrix(holdout))), 0)
    baseline = float(np.mean([r.label for r in training]))
    mae, baseline_mae = float(np.mean(abs(actual-predicted))), float(np.mean(abs(actual-baseline)))
    evaluation = {"train":len(training), "test":len(holdout), "mae":mae, "baseline_mae":baseline_mae,
                  "improvement":1-mae/baseline_mae if baseline_mae > 0 else 0,
                  "holdout_after":boundary.isoformat(), "train_outcome_ids":[r.pk for r in training],
                  "test_outcome_ids":[r.pk for r in holdout], "baseline":baseline,
                  "target":TARGETS[channel], "split":"chronological_purged", "causal_claim":False}
    artifact = {"coefficients":model.coef_.tolist(), "intercept":float(model.intercept_),
                "mean":scaler.mean_.tolist(), "scale":scaler.scale_.tolist(), "features":list(NUMERIC),
                "feature_version":FEATURE_VERSION, "algorithm":"sklearn.Ridge(alpha=10)"}
    instance, _ = LearningModel.objects.get_or_create(company=company, channel=channel, version=version,
        defaults={"target":TARGETS[channel], "training_cutoff":cutoff, "artifact":artifact, "evaluation":evaluation})
    return {"status":"trained", "model_version":version, "mode":instance.mode, "evaluation":evaluation}


def shadow_evaluation(model):
    outcomes = {r.prediction.run_id:r for r in dataset(model.company, model.channel)}
    pairs = [(p, outcomes[p.run_id]) for p in Prediction.objects.filter(model=model, mode="shadow").select_related("run")
             if p.run_id in outcomes and p.idea_index == p.run.selected and p.created_at <= outcomes[p.run_id].published_at
             and p.value is not None]
    if not pairs:
        return {"count":0, "eligible":False}
    mae = sum(abs(p.value-o.label) for p,o in pairs)/len(pairs)
    baseline_mae = sum(abs(model.evaluation["baseline"]-o.label) for _,o in pairs)/len(pairs)
    return {"count":len(pairs), "mae":mae, "baseline_mae":baseline_mae,
            "eligible":len(pairs)>=20 and baseline_mae>0 and mae <= baseline_mae*.9 and model.evaluation.get("improvement", 0)>=.1}


def promote(model):
    evaluation = shadow_evaluation(model)
    if not evaluation["eligible"]:
        raise ValueError("Modellen saknar tillräckligt bra tidsdelad utvärdering och minst 20 egna shadow-resultat.")
    from .models import Company
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=model.company_id)
        LearningModel.objects.filter(company=model.company, channel=model.channel, mode="production").update(mode="retired")
        model.mode = "production"
        model.evaluation["promotion_shadow"] = evaluation
        model.save(update_fields=["mode", "evaluation"])
