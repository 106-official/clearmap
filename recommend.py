# -*- coding: utf-8 -*-
"""推荐引擎：对每个 POI 按用户偏好加权打分，并用贪心算法编排行程。

方法说明（透明、可复现）：
  1. 匹配度 affinity = 该 POI 各偏好维度得分 × 用户对应偏好权重 的加权和，
     除以该 POI 得分总和做归一化，得到 0-5 的可比分数。
  2. 行程编排：先按 affinity 降序加入候选，累计“停留时长 + 点间通勤”不超预算；
     再用“最近邻贪心”从城市重心出发把入选点排成顺路路线。
"""

import math

import data
import config


# MBTI 单字母 → 风格加分（同风格可叠加，体现“维度的叠加画像”）
LETTER_BONUS = {
    "E": {"潮玩都市": 2, "美食烟火": 1, "夜景打卡": 1},
    "I": {"古韵文化": 2, "自然山水": 1},
    "N": {"潮玩都市": 1, "古韵文化": 1},
    "S": {"美食烟火": 2, "潮玩都市": 1},
    "T": {"古韵文化": 1, "自然山水": 1},
    "F": {"亲子休闲": 2, "美食烟火": 1, "夜景打卡": 1},
    "J": {"古韵文化": 1, "潮玩都市": 1},
    "P": {"自然山水": 1, "美食烟火": 1, "夜景打卡": 1},
}


def mbti_affinity(poi, mbti):
    """MBTI 风格契合度（0-5）：对 POI 每个 style 按四字母累计加分，取最高并钳制。"""
    styles = poi.get("style") or []
    mbti = (mbti or "").strip().upper()
    if not styles or len(mbti) != 4 or any(ch not in "EISNTFJP" for ch in mbti):
        return 0.0
    best = 0.0
    for s in styles:
        v = 1.0
        for letter in mbti:
            v += LETTER_BONUS.get(letter, {}).get(s, 0)
        if v > best:
            best = v
    return round(min(5.0, best), 2)


def _dist(a, b):
    """地图格坐标（0-1000 抽象空间）折线距离。"""
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def score_poi(poi, profile):
    """单人、单点匹配度（0-5 分制）。

    约定：对该点“有标注”的每个偏好轴，取 得分×用户权重(0-1)，
    再对所有有标注的轴求平均。结果天然落在 0-5，直观可比。
    """
    scores = poi.get("scores", {})
    terms = []
    for axis in config.PREFERENCE_AXES:
        s = scores.get(axis)
        if s:
            terms.append(s * (profile.get(axis, 0) / 5.0))
    if not terms:
        return 0.0
    return round(sum(terms) / len(terms), 2)


def recommend(profile, limit=None, city="changsha"):
    """按匹配度从高到低返回所有 poi + 便携字段。"""
    pois = data.load_pois(city)
    sc = []
    for p in pois:
        sc.append({"poi": p, "affinity": score_poi(p, profile)})
    sc.sort(key=lambda r: r["affinity"], reverse=True)
    if limit:
        sc = sc[:limit]
    return sc


def build_itinerary(profile, budget_key="full", limit=8, city="changsha"):
    """
    返回 dict：
      {
        "budget": "full",
        "budget_minutes": 480,
        "items": [ {poi..., affinity}, ... ] 按游览顺序,
        "score": 行程总匹配度,
      }
    """
    budget_minutes = config.ITINERARY_BUDGETS.get(budget_key, 8) * 60
    pois = data.load_pois(city)
    if not pois:
        return {"budget": budget_key, "budget_minutes": budget_minutes, "items": [], "score": 0.0}

    # 1) 打分排序
    ranked = sorted(pois, key=lambda p: score_poi(p, profile), reverse=True)

    # 2) 贪心装入：时长 + 通勤不超预算
    chosen = []
    total_min = 0
    cursor = None  # 城市重心
    for p in ranked:
        if len(chosen) >= limit:
            break
        duration = int(p.get("duration_min", 60))
        travel = 0.0
        if cursor is not None and chosen:
            travel = (_dist(cursor, p) / config.TRAVEL_SPEED) * 60  # 分钟折算
        est = total_min + duration + travel
        if chosen and est > budget_minutes:
            continue  # 装不下了，跳过（后续更远，也基本放不下）
        chosen.append(p)
        total_min = est
        cursor = p

    # 3) 最近邻重排：从重心出发找最短接入点链（贪心）
    if chosen:
        center = _centroid(chosen)
        ordered = []
        pool = list(chosen)
        cur = center
        while pool:
            pool.sort(key=lambda p: _dist(cur, p))
            nxt = pool.pop(0)
            ordered.append(nxt)
            cur = nxt
        chosen = ordered

    items = [{"poi": p, "affinity": score_poi(p, profile)} for p in chosen]
    total_score = sum(it["affinity"] for it in items) / max(len(items), 1)
    return {
        "budget": budget_key,
        "budget_minutes": budget_minutes,
        "items": items,
        "score": round(total_score, 2),
    }


def _centroid(pois):
    return {"x": sum(p["x"] for p in pois) / len(pois),
            "y": sum(p["y"] for p in pois) / len(pois)}