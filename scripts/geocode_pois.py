# -*- coding: utf-8 -*-
"""一次性工具：用 Nominatim 为 18 个 POI 解析真实经纬度。
结果打印后手工核对/落盘。仅在构建期使用，运行时无依赖。"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_FILE = os.path.join(BASE, "data", "poi", "changsha.json")

# POI id -> 用于地理编码的查询词（加"长沙"限定城市）
QUERIES = {
    "yuelu-mountain": "岳麓山风景名胜区 长沙",
    "yuelu-academy": "岳麓书院 长沙",
    "yuhu-wetland": "洋湖湿地公园 长沙",
    "juzizhou": "橘子洲 长沙",
    "xiangjiang-view": "湘江风光带 长沙",
    "taiping-street": "太平老街 长沙",
    "pozi-street": "坡子街 长沙",
    "huogongdian": "火宫殿 长沙坡子街",
    "wenheyou": "文和友 长沙海信广场",
    "wuyi-square": "五一广场 长沙",
    "ifs-changsha": "长沙国金中心 IFS 长沙",
    "huangxing-walk": "黄兴路步行街 长沙",
    "jiayi-guju": "贾谊故居 长沙",
    "hun-museum": "湖南省博物馆 长沙",
    "tianxin-pavilion": "天心阁 长沙",
    "dufu-jiangge": "杜甫江阁 长沙",
    "jiefangxi": "解放西路 长沙",
    "orange-ride": "环湘江骑行道 长沙",
}

def geocode(q):
    url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": "ClearMap-build/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        arr = json.load(r)
    if not arr:
        return None
    return float(arr[0]["lat"]), float(arr[0]["lon"])

def main():
    with open(POI_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    for poi in doc["pois"]:
        pid = poi["id"]
        q = QUERIES.get(pid)
        if not q:
            print("%-18s 无查询词，跳过" % pid)
            continue
        try:
            got = geocode(q)
            if got:
                poi["lat"] = got[0]
                poi["lon"] = got[1]
                print("%-18s → (%.6f, %.6f)" % (pid, got[0], got[1]))
            else:
                print("%-18s 未解析到" % pid)
        except Exception as ex:
            print("%-18s 失败: %r" % (pid, ex))
        time.sleep(1.1)  # Nominatim 限速 1 req/s

    with open(POI_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()