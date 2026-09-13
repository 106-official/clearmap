# -*- coding: utf-8 -*-
"""构建真实地理地图数据：从 Overpass API 抓取长沙主城五区 OSM 数据，
Web Mercator 投影量化后，离线落盘为 static/map/changsha.json。

仅使用 Python 标准库（urllib/json/math）。运行一次即可，产物供运行时离线加载。
"""
import json, math, os, sys, time, urllib.request, urllib.error

# ---- 常量（与前端 map.js 共用，务必一致）----
WORLD = 1 << 23  # 8388608，世界坐标整数空间
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根
OUT_DIR = os.path.join(BASE, "static", "map")
OUT_FILE = os.path.join(OUT_DIR, "changsha.json")

# 主城区 + 近郊 bbox（含望城北、长沙县东、湘江两岸主城与南郊）
BBOX = (28.02, 112.78, 28.56, 113.40)  # (south, west, north, east)
DISTRICT_NAMES = {"岳麓区", "天心区", "芙蓉区", "开福区", "雨花区", "望城区", "长沙县"}

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
DISTRICTS_REQ = "relation['boundary'='administrative']['admin_level'='6']"
WATER_REQ = '(way["natural"="water"](%f,%f,%f,%f);way["waterway"="river"](%f,%f,%f,%f););out geom;' % (BBOX + BBOX)

# 建筑抓取：分块（避免单次超载），每块约 0.068° x 0.068°；块间留间隔避免打爆限流
BTILE_X = 9
BTILE_Y = 8
TILE_BACKOFF = [8, 20, 40, 70]  # 每块失败重试等待（秒）
TILE_PAUSE = 2.5  # 相邻块之间的礼貌间隔（秒）


def proj(lon, lat):
    x = (lon + 180.0) / 360.0 * WORLD
    lat = max(-85.0, min(85.0, lat))  # Web Mercator 有效纬度范围
    rad = math.radians(lat)
    y = (1.0 - math.log(math.tan(rad) + 1.0 / math.cos(rad)) / math.pi) / 2.0 * WORLD
    return x, y


def fetch(query, timeout=240, backoff=(5, 12, 30)):
    data = ("[out:json][timeout:%d];%s" % (timeout, query)).encode("utf-8")
    last = None
    for attempt in range(len(backoff)):
        for ep in ENDPOINTS:
            try:
                req = urllib.request.Request(ep, data=data,
                                             headers={"User-Agent": "ClearMap-build/1.0 (local offline map)"})
                # 顶层 socket 超时：防止僵死镜像无限挂起（重试逻辑再兜底）
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.load(r)
            except (urllib.error.URLError, OSError, ValueError) as e:
                last = e
        # 指数退避
        wait = backoff[attempt]
        print("    重试 %d/%d（等 %ds）：%s" % (attempt + 1, len(backoff), wait, last), flush=True)
        time.sleep(wait)
    raise RuntimeError("Overpass 请求失败: %s" % last)


def geom_points(feat):
    """从 with_geom 返回里取节点坐标，并投影为世界坐标 [x, y] 列表。"""
    g = feat.get("geometry")
    if not g:
        return []
    return [list(proj(p["lon"], p["lat"])) for p in g]


def relation_way_segments(feat):
    """relation 在 out geom 下几何放在 members 的 way 成员里（node 成员无几何）。

    返回世界坐标线段列表 [[[x,y],...], ...]，每条线段 = 一条边界 way 的节点序列。
    """
    segs = []
    for m in feat.get("members") or []:
        if m.get("type") != "way" or not m.get("geometry"):
            continue
        segs.append([list(proj(p["lon"], p["lat"])) for p in m["geometry"]])
    return segs


def assemble_rings(segs, tol=5.0):
    """把首尾相接的边界线段拼成闭合环（贪心、单向延伸）。

    返回世界坐标环列表，每环首尾相接（已去掉重复的闭合点）。
    """
    segs = [list(s) for s in segs if len(s) >= 2]
    rings = []
    while segs:
        ring = list(segs.pop(0))
        while True:
            tail = ring[-1]
            found = False
            for i in range(len(segs) - 1, -1, -1):
                sg = segs[i]
                if math.hypot(sg[0][0] - tail[0], sg[0][1] - tail[1]) <= tol:
                    ring.extend(sg[1:])
                    del segs[i]
                    found = True
                    break
                if math.hypot(sg[-1][0] - tail[0], sg[-1][1] - tail[1]) <= tol:
                    ring.extend(list(reversed(sg))[1:])
                    del segs[i]
                    found = True
                    break
            if not found:
                break
        # 去掉重复闭合点
        if len(ring) >= 2 and math.hypot(ring[0][0] - ring[-1][0], ring[0][1] - ring[-1][1]) <= tol:
            ring.pop()
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def thick(points, tol):
    """抽稀：保留首、尾与转折点，丢弃与上一个保留点距离小于 tol 的中间点。"""
    if len(points) < 2:
        return points
    out = [points[0]]
    for p in points[1:]:
        px, py = out[-1]
        if math.hypot(p[0] - px, p[1] - py) < tol:
            continue  # 过渡密集，忽略
        out.append(p)
    # 确保终点保留，避免丢弃末点导致路径回缩
    if len(out) >= 2:
        px, py = out[-1]
        lx, ly = points[-1]
        if math.hypot(lx - px, ly - py) < tol:
            out[-1] = points[-1]
        elif points[-1] != out[-1]:
            out.append(points[-1])
    return out


def encode_path(world_pts):
    """编码为 SVG path 的 d 字符串（绝对坐标）。"""
    if len(world_pts) < 2:
        return None
    parts = ["M %d %d" % (round(world_pts[0][0]), round(world_pts[0][1]))]
    for x, y in world_pts[1:]:
        parts.append("L %d %d" % (round(x), round(y)))
    return " ".join(parts)


def polygon_area(pts):
    """鞋带公式求多边形面积（世界单位²）。"""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def to_local(world_pts, origin):
    return [[x - origin[0], y - origin[1]] for x, y in world_pts]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    s, w, n, e = BBOX
    origin_world = proj(w, n)  # bbox 左上角

    print("== 抓取道路 ==")
    road_feats = fetch(
        'way["highway"](%f,%f,%f,%f);out geom;' % BBOX)
    print("  道路 way 数:", len(road_feats.get("elements", [])))

    print("== 抓取水域 ==")
    water_feats = fetch(WATER_REQ)

    print("== 抓取区界 ==")
    district_feats = fetch(DISTRICTS_REQ + "(%f,%f,%f,%f);out geom;" % BBOX)

    print("== 抓取建筑（分块）==")
    bld_elems = []
    sx, sy = (e - w) / BTILE_X, (n - s) / BTILE_Y
    for iy in range(BTILE_Y):
        for ix in range(BTILE_X):
            since = time.time()
            qs, qw = s + iy * sy, w + ix * sx
            qn, qe = qs + sy, qw + sx
            try:
                fy = fetch('way["building"](%.5f,%.5f,%.5f,%.5f);out geom;' % (qs, qw, qn, qe),
                           timeout=240, backoff=TILE_BACKOFF)
                bld_elems.extend(fy.get("elements", []))
                print("  块(%d,%d) → %d（%.1fs）" % (ix, iy, len(fy.get("elements", [])), time.time() - since), flush=True)
            except RuntimeError as ex:
                print("  块(%d,%d) 失败跳过: %s" % (ix, iy, ex), flush=True)
            time.sleep(TILE_PAUSE)

    # ---- 区界 ----
    districts = []
    seen = set()
    for f in district_feats.get("elements", []):
        name = (f.get("tags") or {}).get("name", "")
        match = next((dn for dn in DISTRICT_NAMES if dn in name or name in dn), None)
        if not match or match in seen:
            continue
        rings = assemble_rings(relation_way_segments(f))
        if not rings:
            continue
        # 世界坐标 → 局部坐标（与道路/建筑一致），每环一条闭合子路径；
        # 质心取所有环点均值（用于前端片区标注定位）
        subpaths = []
        pts_all = []
        for ring in rings:
            local = to_local(ring, origin_world)
            pts_all.extend(local)
            path = encode_path(thick(local, 3))
            if path:
                subpaths.append(path + " Z")
        if not subpaths:
            continue
        path = " ".join(subpaths)
        cx = sum(p[0] for p in pts_all) / len(pts_all)
        cy = sum(p[1] for p in pts_all) / len(pts_all)
        districts.append({"name": match, "path": path, "cx": round(cx), "cy": round(cy)})
        seen.add(match)
        print("  区界命中:", match, "| 环数:", len(rings))

    # ---- 水域 ----
    water = []
    for f in water_feats.get("elements", []):
        tags = f.get("tags") or {}
        kind = "river" if tags.get("waterway") == "river" else "area"
        pts = to_local(geom_points(f), origin_world)
        path = encode_path(thick(pts, 4))
        if path:
            if kind == "area" and len(pts) >= 3:
                path += " Z"
            water.append({"kind": kind, "path": path})

    # ---- 道路（按 tier）----
    tier_map = {
        "motorway": 1, "motorway_link": 1, "trunk": 1, "trunk_link": 1,
        "primary": 1, "primary_link": 1,
        "secondary": 2, "secondary_link": 2, "tertiary": 2, "tertiary_link": 2,
        "residential": 3, "unclassified": 3, "service": 3, "living_street": 3,
        "track": 4, "footway": 4, "cycleway": 4, "path": 4, "pedestrian": 4,
        "steps": 4, "bridleway": 4, "corridor": 4,
    }
    roads = {"tier1": [], "tier2": [], "tier3": [], "tier4": []}
    for f in road_feats.get("elements", []):
        cls = (f.get("tags") or {}).get("highway", "")
        tier = tier_map.get(cls)
        if not tier:
            continue
        pts = to_local(geom_points(f), origin_world)
        tol = 2 if tier >= 3 else 4
        path = encode_path(thick(pts, tol))
        if not path:
            continue
        name = (f.get("tags") or {}).get("name", "")
        roads["tier%d" % tier].append({"cls": cls, "name": name, "path": path})

    # ---- 建筑（网格分桶）----
    cell = 512
    grid = {}
    m2_per_wu2 = (4.22) ** 2  # 世界单位² → 平方米²
    kept = 0
    dropped = 0
    for f in bld_elems:
        pts = to_local(geom_points(f), origin_world)
        if len(pts) < 4:
            dropped += 1
            continue
        area_wu2 = polygon_area(pts)
        if area_wu2 * m2_per_wu2 < 40:  # 过小，丢弃
            dropped += 1
            continue
        flat = [round(c) for p in pts for c in p]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        gk = "%d_%d" % (int(cx // cell), int(cy // cell))
        grid.setdefault(gk, []).append({"area": round(area_wu2), "pts": flat})
        kept += 1

    meta = {
        "city": "长沙",
        "bbox": [round(w, 6), round(s, 6), round(e, 6), round(n, 6)],
        "world": WORLD,
        "origin": [round(origin_world[0]), round(origin_world[1])],
        "cell": cell,
        "m2PerWu2": m2_per_wu2,
        "counts": {
            "roads": {k: len(v) for k, v in roads.items()},
            "buildings": kept,
            "buildings_dropped": dropped,
            "water": len(water),
            "districts": len(districts),
        },
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    payload = {
        "meta": meta,
        "districts": districts,
        "water": water,
        "roads": roads,
        "buildings": {"grid": grid},
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    size_mb = os.path.getsize(OUT_FILE) / 1048576
    print("\n== 完成 ==")
    print(json.dumps(meta["counts"], ensure_ascii=False, indent=2))
    print("输出:", OUT_FILE)
    print("大小: %.2f MB" % size_mb)
    if not seen:
        print("!! 警告：未命中任何行政区！")


if __name__ == "__main__":
    main()