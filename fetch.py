#!/usr/bin/env python3
"""Fetch product images, compress to WebP, pack zips + report.json into out/."""
import json, os, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import requests
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
todo = json.load(open("todo.json"))
os.makedirs("out/webp", exist_ok=True)

def fetch(item):
    pid, url = item["id"], item["url"]
    err = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code in (404, 410):
                return (pid, "dead", str(r.status_code))
            r.raise_for_status()
            im = Image.open(BytesIO(r.content)); im.load()
            im = im.convert("RGB"); im.thumbnail((1200, 1200))
            im.save(f"out/webp/{pid}.webp", "WEBP", quality=82)
            return (pid, "done", str(len(r.content)))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:120]
            time.sleep(3 * (attempt + 1))
    return (pid, "failed", err)

done, dead, failed = [], [], []
with ThreadPoolExecutor(max_workers=4) as ex:
    for pid, status, info in ex.map(fetch, todo):
        if status == "done": done.append(pid)
        elif status == "dead": dead.append(pid)
        else: failed.append({"id": pid, "error": info})
        print(pid, status, info, flush=True)

json.dump({"done": sorted(done), "dead": sorted(dead), "failed": failed},
          open("out/report.json", "w"), indent=1)
files = sorted(os.listdir("out/webp"))
for i in range(0, len(files), 40):
    part = i // 40 + 1
    with zipfile.ZipFile(f"out/results-part-{part:02d}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in files[i:i + 40]:
            z.write(f"out/webp/{f}", f)
print(f"SUMMARY done={len(done)} dead={len(dead)} failed={len(failed)}")
