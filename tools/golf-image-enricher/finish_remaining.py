#!/usr/bin/env python3
from __future__ import annotations
import copy, csv, json, sys, concurrent.futures
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, unquote

# enrich.py is next to this script in GitHub Actions working dir.
import enrich

UPDATED_URLS = {
    "Dalsjö GK": "https://www.dalsjogolf.se/",
    "Hagge GK": "http://www.haggegk.com/",
    "Helsingborgs GK": "https://vikensgk.se/info.html",
    "Järvsöbadens GK": "https://www.jarvsobaden.se/golf/",
}

MANUAL_CANDIDATES = {
    "Billeruds GK": [
        "https://static.wixstatic.com/media/ba5397_cf4e24e414854dddb98d44d0d2feb349~mv2.jpg",
    ],
    "Dalsjö GK": [
        "https://www.dalsjogolf.se/media/wfdhm2sp/haal9_green1.jpg",
    ],
    "Dynekilen GK": [
        "https://static.wixstatic.com/media/16b727_e4ca3acee22940f1a1e2752510691d24~mv2.jpg",
    ],
    "Eksjö GK": [
        "https://cdn.allsquaregolf.com/pictures/pictures/000/127/519/large/eksjo_golfklubb_cover_picture.jpg",
    ],
    "Falsterbo GK": [
        "https://cdn.sanity.io/images/03mhssoh/production/22449433a95c1d60cf914e3f9df1469354354706-5280x2970.jpg",
        "https://cdn.sanity.io/images/03mhssoh/production/40b5c468d7d2f8d76fc7dbbefafc81cb37d03902-5280x2970.jpg",
    ],
    "Fogdö GK": [
        "https://golf-pass.brightspotcdn.com/dims4/default/9b97f12/2147483647/strip/true/crop/960x540%2B0%2B0/resize/1200x675%21/format/webp/quality/90/?url=https%3A%2F%2Fgolf-pass-brightspot.s3.amazonaws.com%2Fa2%2F39%2F6668050e57a5a5096ad03b42f84c%2F82911.jpg",
    ],
    "Fullerö GK": [
        "https://caddee-prod-media.s3.amazonaws.com/course-images/47cd7793-2845-4fa4-a1f7-2cbc1de16114/course-normal_web_rxTTWyv.png",
    ],
    "Furudals Bruk GK": [
        "https://images.citybreakcdn.com/image.aspx?ImageId=302549",
        "https://golf-pass.brightspotcdn.com/dims4/default/2288789/2147483647/strip/true/crop/540x540%2B210%2B0/resize/1200x1200%21/format/webp/quality/90/?url=https%3A%2F%2Fgolf-pass-brightspot.s3.amazonaws.com%2Fca%2F29%2F1aeaeee1b41ac1f46e23701173bf%2F82978.jpg",
    ],
    "Golfservice Marbella": [
        "https://static.costadelsolmalaga.org/visita/subidas/imagenes/2/4/arc_31742_g.jpg",
    ],
    "Grönlund GK": [
        "https://www.1golf.eu/images/golfclubs/groenlund-golfklubb_034318_full.jpg",
    ],
    "Hagge GK": [
        "https://www.svenskgolf.se/app/uploads/2019/12/6302d05a-5de3e12fd321e.jpg",
    ],
    "Helsingborgs GK": [
        "https://golf-pass.brightspotcdn.com/dims4/default/cfd734d/2147483647/strip/true/crop/960x619%2B0%2B50/resize/1200x774%21/format/webp/quality/90/?url=https%3A%2F%2Fgolf-pass-brightspot.s3.amazonaws.com%2Fd9%2Ffc%2F1dde845f2cc5c8099c0f501abc66%2F83090.jpg",
    ],
    "Herrljunga GK": [
        "https://caddee-prod-media.s3.amazonaws.com/club-images/feeeaba1-ad45-477e-afda-5ac37c8e6430/header-normal_web.png",
    ],
    "Hulta Bollebygd Golfklubb": [
        "https://www.hultagk.se/media/2bpfc2x3/nybildhemsida-scaled.jpg?height=800&quality=70&v=1dc7339e7452230&width=2000",
    ],
    "Järvsöbadens GK": [],
    "Kalix Golfklubb": [
        "https://golfhaftet-img.b-cdn.net/golfclubs/379-ef1420.png",
    ],
    "Kungsbacka GK": [
        "https://www.kungsbackagk.se/media/1gnn5ppg/250925_kungsbacka-gk_foto-daniel-stenholm_dji_20250925141516_0732_d.jpg",
    ],
    "Ljusdals GK": [
        "https://www.svenskgolf.se/app/uploads/8ee07a9a-ljusnans-gk.jpg",
    ],
    "Nora GK": [
        "https://klubbar.svenskagolfmuseet.se/images/243_1679405543_tian-1-.jpg",
    ],
    "Perstorps GK": [
        "https://golf-pass.brightspotcdn.com/dims4/default/3ab962a/2147483647/strip/true/crop/1280x826%2B0%2B67/resize/1200x774%21/quality/90/?url=https%3A%2F%2Fgolf-pass-brightspot.s3.amazonaws.com%2F6a%2Fa6%2F3c4d182ab6646c274b1c7d5e5c94%2F83712.jpg",
    ],
    "S:t Ibb GK": [
        "https://static.wixstatic.com/media/68b0ee_583c5a40df0f4bfabd9faf50721a5aa2~mv2.jpg",
    ],
    "Snöå GK": [
        "https://images.citybreakcdn.com/image.aspx?ImageId=6886460",
    ],
    "Sundsta Golf": [
        "https://images.citybreak.com/7631553.jpeg",
        "https://www.visitroslagen.se/sites/cb_visitroslagen/files/styles/slide_large/http/images.citybreak.com/7631553.jpeg.webp?itok=3Ck6mdys",
    ],
    "Sundsvalls GK": [
        "https://golf-pass.brightspotcdn.com/dims4/default/ed6747e/2147483647/strip/true/crop/960x960%2B240%2B0/resize/1200x1200%21/format/webp/quality/90/?url=https%3A%2F%2Fgolf-pass-brightspot.s3.amazonaws.com%2F49%2F64%2F6d41aee7c4166dc56dc53f35f409%2F84011.jpg",
    ],
    "Svartinge GK": [
        "https://cdn.sanity.io/images/03mhssoh/production/caab7c328bf4b86c6e384e1dc61a1a1e1c8f6ecc-1200x801.jpg?auto=format&fit=max&q=75&w=3840",
    ],
    "Sörfors GK": [
        "https://static.wixstatic.com/media/d213b8_f183b3402471464a8bcab913d925a56e.jpg",
    ],
    "Timrå GK": [
        "https://destinationsundsvall.se/images/18.41f70d8418df29f29d71ecd7/1710422871547/Timr%C3%A5%20GK%20h%C3%A5l%2018.jpg",
    ],
    "Vallda Golf & Country Club": [
        "https://golf-pass.brightspotcdn.com/1a/d5/4f26f468ad4a19460e1c6fb4bb7a/85028.jpg",
    ],
}

RESIZE_QUERY_KEYS = {"w","width","h","height","q","quality","fit","crop","mode","rmode","rxy","upscale","dpr","preset"}

def variants(url: str):
    out=[]
    def add(u):
        if u and u not in out: out.append(u)
    add(url)
    try:
        p=urlparse(url)
        # Wix: keep original media object and drop /v1/fill|fit|crop transformations.
        if "wixstatic.com" in (p.hostname or "") and "/v1/" in p.path:
            add(urlunparse((p.scheme,p.netloc,p.path.split('/v1/',1)[0],"","","")))
        params=parse_qsl(p.query,keep_blank_values=True)
        embedded=[v for k,v in params if k.lower()=="url" and v.startswith("http")]
        for e in embedded: add(unquote(e))
        kept=[(k,v) for k,v in params if k.lower() not in RESIZE_QUERY_KEYS]
        if kept != params:
            add(urlunparse((p.scheme,p.netloc,p.path,"",urlencode(kept),"")))
        if "images.citybreakcdn.com" in (p.hostname or "") and p.path.lower().endswith("image.aspx"):
            imgid=next((v for k,v in params if k.lower()=="imageid"),None)
            if imgid:
                add(f"https://images.citybreakcdn.com/image.aspx?ImageId={imgid}")
    except Exception:
        pass
    return out

def acceptable(url, referer=""):
    dims, final, err = enrich.probe_image(url, referer)
    if not dims:
        return None, err
    w,h=dims
    ratio=w/max(h,1)
    if w < 1200 or h < 600 or ratio < 1.10 or ratio > 4.2:
        return None, f"rejected {w}x{h} ratio={ratio:.2f}"
    return {"url": final, "width": w, "height": h}, ""

def solve_target(i, club):
    name=club.get('name','')
    referer=UPDATED_URLS.get(name, club.get('url',''))

    # Fast path: verify curated candidates first. If at least one is valid,
    # there is no reason to spend minutes recrawling a known-hard website.
    imgs=[]
    seen=set()
    manual_errors=[]
    for raw in MANUAL_CANDIDATES.get(name,[]):
        if len(imgs)>=5: break
        for u in variants(raw):
            if len(imgs)>=5: break
            img,err=acceptable(u, referer)
            if img and img['url'] not in seen:
                imgs.append(img); seen.add(img['url'])
            elif err:
                manual_errors.append(f"{u} -> {err}")
    if imgs:
        return i, imgs, {
            'index':i,'name':name,'status':'ok','images_added':len(imgs),
            'crawler_status':'manual_verified','pages_checked':0,
            'candidates_found':len(MANUAL_CANDIDATES.get(name,[])),
            'candidates_probed':len(MANUAL_CANDIDATES.get(name,[])),
            'error':''
        }

    # Slow fallback only for clubs whose curated candidates failed or were absent.
    temp=copy.deepcopy(club)
    if name in UPDATED_URLS:
        temp['url']=UPDATED_URLS[name]
    result=enrich.process_club(i,temp,max_pages=12,max_probes=300,max_images=5)
    imgs=list(result.images or [])
    status='ok' if imgs else result.status
    row={
        'index':i,'name':name,'status':status,'images_added':len(imgs),
        'crawler_status':result.status,'pages_checked':result.pages_checked,
        'candidates_found':result.candidates_found,'candidates_probed':result.candidates_probed,
        'error': result.error or ('; '.join(manual_errors[-3:]) if not imgs else '')
    }
    return i, imgs, row


def main():
    inp=Path(sys.argv[1]); outp=Path(sys.argv[2]); sump=Path(sys.argv[3])
    baseline=json.load(inp.open(encoding='utf-8'))
    output=copy.deepcopy(baseline)
    rows=[]
    targets=[(i,copy.deepcopy(c)) for i,c in enumerate(output) if c.get('active') is True and not c.get('images')]
    print(f"Final pass targets: {len(targets)}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        future_map={pool.submit(solve_target,i,club):(i,club) for i,club in targets}
        for n,future in enumerate(concurrent.futures.as_completed(future_map),1):
            i,club=future_map[future]
            try:
                idx,imgs,row=future.result()
            except Exception as exc:
                idx=i; imgs=[]
                row={'index':i,'name':club.get('name',''),'status':'error','images_added':0,
                     'crawler_status':'error','pages_checked':0,'candidates_found':0,'candidates_probed':0,
                     'error':str(exc)[:500]}
            output[idx]['images']=imgs
            rows.append(row)
            print(f"[{n:02d}/{len(targets)}] {row['name']}: {row['status']}, {len(imgs)} images")
    rows.sort(key=lambda r:r['index'])
    errors=enrich.validate_output(baseline,output)
    if errors:
        print('VALIDATION FAILED')
        for e in errors[:50]: print(e)
        return 2
    outp.parent.mkdir(parents=True,exist_ok=True)
    with outp.open('w',encoding='utf-8') as f:
        json.dump(output,f,ensure_ascii=False,indent=2); f.write('\n')
    with sump.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    remain=[r for r in rows if r['status']!='ok']
    print(f"Done. Resolved {len(rows)-len(remain)}/{len(rows)}; remaining {len(remain)}")
    for r in remain: print('REMAIN',r['name'],r['crawler_status'],r['error'])
    return 0

if __name__=='__main__':
    raise SystemExit(main())