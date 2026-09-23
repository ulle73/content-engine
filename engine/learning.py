"""Own seven-day outcomes only; chronological, purged evaluation; shadow by default.

JSON model coefficients are portable and inspectable. No pickle, service or training queue.
Editorial choices/rejections and competitor observations are never performance labels.
"""
import math
from datetime import timedelta
from statistics import median

from django.db import transaction
from django.utils import timezone

from .models import ContentEvent, ContentRun, LearningModel, OwnOutcome, Prediction
from .sync import fingerprint
from .learning_targets import DEFAULTS as TARGETS, actual, available_paid, spec

FEATURE_VERSION = "idea-features-v1"
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


def _clip(value, limit=360):
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def _run_generation_example(run):
    if run.selected is None or run.selected >= len(run.ideas):
        return None
    idea = run.ideas[run.selected] or {}
    draft = run.draft or {}
    final_copy = draft.get("instagram") or draft.get("facebook") or ""
    return {
        "title": _clip(idea.get("title"), 120),
        "angle": _clip(idea.get("angle"), 260),
        "photo_brief": _clip(idea.get("photo_brief"), 220),
        "final_copy_excerpt": _clip(final_copy, 420),
    }


def _outcome_relative(outcome, target_medians):
    baseline = (outcome.snapshot.baseline or {}) if outcome.snapshot_id else {}
    relative = baseline.get("relative")
    peers = int(baseline.get("peers") or 0)
    if isinstance(relative, (int, float)) and math.isfinite(relative) and relative >= 0 and peers >= 3:
        return min(float(relative), 5.0), {
            "basis": "own_age_baseline",
            "peers": peers,
            "confidence": baseline.get("confidence_label") or "low",
        }

    values = target_medians.get(outcome.target)
    if not values or len(values) < 3:
        return None, None
    benchmark = median(values)
    if not math.isfinite(benchmark) or benchmark <= 0 or not math.isfinite(outcome.label) or outcome.label < 0:
        return None, None
    higher_is_better = spec(outcome.target)[3]
    if higher_is_better:
        relative = outcome.label / benchmark
    elif outcome.label == 0:
        relative = 5.0
    else:
        relative = benchmark / outcome.label
    return min(max(float(relative), 0.0), 5.0), {
        "basis": "same_target_median",
        "target": outcome.target,
        "sample_size": len(values),
    }


def generation_guidance(company, channel):
    """Compact closed-loop guidance for future generation.

    Verified own outcomes may guide performance patterns. Editorial choices,
    rejections and edits are separate preference signals and are never treated
    as performance labels. Historical copy is reference material only, never a
    source of current company facts.
    """
    outcomes = list(
        OwnOutcome.objects.filter(
            prediction__run__workspace=company,
            prediction__channel=channel,
        )
        .select_related("prediction__run", "snapshot")
        .order_by("-recorded_at")[:120]
    )
    target_values = {}
    for outcome in outcomes:
        if isinstance(outcome.label, (int, float)) and math.isfinite(outcome.label):
            target_values.setdefault(outcome.target, []).append(float(outcome.label))

    by_run = {}
    for outcome in outcomes:
        run = outcome.prediction.run
        if run.selected is None or outcome.prediction.idea_index != run.selected:
            continue
        relative, basis = _outcome_relative(outcome, target_values)
        if relative is None:
            continue
        row = by_run.setdefault(
            run.pk,
            {"run": run, "relative": [], "bases": [], "observed_at": outcome.observed_at},
        )
        row["relative"].append(relative)
        row["bases"].append(basis)
        row["observed_at"] = max(row["observed_at"], outcome.observed_at)

    performance_rows = []
    for row in by_run.values():
        example = _run_generation_example(row["run"])
        if not example:
            continue
        score = sum(row["relative"]) / len(row["relative"])
        performance_rows.append(
            {
                **example,
                "relative_to_own_norm": round(score, 2),
                "signal": "stronger" if score >= 1.05 else ("weaker" if score < 0.95 else "typical"),
                "measurement": row["bases"],
                "observed_at": row["observed_at"].isoformat(),
            }
        )
    performance_rows.sort(key=lambda item: item["relative_to_own_norm"], reverse=True)
    sample_size = len(performance_rows)
    confidence = "none" if sample_size < 3 else ("early" if sample_size < 8 else ("growing" if sample_size < 20 else "established"))
    strong_candidates = [item for item in performance_rows if item["relative_to_own_norm"] >= 1.05]
    weak_candidates = [item for item in reversed(performance_rows) if item["relative_to_own_norm"] < 0.95]
    strong = strong_candidates[:3] if sample_size >= 3 else []
    weak = weak_candidates[:2] if sample_size >= 3 else []

    events = list(
        ContentEvent.objects.filter(
            run__workspace=company,
            run__channel=channel,
            action__in=("selected", "rejected", "edited"),
        )
        .select_related("run")
        .order_by("-created_at")[:80]
    )
    selected, rejected, edits = [], [], []
    selected_seen, rejected_seen = set(), set()
    for event in events:
        if event.action in {"selected", "rejected"}:
            idea = (event.data or {}).get("idea") or {}
            title = _clip(idea.get("title"), 120)
            angle = _clip(idea.get("angle"), 240)
            if not title and not angle:
                continue
            key = (title, angle)
            bucket = selected if event.action == "selected" else rejected
            seen = selected_seen if event.action == "selected" else rejected_seen
            if key not in seen and len(bucket) < 4:
                bucket.append({"title": title, "angle": angle})
                seen.add(key)
        elif event.action == "edited" and len(edits) < 3:
            data = event.data or {}
            before = data.get("before") if isinstance(data.get("before"), dict) else {}
            after = data.get("after") if isinstance(data.get("after"), dict) else {}
            before_copy = before.get("instagram") or before.get("facebook") or ""
            after_copy = after.get("instagram") or after.get("facebook") or ""
            if before_copy and after_copy and before_copy != after_copy:
                edits.append(
                    {
                        "before_excerpt": _clip(before_copy, 320),
                        "after_excerpt": _clip(after_copy, 320),
                    }
                )

    editorial_count = sum(1 for event in events if event.action in {"selected", "rejected"})
    return {
        "version": "generation-learning-v1",
        "performance": {
            "sample_size": sample_size,
            "confidence": confidence,
            "strong_examples": strong,
            "weak_examples": weak,
            "instruction": (
                "Lär mekanism, struktur och tonalitet från egna verifierade resultat. "
                "Kopiera aldrig historiska formuleringar eller fakta. Svagare exempel är varningssignaler, inte absoluta förbud."
            ),
        },
        "editorial": {
            "signal_count": editorial_count,
            "selected_examples": selected,
            "rejected_examples": rejected,
            "edit_examples": edits,
            "instruction": (
                "Detta visar redaktionell preferens, inte performance. Följ återkommande stilval och undvik tydligt avvisade vinklar, "
                "men låt verifierad performance väga tyngre."
            ),
        },
    }


def generation_guidance_summary(company, channel):
    guidance = generation_guidance(company, channel)
    return {
        "performance_examples": guidance["performance"]["sample_size"],
        "performance_confidence": guidance["performance"]["confidence"],
        "editorial_signals": guidance["editorial"]["signal_count"],
        "edit_examples": len(guidance["editorial"]["edit_examples"]),
        "version": guidance["version"],
    }


def predict(model, values):
    a = model.artifact
    return max(0., a["intercept"] + sum(c*(values[k]-m)/s for k,c,m,s in
        zip(NUMERIC, a["coefficients"], a["mean"], a["scale"], strict=True)))


def record_predictions(run):
    """Freeze forecasts before user choice or publication; shadow does not change ranking."""
    channel = run.channel
    production = LearningModel.objects.filter(company=run.workspace, channel=channel, mode="production").order_by("-trained_at").first()
    shadows = list(LearningModel.objects.filter(company=run.workspace, channel=channel, mode="shadow").order_by("-trained_at"))
    models = ([production] if production else []) + shadows or [None]
    rows = [(idea, features(idea, run.context)) for idea in run.ideas]
    if production:
        direction = -1 if spec(production.target)[3] else 1
        rows.sort(key=lambda row: direction*predict(production, row[1]["numeric"]))
    with transaction.atomic():
        ContentRun.objects.select_for_update().get(pk=run.pk)
        if run.predictions.exists():
            return
        for index, (idea, data) in enumerate(rows):
            idea["learning"] = {"mode":"production" if production else "shadow", "target":production.target if production else TARGETS[channel],
                                "model_version":production.version if production else "heuristic-only"}
            for model in models:
                Prediction.objects.create(run=run, idea_index=index, channel=channel, features=data,
                    feature_version=FEATURE_VERSION, model=model, model_version=model.version if model else "heuristic-only",
                    target=model.target if model else TARGETS[channel], value=predict(model, data["numeric"]) if model else None,
                    mode=model.mode if model else "shadow")
        run.ideas = [row[0] for row in rows]
        run.save(update_fields=["ideas"])


def record_outcome(run, *, source, external_id, published_at, window_end, observed_at, metrics, evidence, target=None, platform="", snapshot=None):
    from .ads import safe_url
    if run.selected is None:
        raise ValueError("Välj ett verkligt producerat innehåll före resultatregistrering.")
    if source not in ("meta_export", "postiz_export", "manual_verified", "postiz_api") or not isinstance(external_id,str) or not external_id.strip() or not safe_url(evidence):
        raise ValueError("Ange källa, verkligt post-/annons-id och en spårbar resultatlänk.")
    if any(timezone.is_naive(t) for t in (published_at, window_end, observed_at)):
        raise ValueError("Resultattider måste ha tidszon.")
    auto = source == "postiz_api"
    if auto and (not snapshot or snapshot.post.run_id != run.pk or snapshot.post.company_id != run.workspace_id or snapshot.metrics != metrics or snapshot.observed_at != window_end):
        raise ValueError("Automatiskt resultat kräver en riktig matchad snapshot.")
    valid_window = published_at+timedelta(days=7) <= window_end < published_at+timedelta(days=8) if auto else window_end == published_at+timedelta(days=7)
    if not valid_window or not window_end <= observed_at <= timezone.now()+timedelta(minutes=5):
        raise ValueError("Resultatet ska avse exakt de första sju dygnen och vara observerat efter fönstrets slut.")
    allowed = {"impressions", "likes", "comments", "clicks", "conversions", "spend", "revenue", "currency", "views", "reach", "reactions", "saves", "shares"}
    if not isinstance(metrics, dict) or not set(metrics).issubset(allowed):
        raise ValueError("Saknade resultat får inte ersättas med noll. Ange mätta impressions och likes/kommentarer eller klick.")
    for key, value in metrics.items():
        if key == "currency":
            import re
            if not isinstance(value,str) or not re.fullmatch(r"[A-Z]{3}",value):
                raise ValueError("Ange en valutakod med tre versaler.")
            continue
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            raise ValueError("Resultat måste vara ändliga, icke-negativa mätvärden.")
        if key not in ("spend", "revenue") and int(value) != value:
            raise ValueError("Antal måste vara heltal.")
    target = target or (next(iter(available_paid(metrics)),TARGETS["paid"]) if run.channel == "paid" else TARGETS["organic"])
    if spec(target)[4] != run.channel or ("7to8d" in target) != auto:
        raise ValueError("Målets kanal och tidsfönster måste matcha resultatkällan.")
    label = actual(target,metrics)
    with transaction.atomic():
        # Serialize own outcomes by company; one external object cannot label multiple ideas.
        from .models import Company
        Company.objects.select_for_update().get(pk=run.workspace_id)
        predictions = run.predictions.filter(idea_index=run.selected, created_at__lte=published_at,
            channel=run.channel, feature_version=FEATURE_VERSION).order_by("created_at", "pk")
        prediction = predictions.filter(target=target).first() or predictions.first()
        if not prediction:
            raise ValueError("Det saknas en fryst prediction från före publiceringen. Retroaktivt skapade features används inte för ML.")
        existing = OwnOutcome.objects.filter(prediction__run__workspace_id=run.workspace_id,
            prediction__channel=run.channel, external_id=external_id.strip(), target=target, window_end=window_end).first()
        if existing:
            if existing.prediction.run_id != run.pk or existing.metrics != metrics or existing.published_at != published_at:
                raise ValueError("Resultatet finns redan med annat innehåll eller andra mätvärden; skriv inte över historiska labels.")
            return existing
        if OwnOutcome.objects.filter(prediction__run=run,target=target,platform=platform).exists():
            raise ValueError("Det finns redan ett sjudygnsresultat för detta innehåll. Skapa inte dubbla träningslabels.")
        outcome = OwnOutcome.objects.create(prediction=prediction, source=source, external_id=external_id.strip(),
            published_at=published_at, window_end=window_end, observed_at=observed_at, metrics=metrics, label=label, evidence=evidence,
            target=target,platform=platform,snapshot=snapshot)
        ContentEvent.objects.create(run=run, idea_index=run.selected, action="own_outcome",
            data={"outcome_id":outcome.pk, "channel":run.channel, "target":target, "source":source,
                  "draft_hash":fingerprint(run.draft), "media_asset_id":str(run.media_asset_id) if run.media_asset_id else None})
        return outcome


def dataset(company, channel, cutoff=None, target=None):
    cutoff = cutoff or timezone.now()
    return list(OwnOutcome.objects.filter(prediction__run__workspace=company, prediction__channel=channel,
        prediction__feature_version=FEATURE_VERSION, target=target or TARGETS[channel], recorded_at__lte=cutoff,
        observed_at__lte=cutoff, window_end__lte=cutoff).select_related("prediction").order_by("prediction__created_at", "pk"))


def train(company, channel, target=None):
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    cutoff = timezone.now()
    target = target or TARGETS[channel]
    if spec(target)[4] != channel:
        raise ValueError("Fel kanal för learning-målet.")
    rows = dataset(company, channel, cutoff, target)
    if len(rows) < 80:
        return {"status":"insufficient", "labels":len(rows), "required":80, "channel":channel}
    candidate = LearningModel.objects.filter(company=company, channel=channel, target=target, mode="shadow").order_by("-trained_at").first()
    if candidate:
        shadow = shadow_evaluation(candidate)
        if shadow["count"] < 20 or shadow["eligible"]:
            # Keep one candidate long enough to accumulate actual prospective evidence.
            return {"status":"cached", "model_version":candidate.version, "mode":"shadow", "shadow":shadow}
        candidate.mode = "rejected"
        candidate.save(update_fields=["mode"])
    version = fingerprint(["ridge-v2", channel, target, FEATURE_VERSION, [(r.pk,r.label) for r in rows]])
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
                  "target":target, "split":"chronological_purged", "causal_claim":False}
    artifact = {"coefficients":model.coef_.tolist(), "intercept":float(model.intercept_),
                "mean":scaler.mean_.tolist(), "scale":scaler.scale_.tolist(), "features":list(NUMERIC),
                "feature_version":FEATURE_VERSION, "algorithm":"sklearn.Ridge(alpha=10)"}
    instance, _ = LearningModel.objects.get_or_create(company=company, channel=channel, version=version,
        defaults={"target":target, "training_cutoff":cutoff, "artifact":artifact, "evaluation":evaluation})
    return {"status":"trained", "model_version":version, "mode":instance.mode, "evaluation":evaluation}


def shadow_evaluation(model):
    outcomes = {r.prediction.run_id:r for r in dataset(model.company, model.channel,target=model.target)}
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
