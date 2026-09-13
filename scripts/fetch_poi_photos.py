# -*- coding: utf-8 -*-
"""为每个景点抓取 3-5 张无水印真实实拍图（Wikimedia Commons），存到本地并改写 POI 数据。

- 数据源：Wikimedia Commons 搜索 + imageinfo 缩略图（iiurlwidth=1280，无水印）。
- 产物：static/media/pois/<poi_id>/imgN.jpg 本地文件；data/poi/changsha.json 的 images 改写为
        本地相对路径（由 server 直接托管，离线可看）。
- 失败开路由：某个景点下不到图时，保留其原有 images 条目，不影响整体。

用法：  python scripts/fetch_poi_photos.py
仅用标准库（urllib/json/shutil/os）。网络到 commons.wikimedia.org 需可用。
"""
import json, os, shutil, time, urllib.parse, urllib.request, urllib.error

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_FILE = os.path.join(BASE, "data", "poi", "changsha.json")
MEDIA_DIR = os.path.join(BASE, "static", "media", "pois")

# 每景点抓取目标数量；抓不到时保留原图
TARGET = 5
MIN = 3

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "ClearMap-photos/1.0 (offline local map; edu)"}
TIMEOUT = 25

# 常见长沙景点的英文/拼音别称，帮助 Commons 搜索命中
ALIASES = {
    "岳麓山": ["Yuelu Mountain", "Yuelu Hill"],
    "岳麓书院": ["Yuelu Academy"],
    "橘子洲": ["Orange Isle", "Orange Island"],
    "湖南大学": ["Hunan University"],
    "五一广场": ["Wuyi Square Changsha"],
    "太平街": ["Taiping Street Changsha"],
    "天心阁": ["Tianxin Pavilion"],
    "杜甫江阁": ["Du Fu Jiang Ge"],
    "爱晚亭": ["Aiwan Pavilion", "Love Evening Pavilion"],
    "长沙世界之窗": ["Window of the World Changsha"],
    "长沙海底世界": ["Changsha Aquarium"],
    "湖南省博物馆": ["Hunan Provincial Museum"],
    "国际会展中心": ["Changsha International Convention Center"],
    "开福寺": ["Kaifu Temple Changsha"],
    "星沙": ["Xingsha"],
    "望城": ["Wangcheng"],
    "黄兴路": ["Huangxing Road Changsha"],
    "坡子街": ["Pozi Street"],
    "窑岭": ["Yaoling"],
    "洋湖": ["Yanghu"],
    "梅溪湖": ["Meixi Lake"],
    "松雅湖": ["Songya Lake"],
}


def find_alias(name):
    for cn, en in ALIASES.items():
        if cn in name:
            return en
    return None


def fetch_json(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def search(query, limit=8):
    """返回 [{url, mime, width}] 命中的图片列表。"""
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": query, "gsrnamespace": "6",
        "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1280,
    }
    d = fetch_json(params)
    pages = (d.get("query") or {}).get("pages") or {}
    out = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [None])[0]
        if not ii:
            continue
        if "/" in ii.get("mime", "") and ii["mime"].split("/", 1)[0] not in ("image",):
            continue
        thumb = ii.get("thumburl") or ii.get("url")
        if not thumb:
            continue
        out.append({"url": thumb, "mime": ii.get("mime", "image/jpeg"),
                    "w": ii.get("thumbwidth") or ii.get("width")})
    # 去重（同文件名）
    seen, uniq = set(), []
    for o in out:
        key = os.path.basename(o["url"]).split("?")[0] or o["url"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(o)
    return uniq


def queries_for(poi):
    name = poi["name"]
    district = poi.get("district", "")
    qs = [name]
    a = find_alias(name)
    if a:
        qs = list(a) + qs
    if district:
        qs.append(name + " " + district)
    # 去空格别名（去掉“长沙”“区民众化后缀”尽量命中）
    qs.append((name or "").replace("区", "").replace("市", ""))
    return [q for q in dict.fromkeys(qs) if q and q.strip()]


def save(url, folder, idx):
    ext_map = {"image/png": ".png", "image/gif": ".gif", "image/webp": ".webp",
               "image/svg+xml": ".svg", "image/jpeg": ".jpg"}
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        # 由 content-type 推断扩展名（若无则取默认 .jpg）
        ct = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        ext = ext_map.get(ct) or ".jpg"
        with open(os.path.join(folder, "tmp%d" % idx), "wb") as f:
            shutil.copyfileobj(r, f)
    final = os.path.join(folder, "img%d%s" % (idx, ext))
    os.replace(os.path.join(folder, "tmp%d" % idx), final)
    return os.path.basename(final), ext


def main():
    if not os.path.isfile(POI_FILE):
        raise SystemExit("找不到 POI 数据文件：%s" % POI_FILE)
    with open(POI_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)

    changed = 0
    for poi in doc.get("pois", []):
        pid = poi["id"]
        name = poi["name"]
        folder = os.path.join(MEDIA_DIR, pid)
        os.makedirs(folder, exist_ok=True)
        hits = []
        for q in queries_for(poi):
            try:
                hits = search(q)
            except (urllib.error.URLError, OSError, ValueError) as e:
                print("  [warn] 搜索失败 %s: %s" % (q, e))
                continue
            if hits:
                break
            time.sleep(0.3)
        saved = []
        kept_old = []
        if hits:
            for idx, h in enumerate(hits[:TARGET], start=1):
                if len(saved) >= TARGET:
                    break
                try:
                    base, ext = save(h["url"], folder, idx)
                    # 本地相对路径：由 server 托管（其扩展名可能非 .jpg）
                    saved.append({"src": "/media/pois/%s/%s" % (pid, base),
                                  "alt": name, "ext": ext})
                except (urllib.error.URLError, OSError, ValueError) as e:
                    print("  [warn] 下载失败 %s: %s" % (h.get("url"), e))
        # 不足 MIN 张时，保留原有 AI 图补齐
        old = [dict(i) for i in poi.get("images", []) if isinstance(i, dict)]
        if len(saved) < MIN and old:
            keep = old[: (MIN - len(saved))]
            keep += [i for i in old if i not in keep][: (TARGET - len(saved))]
            saved = (saved + keep)[:TARGET]
        if saved != poi.get("images"):
            poi["images"] = saved
            changed += 1
            print("  %-12s %-14s → %d 图 (%d 新下载)" % (pid, name, len(saved), sum(1 for i in saved if i.get("ext"))))
        else:
            print("  %-12s %-14s → 保留原有图" % (pid, name))

    with open(POI_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print("== 完成 ==")
    print("更新了 %d 个景点的图片字段；本地图片在 %s" % (changed, MEDIA_DIR))


if __name__ == "__main__":
    main()