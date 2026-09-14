# -*- coding: utf-8 -*-
"""构建真实地理地图数据：从 Overpass API 抓取指定城市的 OSM 数据，
Web Mercator 投影量化后，离线落盘为 static/map/<city>.json。

仅使用 Python 标准库（urllib/json/math）。运行一次即可，产物供运行时离线加载。
用法：python build_map.py [city]   # city ∈ changsha|shanghai|beijing，缺省 changsha
"""
import json, math, os, sys, time, urllib.request, urllib.error, http.client

# ---- 常量（与前端 map.js 共用，务必一致）----
WORLD = 1 << 23  # 8388608，世界坐标整数空间
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根
OUT_DIR = os.path.join(BASE, "static", "map")

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
DISTRICTS_REQ = "relation['boundary'='administrative']['admin_level'='6']"

# 各城市配置：bbox=(s,w,n,e) · 区名(区界命中) · tiles=建筑分块(按 bbox 面积适配) · 输出名
# 说明：当前主要为“核心城区”矢量底图；全境可后续把 bbox 扩大并按需调细分块。
CITIES = {
    "changsha": {
        "bbox": (28.02, 112.78, 28.56, 113.40),
        "districts": {"岳麓区", "天心区", "芙蓉区", "开福区", "雨花区", "望城区", "长沙县"},
        "tiles": (9, 8),
        "output": "changsha.json",
    },
    "shanghai": {
        "bbox": (31.14, 121.395, 31.31, 121.575),   # 上海核心城区（黄浦/静安/徐汇东等）
        "districts": {"黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区", "浦东新区"},
        "tiles": (8, 7),
        "output": "shanghai.json",
    },
    "beijing": {
        "bbox": (39.72, 116.16, 40.06, 116.62),       # 北京城六区（东城/西城/朝阳/海淀/丰台/石景山）
        "districts": {"东城区", "西城区", "朝阳区", "海淀区", "丰台区", "石景山区"},
        "tiles": (9, 8),        # 道路分块（道路已缓存，勿改）
        "btiles": (15, 13),     # 建筑分块（更细→单次请求更小更快，减少 504/超载）
        "output": "beijing.json",
    },
}

TILE_BACKOFF = [3, 5, 10, 15]  # 每块失败重试等待（秒）
TILE_PAUSE = 2  # 相邻块之间的礼貌间隔（秒）
CACHE_DIR = os.path.join(BASE, "build_cache")  # 已抓取数据缓存，中断后可复用


def load_cache(key):
    p = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None
    return None


def save_cache(key, obj):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(os.path.join(CACHE_DIR, key + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


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
            except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
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


MAX_SPLIT_DEPTH = 3  # 顶层失败最多递归拆成 4^3 个子块，覆盖最密的路网


def collect_tile(qfilter, key, s, w, n, e, label, cache_dir, depth, src_label):
    """抓取单个分块。成功写整块缓存；连续失败则递归拆成 2x2 四份子块再抓。

    每(子)块成功即写入独立缓存 <cache_dir>/<key>.json，重启可复用。
    返回该块的 elements。所有重试仍失败的块返回空（不中断整城）。
    """
    os.makedirs(cache_dir, exist_ok=True)
    cf = os.path.join(cache_dir, key + ".json")
    if os.path.exists(cf):
        try:
            with open(cf, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass
    since = time.time()
    try:
        fy = fetch('%s(%.5f,%.5f,%.5f,%.5f);out geom;' % (qfilter, s, w, n, e),
                   timeout=60, backoff=TILE_BACKOFF)
        te = fy.get("elements", [])
        with open(cf, "w", encoding="utf-8") as fh:
            json.dump(te, fh, ensure_ascii=False)
        print("  %s块 %s → %d（%.1fs）" % (src_label, key, len(te), time.time() - since), flush=True)
        time.sleep(TILE_PAUSE)
        return te
    except Exception as ex:
        if depth >= MAX_SPLIT_DEPTH:
            print("  %s块 %s 已达最大拆分级仍失败，跳过: %s" % (src_label, key, ex), flush=True)
            return []
        # 拆成 2x2 子块递归（子块各自独立缓存/退避，避免大面积重试拖慢全局）
        mid_s, mid_w, mid_n, mid_e = (s + n) / 2, (w + e) / 2, (s + n) / 2, (w + e) / 2
        print("  %s块 %s 拆分重试" % (src_label, key), flush=True)
        time.sleep(TILE_PAUSE)
        te = []
        for qy in (0, 1):
            for qx in (0, 1):
                sub = collect_tile(
                    qfilter, "%s_%d_%d" % (key, qx, qy),
                    (s if qy == 0 else mid_s),      # 子南界
                    (w if qx == 0 else mid_w),      # 子西界
                    (mid_n if qy == 0 else n),      # 子北界
                    (mid_w if qx == 0 else e),      # 子东界
                    label, cache_dir, depth + 1, src_label)
                te.extend(sub)
        return te


def tiled_elements(qfilter, s, w, n, e, tx, ty, label, cache_tag, cache_dir):
    """把某类要素按 bbox 网格分块抓取（避免超大单次请求被 Overpass 截断/超载）。

    每块成功即写入独立缓存 <cache_dir>/<cache_tag>_<ix>_<iy>.json，重启可从中恢复。
    单个分块在重试后仍失败时，会递归拆成 2x2 子块继续抓取，尽量不丢大城密区数据。
    返回合并后的 elements 列表。
    """
    elems = []
    os.makedirs(cache_dir, exist_ok=True)
    sx, sy = (e - w) / tx, (n - s) / ty
    for iy in range(ty):
        for ix in range(tx):
            qs, qw = s + iy * sy, w + ix * sx
            qn, qe = qs + sy, qw + sx
            key = "%s_%d_%d" % (cache_tag, ix, iy)
            if os.path.exists(os.path.join(cache_dir, key + ".json")):
                # 整体命中缓存
                te = collect_tile(qfilter, key, qs, qw, qn, qe, label, cache_dir, 0, label)
                elems.extend(te)
                continue
            # 整块未命中：先尝试整块抓取，失败则由 collect_tile 自行拆分
            elems.extend(_collect_root(qfilter, key, qs, qw, qn, qe, label, cache_dir))
    return elems


def _collect_root(qfilter, key, qs, qw, qn, qe, label, cache_dir):
    """顶层分块入口：先尝试整块，若整块缓存不存在才进入 collect_tile（内含拆分）。"""
    cf = os.path.join(cache_dir, key + ".json")
    if os.path.exists(cf):
        try:
            with open(cf, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass
    return collect_tile(qfilter, key, qs, qw, qn, qe, label, cache_dir, 0, label)


def main():
    city = (sys.argv[1] if len(sys.argv) > 1 else "changsha").strip().lower()
    cfg = CITIES.get(city)
    if not cfg:
        sys.exit("未知城市: %s（可选 %s）" % (city, "、".join(CITIES)))
    s, w, n, e = cfg["bbox"]
    DISTRICT_NAMES = cfg["districts"]
    BTILE_X, BTILE_Y = cfg["tiles"]
    BGX, BGY = cfg.get("btiles", (BTILE_X, BTILE_Y))  # 建筑可用更细分块（单次更小更快）
    OUT_FILE = os.path.join(OUT_DIR, cfg["output"])

    def WATER_REQ():
        return ('(way["natural"="water"](%f,%f,%f,%f);way["waterway"="river"](%f,%f,%f,%f););out geom;'
                % (s, w, n, e, s, w, n, e))

    os.makedirs(OUT_DIR, exist_ok=True)
    origin_world = proj(w, n)  # bbox 左上角

    print("== 城市: %s · bbox=%s · 输出=%s ==" % (city, cfg["bbox"], cfg["output"]))

    print("== 抓取道路（分块，避免超大城市单次超载）==")
    road_ways = load_cache("%s_roads" % city)
    if road_ways is not None:
        print("  道路: 使用本地缓存，%d 条" % len(road_ways))
    else:
        road_ways = tiled_elements('way["highway"]', s, w, n, e, BTILE_X, BTILE_Y, "路",
                                  "road_" + city, CACHE_DIR)
        save_cache("%s_roads" % city, road_ways)
    road_feats = {"elements": road_ways}
    print("  道路 way 数:", len(road_feats["elements"]))

    print("== 抓取水域 ==")
    water_feats = load_cache("%s_water" % city)
    if water_feats is not None:
        print("  水域: 使用本地缓存")
    else:
        try:
            water_feats = fetch(WATER_REQ())
            save_cache("%s_water" % city, water_feats)
        except RuntimeError as ex:
            print("水域抓取失败，跳过: %s" % ex, flush=True)
            water_feats = {"elements": []}

    print("== 抓取区界 ==")
    district_feats = load_cache("%s_districts" % city)
    if district_feats is not None:
        print("  区界: 使用本地缓存")
    else:
        try:
            district_feats = fetch(DISTRICTS_REQ + "(%f,%f,%f,%f);out geom;" % (s, w, n, e))
            save_cache("%s_districts" % city, district_feats)
        except RuntimeError as ex:
            print("区界抓取失败，跳过: %s" % ex, flush=True)
            district_feats = {"elements": []}

    print("== 建筑缓存检测 ==")
    bld_elems = load_cache("%s_buildings" % city)
    if bld_elems is not None:
        print("  建筑: 使用本地缓存，%d 条" % len(bld_elems))

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

    # ---- 写盘（基础图层立即落盘，建筑随抓取进度补充）----
    def write_map():
        cell = 512
        grid = {}
        m2_per_wu2 = (4.22) ** 2  # 世界单位² → 平方米²
        kept = 0
        dropped = 0
        for f in (bld_elems or []):
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
            "city": city,
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
        print("\n== 写盘（建筑 %d）==  %.2f MB" % (kept, size_mb), flush=True)
        print(json.dumps(meta["counts"], ensure_ascii=False, indent=2), flush=True)
        if not seen:
            print("!! 警告：未命中任何行政区！", flush=True)
        return kept

    write_map()  # 基础图层：道路+水域+区界（建筑可能为空），立即可用

    # ---- 建筑（长耗时）：缺失才抓，完成后重写 ----
    if bld_elems is None:
        bld_elems = tiled_elements('way["building"]', s, w, n, e, BGX, BGY, "建",
                                   "bld_" + city, CACHE_DIR)
        save_cache("%s_buildings" % city, bld_elems)
        write_map()  # 含建筑完整图层


if __name__ == "__main__":
    import traceback
    try:
        main()
    except BaseException as ex:
        traceback.print_exc()
        with open(os.path.join(BASE, "build_cache", "crash_log.txt"), "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise