# -*- coding: utf-8 -*-
"""REST 业务处理：json 入参 -> dict 出参，不关心 HTTP 细节。

统一返回 {"ok": True/False, ...} 结构。异常一律转成 ok=False，
由上层交给 JSON 响应，保证接口永不 500。
"""

import base64
import json
import mimetypes
import os
import urllib.parse

import data
import recommend
import route as route_mod   # 别名为 route_mod：避免与下方 handler 函数 route() 重名遮蔽
import config
import auth


class ApiError(Exception):
    def __init__(self, message):
        self.message = message


# ---- 入参工具 --------------------------------------------------------------

def _json_body(raw, size=1 << 20):
    if not raw:
        return {}
    try:
        if len(raw) > size:
            raise ApiError("请求体过大")
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise ApiError("JSON 解析失败: %s" % e)


def _path_id(segments, idx):
    if idx >= len(segments):
        raise ApiError("缺少资源 ID")
    return segments[idx]


# ---- 各接口 ----------------------------------------------------------------

def pois(user_id="guest", city="changsha"):
    user = data.ensure_user(user_id)
    profile = user.get("profile", {})
    mbti = user.get("mbti")
    sc = recommend.recommend(profile, city=city)
    out = []
    for r in sc:
        p = r["poi"]
        out.append({
            "id": p["id"], "name": p["name"], "district": p.get("district", ""),
            "type": p.get("type", ""), "tags": p.get("tags", []),
            "duration_min": p.get("duration_min", 60), "desc": p.get("desc", ""),
            "x": p["x"], "y": p["y"], "lat": p.get("lat"), "lon": p.get("lon"),
            "affinity": r["affinity"],
            "mbti_affinity": recommend.mbti_affinity(p, mbti) if mbti else None,
            "style": p.get("style", []),
            "hours": p.get("hours", {}),
            "ticket": p.get("ticket", ""),
            "images": p.get("images", []),
        })
    return {"ok": True, "pois": out}


def get_profile(user_id):
    user = data.ensure_user(user_id)
    return {"ok": True, "profile": user["profile"],
            "favorites": user.get("favorites", []),
            "plans": user.get("plans", [])}


def favorite(user_id, poi_id):
    _, action = data.toggle_favorite(user_id, poi_id)
    user = data.ensure_user(user_id)
    return {"ok": True, "action": action, "favorites": user["favorites"]}


# ---- 个人中心 ----

def get_me(user_id):
    user = data.ensure_user(user_id)
    return {"ok": True, "me": {
        "id": user["id"],
        "nickname": user.get("nickname", ""),
        "signature": user.get("signature", ""),
        "avatar": user.get("avatar", ""),
        "mbti": user.get("mbti"),
        "mbti_name": (config.MBTI_TYPES.get(user.get("mbti")) or ("", ""))[0],
        "created": user.get("created"),
    }, "profile": user["profile"], "favorites": user.get("favorites", []),
        "plans": user.get("plans", []),
        "checkins": _decorate_checkins(user.get("checkins", []), user_id),
        "routes": user.get("routes", []),
        "essays": data.my_essays(user_id)}


def _decorate_checkins(checkins, user_id="guest"):
    pois = {p["id"]: p["name"] for p in data.load_pois()}
    out = []
    for c in checkins:
        c = dict(c)
        c["poi_name"] = pois.get(c.get("poi_id"), "")
        if c.get("img"):
            c["img"] = "/api/media?user=" + urllib.parse.quote(user_id) + "&file=" + urllib.parse.quote(c["img"])
        out.append(c)
    return out


def update_me(user_id, body):
    mbti = body.get("mbti")
    if mbti is not None:
        mbti = str(mbti).strip().upper()
        if mbti and (len(mbti) != 4 or any(ch not in "EISNTFJP" for ch in mbti)):
            raise ApiError("MBTI 需为四位字母，如 INFJ")
        if mbti not in config.MBTI_TYPES:
            raise ApiError("无效的 MBTI 类型: %s" % mbti)
        body["mbti"] = mbti or None
    user = data.update_me(user_id, body)
    return {"ok": True, "me": {
        "id": user["id"], "nickname": user.get("nickname", ""),
        "signature": user.get("signature", ""), "avatar": user.get("avatar", ""),
        "mbti": user.get("mbti"),
        "mbti_name": (config.MBTI_TYPES.get(user.get("mbti")) or ("", ""))[0]}}


def upload_avatar(user_id, body):
    fn = _save_image(user_id, body.get("data"), "avatar")
    url = "/api/media?user=" + urllib.parse.quote(user_id) + "&file=" + urllib.parse.quote(fn)
    user = data.update_me(user_id, {"avatar": url})
    return {"ok": True, "avatar": url, "me": {"avatar": url, "nickname": user.get("nickname", ""),
                                              "mbti": user.get("mbti")}}


def add_checkin(user_id, body):
    img = _save_image(user_id, body.get("img"), "checkin") if body.get("img") else ""
    lat, lon = body.get("lat"), body.get("lon")
    if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
        raise ApiError("打卡需要有效坐标")
    poi_id = body.get("poi_id") or ""
    if poi_id and not data.get_poi(poi_id):
        raise ApiError("关联的景点不存在")
    c = data.add_checkin(user_id, {
        "poi_id": poi_id, "img": img,
        "caption": body.get("caption", ""), "lat": lat, "lon": lon,
    })
    return {"ok": True, "checkin": c}


def delete_checkin(user_id, checkin_id):
    if not data.delete_checkin(user_id, checkin_id):
        raise ApiError("打卡记录不存在")
    return {"ok": True, "id": checkin_id}


def add_route(user_id, body):
    points = body.get("points", [])
    if not isinstance(points, list) or len(points) < 2:
        raise ApiError("路线至少需要两个采样点")
    r = data.add_route(user_id, {
        "title": body.get("title", ""),
        "start": body.get("start"), "end": body.get("end"),
        "points": points,
    })
    return {"ok": True, "route": r}


def delete_route(user_id, route_id):
    if not data.delete_route(user_id, route_id):
        raise ApiError("路线不存在")
    return {"ok": True, "id": route_id}


# ---- 旅游随笔 / 发现（preview-1.22）----------------------------------------

_ESSAY_IMAGES_MAX = 6


def publish_essay(user_id, body):
    if user_id == "guest":
        raise ApiError("请先登录后再发布随笔")
    text = str(body.get("text", "")).strip()
    if not text:
        raise ApiError("随笔内容不能为空")
    imgs = body.get("imgs") or []
    if not isinstance(imgs, list):
        raise ApiError("图片参数非法")
    if len(imgs) > _ESSAY_IMAGES_MAX:
        raise ApiError("最多上传 %d 张图片" % _ESSAY_IMAGES_MAX)
    files = [_save_image(user_id, d, "essay") for d in imgs]
    e = data.add_essay(user_id, {
        "text": text, "imgs": files,
        "lat": body.get("lat"), "lon": body.get("lon"),
    })
    return {"ok": True, "essay": e}


def remove_essay(user_id, essay_id):
    if not data.delete_essay(user_id, essay_id):
        raise ApiError("随笔不存在")
    return {"ok": True, "id": essay_id}


def discover_feed(user_id, limit=30):
    return {"ok": True, "essays": data.feed_essays(limit)}


def mbti_recommendations(user_id, limit=6, city="changsha"):
    user = data.ensure_user(user_id)
    mbti = user.get("mbti")
    if not mbti:
        return {"ok": True, "mbti": None, "recommended": [], "name": ""}
    sc = [{"poi": p, "affinity": recommend.score_poi(p, user["profile"]),
           "mbti_affinity": recommend.mbti_affinity(p, mbti)}
          for p in data.load_pois(city)]
    sc.sort(key=lambda r: r["mbti_affinity"], reverse=True)
    sc = sc[:limit]
    return {"ok": True, "mbti": mbti,
            "name": (config.MBTI_TYPES.get(mbti) or ("", ""))[0],
            "recommended": [{
                "poi": {k: r["poi"][k] for k in ("id", "name", "district", "type", "x", "y",
                                                 "style", "hours", "ticket", "images", "desc")},
                "affinity": r["affinity"], "mbti_affinity": r["mbti_affinity"],
            } for r in sc]}


# ---- 换乘路线 / 公交 ----

def _pt(body, key):
    """从 body[key] 解析一个 {lat, lon} 点。"""
    v = body.get(key)
    if not isinstance(v, dict):
        raise ApiError("%s 需要 lat/lon" % key)
    lat, lon = v.get("lat"), v.get("lon")
    if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
        raise ApiError("%s 坐标非法" % key)
    return lat, lon, v.get("name", "")


def route_plan(user_id, body):
    """换乘路线规划：from={lat,lon,name?}, to={poi_id} 或 {lat,lon}。"""
    fl, fo, fname = _pt(body, "from")
    to = body.get("to") or {}
    if "poi_id" in to:
        poi = data.get_poi(to["poi_id"])
        if not poi:
            raise ApiError("目标景点不存在")
        tl, tn = poi["lat"], poi["lon"]
        tname = poi["name"]
    else:
        tl, tn, tname = _pt(body, "to")
    if not route_mod.available():
        raise ApiError("公交/地铁数据未就绪")
    result = route_mod.route_plan((fl, fo), (tl, tn))
    if not result.get("ok"):
        raise ApiError(result.get("error", "规划失败"))
    return {"ok": True, "start": {"lat": fl, "lon": fo, "name": fname},
            "end": {"lat": tl, "lon": tn, "name": tname},
            "total_min": result["total_min"], "transfers": result["transfers"],
            "legs": result["legs"], "coords": result["coords"]}


# ---- 认证 / 账号 ------------------------------------------------------------

def send_code(phone):
    ok, msg, mock = auth.send_code(phone)
    resp = {"ok": ok, "msg": msg}
    if mock:
        resp["dev_code"] = mock   # 仅调试模式出现，前端用于填充输入框
    return 200, resp


def auth_login(body):
    ok, msg, sess = auth.register_or_login(body.get("phone"), body.get("code"))
    if not ok:
        return 400, {"ok": False, "error": msg}
    return 200, {"ok": True, "msg": msg, "session": sess}


def auth_logout(body):
    auth.logout(body.get("token"))
    return 200, {"ok": True}


def auth_me(query):
    token = (urllib.parse.parse_qs(query or "").get("token", [""]) or [""])[0]
    info = auth.session_info(token)
    user_id = info["user_id"] if info else "guest"
    user = data.ensure_user(user_id)
    return 200, {"ok": True, "me": {
        "user_id": user["id"],
        "phone": (info or {}).get("phone", "") if user_id != "guest" else "",
        "nickname": user.get("nickname", ""),
        "avatar": user.get("avatar", ""),
        "is_new": user.get("created"),
        "signed_in": user_id != "guest",
    }}


# ---- 图片存取 ----

_MAX_IMAGE = 4 * 1024 * 1024  # 4MB
_EXT_BY_MIME = {"image/jpeg": ".jpg", "image/png": ".png",
                "image/gif": ".gif", "image/webp": ".webp"}


def _save_image(user_id, data_url, prefix):
    """解析 data URL 图片，落盘 uploads/<user>/<prefix>-<rand>.<ext>，返回文件名。"""
    if not data_url or not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise ApiError("仅支持图片上传")
    head, _, b64 = data_url.partition(",")
    mime = head[5:head.find(";")]
    ext = _EXT_BY_MIME.get(mime)
    if not ext:
        raise ApiError("不支持的图片格式")
    try:
        raw = base64.b64decode(b64)
    except (ValueError, TypeError):
        raise ApiError("图片数据损坏")
    if not raw or len(raw) > _MAX_IMAGE:
        raise ApiError("图片超过 4MB")
    folder = os.path.join(config.UPLOAD_DIR, _safe_user(user_id))
    os.makedirs(folder, exist_ok=True)
    fn = prefix + "-" + __import__("uuid").uuid4().hex[:12] + ext
    with open(os.path.join(folder, fn), "wb") as f:
        f.write(raw)
    return fn


def _safe_user(user_id):
    u = str(user_id or "guest").strip().lower() or "guest"
    return "".join(ch for ch in u if ch.isalnum() or ch in "_-") or "guest"


def media(user_id, filename):
    """返回 (status, payload, content_type)；content_type 为 None 时 payload 为 JSON 错误。"""
    name = os.path.basename(filename or "")
    if not name or name != filename or any(ch in name for ch in ("\\", "/", "..", ":")):
        return 404, {"ok": False, "error": "非法文件名"}, None
    path = os.path.realpath(os.path.join(config.UPLOAD_DIR, _safe_user(user_id), name))
    base = os.path.realpath(config.UPLOAD_DIR)
    if base != os.path.commonpath([base, path]) or not os.path.isfile(path):
        return 404, {"ok": False, "error": "文件不存在"}, None
    with open(path, "rb") as f:
        return 200, f.read(), mimetypes.guess_type(name)[0] or "application/octet-stream"


# ---- 路由表 ----------------------------------------------------------------

def route(method, path, body_raw=None, query=None):
    """返回 (status_code, dict)。所有异常转为 400/404。"""
    try:
        if method == "GET":
            if path == "/api/health":
                return 200, {"ok": True, "status": "up"}
            if path == "/api/pois":
                return 200, pois(query_id(query), _query_city(query))
            if path == "/api/profile":
                return 200, get_profile(query_id(query))
            if path == "/api/me":
                return 200, get_me(query_id(query))
            if path.startswith("/api/mbti-recs"):
                return 200, mbti_recommendations(query_id(query),
                                                 limit=_query_int(query, "limit") or 6,
                                                 city=_query_city(query))
            if path == "/api/feed":
                return 200, discover_feed(query_id(query), _query_int(query, "limit") or 30)
            if path == "/api/auth/me":
                return auth_me(query)

        elif method == "POST":
            body = _json_body(body_raw)
            if path == "/api/me":
                return 200, update_me(query_id(query), body)
            if path == "/api/avatar":
                return 200, upload_avatar(query_id(query), body)
            if path == "/api/checkin":
                return 200, add_checkin(query_id(query), body)
            if path == "/api/route":
                return 200, add_route(query_id(query), body)
            if path.startswith("/api/favorite/"):
                seg = path.split("/")[3:]
                return 200, favorite(query_id(query), _path_id(seg, 0))
            if path == "/api/route-plan":
                return 200, route_plan(query_id(query), body)
            if path == "/api/sms":
                return send_code(body.get("phone"))
            if path == "/api/essay":
                return 200, publish_essay(query_id(query), body)
            if path == "/api/auth/login":
                return auth_login(body)
            if path == "/api/auth/logout":
                return auth_logout(body)

        elif method == "DELETE":
            if path.startswith("/api/checkin/"):
                seg = path.split("/")[3:]
                return 200, delete_checkin(query_id(query), _path_id(seg, 0))
            if path.startswith("/api/route/"):
                seg = path.split("/")[3:]
                return 200, delete_route(query_id(query), _path_id(seg, 0))
            if path.startswith("/api/essay/"):
                seg = path.split("/")[3:]
                return 200, remove_essay(query_id(query), _path_id(seg, 0))

        return 404, {"ok": False, "error": "接口不存在"}

    except ApiError as e:
        return 400, {"ok": False, "error": e.message}
    except Exception as e:  # 兜底，绝不 500 裸奔
        return 500, {"ok": False, "error": "服务异常: %s" % e}


def query_id(query):
    q = urllib.parse.parse_qs(query or "")
    token = q.get("token", [""])[0]
    if token:
        uid = auth.resolve(token)
        if uid:
            return uid
    return (q.get("user", ["guest"])[0]) or "guest"


def _query_int(query, key):
    q = urllib.parse.parse_qs(query or "")
    try:
        return max(1, int(q[key][0]))
    except (KeyError, ValueError):
        return None


def _query_city(query):
    """从查询串读城市；缺省/非法回退 changsha。"""
    q = urllib.parse.parse_qs(query or "")
    c = (q.get("city", ["changsha"])[0] or "changsha").strip().lower()
    return c if c in config.POI_FILES else "changsha"