#!/usr/bin/env python3
"""
Vloží rozvrh z data/treningy.json, akcie z data/akcie.json a kontakty z data/kontakt.json
priamo do HTML stránok a vytvorí kalendáre v kalendar/ (pozri scripts/kalendar.py),
aby boli aktuálne aj bez JavaScriptu (vyhľadávače, náhľady odkazov, staršie prehliadače).

Spúšťa sa pri každom nasadení a každé 3 hodiny, takže zmena s dátumom "od"/"do"
sa na webe prejaví najneskôr do 3 hodín po polnoci. Lokálne:  python scripts/build_pages.py

V HTML sa prepisuje len:
  <!--@meno-->…<!--/@meno-->            bloky rozvrhu a oznamu
  href="tel:…" data-k="tel" / "tel2"   telefónne odkazy
  <span data-k="cislo">…</span>        zobrazené číslo (cislo2 = druhé číslo)
"""
import glob
import html
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kalendar  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOPRED = PO = 7   # koľko dní pred zmenou a po nej (aj pred koncom dočasnej zmeny) ju web hlási

V_DEN = {"pondelok": "v pondelok", "utorok": "v utorok", "streda": "v stredu", "štvrtok": "vo štvrtok",
         "piatok": "v piatok", "sobota": "v sobotu", "nedeľa": "v nedeľu"}
MES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PIN = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1E5B3A" stroke-width="2" '
       'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.5-7-12a7 7 0 0 1 14 0'
       'c0 5.5-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>')
e = lambda s: html.escape(str(s or ""), quote=True)


def dnes():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Bratislava")).date()
    except Exception:
        return (datetime.now(timezone.utc) + timedelta(hours=1)).date()


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


sk = lambda d: f"{d.day}. {d.month}."
en = lambda d: f"{d.day} {MES[d.month - 1]}"
kedy = lambda x: f"{V_DEN.get(x['den'].lower(), x['den'].lower())} o {x['cas']} · {x['miesto']}"
mapa = lambda x: f' <a href="{e(x["mapa"])}">Mapa →</a>' if x.get("mapa") else ""


def obdobie(od, do):
    return f"od {sk(od)} do {sk(do)}" if do else f"od {sk(od)}"


def stav(x, today):
    """Vráti (platný tréning, hlásenie alebo None). Hlásenie: (druh, od, do, údaje, ktoré ukázať)."""
    z = x.get("zmena")
    if not z or not z.get("od"):
        return x, None
    od = date.fromisoformat(z["od"])
    do = date.fromisoformat(z["do"]) if z.get("do") else None
    nove = {k: v for k, v in {**x, **z}.items() if k not in ("zmena", "od", "do")}
    nove["_do"] = do
    povodne = {k: v for k, v in x.items() if k != "zmena"}
    kym = (od - today).days
    if do and today > do:
        return povodne, None                                   # dočasná zmena skončila
    if kym > VOPRED:
        return povodne, None                                   # ešte priskoro hlásiť
    if kym > 0:
        return povodne, ("pripravuje", od, do, nove)           # o pár dní
    if -kym < PO:
        return nove, ("zacala", od, do, nove)                  # práve sa zmenilo
    if do and (do - today).days < VOPRED:
        return nove, ("konci", do + timedelta(days=1), None, povodne)  # o pár dní späť
    return nove, None


def rozvrh(t, oznam):
    hero, karty, eng, msgs = [], [], [], []
    if oznam.strip():
        msgs.append(e(oznam))
    for x, h in t:
        druh, od, do, y = h or (None, None, None, None)
        pozn = box = zm = ""
        if druh == "pripravuje":
            pozn = f"Od {sk(od)}: {kedy(y)}"
            box = f"<strong>Zmena {obdobie(od, do)}</strong>{e(kedy(y))}{mapa(y)}"
            msgs.append(f"<b>Pozor, zmena!</b> {e(x['skupina'])} {obdobie(od, do)} trénuje {e(kedy(y))}.{mapa(y)}")
            zm = f" <em>From {en(od)}{f' to {en(do)}' if do else ''}: {e(y.get('en_den') or y['den'])} {e(y['cas'])}, {e(y.get('en_miesto') or y['miesto'])}.</em>"
        elif druh == "zacala":
            pozn = f"Zmena {obdobie(od, do)}"
            box = f"<strong>Nové {obdobie(od, do)}</strong>Pozor na zmenený čas alebo miesto."
            msgs.append(f"{e(x['skupina'])} {obdobie(od, do)} trénuje {e(kedy(y))}.{mapa(y)}")
        elif druh == "konci":
            pozn = f"Od {sk(od)} späť: {kedy(y)}"
            box = f"<strong>Od {sk(od)} späť</strong>{e(kedy(y))}{mapa(y)}"
            msgs.append(f"{e(x['skupina'])} sa od {sk(od)} vracia: {e(kedy(y))}.{mapa(y)}")
            zm = f" <em>From {en(od)} again: {e(y.get('en_den') or y['den'])} {e(y['cas'])}, {e(y.get('en_miesto') or y['miesto'])}.</em>"
        elif x.get("_do"):
            zm = f" <em>Until {en(x['_do'])}.</em>"
        cls = ' class="zmena"' if h else ""
        pozn_html = f'<span class="hs-z">{e(pozn)}</span>' if pozn else ""
        box_html = f'<div class="zmena-box">{box}</div>' if box else ""
        mapa_html = f'<a class="more" href="{e(x["mapa"])}">Otvoriť v mape →</a>' if x.get("mapa") else ""
        hero.append(f'<li{cls}><span class="hs-g">{e(x["skupina"])}</span><span class="hs-t">{e(x["den"])} <b>{e(x["cas"])}</b></span>'
                    f'<span class="hs-p">{e(x["miesto"])}</span>{pozn_html}</li>')
        karty.append(f'<article class="card"><div class="kicker" style="letter-spacing:1px">{e(x["skupina"])}</div>'
                     f'<h3>{e(x["den"])} {e(x["cas"])}</h3><div class="row">{PIN}<span>{e(x["miesto"])}</span></div>'
                     f'{box_html}{mapa_html}{kalendar.trening_odkazy(x)}</article>')
        eng.append(f'<strong>{e(x.get("en_skupina") or x["skupina"])}:</strong> {e(x.get("en_den") or x["den"])} {e(x["cas"])}, '
                   f'{e(x.get("en_miesto") or x["miesto"])}.{zm}')
    oz = ('<div id="oznam" class="oznam" role="status">' + "".join(f"<p>{m}</p>" for m in msgs) + "</div>") if msgs \
        else '<div id="oznam" class="oznam" role="status" hidden></div>'
    return {"rozvrh-hero": "".join(hero), "rozvrh-karty": "\n".join(karty), "rozvrh-en": " ".join(eng), "oznam": oz}


def whatsapp(k):
    cislo = re.sub(r"\D", "", k["cislo"])
    url = f"https://wa.me/{cislo}?text={quote(k['sprava'])}"
    data = json.dumps({"cislo": cislo, "sprava": k["sprava"], "spravy": k.get("spravy", {})}, ensure_ascii=False)
    script = ("<script>(function(){var K=" + data.replace("</", "<\\/") + ";"
              "var z=new URLSearchParams(location.search).get('z');"
              "var u='https://wa.me/'+K.cislo+'?text='+encodeURIComponent(K.spravy[z]||K.sprava);"
              "document.getElementById('wa').href=u;location.replace(u);})();</script>")
    return {"wa-refresh": f'<meta http-equiv="refresh" content="1;url={e(url)}">',
            "wa-odkaz": f'<a id="wa" class="btn btn-y" href="{e(url)}">Otvoriť WhatsApp →</a>',
            "wa-script": script}


def apply(s, bloky, k):
    for name, val in bloky.items():
        s = re.sub(rf"(<!--@{name}-->).*?(<!--/@{name}-->)", lambda m: m.group(1) + val + m.group(2), s, flags=re.S)
    tel = lambda c: "tel:+" + re.sub(r"\D", "", c)
    s = re.sub(r'href="tel:[^"]*"(\s+data-k="tel")', lambda m: f'href="{tel(k["cislo"])}"' + m.group(1), s)
    s = re.sub(r'href="tel:[^"]*"(\s+data-k="tel2")', lambda m: f'href="{tel(k["cislo2"])}"' + m.group(1), s)
    s = re.sub(r'(<span data-k="cislo">)[^<]*(</span>)', lambda m: m.group(1) + e(k["cislo"]) + m.group(2), s)
    s = re.sub(r'(<span data-k="cislo2">)[^<]*(</span>)', lambda m: m.group(1) + e(k["cislo2"]) + m.group(2), s)
    return s


def main():
    k = load("kontakt.json")
    d = load("treningy.json")
    today = dnes()
    t = [stav(x, today) for x in d.get("treningy", []) if x.get("den") and x.get("cas")]
    akcie = load("akcie.json").get("akcie", [])
    bloky = {**rozvrh(t, d.get("oznam", "")), **whatsapp(k), **kalendar.akcie_bloky(akcie, today)}
    kalendar.zapis_kalendare(ROOT, [x for x in d.get("treningy", []) if x.get("den") and x.get("cas")], akcie, today)
    zmenene = 0
    for path in glob.glob(os.path.join(ROOT, "*.html")):
        old = open(path, encoding="utf-8").read()
        new = apply(old, bloky, k)
        if new != old:
            open(path, "w", encoding="utf-8", newline="\n").write(new)
            zmenene += 1
    hl = [h for _, h in t if h]
    print(f"Stránky: {zmenene} upravených, dnes {today}, hlásení zmien: {len(hl)}, akcií: {len(akcie)}")


if __name__ == "__main__":
    sys.exit(main())
