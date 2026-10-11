#!/usr/bin/env python3
"""
Zlúči už stiahnuté FB a IG príspevky (data/posts) podľa aktuálnych pravidiel
v fetch_social.py – bez tokenu a bez pripojenia na Metu.
Hodí sa na lokálnu kontrolu alebo po zmene pravidiel zlučovania.

Použitie:  python scripts/remerge_local.py
"""
import glob
import os

import fetch_social as F
from common import INDEX, POSTS_DIR, load_json, save_json


def main():
    posts = [load_json(p, {}) for p in glob.glob(f"{POSTS_DIR}/*.json")]
    def item(p):
        return {"source": p["source"], "sid": p["id"].split("-", 1)[1], "date": p["date"],
                "text": p.get("text", ""), "link": p.get("link"), "imgs": p.get("images", []),
                "pid": p["id"]}
    fb = [item(p) for p in posts if p.get("source") == "facebook"]
    ig = [item(p) for p in posts if p.get("source") == "instagram"]
    for f in fb:
        f["also_on"] = []
    F.merge(fb, ig)

    index = load_json(INDEX, [])
    removed = {i["pid"] for i in ig if i.get("merged")}
    for f in fb:
        p = load_json(f"{POSTS_DIR}/{f['pid']}.json", {})
        if p.get("also_on", []) != f["also_on"]:
            p["also_on"] = f["also_on"]
            save_json(f"{POSTS_DIR}/{f['pid']}.json", p)
    for pid in removed:
        os.remove(f"{POSTS_DIR}/{pid}.json")
    index = [p for p in index if p["id"] not in removed]
    save_json(INDEX, index, indent=1)
    print(f"Zlúčených {len(removed)} dvojíc FB + IG, spolu {len(index)} príspevkov.")


if __name__ == "__main__":
    main()
