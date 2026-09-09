"""Explicit metric/window contracts; currencies never share a monetary target."""
import re

DEFAULTS = {"organic":"interactions_per_1000_impressions_7d", "paid":"clicks_per_1000_impressions_7d"}
AUTO_ORGANIC = {"instagram":"interactions_per_1000_views_7to8d", "facebook":"reactions_per_1000_reach_7to8d"}


def spec(target):
    definitions = {
        DEFAULTS["organic"]:(("likes","comments"),"impressions",1000.,True,"organic"),
        DEFAULTS["paid"]:(("clicks",),"impressions",1000.,True,"paid"),
        AUTO_ORGANIC["instagram"]:(("likes","comments"),"views",1000.,True,"organic"),
        AUTO_ORGANIC["facebook"]:(("reactions",),"reach",1000.,True,"organic"),
        "conversions_per_100_clicks_7d":(("conversions",),"clicks",100.,True,"paid"),
        "roas_7d":(("revenue",),"spend",1.,True,"paid"),
    }
    if target in definitions:
        return definitions[target]
    if re.fullmatch(r"cpa_[A-Z]{3}_7d",target):
        return (("spend",),"conversions",1.,False,"paid")
    if re.fullmatch(r"revenue_per_1000_impressions_[A-Z]{3}_7d",target):
        return (("revenue",),"impressions",1000.,True,"paid")
    raise ValueError("Okänt eller odokumenterat learning-mål.")


def actual(target, metrics):
    numerator, denominator, scale, _, _ = spec(target)
    if any(k not in metrics for k in (*numerator,denominator)) or metrics[denominator] <= 0:
        raise ValueError("Mätvärden saknas eller nämnaren är noll för detta mål.")
    monetary = re.search(r"_([A-Z]{3})_7d$",target)
    if target=="roas_7d" and not re.fullmatch(r"[A-Z]{3}",metrics.get("currency","")):
        raise ValueError("ROAS kräver verifierad gemensam valuta för spend och revenue.")
    if monetary and metrics.get("currency") != monetary.group(1):
        raise ValueError("Valutan måste matcha modellens mål; olika valutor blandas inte.")
    return scale*sum(metrics[k] for k in numerator)/metrics[denominator]


def available_paid(metrics):
    candidates=["roas_7d","conversions_per_100_clicks_7d"]
    currency=metrics.get("currency","")
    if re.fullmatch(r"[A-Z]{3}",currency):
        candidates += [f"cpa_{currency}_7d",f"revenue_per_1000_impressions_{currency}_7d"]
    candidates.append(DEFAULTS["paid"])
    result=[]
    for target in candidates:
        try:
            actual(target,metrics)
            result.append(target)
        except (ValueError,TypeError):
            pass
    return result
