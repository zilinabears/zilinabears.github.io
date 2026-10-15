# Web Žilina Bears

Statický web klubu na GitHub Pages. Novinky sa automaticky sťahujú z Facebooku
a Instagramu klubu každé 3 hodiny, statický obsah (tréningy, nábor, kontakt)
sa upravuje priamo v HTML.

## Štruktúra

| Cesta | Čo to je |
| --- | --- |
| `index.html` | Úvodná stránka – tréningy, nábor, o klube, kontakt |
| `ragby.html` | Sekcia O ragby – články a materiály na stiahnutie |
| `obsah/` | Texty článkov O ragby, ich obrázky a súbory |
| `noviny.html` | Zoznam noviniek s filtrom podľa zdroja |
| `clanok.html?id=…` | Detail príspevku alebo archívneho článku |
| `assets/css/style.css` | Celý vzhľad webu |
| `assets/js/site.js` | Menu na mobile, načítanie noviniek, galéria |
| `assets/img/hero.jpg` | Úvodná fotka (doplniť, na šírku, aspoň 1600 px) |
| `data/posts.json` | Zoznam všetkých noviniek (generuje sa) |
| `data/posts/<id>.json` | Obsah jednotlivých noviniek (generuje sa) |
| `data/hidden.json` | Zoznam ID príspevkov, ktoré sa na webe nemajú zobraziť |
| `scripts/fetch_social.py` | Sťahovanie z FB a IG cez Meta Graph API |
| `scripts/backup_archive_images.py` | Jednorazová záloha fotiek zo starých článkov |

## Bežné úpravy

**Zmena času alebo miesta tréningu:** na GitHube otvor `data/treningy.json`, klikni na ceruzku,
prepíš text v úvodzovkách a klikni na *Commit changes*. Rozvrh sa zmení naraz v úvode, v sekcii
Tréningy aj v anglickej časti. Do poľa `"oznam"` môžeš napísať krátku správu (napr. že tréning odpadá),
zobrazí sa žltým v úvode; keď ju vymažeš na `""`, zmizne. Web sa aktualizuje do 2 minút.

**Skrytie príspevku:** ID príspevku je v adrese článku (`clanok.html?id=fb-123_456`).
Pridaj ho do `data/hidden.json`, napr. `["fb-123_456"]`. Pri ďalšom behu zmizne.

## Sekcia „O ragby“ – články a materiály na stiahnutie

Články sú obyčajné textové súbory v priečinku `obsah/`. Web ich zobrazí na stránke `ragby.html`
a tri najnovšie aj na úvodnej stránke.

**Nový článok:** na GitHube otvor `obsah/_vzor.md`, skopíruj jeho obsah, potom v priečinku `obsah`
klikni *Add file → Create new file*, pomenuj ho napr. `skrumaz.md` (bez medzier a diakritiky),
vlož text, uprav hlavičku a klikni *Commit changes*. Do 2 minút je na webe.

**Obrázky a súbory na stiahnutie** (PDF plagáty, brožúrky…) nahraj cez *Add file → Upload files*
do `obsah/obrazky/` resp. `obsah/subory/` a v hlavičke článku na ne odkáž:

```
obrazok: obsah/obrazky/skrumaz.jpg
subor: obsah/subory/plagat.pdf | Plagát A5 (PDF)
```

Kategórie si vymýšľaš sám (napr. Pravidlá, História, Pre rodičov, Na stiahnutie) – web z nich
automaticky spraví filter. Článok zmažeš tak, že zmažeš jeho `.md` súbor.

Lokálne si zmeny pozrieš po spustení `python scripts/build_content.py`.

## Nastavenie (raz)

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. **Settings → Secrets and variables → Actions:**
   - záložka *Secrets* → `META_TOKEN` = token systémového používateľa z Meta Business Suite,
   - záložka *Variables* → `FB_PAGE_ID` = ID Facebook stránky klubu,
   - voliteľne *Variables* → `IG_USER_ID` (inak sa zistí zo stránky).
3. **Actions → Aktualizácia a nasadenie webu → Run workflow**, pri prvom spustení zaškrtni
   „Stiahnuť celú históriu“.
4. **Actions → Záloha fotiek z archívu → Run workflow** – stiahne fotky starých článkov
   z postimg/ibb/WordPressu. Potom spusti ešte raz krok 3, aby sa zmeny nasadili.

Bez tokenu web funguje tiež – zobrazí len archív starých článkov.

### Token z Meta Business Suite

V Business Suite → Nastavenia → Používatelia → **Systémoví používatelia** → Pridať
(úloha Admin) → **Priradiť aktíva**: FB stránka a Instagram účet (plná kontrola) →
**Generovať token** pre aplikáciu klubu s oprávneniami `pages_show_list`,
`pages_read_engagement`, `pages_read_user_content`, `instagram_basic`,
`business_management`, platnosť *Nikdy*.
Aplikáciu vytvoríš na developers.facebook.com (typ *Business*) a pripojíš k firemnému portfóliu klubu.

## Lokálne spustenie

```bash
python3 -m http.server 8000   # potom http://localhost:8000
```
Stránku netreba otvárať priamo zo súboru, novinky sa načítavajú cez `fetch` a vyžadujú server.
