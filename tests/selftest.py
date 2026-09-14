# -*- coding: utf-8 -*-
"""接受性自检：验证数据完整性、推荐引擎、行程编排与全部 API 路由。
不启动真实 Socket，直接调用 api.route，安全快速。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config, data, recommend, api

fail = []
count = [0]
def check(name, cond, detail=""):
    count[0] += 1
    print(("  [PASS] " if cond else "  [FAIL] ") + name + ((" — " + str(detail)) if detail else ""))
    if not cond:
        fail.append(name)

print("== POI 数据完整性 ==")
pois = data.load_pois()
check("非空且 >=8 个点", len(pois) >= 8, len(pois))
ids = [p["id"] for p in pois]
check("id 唯一", len(set(ids)) == len(ids))
for p in pois:
    for k in ("id","name","district","type","desc","x","y","duration_min","scores"):
        check("字段齐全:%s.%s" % (p.get("id"),k), k in p and p[k] is not None, p.get("id"))
    ok = 0 <= p["x"] <= 1000 and 0 <= p["y"] <= 1000
    check("坐标在界内:%s" % p["id"], ok, (p["x"],p["y"]))
    bad = [a for a in config.PREFERENCE_AXES if p["scores"].get(a) is not None and not (0 <= p["scores"][a] <= 5)]
    check("分数值域:%s" % p["id"], not bad, bad)

print("== 推荐引擎 ==")
profile = {'nature':5,'culture':3,'food':3,'shopping':2,'nightlife':2,'family':4,'photo':3}
sc = recommend.recommend(profile)
check("打分排序降序", all(sc[i]["affinity"] >= sc[i+1]["affinity"] for i in range(len(sc)-1)))
check("nautre 偏好命中山水/江畔", max(sc,key=lambda r:r["affinity"])["poi"]["type"] in ("nature",), max(sc,key=lambda r:r["affinity"])["poi"]["name"])

print("== 行程编排 ==")
for k in config.ITINERARY_BUDGETS:
    it = recommend.build_itinerary(profile, k)
    tot = sum(i["poi"].get("duration_min",60) for i in it["items"])
    check("budget=%s 未超预算" % k, tot <= it["budget_minutes"], "%d<=%d 站数%d" % (tot, it["budget_minutes"], len(it["items"])))
it = recommend.build_itinerary(profile, "full")
check("全天行程有站", len(it["items"]) >= 1, len(it["items"]))
check("返回字段齐全", {"budget","budget_minutes","items","score"} <= set(it))

print("== API 路由 ==")
def call(m, p, body=None, q=None):
    c, d = api.route(m, p, body_raw=(body.encode() if body else None), query=q)
    return c, d

c,d = call("GET","/api/health"); check("GET /api/health", c==200 and d.get("status")=="up")
c,d = call("GET","/api/meta"); check("GET /api/meta 城市长沙", c==200 and d.get("city")=="长沙")
c,d = call("GET","/api/pois"); check("GET /api/pois 返回点", c==200 and len(d.get("pois",[]))>=1, len(d.get("pois",[])))
c,d = call("GET","/api/pois")
ap = d.get("pois",[{}])[0]
check("GET /api/pois 含真实经纬度", c==200 and isinstance(ap.get("lat"),(int,float)) and isinstance(ap.get("lon"),(int,float)), (ap.get("id"), ap.get("lat"), ap.get("lon")))
c,d = call("GET","/api/itinerary/full"); check("GET /api/itinerary/full", c==200 and d["ok"] and len(d["items"])>=1)
c,d = call("GET","/api/profile"); check("GET /api/profile 默认档案", c==200 and d["ok"] and len(d["profile"])==7)
c,d = call("POST","/api/profile",body='{"profile":{"nature":5,"log":"x"}}'); check("POST /api/profile 过滤非法键", c==200 and "log" not in d["profile"])
# 持久性：写入后能读回（query 与 path 分离，遵从真实 HTTP urlparse 行为）
c,d = call("GET","/api/profile",q="user=test"); check("读回自定义用户", c==200 and d["ok"])
c,d = call("POST","/api/profile",body='{"profile":{"food":5}}',q="user=test"); check("写自定义用户", c==200 and d["profile"]["food"]==5)
c,d = call("GET","/api/profile",q="user=test"); check("自定义用户已持久化", c==200 and d["profile"]["food"]==5)
pid = pois[0]["id"]
c,d = call("POST","/api/favorite/"+pid, body="{}", q="user=test"); check("收藏写入", c==200 and d["action"]=="added")
c,d = call("POST","/api/favorite/"+pid, body="{}", q="user=test"); check("重复收藏返回removed", c==200 and d["action"]=="removed")
c,d = call("POST","/api/plan",body='{"title":"测试行程","budget":"full","items":[{"id":"x"},{"id":"y"}]}',q="user=test"); check("保存行程", c==200 and d["ok"] and d["plan"].get("id"))
c,d = call("GET","/api/profile",q="user=test"); check("行程已入档", c==200 and len(d["plans"])>=1)
c,d = call("POST","/api/plan", body="{bad json", q="user=test"); check("坏 JSON -> 400", c==400)
c,d = call("GET","/api/nope"); check("未知路由 -> 404", c==404)

print("== 换乘路线（公交/地铁）==")
c,d = call("GET","/api/transit"); check("GET /api/transit 可用", c==200 and d.get("available")==True, d.get("stats"))
import route
check("换乘数据：地铁可用", route.available() and route.stats().get("subway_lines",0)>=1, route.stats())
check("换乘数据：公交可用", route.stats().get("bus_lines",0)>=1, route.stats())
if route.available() and pois:
    p0 = pois[0]
    c1,d1 = call("POST","/api/route-plan",
        body='{"from":{"lat":%.6f,"lon":%.6f,"name":"起点"},"to":{"poi_id":"%s"}}' % (p0["lat"]-0.015, p0["lon"], p0["id"]))
    check("POST /api/route-plan 返回换乘", c1==200 and d1["ok"] and d1.get("legs"), d1.get("error"))
    if d1.get("ok"):
        check("route-plan legs 合法", all(l.get("mode") in ("walk","subway","bus") for l in d1["legs"]), [l["mode"] for l in d1["legs"]])
        check("route-plan 总耗时>0", isinstance(d1["total_min"],(int,float)) and d1["total_min"]>0, d1.get("total_min"))

print("== 认证 / 账号 ==")
import auth
import random as _r
phone = "+86" + "".join(_r.choice("0123456789") for _ in range(11))
c,d = call("POST","/api/sms",body=json.dumps({"phone":phone}))
check("POST /api/sms 发送验证码", c==200 and d["ok"] and d.get("dev_code"), d.get("dev_code"))
code = d.get("dev_code") or config.SMS_MOCK_CODE
c,d = call("POST","/api/auth/login",body=json.dumps({"phone":phone,"code":code}))
check("登录成功返回 token", c==200 and d["ok"] and d["session"]["token"], d.get("error"))
sess = d.get("session",{})
tok = sess.get("token","")
check("session 绑定手机号", c==200 and sess.get("phone")==phone)
c,d = call("GET","/api/auth/me",q="token="+tok)
check("token 可解析出登录用户", c==200 and d["ok"] and d["me"]["signed_in"] is True and d["me"]["phone"]==phone)
# token 鉴权：用 token 访问受保护资源，写入应落在该 user
c,d = call("POST","/api/profile",body='{"profile":{"nature":5}}',q="token="+tok)
check("token 鉴权写个人资料", c==200 and d["ok"] and d["profile"]["nature"]==5)
# 错误验证码
c,d = call("POST","/api/auth/login",body=json.dumps({"phone":phone,"code":"000000"}))
check("错误验证码拒绝", c==400 or (c==200 and not d.get("ok")))
# 无效验证码重试上限后失效
for _ in range(config.SMS_MAX_ATTEMPTS+1):
    c,d = call("POST","/api/auth/login",body=json.dumps({"phone":phone,"code":"000000"}))
check("超次数后拒绝", c==400 or (c==200 and not d.get("ok")))
# 退出登录
c,d = call("POST","/api/auth/logout",body=json.dumps({"token":tok}))
check("退出登录", c==200 and d["ok"])
c,d = call("GET","/api/auth/me",q="token="+tok)
check("退出后 token 失效", c==200 and d["ok"] and d["me"]["signed_in"] is False)
# 非法手机号
c,d = call("POST","/api/sms",body=json.dumps({"phone":"abc"}))
check("非法手机号拒绝", c==200 and not d["ok"])

print("\n== 结果 == 全部 %d 项检查，失败 %d ==" % (count[0], len(fail)))

import os
static = {os.path.join(config.STATIC_DIR, r): os.path.isfile(os.path.join(config.STATIC_DIR,r)) for r in
          ("index.html","css/style.css","js/store.js","js/map.js","js/render.js","js/app.js","map/changsha.json","map/transit.json")}
for p,ok in static.items():
    check("静态资源存在:"+os.path.basename(p), ok)
if any(not ok for ok in static.values()):
    fail.append("静态资源缺失")

print("== 地图数据 ==")
map_path = os.path.join(config.STATIC_DIR, "map", "changsha.json")
try:
    with open(map_path, "r", encoding="utf-8") as f:
        mdata = json.load(f)
except Exception as ex:
    mdata = None
    check("地图数据可解析", False, repr(ex))

if mdata:
    meta = mdata.get("meta", {})
    bbox = meta.get("bbox")
    check("meta.bbox 合法", isinstance(bbox, list) and len(bbox) == 4 and bbox[0] < bbox[2] and bbox[1] < bbox[3], bbox)
    check("meta.world 为正整数", isinstance(meta.get("world"), int) and meta["world"] > 0, meta.get("world"))
    origin = meta.get("origin")
    check("meta.origin 为长度2数组", isinstance(origin, list) and len(origin) == 2 and all(isinstance(v, (int, float)) for v in origin), origin)
    districts = mdata.get("districts", [])
    dnames = {d.get("name") for d in districts}
    check("主城区+近郊 区级齐全", dnames == {"岳麓区", "天心区", "芙蓉区", "开福区", "雨花区", "望城区", "长沙县"}, sorted(dnames))
    check("区界含质心", all(d.get("cx") is not None and d.get("cy") is not None for d in districts))
    roads = mdata.get("roads", {})
    for t in ("tier1", "tier2", "tier3", "tier4"):
        tl = roads.get(t, [])
        check("道路 %s 非空且含路径" % t, len(tl) > 0 and all(r.get("path","").startswith("M ") for r in tl), len(tl))
    grid = mdata.get("buildings", {}).get("grid", {})
    total_b = sum(len(v) for v in grid.values())
    check("建筑数量 > 0", total_b > 0, total_b)
    bad_pts = [b for cell in grid.values() for b in cell if len(b.get("pts", [])) % 2 != 0 or len(b.get("pts", [])) < 4]
    check("建筑 pts 为偶长", not bad_pts, len(bad_pts))
    bad_area = [b for cell in grid.values() for b in cell if not b.get("area", 0) > 0]
    check("建筑 area > 0", not bad_area, len(bad_area))
    # 投影 sanity：bbox 四角经 Web Mercator 复算落于 0..world
    import math
    W = meta.get("world")
    ok_corner = True
    for lon, lat in ((bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3])):
        x = (lon + 180.0) / 360.0 * W
        rad = math.radians(lat)
        y = (1 - math.log(math.tan(rad) + 1 / math.cos(rad)) / math.pi) / 2 * W
        if not (0 <= x <= W and 0 <= y <= W):
            ok_corner = False
    check("投影 sanity（四角落于世界）", ok_corner)
    check("建筑网格 cell 为整数", isinstance(meta.get("cell"), int) and meta["cell"] > 0, meta.get("cell"))

# POI lat/lon 校验
print("== POI 真实坐标 ==")
pois = data.load_pois()
bb = None
if mdata:
    bb = mdata.get("meta", {}).get("bbox")
for p in pois:
    lat, lon = p.get("lat"), p.get("lon")
    check("POI %s 有真实经纬度" % p.get("id"), isinstance(lat, (int, float)) and isinstance(lon, (int, float)), (lat, lon))
    if bb and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        inb = bb[0] <= lon <= bb[2] and bb[1] <= lat <= bb[3]
        check("POI %s 在 bbox 内" % p.get("id"), inb, (lat, lon))

print()
if fail:
    print("FAILED:", fail)
    sys.exit(1)
print("ALL GREEN — 验收通过")