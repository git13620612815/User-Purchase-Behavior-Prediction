"""从维基共享资源下载与商品名称对应的实拍图。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "products"
QUERIES = {
    "CN001": "iPhone 11 black",
    "CN002": "Huawei smartphone",
    "CN003": "Honor smartphone",
    "CN004": "Xiaomi Redmi phone",
    "CN005": "white smartphone",
    "CN006": "OPPO smartphone",
    "CN007": "vivo smartphone orange",
    "CN008": "OnePlus smartphone blue",
    "CN009": "side-by-side refrigerator",
    "CN010": "front-load washing machine",
    "CN011": "split air conditioner indoor unit",
    "CN012": "microwave oven",
    "CN013": "flat screen television",
    "CN014": "soy milk maker appliance",
    "CN015": "pedestal fan",
    "CN016": "electric storage water heater",
    "CN017": "grey hoodie",
    "CN018": "blue jeans",
    "CN019": "red down jacket",
    "CN020": "white t-shirt",
    "CN021": "canvas sneakers",
    "CN022": "backpack",
    "CN023": "wool scarf",
    "CN024": "casual trousers",
    "CN025": "milk carton",
    "CN026": "yogurt cup",
    "CN027": "bag of rice",
    "CN028": "mixed nuts",
    "CN029": "plastic water bottle",
    "CN030": "instant noodles",
    "CN031": "beef jerky",
    "CN032": "rice cracker snack",
    "CN033": "running shoes",
    "CN034": "basketball shoes",
    "CN035": "yoga mat",
    "CN036": "badminton racket",
    "CN037": "sports water bottle",
    "CN038": "hiking jacket green",
    "CN039": "basketball ball",
    "CN040": "hiking backpack",
    "CN041": "desk lamp",
    "CN042": "bed sheet set",
    "CN043": "laundry detergent bottle",
    "CN044": "plastic storage box",
    "CN045": "wok pan",
    "CN046": "bed pillow",
    "CN047": "facial tissue box",
    "CN048": "LED desk lamp",
}
SKIP = ("logo", "icon", "flag", "map", "diagram", "svg", "coat of arms", "wordmark", "screenshot", "mall", "shop", "community fridge")
REDO = {"CN001", "CN005", "CN007", "CN009"}


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "purchase-predict/1.0 (local product catalog)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                raise
            time.sleep(15 * (attempt + 1))
    return {}


def search(query: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": 800,
    })
    payload = fetch_json("https://commons.wikimedia.org/w/api.php?" + params)
    pages = (payload.get("query") or {}).get("pages") or {}
    found = []
    for page in pages.values():
        title = str(page.get("title", "")).lower()
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime") or ""
        url = info.get("thumburl") or info.get("url")
        if mime not in ("image/jpeg", "image/png", "image/webp") or not url:
            continue
        if any(word in title for word in SKIP):
            continue
        if int(info.get("size") or 0) < 8000 and not info.get("thumburl"):
            continue
        words = [word.lower() for word in query.split() if len(word) > 2]
        score = sum(2 for word in words if word in title)
        found.append({"title": page.get("title"), "url": url, "mime": mime, "score": score})
    found.sort(key=lambda item: item["score"], reverse=True)
    return found


def download(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "purchase-predict/1.0 (local product catalog)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                path.write_bytes(response.read())
                return
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                raise
            time.sleep(15 * (attempt + 1))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for sku, query in QUERIES.items():
        existing = list(OUT.glob(sku + ".*"))
        if existing and sku not in REDO and not str(existing[0]).endswith("manifest.json"):
            manifest[sku] = existing[0].name
            print(f"KEEP {sku}")
            continue
        for old in existing:
            if old.name != "manifest.json":
                old.unlink()
        time.sleep(2)
        matches = search(query)
        if not matches:
            print(f"MISS {sku} {query}")
            continue
        chosen = matches[0]
        ext = ".png" if chosen["mime"] == "image/png" else ".jpg"
        path = OUT / f"{sku}{ext}"
        download(chosen["url"], path)
        manifest[sku] = path.name
        print(f"OK {sku} {chosen['title']} -> {path.name} {path.stat().st_size}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {len(manifest)}")


if __name__ == "__main__":
    main()
