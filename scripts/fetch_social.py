#!/usr/bin/env python3
"""
Stiahne príspevky z Facebook stránky a Instagram účtu klubu cez Meta Graph API
a uloží ich do data/posts.json + data/posts/<id>.json + assets/posts/*.jpg.

Premenné prostredia (GitHub → Settings → Secrets and variables → Actions):
  META_TOKEN    – token systémového používateľa z Meta Business Suite (secret)
  FB_PAGE_ID    – ID Facebook stránky klubu (variable alebo secret)
  IG_USER_ID    – voliteľné, ID Instagram firemného účtu (inak sa zistí zo stránky)
  GRAPH_VERSION – voliteľné, napr. v23.0

Použitie:  python scripts/fetch_social.py            (posledných ~25 príspevkov)
           python scripts/fetch_social.py --all      (celá história, prvé spustenie)
"""
import difflib
import os
import re
import sys
import unicodedata
from datetime import datetime

import requests

from common import INDEX, POSTS_DIR, load_json, save_image, save_json, DATA

TOKEN = os.environ.get("META_TOKEN", "").strip()
PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
IG_ID = os.environ.get("IG_USER_ID", "").strip()
VER = os.environ.get("GRAPH_VERSION", "v23.0").strip()
API = f"https://graph.facebook.com/{VER}"
ALL = "--all" in sys.argv
MAX_PAGES = 40 if ALL else 1
MAX_IMAGES = 12
MERGE_WINDOW_H = 72     # FB a IG príspevok s podobným textom do 3 dní = jeden článok
MERGE_RATIO = 0.85


def get(path, params, token):
    params = dict(params, access_token=token)
    r = requests.get(f"{API}/{path}" if not path.startswith("http") else path, params=params, timeout=30)
    if r.status_code != 200:
        raise MetaError(r)
    return r.json()


HINTS = {
    190: "Kľúč (META_TOKEN) vypršal alebo bol zrušený. Vygeneruj nový v Business Suite → System users → web-bot → Generate token.",
    200: "Meta zablokovala prístup aplikácie (API access blocked). Skontroluj na developers.facebook.com, či aplikácia nemá upozornenie alebo obmedzenie.",
    10: "Kľúču chýba oprávnenie. Vygeneruj nový token so všetkými oprávneniami z README.",
    100: "Zlé ID stránky (FB_PAGE_ID) alebo nepodporované pole.",
    4: "Prekročený limit volaní. Ďalší beh to skúsi znova.",
    17: "Prekročený limit volaní. Ďalší beh to skúsi znova.",
}


class MetaError(RuntimeError):
    def __init__(self, r):
        try:
            e = r.json().get("error", {})
        except ValueError:
            e = {}
        self.code = e.get("code")
        msg = e.get("message") or r.text[:200]
        hint = HINTS.get(self.code, "Neznáma chyba Mety, pošli tento výpis správcovi webu.")
        super().__init__(f"Meta API chyba {self.code} (HTTP {r.status_code}): {msg}\n→ {hint}")


def paged(path, params, token):
    data = get(path, params, token)
    for _ in range(MAX_PAGES):
        yield from data.get("data", [])
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        r = requests.get(nxt, timeout=30)
        r.raise_for_status()
        data = r.json()


def norm(text):
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"https?://\S+|#\w+|@\w+", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:400]


def make_title(text, source, date):
    first = (text or "").strip().split("\n", 1)[0]
    first = re.split(r"(?<=[.!?])\s", first, maxsplit=1)[0].strip(" .!")
    first = re.sub(r"\s+#\w+.*$", "", first)
    if not first:
        return f"Príspevok z {'Facebooku' if source == 'facebook' else 'Instagramu'} – {date[:10]}"
    if len(first) > 80:
        first = first[:80].rsplit(" ", 1)[0] + "…"
    return first


def make_excerpt(text, title):
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if t.startswith(title.rstrip("…")):
        t = t[len(title.rstrip("…")):].lstrip(" .!?")
    return (t[:157].rsplit(" ", 1)[0] + "…") if len(t) > 160 else t


def fb_posts():
    page = get(PAGE_ID, {"fields": "access_token,instagram_business_account"}, TOKEN)
    ptoken = page.get("access_token", TOKEN)
    global IG_ID
    if not IG_ID:
        IG_ID = (page.get("instagram_business_account") or {}).get("id", "")
    fields = ("id,message,created_time,permalink_url,full_picture,"
              "attachments{media_type,media,subattachments{media_type,media}}")
    out = []
    for p in paged(f"{PAGE_ID}/published_posts", {"fields": fields, "limit": 25}, ptoken):
        imgs = []
        for a in (p.get("attachments") or {}).get("data", []):
            subs = (a.get("subattachments") or {}).get("data") or [a]
            for s in subs:
                src = ((s.get("media") or {}).get("image") or {}).get("src")
                if src:
                    imgs.append(src)
        if not imgs and p.get("full_picture"):
            imgs = [p["full_picture"]]
        if not p.get("message") and not imgs:
            continue
        out.append({"source": "facebook", "sid": p["id"], "date": p["created_time"],
                    "text": p.get("message", ""), "link": p.get("permalink_url"), "imgs": imgs})
    return out


def ig_posts():
    if not IG_ID:
        print("Instagram: účet nie je prepojený so stránkou, preskakujem.")
        return []
    fields = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{media_type,media_url,thumbnail_url}"
    out = []
    for m in paged(f"{IG_ID}/media", {"fields": fields, "limit": 25}, TOKEN):
        items = (m.get("children") or {}).get("data") or [m]
        imgs = [(c.get("thumbnail_url") if c.get("media_type") == "VIDEO" else c.get("media_url")) for c in items]
        out.append({"source": "instagram", "sid": m["id"], "date": m["timestamp"],
                    "text": m.get("caption", ""), "link": m.get("permalink"), "imgs": [i for i in imgs if i]})
    return out


def ts(iso):
    return datetime.fromisoformat(iso.replace("+0000", "+00:00").replace("Z", "+00:00")).timestamp()


def merge(fb, ig):
    """Spojí rovnaký príspevok zdieľaný naraz na FB aj IG do jedného."""
    for i in ig:
        best = None
        for f in fb:
            if abs(ts(f["date"]) - ts(i["date"])) > MERGE_WINDOW_H * 3600:
                continue
            a, b = norm(f["text"]), norm(i["text"])
            n = min(len(a), len(b), 200)
            if a and b and (a[:n] == b[:n] or difflib.SequenceMatcher(None, a, b).ratio() >= MERGE_RATIO):
                best = f
                break
        if best:
            best.setdefault("also_on", []).append({"source": "instagram", "link": i["link"]})
            if not best["imgs"]:
                best["imgs"] = i["imgs"]
            i["merged"] = True
    return fb + [i for i in ig if not i.get("merged")]


def main():
    if not TOKEN or not PAGE_ID:
        print("META_TOKEN alebo FB_PAGE_ID nie je nastavené – sťahovanie zo sociálnych sietí preskakujem.")
        return
    index = load_json(INDEX, [])
    hidden = set(load_json(f"{DATA}/hidden.json", []))
    by_id = {p["id"]: p for p in index}
    fb, ig = fb_posts(), ig_posts()
    items = merge(fb, ig)
    # IG príspevky, ktoré sa teraz spojili s FB, odstránime aj zo starších behov
    for i in ig:
        if i.get("merged"):
            gone = "ig-" + re.sub(r"\W", "-", i["sid"])
            by_id.pop(gone, None)
            try:
                os.remove(f"{POSTS_DIR}/{gone}.json")
            except FileNotFoundError:
                pass
    new = updated = 0
    for it in items:
        pid = ("fb-" if it["source"] == "facebook" else "ig-") + re.sub(r"\W", "-", it["sid"])
        if pid in hidden:
            continue
        old = load_json(f"{POSTS_DIR}/{pid}.json", None)
        if old and old.get("text") == it["text"] and old.get("also_on", []) == it.get("also_on", []):
            continue
        local = []
        for n, url in enumerate(it["imgs"][:MAX_IMAGES]):
            rel = save_image(url, f"assets/posts/{pid}-{n + 1}.jpg")
            if rel:
                local.append(rel)
        title = make_title(it["text"], it["source"], it["date"])
        rec = {"id": pid, "source": it["source"], "date": it["date"].replace("+0000", "+00:00"),
               "title": title, "excerpt": make_excerpt(it["text"], title),
               "thumb": local[0] if local else None}
        save_json(f"{POSTS_DIR}/{pid}.json", dict(rec, text=it["text"], images=local,
                                                   link=it["link"], also_on=it.get("also_on", [])))
        updated += bool(old)
        new += not old
        by_id[pid] = rec
    out = sorted((p for p in by_id.values() if p["id"] not in hidden), key=lambda p: p["date"], reverse=True)
    save_json(INDEX, out, indent=1)
    print(f"Hotovo: {new} nových, {updated} upravených, spolu {len(out)} príspevkov.")


if __name__ == "__main__":
    try:
        main()
    except MetaError as e:
        print(f"::error title=Sťahovanie z FB/IG zlyhalo::{e}".replace("\n", "%0A"))
        print(e)
        sys.exit(1)
