# -*- coding: utf-8 -*-
"""数据层：POI 单一数据源 + 用户数据 JSON 持久化。

所有磁盘读写集中在本模块，且均带防御式异常与幂等创建，
避免“数据文件缺失/损坏”导致整个服务崩溃。
"""

import json
import os
import time
import uuid

import config

# ---- 通用读写工具 ----------------------------------------------------------

def _read_json(path, default):
    """安全读取 JSON；文件缺失/损坏时返回 default，绝不抛错致死。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return default


def _write_json(path, obj):
    """原子写入 JSON：先写临时文件再改名，避免写一半损坏主文件。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---- POI 单一数据源 --------------------------------------------------------

def load_pois():
    """返回 POI 列表；源缺失则回退为空列表（前端会给出友好空态）。"""
    data = _read_json(config.POI_FILE, {"pois": []})
    return data.get("pois", [])


def _item(pois, poi_id):
    for p in pois:
        if str(p.get("id")) == str(poi_id):
            return p
    return None


def get_poi(poi_id):
    return _item(load_pois(), poi_id)


# ---- 用户数据持久化 --------------------------------------------------------

def _user_path(user_id):
    u = str(user_id or "guest").strip().lower() or "guest"
    # 只允许安全字符，防止路径穿越
    safe = "".join(ch for ch in u if ch.isalnum() or ch in "_-")
    safe = safe or "guest"
    return os.path.join(config.USERS_DIR, safe + ".json")


def ensure_user(user_id="guest"):
    """取用户数据；不存在则初始化默认档案并落盘。返回 dict。"""
    path = _user_path(user_id)
    user = _read_json(path, None)
    if user is None:
        user = {
            "id": os.path.basename(path)[:-5],
            "created": int(time.time()),
            "profile": dict(config.DEFAULT_PROFILE),
            "favorites": [],
            "plans": [],
        }
        _write_json(path, user)
    # 兼容旧档案：补齐新字段
    changed = False
    for key, default in (("nickname", ""), ("signature", ""), ("avatar", ""),
                         ("mbti", None), ("checkins", []), ("routes", [])):
        if key not in user:
            user[key] = default
            changed = True
    if changed:
        save_user(user_id, user)
    return user


def save_user(user_id, user):
    _write_json(_user_path(user_id), user)


def update_profile(user_id, profile):
    user = ensure_user(user_id)
    merged = dict(config.DEFAULT_PROFILE)
    merged.update({k: int(v) for k, v in (profile or {}).items() if k in config.PREFERENCE_AXES})
    user["profile"] = merged
    save_user(user_id, user)
    return user


def toggle_favorite(user_id, poi_id):
    user = ensure_user(user_id)
    favs = user.get("favorites", [])
    if poi_id in favs:
        favs.remove(poi_id)
        action = "removed"
    else:
        favs.append(poi_id)
        action = "added"
    user["favorites"] = favs
    save_user(user_id, user)
    return user, action


def add_plan(user_id, plan):
    """保存一段行程到用户数据。plan 为 dict，补充 id 与时间戳。"""
    user = ensure_user(user_id)
    plan = dict(plan)
    plan["id"] = uuid.uuid4().hex[:10]
    plan["saved_at"] = int(time.time())
    user.setdefault("plans", []).append(plan)
    save_user(user_id, user)
    return plan


# ---- 个人资料 / 打卡 / 路线 / MBTI ----

def update_me(user_id, patch):
    """更新个人资料：nickname/signature/mbti（白名单键）。"""
    user = ensure_user(user_id)
    for key in ("nickname", "signature", "mbti"):
        if key in patch and patch[key] is not None:
            user[key] = str(patch[key]).strip()[:80]
    if "avatar" in patch and patch["avatar"] is not None:
        user["avatar"] = str(patch["avatar"])
    save_user(user_id, user)
    return user


def add_checkin(user_id, checkin):
    """新增打卡记录：{poi_id?, img, caption, lat, lon}，补充 id 与时间戳。"""
    user = ensure_user(user_id)
    c = {
        "id": uuid.uuid4().hex[:10],
        "created": int(time.time()),
        "poi_id": checkin.get("poi_id") or "",
        "img": checkin.get("img", ""),
        "caption": str(checkin.get("caption", "")).strip()[:200],
        "lat": checkin.get("lat"),
        "lon": checkin.get("lon"),
    }
    user.setdefault("checkins", []).append(c)
    save_user(user_id, user)
    return c


def delete_checkin(user_id, checkin_id):
    user = ensure_user(user_id)
    before = len(user.get("checkins", []))
    user["checkins"] = [c for c in user.get("checkins", []) if c["id"] != checkin_id]
    if len(user["checkins"]) == before:
        return False
    save_user(user_id, user)
    return True


def add_route(user_id, route):
    """保存一条 GPS 路线：{title, start, end, points:[[lat,lon]...]}。"""
    user = ensure_user(user_id)
    points = [p for p in route.get("points", []) if isinstance(p, list) and len(p) >= 2]
    r = {
        "id": uuid.uuid4().hex[:10],
        "created": int(time.time()),
        "title": str(route.get("title", "我的足迹")).strip()[:60] or "我的足迹",
        "start": int(route.get("start") or time.time()),
        "end": int(route.get("end") or time.time()),
        "points": points,
    }
    r["duration_min"] = max(1, (r["end"] - r["start"]) // 60)
    r["distance_m"] = _route_distance(points)
    user.setdefault("routes", []).append(r)
    save_user(user_id, user)
    return r


def delete_route(user_id, route_id):
    user = ensure_user(user_id)
    before = len(user.get("routes", []))
    user["routes"] = [r for r in user.get("routes", []) if r["id"] != route_id]
    if len(user["routes"]) == before:
        return False
    save_user(user_id, user)
    return True


def _route_distance(points):
    """球面距离近似（米）。"""
    import math
    if len(points) < 2:
        return 0
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * \
            math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        total += 2 * 6371000 * math.asin(min(1, math.sqrt(a)))
    return int(total)