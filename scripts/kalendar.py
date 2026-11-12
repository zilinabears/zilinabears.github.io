"""
Kalendáre tréningov a akcií pre scripts/build_pages.py.

Vytvára priečinok kalendar/ (negeneruje sa do gitu):
  treningy-<skupina>.ics      opakované tréningy jednej skupiny vrátane blokov "zmena"
  akcie.ics, akcie-<kat>.ics  všetky akcie / akcie jednej kategórie (na odber)
  akcia/<id>.ics              jedna akcia (jednorazové pridanie, Apple a iné)
a HTML bloky pre index.html a akcie.html.
"""
import html
import json
import os
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, urlencode

SITE = "https://zilinabears.github.io"
HOST = "zilinabears.github.io"
KATEGORIE = ["U8", "U10", "U12", "U14", "U16", "Dospelí", "Veteráni 35+"]   # "Všetci" patrí do každej
DETI = ["U8", "U10", "U12"]                                                 # "Deti" = všetky tri
TRVANIE_MIN = 90                                                # dĺžka tréningu, ak nie je "trvanie"
DNI = {"pondelok": 0, "utorok": 1, "streda": 2, "štvrtok": 3, "piatok": 4, "sobota": 5, "nedeľa": 6}
DEN_NAZOV = ["pondelok", "utorok", "streda", "štvrtok", "piatok", "sobota", "nedeľa"]
MES = ["jan", "feb", "mar", "apr", "máj", "jún", "júl", "aug", "sep", "okt", "nov", "dec"]
MES_GEN = ["januára", "februára", "marca", "apríla", "mája", "júna", "júla", "augusta", "septembra",
           "októbra", "novembra", "decembra"]
MESIAC = ["Január", "Február", "Marec", "Apríl", "Máj", "Jún", "Júl", "August", "September", "Október", "November", "December"]
e = lambda s: html.escape(str(s or ""), quote=True)

VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Bratislava
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def slug(s):
    s = re.sub(r"[–—·/]", " ", str(s))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def esc_ics(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):
    out, b = [], line.encode("utf-8")
    while len(b) > 75:
        cut = 75 if not out else 74
        while (b[cut] & 0xC0) == 0x80:      # nedeliť UTF-8 znak
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n ".join(out)


def calendar(name, events, tz=False):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Zilina Bears//web//SK", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{esc_ics(name)}", "X-WR-TIMEZONE:Europe/Bratislava",
             "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
    if tz:
        lines += VTIMEZONE.split("\n")
    for ev in events:
        lines += ["BEGIN:VEVENT"] + ev + ["END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def stamp():
    return "DTSTAMP:" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------- tréningy

def segmenty(x, today):
    """Úseky platnosti tréningu: (od, do alebo None, údaje). Zohľadní blok "zmena"."""
    zac = date(today.year if today.month >= 8 else today.year - 1, 9, 1)     # začiatok sezóny
    povodne = {k: v for k, v in x.items() if k != "zmena"}
    z = x.get("zmena") or {}
    if not z.get("od"):
        return [(zac, None, povodne)]
    od = date.fromisoformat(z["od"])
    do = date.fromisoformat(z["do"]) if z.get("do") else None
    nove = {k: v for k, v in {**x, **z}.items() if k not in ("zmena", "od", "do")}
    seg = [(zac, od - timedelta(days=1), povodne), (od, do, nove)]
    if do:
        seg.append((do + timedelta(days=1), None, povodne))
    return [(a, b, d) for a, b, d in seg if b is None or b >= a]


def trening_ics(x, today):
    events = []
    for i, (od, do, d) in enumerate(segmenty(x, today)):
        wd = DNI.get(str(d["den"]).lower())
        if wd is None:
            continue
        prvy = od + timedelta(days=(wd - od.weekday()) % 7)
        if do and prvy > do:
            continue
        h, m = (int(v) for v in d["cas"].split(":"))
        start = datetime(prvy.year, prvy.month, prvy.day, h, m)
        end = start + timedelta(minutes=int(d.get("trvanie") or TRVANIE_MIN))
        rr = "RRULE:FREQ=WEEKLY"
        if do:
            rr += ";UNTIL=" + (datetime(do.year, do.month, do.day, 23, 59, 59) - timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")
        popis = f"Tréning Žilina Bears – {x['skupina']}.\nAktuálny rozvrh: {SITE}/treningy"
        ev = [f"UID:trening-{slug(x['skupina'])}-{i}@{HOST}", stamp(),
              f"DTSTART;TZID=Europe/Bratislava:{start:%Y%m%dT%H%M%S}",
              f"DTEND;TZID=Europe/Bratislava:{end:%Y%m%dT%H%M%S}", rr,
              f"SUMMARY:{esc_ics('Ragby tréning · ' + x['skupina'])}",
              f"LOCATION:{esc_ics(d['miesto'])}", f"DESCRIPTION:{esc_ics(popis)}"]
        if d.get("mapa"):
            ev.append(f"URL:{d['mapa']}")
        events.append(ev)
    return calendar(f"Žilina Bears – tréningy {x['skupina']}", events, tz=True)


def odber(subor):
    """Odkazy na odber kalendára: (iPhone/Apple, Google)."""
    webcal = f"webcal://{HOST}/kalendar/{subor}"
    return webcal, "https://calendar.google.com/calendar/render?" + urlencode({"cid": webcal})


def trening_odkazy(x):
    apple, google = odber(f"treningy-{slug(x['skupina'])}.ics")
    return (f'<div class="cal">Do kalendára: <a href="{e(apple)}">iPhone</a> · '
            f'<a href="{e(google)}" target="_blank" rel="noopener">Google</a></div>')


# ---------------------------------------------------------------- akcie

def kat(a):
    k = a.get("kategoria") or "Všetci"
    out = []
    for x in (k if isinstance(k, list) else [k]):
        out += DETI if x == "Deti" else [x]
    return list(dict.fromkeys(out))


def vysledky(a):
    """Výsledok ako zoznam (družstvo, výsledok); "vysledok" je text alebo {"U10 A": "1. miesto", ...}."""
    v = a.get("vysledok")
    if not v:
        return []
    return list(v.items()) if isinstance(v, dict) else [("", v)]


def dni(a):
    od = date.fromisoformat(a["datum"])
    return od, date.fromisoformat(a["do"]) if a.get("do") else od


def akcia_id(a):
    return a.get("id") or f"{a['datum']}-{'-'.join(slug(a['nazov']).split('-')[:6])}"


def prirad_id(root):
    """Akciám bez id (alebo s duplicitným id) vytvorí id a zapíše ho do data/akcie.json.
    Id sa potom už nemení, takže odkaz na akciu prežije zmenu dátumu, názvu aj kategórie."""
    path = os.path.join(root, "data", "akcie.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    videne, zmena = set(), False
    for i, a in enumerate(d.get("akcie", [])):
        aid = a.get("id")
        if not aid or aid in videne:
            if aid:
                print(f"::warning::Akcia „{a.get('nazov')}“ má rovnaké id ako iná akcia ({aid}), dostáva nové.")
            zaklad = akcia_id({k: v for k, v in a.items() if k != "id"})
            aid, n = zaklad, 2
            while aid in videne:
                aid, n = f"{zaklad}-{n}", n + 1
            d["akcie"][i] = {"id": aid, **{k: v for k, v in a.items() if k != "id"}}
            zmena = True
        videne.add(aid)
    if zmena:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    return zmena


def detail_url(a):
    return f"{SITE}/akcia/{akcia_id(a)}"


def kedy(a):
    od, do = dni(a)
    if od == do:
        return f"{DEN_NAZOV[od.weekday()]} {od.day}. {MES_GEN[od.month - 1]} {od.year}"
    if od.month == do.month:
        return f"{od.day}. – {do.day}. {MES_GEN[do.month - 1]} {do.year}"
    return f"{od.day}. {MES_GEN[od.month - 1]} – {do.day}. {MES_GEN[do.month - 1]} {do.year}"


def popis(a, today):
    r = []
    if a.get("zaciatok"):
        r.append(f"Začiatok: {a['zaciatok']}")
    if a.get("zraz"):
        r.append("Zraz: " + ", ".join(v for v in (a.get("zraz"), a.get("zraz_miesto")) if v))
    elif dni(a)[1] >= today:
        r.append("Zraz upresníme v týždni pred akciou.")
    for tim, v in vysledky(a):
        r.append(f"Výsledok{' ' + tim if tim else ''}: {v}")
    if a.get("popis"):
        r.append(a["popis"])
    r.append(f"Detail a zmeny: {detail_url(a)}")
    return "\n".join(r)


def akcia_event(a, today):
    od, do = dni(a)
    ev = [f"UID:{akcia_id(a)}@{HOST}", stamp(), f"SUMMARY:{esc_ics(a['nazov'])}"]
    if a.get("cas"):
        h, m = (int(v) for v in a["cas"].split(":"))
        ev.append(f"DTSTART;TZID=Europe/Bratislava:{od:%Y%m%d}T{h:02d}{m:02d}00")
        ev.append(f"DTEND;TZID=Europe/Bratislava:{od:%Y%m%d}T{(h + 2) % 24:02d}{m:02d}00")
    else:
        ev += [f"DTSTART;VALUE=DATE:{od:%Y%m%d}", f"DTEND;VALUE=DATE:{do + timedelta(days=1):%Y%m%d}", "TRANSP:TRANSPARENT"]
    if a.get("miesto"):
        ev.append(f"LOCATION:{esc_ics(a['miesto'])}")
    ev.append(f"URL:{detail_url(a)}")
    ev.append(f"DESCRIPTION:{esc_ics(popis(a, today))}")
    return ev


def google_link(a, today):
    od, do = dni(a)
    dates = f"{od:%Y%m%d}/{do + timedelta(days=1):%Y%m%d}"
    if a.get("cas"):
        h, m = (int(v) for v in a["cas"].split(":"))
        dates = f"{od:%Y%m%d}T{h:02d}{m:02d}00/{od:%Y%m%d}T{(h + 2) % 24:02d}{m:02d}00"
    q = {"action": "TEMPLATE", "text": a["nazov"], "dates": dates, "details": popis(a, today),
         "location": a.get("miesto", ""), "ctz": "Europe/Bratislava"}
    return "https://calendar.google.com/calendar/render?" + urlencode(q, quote_via=quote)


def datum_html(a):
    od, do = dni(a)
    den = f"{od.day}." if od == do else f"{od.day}.–{do.day}." if od.month == do.month else f"{od.day}. {MES[od.month - 1]} –"
    dnt = DEN_NAZOV[od.weekday()] if od == do else f"{DEN_NAZOV[od.weekday()][:2]} – {DEN_NAZOV[do.weekday()][:2]}"
    return (f'<div class="thumb ak-d" aria-hidden="true"><b>{den}</b><span>{MES[do.month - 1]}</span>'
            f'<small>{dnt}</small></div>')


def akcia_html(a, today, plna=True, stav=""):
    """Dlaždica akcie s odkazom na detail. stav: "" budúca, "minula" odohratá, "najblizsia" zvýraznená."""
    kats = kat(a)
    badges = "".join(f'<span class="badge akcia-k">{e(k)}</span>' for k in kats)
    if stav == "najblizsia":
        badges = '<span class="badge ak-naj">Najbližšia akcia</span>' + badges
    riadky = [f'<p class="ak-m">{e(a["miesto"])}</p>'] if a.get("miesto") else []
    vys = vysledky(a)
    if vys:
        li = "".join(f"<li>{'<b>' + e(t) + '</b> ' if t else ''}{e(v)}</li>" for t, v in vys)
        riadky.append(f'<div class="ak-v"><b>Výsledok</b><ul>{li}</ul></div>')
    if stav != "minula":
        if a.get("zaciatok"):
            riadky.append(f"<p>Začiatok {e(a['zaciatok'])}</p>")
        if plna:
            if a.get("zraz"):
                z = ", ".join(e(v) for v in (a.get("zraz"), a.get("zraz_miesto")) if v)
                riadky.append(f'<p class="ak-z"><b>Zraz:</b> {z}</p>')
            else:
                riadky.append('<p class="ak-z ak-z0">Zraz upresníme v týždni pred akciou.</p>')
    data = e(" ".join(slug(k) for k in kats))
    cls = f"post akcia {stav}".strip()
    idattr = ' id="najblizsia"' if stav == "najblizsia" else ""
    return (f'<a class="{cls}"{idattr} href="akcia/{e(akcia_id(a))}.html" data-kat="{data}">{datum_html(a)}<span class="body">'
            f'<span class="meta">{badges}</span>'
            f'<h3>{e(a["nazov"])}</h3>{"".join(riadky)}<span class="ak-viac">Detail akcie →</span></span></a>')


def detail_html(a, today):
    """Obsah <main> stránky jednej akcie."""
    minula = dni(a)[1] < today
    badges = "".join(f'<span class="badge akcia-k">{e(k)}</span>' for k in kat(a))
    info = []
    if a.get("miesto"):
        mapa = f' <a href="{e(a["mapa"])}">Otvoriť v mape →</a>' if a.get("mapa") else ""
        info.append(f"<div><dt>Miesto</dt><dd>{e(a['miesto'])}{mapa}</dd></div>")
    if a.get("zaciatok") and not minula:
        info.append(f"<div><dt>Začiatok</dt><dd>{e(a['zaciatok'])}</dd></div>")
    if not minula:
        if a.get("zraz"):
            z = ", ".join(e(v) for v in (a.get("zraz"), a.get("zraz_miesto")) if v)
            info.append(f'<div class="ak-z"><dt>Zraz</dt><dd>{z}</dd></div>')
        else:
            info.append('<div class="ak-z ak-z0"><dt>Zraz</dt><dd>Upresníme v týždni pred akciou.</dd></div>')
    vys = vysledky(a)
    if vys:
        li = "".join(f"<li>{'<b>' + e(t) + '</b> ' if t else ''}{e(v)}</li>" for t, v in vys)
        info.append(f"<div><dt>Výsledok</dt><dd><ul>{li}</ul></dd></div>")
    if a.get("popis"):
        info.append(f"<div><dt>Poznámka</dt><dd>{e(a['popis'])}</dd></div>")
    text = f"{a['nazov']} – {kedy(a)}"
    wa = "https://wa.me/?text=" + quote(f"{text}: {detail_url(a)}")
    tl = [f'<a class="btn btn-y" href="{e(wa)}" data-share data-text="{e(text)}" data-url="{e(detail_url(a))}">Pošli ďalej</a>']
    if not minula:
        tl += [f'<a class="btn btn-d" href="{e(google_link(a, today))}" target="_blank" rel="noopener">Do Google kalendára</a>',
               f'<a class="btn btn-d" href="kalendar/akcia/{e(akcia_id(a))}.ics">Do Apple / iného kalendára</a>']
    return (f'<main>\n<section class="dark"><div class="wrap ak-hero">'
            f'<a class="ak-spat" href="akcie.html">← Všetky akcie</a><div class="ak-ks">{badges}</div>'
            f'<h1 class="disp">{e(a["nazov"])}</h1><p class="ak-kedy">{e(kedy(a))}</p></div></section>\n'
            f'<div class="wrap ak-detail"><dl class="ak-info">{"".join(info)}</dl>'
            f'<div class="ak-tl">{"".join(tl)}</div></div>\n</main>')


def detail_stranka(sablona, a, today):
    """Celá stránka akcie z akcie.html: iná hlavička, <base> a obsah <main>."""
    opis = " · ".join(v for v in [kedy(a), a.get("miesto", ""),
                                  ("Zraz " + ", ".join(v for v in (a.get("zraz"), a.get("zraz_miesto")) if v)) if a.get("zraz") else ""] if v)
    nazov = f"{a['nazov']} – Žilina Bears"
    h = sablona.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<base href="/">', 1)
    h = re.sub(r"<title>.*?</title>", lambda m: f"<title>{e(nazov)}</title>", h, count=1, flags=re.S)
    for attr, val in [('name="description"', opis), ('property="og:title"', nazov), ('property="og:description"', opis)]:
        h = re.sub(rf'<meta {attr} content="[^"]*">', lambda m: f'<meta {attr} content="{e(val)}">', h, count=1)
    meta = (f'<meta property="og:url" content="{e(detail_url(a))}">\n'
            f'<meta property="og:image" content="{SITE}/assets/img/hero.jpg">\n')
    h = h.replace('<meta property="og:type" content="website">', '<meta property="og:type" content="website">\n' + meta, 1)
    return re.sub(r"<main>.*?</main>", lambda m: detail_html(a, today), h, count=1, flags=re.S)


def zapis_detaily(root, akcie, today):
    out = os.path.join(root, "akcia")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    sablona = open(os.path.join(root, "akcie.html"), encoding="utf-8").read()
    for a in akcie:
        with open(os.path.join(out, f"{akcia_id(a)}.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(detail_stranka(sablona, a, today))


def sezona(today):
    """Začiatok aktuálnej sezóny (1. september)."""
    return date(today.year if today.month >= 8 else today.year - 1, 9, 1)


def akcie_bloky(akcie, today):
    zor = sorted(akcie, key=lambda a: (a["datum"], a["nazov"]))
    buduce = [a for a in zor if dni(a)[1] >= today]
    najbl = buduce[0] if buduce else None
    sez = [a for a in zor if dni(a)[0] >= sezona(today) or dni(a)[1] >= today]
    mesiace, skupiny = [], {}
    for a in sez:
        od = dni(a)[0]
        k = f"{od.year}-{od.month:02d}"
        if k not in skupiny:
            skupiny[k] = []
            mesiace.append((k, f"{MESIAC[od.month - 1]} {od.year}"))
        skupiny[k].append(a)
    casti = []
    for k, nazov in mesiace:
        dl = "\n".join(akcia_html(a, today, stav="najblizsia" if a is najbl else "minula" if dni(a)[1] < today else "")
                       for a in skupiny[k])
        casti.append(f'<section class="ak-mesiac" id="m-{k}"><h2 class="ak-mh">{e(nazov)}</h2>'
                     f'<div class="grid news akcie">{dl}</div></section>')
    if not buduce:
        casti.append('<div class="empty">Ďalšie akcie doplníme, keď bude známy rozpis.</div>')
    chips = ['<button type="button" class="chip" aria-pressed="true" data-f="">Všetky</button>'] + \
        [f'<button type="button" class="chip" aria-pressed="false" data-f="{slug(k)}">{e(k)}</button>' for k in KATEGORIE]
    skoky = "".join(f'<a class="ak-skok" href="#m-{k}">{e(n.split()[0])}</a>' for k, n in mesiace)
    odbery = []
    for nazov, subor in [("Všetky akcie", "akcie.ics")] + [(k, f"akcie-{slug(k)}.ics") for k in KATEGORIE]:
        apple, google = odber(subor)
        odbery.append(f'<li><b>{e(nazov)}</b><span><a href="{e(apple)}">iPhone</a> · '
                      f'<a href="{e(google)}" target="_blank" rel="noopener">Google</a></span></li>')
    uvod = "\n".join(akcia_html(a, today, plna=False, stav="najblizsia" if i == 0 else "")
                     for i, a in enumerate(buduce[:4]))
    home = (f'<section id="akcie" class="wrap sec"><div class="sec-head"><div><div class="kicker">Kalendár</div>'
            f'<h2 class="disp h2">Najbližšie akcie</h2></div><a class="more" href="akcie.html">Celý kalendár a odber →</a></div>'
            f'<div class="grid news akcie">{uvod}</div></section>') if buduce else ""
    return {"akcie-zoznam": "\n".join(casti), "akcie-filtre": "".join(chips), "akcie-mesiace": skoky,
            "akcie-odber": "".join(odbery), "akcie-uvod": home}


def zapis_kalendare(root, treningy, akcie, today):
    out = os.path.join(root, "kalendar")
    os.makedirs(os.path.join(out, "akcia"), exist_ok=True)
    for f in os.listdir(os.path.join(out, "akcia")):
        os.remove(os.path.join(out, "akcia", f))
    w = lambda p, s: open(os.path.join(out, p), "w", encoding="utf-8", newline="").write(s)
    for x in treningy:
        w(f"treningy-{slug(x['skupina'])}.ics", trening_ics(x, today))
    w("akcie.ics", calendar("Žilina Bears – akcie", [akcia_event(a, today) for a in akcie], tz=True))
    for k in KATEGORIE:
        sel = [a for a in akcie if k in kat(a) or "Všetci" in kat(a)]
        w(f"akcie-{slug(k)}.ics", calendar(f"Žilina Bears – {k}", [akcia_event(a, today) for a in sel], tz=True))
    for a in akcie:
        w(f"akcia/{akcia_id(a)}.ics", calendar("Žilina Bears", [akcia_event(a, today)], tz=True))
    return len(akcie)
