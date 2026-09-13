# -*- coding: utf-8 -*-
"""换乘路线引擎：步行–公交–地铁混合的最省时路线规划。

建模方式（对齐高德/腾讯公交规划）：
  - 把每条线路的站点序列展开为“站点实例节点”（同一物理站出现多次 = 换乘节点）。
  - 线路内相邻站点连“乘车边”，权 = 大圆距离 / 车型速度（分钟）。
  - 跨线路同名站连“换乘边”，权 = 换乘惩罚（扼制过多换乘）。
  - 一定半径内不同名站连“步行换乘边”，权 = 距离 / 步行速度（模拟站台间短走）。
  - 起点/终点到附近站点连“步行接驳边”，权 = 距离 / 步行速度。
  - Dijkstra 求总耗时最短路径；纯步行作为兜底候选由同图自然表达。

数据源：static/map/transit.json（由 scripts/build_transit.py 生成）。
全部离线、纯标准库。
"""
import heapq
import json
import math
import os

import config


def _hav(lat1, lon1, lat2, lon2):
    """大圆距离（米）。"""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _norm(name):
    """站点名规范化，用于跨线同名匹配。"""
    return str(name or "").replace("站", "").strip().lower()


class TransitRouter:
    def __init__(self, path=None):
        self._path = path or os.path.join(config.STATIC_DIR, "map", "transit.json")
        self._data = None
        self._nodes = {}       # stop_id -> {lat, lon, name, kind}
        self._adj = {}         # stop_id -> [ (other, weight_min, edge) ]
        self._built = False

    # ---- 装载 ----
    def _load(self):
        if self._data is not None:
            return self._data
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (OSError, ValueError):
            self._data = None
        return self._data

    def available(self):
        d = self._load()
        return bool(d and (d.get("subway", {}).get("stops") or d.get("bus", {}).get("stops")))

    def stats(self):
        d = self._load()
        if not d:
            return {"subway_lines": 0, "subway_stops": 0, "bus_lines": 0, "bus_stops": 0}
        m = d.get("meta", {}).get("counts", {})
        return {"subway_lines": m.get("subway_lines", 0), "subway_stops": m.get("subway_stops", 0),
                "bus_lines": m.get("bus_lines", 0), "bus_stops": m.get("bus_stops", 0)}

    def _param(self):
        d = self._load()
        return (d or {}).get("param") or {}

    # ---- 建图（一次性）----
    def _ensure_graph(self):
        if self._built:
            return
        d = self._load()
        self._built = True
        if not d:
            return
        p = self._param()

        # 收集站点实例及所属 kind
        for bucket, kind in (("subway", "subway"), ("bus", "bus")):
            for L in (d.get(bucket, {}) or {}).get("lines", []) or []:
                for s in L.get("stops", []) or []:
                    sid = s.get("stop_id")
                    self._nodes[sid] = {
                        "lat": s["lat"], "lon": s["lon"],
                        "name": s.get("name", ""), "kind": kind,
                    }

        # 1) 线路内乘车边（相邻站点，双向）
        for bucket, kind in (("subway", "subway"), ("bus", "bus")):
            speed = p.get("subway_speed" if kind == "subway" else "bus_speed", 200.0)
            for L in (d.get(bucket, {}) or {}).get("lines", []) or []:
                line_id = L.get("id")
                name = L.get("name", "")
                color = L.get("color", "")
                sts = L.get("stops", []) or []
                for a, b in zip(sts, sts[1:]):
                    if a.get("stop_id") not in self._nodes or b.get("stop_id") not in self._nodes:
                        continue
                    dist = _hav(a["lat"], a["lon"], b["lat"], b["lon"])
                    w = max(0.5, dist / speed)
                    edge = {"mode": kind, "line": line_id, "name": name, "color": color}
                    self._add_edge(a["stop_id"], b["stop_id"], w, edge)

        # 2) 同名跨线换乘边（惩罚）
        pen = p.get("transfer_penalty", {})
        by_name = {}
        for sid, nd in self._nodes.items():
            by_name.setdefault(_norm(nd["name"]), []).append(sid)
        for sids in by_name.values():
            sids = list(set(sids))
            for i in range(len(sids)):
                for j in range(i + 1, len(sids)):
                    a, b = sids[i], sids[j]
                    ka, kb = self._nodes[a]["kind"], self._nodes[b]["kind"]
                    if ka == kb == "subway":
                        w = pen.get("subway", 3.0)
                    elif ka == kb == "bus":
                        w = pen.get("bus", 5.0)
                    else:
                        w = pen.get("mix", 6.0)
                    self._add_edge(a, b, w, {"mode": "xfer", "line": None, "name": None, "color": None})

        # 3) 步行换乘边（xfer_radius 内最近邻，模拟站台间短走）
        radius = p.get("xfer_radius", 200.0)
        walk_speed = p.get("walk_speed", 72.0)
        for sid, nd in self._nodes.items():
            best = []
            for oid, on in self._nodes.items():
                if oid == sid:
                    continue
                dist = _hav(nd["lat"], nd["lon"], on["lat"], on["lon"])
                if dist <= radius and math.fabs(nd["lat"] - on["lat"]) < radius * 2 and math.fabs(nd["lon"] - on["lon"]) < radius * 2:
                    best.append((dist, oid))
            best.sort(key=lambda t: t[0])
            for dist, oid in best[:2]:
                w = dist / walk_speed
                self._add_edge(sid, oid, w, {"mode": "walk", "line": None, "name": None, "color": None})

    def _add_edge(self, a, b, w, edge):
        self._adj.setdefault(a, []).append((b, w, edge))
        self._adj.setdefault(b, []).append((a, w, edge))

    # ---- 路径规划 ----
    def plan(self, from_pt, to_pt):
        """from_pt/to_pt = (lat, lon)。返回耗时最短的 leg 序列。"""
        self._ensure_graph()
        d = self._load()
        if not d or not self._nodes:
            return self._walk_only(from_pt, to_pt)
        p = self._param()
        walk_speed = p.get("walk_speed", 72.0)
        max_walk = p.get("max_walk_to_stop", 1200.0)

        S, T = ("FROM", "TO")
        # 起点/终点 → 附近站点 步行接驳边
        adj = dict(self._adj)
        adj.setdefault(S, [])
        for sid, nd in self._nodes.items():
            distS = _hav(from_pt[0], from_pt[1], nd["lat"], nd["lon"])
            if distS <= max_walk:
                adj[S].append((sid, distS / walk_speed, {"mode": "walk", "line": None, "name": None, "color": None}))
            distT = _hav(to_pt[0], to_pt[1], nd["lat"], nd["lon"])
            if distT <= max_walk:
                adj.setdefault(sid, []).append((T, distT / walk_speed, {"mode": "walk", "line": None, "name": None, "color": None}))
        # 纯步行兜底
        d0 = _hav(from_pt[0], from_pt[1], to_pt[0], to_pt[1])
        adj[S].append((T, d0 / walk_speed, {"mode": "walk", "line": None, "name": None, "color": None}))

        # Dijkstra
        dist = {S: 0.0}
        prev = {}
        pq = [(0.0, S)]
        adj.setdefault(T, [])
        while pq:
            cur_d, node = heapq.heappop(pq)
            if node == T:
                break
            if cur_d > dist.get(node, math.inf):
                continue
            for nb, w, edge in adj.get(node, []):
                ndd = cur_d + w
                if ndd < dist.get(nb, math.inf):
                    dist[nb] = ndd
                    prev[nb] = (node, edge)
                    heapq.heappush(pq, (ndd, nb))

        if T not in prev:
            return {"ok": False, "error": "无可达路线", "total_min": None, "legs": [], "coords": [list(from_pt), list(to_pt)], "transfers": 0}

        # 重构节点路径 S..T
        path = [T]
        while path[-1] != S:
            path.append(prev[path[-1]][0])
        path.reverse()

        # 各点坐标 + 各跳到达边
        def ncoord(node):
            if node == S:
                return list(from_pt)
            if node == T:
                return list(to_pt)
            nd = self._nodes[node]
            return [nd["lat"], nd["lon"]]

        moves = [prev[path[i + 1]][1] for i in range(len(path) - 1)]
        coords = [ncoord(n) for n in path]

        # 拼装 legs
        legs = []
        transfer_count = 0
        i = 0
        while i < len(moves):
            edge = moves[i]
            mode = edge.get("mode", "walk")
            if mode == "xfer":
                transfer_count += 1
                i += 1
                continue
            j = i
            if mode == "walk":
                while j + 1 < len(moves) and moves[j + 1].get("mode", "") == "walk":
                    j += 1
            else:  # ride
                while j + 1 < len(moves):
                    e = moves[j + 1]
                    if e.get("mode") == mode and e.get("line") == edge.get("line"):
                        j += 1
                    else:
                        break
            stops = [ncoord(path[k]) for k in range(i, j + 2)]  # 经 i..j 跳 → 覆盖 i..j+1 节点
            mode_label = mode if mode in ("walk", "subway", "bus") else "walk"
            legs.append({
                "mode": mode_label,
                "line": edge.get("name"),
                "color": edge.get("color"),
                "name": edge.get("name"),
                "time_min": 0.0,
                "stops": stops,
            })
            i = j + 1

        # 补算每一段时间
        for L in legs:
            if L["mode"] == "subway":
                sp = self._param().get("subway_speed", 600.0)
            elif L["mode"] == "bus":
                sp = self._param().get("bus_speed", 200.0)
            else:
                sp = self._param().get("walk_speed", 72.0)
            ms = sum(_hav(a[0], a[1], b[0], b[1]) for a, b in zip(L["stops"], L["stops"][1:]))
            L["time_min"] = round(max(0.5, ms / sp), 1)

        total_min = sum(L["time_min"] for L in legs)
        return {"ok": True, "total_min": round(total_min, 1), "transfers": transfer_count,
                "legs": legs, "coords": coords}

    def _walk_only(self, from_pt, to_pt):
        walk_speed = self._param().get("walk_speed", 72.0)
        d = _hav(from_pt[0], from_pt[1], to_pt[0], to_pt[1])
        return {"ok": True, "total_min": round(d / walk_speed, 1), "transfers": 0,
                "legs": [{"mode": "walk", "line": None, "color": None, "name": None,
                          "time_min": round(d / walk_speed, 1), "stops": [list(from_pt), list(to_pt)]}],
                "coords": [list(from_pt), list(to_pt)]}


_router = TransitRouter()


def route_plan(from_pt, to_pt):
    """对外入口：from_pt/to_pt = (lat, lon)。"""
    return _router.plan(from_pt, to_pt)


def available():
    """公交/地铁数据是否就绪。"""
    return _router.available()


def stats():
    """公交/地铁数据概况。"""
    return _router.stats()