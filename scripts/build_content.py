#!/usr/bin/env python3
"""
Z textových článkov v priečinku obsah/*.md vyrobí data/ragby.json a data/ragby/<názov>.json,
ktoré zobrazuje stránka „O ragby“. Spúšťa sa automaticky pri každom nasadení;
lokálne:  python scripts/build_content.py

Formát článku (súbory začínajúce podčiarkovníkom sa ignorujú, napr. _vzor.md):

    ---
    nazov: Názov článku
    datum: 2026-10-12
    kategoria: Pravidlá
    perex: Jedna-dve vety do zoznamu článkov.
    obrazok: obsah/obrazky/titulna.jpg
    subor: obsah/subory/plagat.pdf | Plagát na stiahnutie (A5, PDF)
    subor: obsah/subory/brozura.pdf | Brožúrka (A4, PDF)
    ---
    Text článku v Markdowne…
"""
import glob
import os
import re
import sys

import markdown

from common import DATA, ROOT, save_json

SRC = os.path.join(ROOT, "obsah")
OUT = os.path.join(DATA, "ragby")


def parse(path):
    raw = open(path, encoding="utf-8").read().lstrip("﻿")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if not m:
        raise ValueError("chýba hlavička medzi riadkami ---")
    meta, files = {}, []
    for line in m.group(1).splitlines():
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "subor":
            p, _, label = v.partition("|")
            files.append({"href": p.strip(), "label": (label.strip() or os.path.basename(p.strip()))})
        else:
            meta[k] = v
    if not meta.get("nazov"):
        raise ValueError("chýba 'nazov'")
    return meta, files, m.group(2)


def main():
    os.makedirs(OUT, exist_ok=True)
    index, errors = [], 0
    for path in sorted(glob.glob(os.path.join(SRC, "*.md"))):
        name = os.path.basename(path)
        if name.startswith("_"):
            continue
        slug = os.path.splitext(name)[0]
        try:
            meta, files, body = parse(path)
        except ValueError as e:
            print(f"::warning file=obsah/{name}::{e} – článok preskakujem")
            errors += 1
            continue
        for f in files:
            if not f["href"].startswith("http") and not os.path.exists(os.path.join(ROOT, f["href"])):
                print(f"::warning file=obsah/{name}::súbor {f['href']} neexistuje")
        html = markdown.markdown(body, extensions=["extra", "sane_lists"])
        rec = {"id": slug, "source": "ragby", "title": meta["nazov"], "date": meta.get("datum", ""),
               "category": meta.get("kategoria", "Články"), "excerpt": meta.get("perex", ""),
               "thumb": meta.get("obrazok") or None}
        save_json(os.path.join(OUT, f"{slug}.json"), dict(rec, html=html, files=files))
        index.append(dict(rec, files=len(files)))
    # zmazané články odstránime aj z dát
    keep = {r["id"] for r in index}
    for old in glob.glob(os.path.join(OUT, "*.json")):
        if os.path.splitext(os.path.basename(old))[0] not in keep:
            os.remove(old)
    index.sort(key=lambda r: r["date"], reverse=True)
    save_json(os.path.join(DATA, "ragby.json"), index, indent=1)
    print(f"O ragby: {len(index)} článkov" + (f", {errors} s chybou" if errors else ""))


if __name__ == "__main__":
    sys.exit(main())
