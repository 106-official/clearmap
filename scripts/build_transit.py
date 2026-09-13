# -*- coding: utf-8 -*-
"""构建长沙公共交通（地铁 / 公交）线路数据。

从 Overpass API 抓取 relation['route'=subway|light_rail|bus] 的线路与站点序列，
保留站点经纬度，离线落盘为 static/map/transit.json。
产物供运行时 route.py 离线构建“换乘图”。纯标准库。

用法：  python scripts/build_transit.py
"""
import json, os, time, urllib.request, urllib.error

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "static", "map")
OUT_FILE = os.path.join(OUT_DIR, "transit.json")

# 主城区 + 近郊范围（与 build_map.py 一致）
BBOX = (28.02, 112.78, 28.56, 113.40)

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# 视为“站点”的成员角色
STOP_ROLES = {"stop", "stop_position", "platform", "tram", "subway", "bus"}

# 判定一个节点是否是乘车点（有名字 + 停靠类标签）
STOP_TAG_KEYS = ("public_transport", "highway", "railway", "amenity", "bus")


def fetch(query, timeout=300, backoff=(5, 12, 30)):
    payload = ("[out:json][timeout:%d];%s" % (timeout, query)).encode("utf-8")
    last = None
    for attempt in range(len(backoff)):
        for ep in ENDPOINTS:
            try:
                req = urllib.request.Request(ep, data=payload,
                                             headers={"User-Agent": "ClearMap-transit/1.0 (offline local)"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.load(r)
            except (urllib.error.URLError, OSError, ValueError) as e:
                last = e
        print("  重试 %d/%d（等 %ds）：%s" % (attempt + 1, len(backoff), backoff[attempt], last), flush=True)
        time.sleep(backoff[attempt])
    raise RuntimeError("Overpass 请求失败: %s" % last)


def _route_query(route_re):
    return (
        'relation["route"~"^(%s)$"](%.5f,%.5f,%.5f,%.5f);'
        "(._;>;);out body;" % (route_re, BBOX[0], BBOX[1], BBOX[2], BBOX[3])
    )


def _is_stop(node):
    tags = node.get("tags") or {}
    if "name" not in tags:
        return False
    for k in STOP_TAG_KEYS:
        v = tags.get(k)
        if k == "highway" and (v in ("bus_stop", "platform")):
            return True
        if k == "railway" and v in ("station", "stop", "platform", "station_entrance", "halt"):
            return True
        if k == "public_transport" and v in ("stop_position", "platform", "stop_area"):
            return True
        if k == "amenity" and v == "bus_station":
            return True
        if k == "bus" and v in ("yes", "platform"):
            return True
    return False


def make_line(rel, elems):
    """从一条 route relation 提取 {id,name,color,kind,stops}。"""
    tags = rel.get("tags") or {}
    kind = tags.get("route", "")
    nodes = {e["id"]: e for e in elems if e.get("type") == "node"}
    stops = []
    for m in rel.get("members") or []:
        if m.get("type") != "node" or m.get("role") not in STOP_ROLES:
            continue
        nd = nodes.get(m.get("ref"))
        if not nd:
            continue
        if not _is_stop(nd):
            continue
        stop_id = "%d:%d" % (rel.get("id"), len(stops))
        stops.append({
            "stop_id": stop_id,
            "name": (nd.get("tags") or {}).get("name", "").strip(),
            "lat": nd.get("lat"),
            "lon": nd.get("lon"),
        })
    return {
        "id": str(rel.get("id")),
        "name": tags.get("name", "").strip(),
        "ref": tags.get("ref", "").strip(),
        "color": tags.get("colour") or tags.get("color") or tags.get("metro:colour") or "",
        "kind": kind,
        "stops": [s for s in stops if s["lon"] is not None and s["lat"] is not None and s["name"]],
    }


def parse_output(data, kind_ok):
    """data 为 Overpass response；返回合法线路列表。"""
    lines = []
    for el in data.get("elements", []):
        if el.get("type") != "relation":
            continue
        route = (el.get("tags") or {}).get("route", "")
        if route not in kind_ok:
            continue
        line = make_line(el, data.get("elements", []))
        if line["name"] and len(line["stops"]) >= 2:
            lines.append(line)
    # 去重：同名+同首末站合并（避免把往返方向拆成两条干扰图，但保留方向会利于选站，此处简单合并）
    seen = {}
    for L in lines:
        key = (L["kind"], L["name"], L["stops"][0]["stop_id"], L["stops"][-1]["stop_id"])
        if key not in seen:
            seen[key] = L
    return list(seen.values())


def all_stops(lines):
    seen, out = {}, []
    for L in lines:
        for s in L["stops"]:
            if s["stop_id"] not in seen:
                seen[s["stop_id"]] = True
                out.append(s)
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("== 抓取地铁 / 轻轨 ==")
    subway_raw = fetch(_route_query("subway|light_rail"))
    subway_lines = parse_output(subway_raw, {"subway", "light_rail"})
    print("  地铁线路:", len(subway_lines))

    print("== 抓取公交 ==")
    time.sleep(2)
    bus_raw = fetch(_route_query("bus"))
    bus_lines = parse_output(bus_raw, {"bus"})
    print("  公交线路:", len(bus_lines))

    subway_stops = all_stops(subway_lines)
    bus_stops = all_stops(bus_lines)

    meta = {
        "bbox": list(BBOX),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "counts": {
            "subway_lines": len(subway_lines), "subway_stops": len(subway_stops),
            "bus_lines": len(bus_lines), "bus_stops": len(bus_stops),
        },
    }
    param = {
        "walk_speed": 72.0,        # 米/分钟 ≈ 4.3 km/h
        "subway_speed": 600.0,     # 米/分钟 ≈ 36 km/h（含停站）
        "bus_speed": 200.0,        # 米/分钟 ≈ 12 km/h（含停站）
        "transfer_penalty": {"subway": 3.0, "bus": 5.0, "mix": 6.0},  # 分钟
        "max_walk_to_stop": 1200.0,  # 米：起点/终点步行接驳上限
        "xfer_radius": 200.0,        # 米：不同站台同换乘点的连边半径
    }
    payload = {
        "meta": meta,
        "subway": {"lines": subway_lines, "stops": subway_stops},
        "bus": {"lines": bus_lines, "stops": bus_stops},
        "param": param,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(OUT_FILE) / 1048576
    print("== 完成 ==")
    print(json.dumps(meta["counts"], ensure_ascii=False))
    print("输出:", OUT_FILE, "| %.2f MB" % size_mb)


if __name__ == "__main__":
    main()