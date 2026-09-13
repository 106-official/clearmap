# -*- coding: utf-8 -*-
"""ClearMap 全局配置：路径、偏好维度、行程参数。

只放常量与零逻辑函数，保持无副作用、可被任意模块安全导入。
"""

import os

# ---- 路径 ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
POI_FILE = os.path.join(DATA_DIR, "poi", "changsha.json")
USERS_DIR = os.path.join(DATA_DIR, "users")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")   # 用户上传的头像 / 打卡图片
STATIC_DIR = os.path.join(BASE_DIR, "static")

# 保证数据目录存在（幂等）
os.makedirs(USERS_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "poi"), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---- 服务 ----
HOST = "127.0.0.1"
PORT = 9100

# ---- 偏好维度（推荐引擎的权重轴）----
# 每个维度一段说明文字，前端滑块范围 0-5（0=不感兴趣, 5=非常感兴趣）。
PREFERENCE_AXES = {
    "nature":    "自然山水",
    "culture":   "历史人文",
    "food":      "美食风味",
    "shopping":  "逛街购物",
    "nightlife": "夜生活",
    "family":    "亲子休闲",
    "photo":     "网红打卡",
}

# 行程时长档位（小时），用于贪心行程的预算上界
ITINERARY_BUDGETS = {
    "quick": 4,      # 半日快游
    "full":  8,      # 全天
    "relax": 12,     # 慢节奏两日之内
}

DEFAULT_PROFILE = {axis: 3 for axis in PREFERENCE_AXES}  # 默认中性偏好

# 途中相邻两点间，每分钟可覆盖的“距离单位”
TRAVEL_SPEED = 30.0

# ---- MBTI 风格分类 ----
# 每个 POI 的 style 字段取自这些风格；MBTI 四字母按维度加分匹配。
MBTI_STYLES = ["古韵文化", "自然山水", "潮玩都市", "美食烟火", "亲子休闲", "夜景打卡"]

# 16 型人格：中文名 + 一句话性格描述（前端选择器/推荐卡片展示用）
MBTI_TYPES = {
    "INTJ": ("建筑师", "理性规划，偏爱安静深刻的所在"),
    "INTP": ("逻辑学家", "好奇心旺盛，爱钻小众有意思的角落"),
    "ENTJ": ("指挥官", "目标明确，行程要高效且体面"),
    "ENTP": ("辩论家", "喜欢新鲜刺激，哪里热闹往哪里去"),
    "INFJ": ("提倡者", "细腻感性，容易被人文氛围打动"),
    "INFP": ("调停者", "浪漫随性，为一片风景一个故事停留"),
    "ENFJ": ("主人公", "热情外放，爱把快乐分享给所有人"),
    "ENFP": ("竞选者", "能量满格，哪里好玩哪里就有我"),
    "ISTJ": ("物流师", "按部就班，经典与稳妥最让人安心"),
    "ISFJ": ("守卫者", "温和细心，喜欢熟悉与温暖的去处"),
    "ESTJ": ("总经理", "务实高效，吃好玩好不绕路"),
    "ESFJ": ("执政官", "照顾全场，热闹友善的地方最合适"),
    "ISTP": ("鉴赏家", "动手又探险，偏爱户外与自由"),
    "ISFP": ("探险家", "审美敏锐，为美与细节驻足"),
    "ESTP": ("企业家", "行动派玩家，夜生活与美食来者不拒"),
    "ESFP": ("表演者", "聚会中心，热闹与烟火都是主场"),
}