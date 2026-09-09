"""Published Postiz objects and current lifetime metrics; no invented historical series."""
import json
import math
from datetime import datetime, timedelta
from statistics import median

from django.db import transaction
from django.utils import timezone

from . import postiz
from .models import ContentRun, OwnPost, OwnSnapshot, OwnOutcome
from .sync import fingerprint, state_for

CONTRACT = "postiz-current-totals-v1"


def timestamp(value):
    result=datetime.fromisoformat(value.replace("Z","+00:00"))
    if timezone.is_naive(result):
        raise ValueError("Källan saknar tidszon.")
    return result


def matching_run(company, post_id, integration_id):
    matches=[]
    for run in ContentRun.objects.filter(workspace=company,channel="organic",delivery_status="sent").select_related("media_asset"):
        if any(isinstance(item,dict) and item.get("postId")==post_id and item.get("integration")==integration_id for item in run.delivery_result):
            matches.append(run)
    return matches[0] if len(matches)==1 else None


def normalize_post(company,row):
    if row.get("state") != "PUBLISHED":
        return None
    channel=row.get("integration",{})
    allowed={c["id"]:c["identifier"] for c in company.postiz_channels}
    if channel.get("id") not in allowed or channel.get("providerIdentifier") != allowed[channel["id"]]:
        return None
    platform="instagram" if allowed[channel["id"]].startswith("instagram") else "facebook"
    if platform not in ("instagram","facebook") or not row.get("id") or not row.get("releaseId"):
        raise ValueError("Publicerat inlägg saknar säker extern identitet.")
    published=timestamp(row["publishDate"])
    if published>timezone.now():
        raise ValueError("Publiceringstiden ligger i framtiden.")
    run=matching_run(company,row["id"],channel["id"])
    settings=row.get("settings") or {}
    if isinstance(settings,str):
        settings=json.loads(settings)
    kind="reel" if settings.get("post_type") in ("reel","reels") else "unknown"
    # Public list endpoint omits media. A generic post setting does not prove image vs carousel.
    if kind=="unknown" and run and run.media_asset_id:
        kind=run.media_asset.kind
    return dict(company=company,postiz_id=str(row["id"]),integration_id=channel["id"],release_id=str(row["releaseId"]),
        platform=platform,format=kind,caption=str(row.get("content") or ""),url=str(row.get("releaseURL") or ""),published_at=published,run=run)


def discover(company):
    if not company.postiz_ciphertext or not company.postiz_channels:
        return {"status":"skipped","message":"Postiz-koppling saknas."}
    state=state_for(company,"postiz_own",fingerprint(sorted(c["id"] for c in company.postiz_channels)))
    now=timezone.now()
    if state.next_attempt_at and state.next_attempt_at>now:
        return {"status":"skipped","message":"Egna publiceringar kontrollerades nyligen."}
    with transaction.atomic():
        type(state).objects.select_for_update().get(pk=state.pk)
        state.refresh_from_db()
        if state.next_attempt_at and state.next_attempt_at>now:
            return {"status":"skipped","message":"Kontrollen har redan startats."}
        first=not state.backfill_attempted_at
        since=now-timedelta(days=90) if first else (state.watermark or now-timedelta(days=2))-timedelta(days=2)
        state.backfill_attempted_at=state.backfill_attempted_at or now
        state.next_attempt_at=now+timedelta(hours=23)
        state.details={**state.details,"start":since.isoformat(),"end":now.isoformat(),"status":"running"}
        state.save()
    try:
        data=postiz.request(company.postiz_key,"GET","/posts",params={"startDate":since.isoformat(),"endDate":now.isoformat()})
        if not isinstance(data,dict) or not isinstance(data.get("posts"),list):
            raise ValueError("Postiz gav oväntat listformat.")
        new,known,changed,skipped=0,0,0,0
        for row in data["posts"]:
            try:
                item=normalize_post(company,row)
                if item is None:
                    continue
                with transaction.atomic():
                    obj,created=OwnPost.objects.get_or_create(company=company,integration_id=item["integration_id"],release_id=item["release_id"],defaults={k:v for k,v in item.items() if k not in ("company","integration_id","release_id")})
                    new+=int(created)
                    different=any(getattr(obj,k)!=item[k] for k in ("caption","url"))
                    changed+=int(not created and different)
                    known+=int(not created and not different)
                    if not created:
                        if obj.published_at != item["published_at"] or (obj.run_id and item["run"] and obj.run_id!=item["run"].pk):
                            raise ValueError("Konflikt i publiceringens frysta identitet.")
                        obj.caption,obj.url=item["caption"],item["url"]
                        if not obj.run_id:
                            obj.run=item["run"]
                        if obj.format=="unknown":
                            obj.format=item["format"]
                        obj.save()
            except (ValueError,TypeError,KeyError,AttributeError):
                skipped+=1
        state.details={**state.details,"status":"partial" if skipped else "succeeded","returned":len(data["posts"]),"new":new,"changed":changed,"known":known,"skipped":skipped,
            "scope":"Postiz-listed posts only; outside-Postiz history is not exposed by this endpoint"}
        if not skipped:
            state.watermark=now
        state.save()
        return {**state.details,"status":"attention" if skipped else "success"}
    except Exception:
        state.details={**state.details,"status":"failed","error":"Postiz-listningen misslyckades; nästa försök gör ingen ny full backfill."}
        state.save(update_fields=["details"])
        raise


def normalize_metrics(raw, platform, now):
    if not isinstance(raw,list):
        raise ValueError("Postiz gav oväntat analytics-format.")
    mapping={"Views":"views","Reach":"reach","Likes":"likes","Comments":"comments","Saves":"saves","Shares":"shares"}
    if platform=="facebook":
        # Upstream's Impressions label represents unique media views (reach), not impressions.
        mapping={"Impressions":"reach","Reactions":"reactions","Clicks":"clicks"}
    metrics,dates={},set()
    for series in raw:
        key=mapping.get(series.get("label"))
        if not key:
            continue
        points=series.get("data",[])
        if len(points)!=1:
            raise ValueError("Analytics tidsserie kräver ett annat mätkontrakt; inga totalsiffror summeras på chans.")
        point=points[0]
        day=datetime.fromisoformat(point["date"]).date()
        if day not in (now.date(),timezone.localtime(now).date()):
            raise ValueError("Analytics är inte daterad till dagens observation.")
        value=point.get("total")
        if isinstance(value,bool) or value is None or value=="":
            continue
        number=float(value)
        if not math.isfinite(number) or number<0 or number!=int(number):
            raise ValueError("Ogiltigt observerat antal.")
        if key in metrics:
            raise ValueError("Dubbla metrics med oklar betydelse.")
        metrics[key]=int(number)
        dates.add(day)
    if not metrics or len(dates)!=1:
        raise ValueError("Analytics saknas eller har blandade observationstider.")
    return metrics,dates.pop()


def collect(post):
    post.refresh_from_db()
    now=timezone.now()
    if post.finalized_at or (post.next_check_at and post.next_check_at>now):
        return {"status":"skipped","post_id":post.pk}
    with transaction.atomic():
        locked=OwnPost.objects.select_for_update().get(pk=post.pk)
        if locked.finalized_at or (locked.next_check_at and locked.next_check_at>now):
            return {"status":"skipped","post_id":post.pk}
        locked.next_check_at=now+timedelta(hours=23)
        locked.attempts+=1
        locked.save(update_fields=["next_check_at","attempts"])
    try:
        raw=postiz.request(post.company.postiz_key,"GET",f"/analytics/post/{post.postiz_id}",params={"date":"7"})
        observed=timezone.now()
        metrics,day=normalize_metrics(raw,post.platform,observed)
        checkpoint="final" if post.published_at+timedelta(days=7)<=observed<post.published_at+timedelta(days=8) else "daily"
        snapshot,created=OwnSnapshot.objects.get_or_create(post=post,source_day=day,contract=CONTRACT,checkpoint=checkpoint,
            defaults={"observed_at":observed,"metrics":metrics,"raw":{"analytics":raw,"published_content":post.caption,
                "content_hash":fingerprint(post.caption),"format":post.format,"postiz_id":post.postiz_id,"release_id":post.release_id,
                "publish_date_basis":"Postiz publishDate","published_at":post.published_at.isoformat()}})
        # Daily snapshots through 7–8 days; an older imported post gets one current baseline observation.
        final=observed>=post.published_at+timedelta(days=7)
        OwnPost.objects.filter(pk=post.pk).update(last_error="",finalized_at=observed if final else None)
        return {"status":"success","post_id":post.pk,"snapshot_id":snapshot.pk,"new_snapshot":created,"metrics":snapshot.metrics,"final":final}
    except (postiz.PostizError,ValueError,TypeError,KeyError) as exc:
        old=now>=post.published_at+timedelta(days=8)
        OwnPost.objects.filter(pk=post.pk).update(last_error="Analytics saknas eller kunde inte tolkas; inga värden ersattes med noll.",
            finalized_at=now if old and locked.attempts>=3 else None)
        return {"status":"attention","post_id":post.pk,"message":"Analytics saknas eller har ett annat mätkontrakt."}


def bucket(snapshot):
    hours=(snapshot.observed_at-snapshot.post.published_at).total_seconds()/3600
    for lo,hi,label in ((0,24,"0-1d"),(24,48,"1-2d"),(48,96,"2-4d"),(96,168,"4-7d"),(168,192,"7-8d"),(336,2160,"mature")):
        if lo<=hours<hi:
            return label
    return None


def update_baselines(company):
    snapshots=list(OwnSnapshot.objects.filter(post__company=company).select_related("post").order_by("observed_at","pk"))
    updated=0
    for current in snapshots:
        if current.baseline:
            continue
        measure="reactions" if current.post.platform=="facebook" else "interactions"
        def value(s):
            m=s.metrics
            return m.get("reactions") if measure=="reactions" else (m["likes"]+m["comments"] if "likes" in m and "comments" in m else None)
        peers={}
        for s in snapshots:
            if s.post_id!=current.post_id and s.contract==current.contract and s.post.platform==current.post.platform and s.post.format==current.post.format and s.observed_at<=current.observed_at and bucket(s)==bucket(current) and bucket(s) and value(s) is not None:
                peers[s.post_id]=s
        confidence=min(.8,len(peers)/20) if len(peers)>=3 else 0
        base=median(value(s) for s in peers.values()) if len(peers)>=3 else None
        current.baseline={"version":"own-age-v1","metric":measure,"age_bucket":bucket(current),"peer_snapshot_ids":[s.pk for s in peers.values()],"peers":len(peers),
            "median":base,"relative":value(current)/base if base and value(current) is not None else None,
            "confidence":confidence,"confidence_label":"low" if confidence<.5 else "moderate","as_of":current.observed_at.isoformat(),
            "format":current.post.format,"platform":current.post.platform}
        current.save(update_fields=["baseline"])
        updated+=1
    return {"snapshots_updated":updated}


def create_outcomes(company):
    from .learning import record_outcome
    from .learning_targets import AUTO_ORGANIC
    saved,unmatched,unavailable=0,0,0
    for snapshot in OwnSnapshot.objects.filter(post__company=company).select_related("post__run"):
        post=snapshot.post
        if bucket(snapshot)!="7-8d" or OwnOutcome.objects.filter(snapshot=snapshot).exists():
            continue
        if not post.run_id or not post.run.predictions.filter(created_at__lte=post.published_at).exists():
            unmatched+=1
            continue
        try:
            record_outcome(post.run,source="postiz_api",external_id=f"{post.platform}:{post.integration_id}:{post.release_id}",
                published_at=post.published_at,window_end=snapshot.observed_at,observed_at=snapshot.observed_at,metrics=snapshot.metrics,
                evidence=post.url,target=AUTO_ORGANIC[post.platform],platform=post.platform,snapshot=snapshot)
            saved+=1
        except ValueError:
            unavailable+=1
    return {"saved":saved,"without_prepublication_features":unmatched,"missing_required_metrics":unavailable}
