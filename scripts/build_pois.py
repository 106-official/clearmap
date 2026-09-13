# -*- coding: utf-8 -*-
"""一次性构建工具：把 POI 扩充到 55 个（五区分散），并补充
   style（风格分类）/ hours（开放时间）/ ticket（门票）/ images（图片）字段。
结果落盘 data/poi/changsha.json，运行时无依赖。

坐标约定：
  - lat/lon 为真实经纬度（须落在地图 bbox 内 [112.86, 28.05, 113.12, 28.4]）；
  - x/y 为 0-1000 抽象格坐标，由 bbox 线性映射（仅用于行程距离估算与兼容旧字段）。
图片使用站内图床接口（text_to_image），prompt 由景点名 + 描述生成。
"""
import json
import os
import sys
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_FILE = os.path.join(BASE, "data", "poi", "changsha.json")

LON0, LON1, LAT0, LAT1 = 112.86, 113.12, 28.05, 28.4  # w, e, s, n


def grid_xy(lon, lat):
    x = round((lon - LON0) / (LON1 - LON0) * 1000)
    y = round((LAT1 - lat) / (LAT1 - LAT0) * 1000)
    return max(0, min(1000, x)), max(0, min(1000, y))


def img(prompt_suffix, seed):
    prompt = "长沙实景旅游摄影，" + prompt_suffix + "，晴天自然光，高清摄影作品，构图精美"
    return ("https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt="
            + urllib.parse.quote(prompt) + "&image_size=landscape_16_9&seed=" + seed)


def images(name, desc, n=2):
    return [{"src": img(name + "，" + desc, str(i + 1)), "alt": name + " 景致 " + str(i + 1)} for i in range(n)]


# ---- 新 37 个 POI（每区补齐至 岳麓12 / 天心12 / 芙蓉11 / 开福10 / 雨花10）----
NEW = [
    # ============ 岳麓区 +7 ============
    dict(id="meixihu-island", name="梅溪湖城市岛", district="岳麓区", type="photo",
         tags=["湖湾", "白桥", "夜景"], duration_min=90, lat=28.1925, lon=112.8950,
         desc="螺旋白桥悬于梅溪湖面，黄昏亮灯后湖光倒影如画，是河西最出片的打卡地。",
         scores=dict(nature=4, photo=5, family=3, nightlife=3, culture=1, food=2, shopping=1),
         style=["自然山水", "夜景打卡"],
         hours=dict(open="00:00", close="24:00", note="全天开放"), ticket="免费"),
    dict(id="aiwanting", name="爱晚亭", district="岳麓区", type="culture",
         tags=["名亭", "红叶", "诗境"], duration_min=45, lat=28.1833, lon=112.9408,
         desc="岳麓山清风峡中的百年名亭，杜牧诗句“停车坐爱枫林晚”即出于此，秋日层林尽染。",
         scores=dict(culture=5, nature=4, photo=4, family=3, food=1, shopping=1, nightlife=1),
         style=["古韵文化"],
         hours=dict(open="06:00", close="22:00", note="随岳麓山景区开放"), ticket="免费"),
    dict(id="hunan-university", name="湖南大学", district="岳麓区", type="culture",
         tags=["千年学府", "红墙", "书香"], duration_min=60, lat=28.1800, lon=112.9410,
         desc="没有围墙的大学，东方红广场与红楼并列，与岳麓书院一脉相承的书香气息。",
         scores=dict(culture=5, photo=3, family=3, food=2, shopping=1, nightlife=1, nature=2),
         style=["古韵文化", "潮玩都市"],
         hours=dict(open="00:00", close="24:00", note="校园开放"), ticket="免费"),
    dict(id="yuren-pier", name="渔人码头", district="岳麓区", type="nightlife",
         tags=["欧式街区", "江畔", "夜宵"], duration_min=90, lat=28.2380, lon=112.9580,
         desc="湘江西岸的欧式风情街区，临江露台吹风喝一杯，入夜霓虹与江影交错。",
         scores=dict(food=4, nightlife=4, photo=4, shopping=2, family=3, culture=1, nature=2),
         style=["美食烟火", "夜景打卡"],
         hours=dict(open="10:00", close="24:00", note="餐饮街区营业至深夜"), ticket="免费"),
    dict(id="xihu-park", name="西湖公园", district="岳麓区", type="nature",
         tags=["湖景", "草坪", "亲子"], duration_min=90, lat=28.2110, lon=112.9280,
         desc="城西的静谧湖园，环湖步道树影婆娑，草坪开阔，适合散步与野餐。",
         scores=dict(nature=4, family=4, photo=3, culture=1, food=2, shopping=1, nightlife=1),
         style=["自然山水", "亲子休闲"],
         hours=dict(open="06:00", close="22:00", note="免费入园"), ticket="免费"),
    dict(id="lizijian-gallery", name="李自健美术馆", district="岳麓区", type="culture",
         tags=["油画", "湖景", "艺术"], duration_min=90, lat=28.1320, lon=112.9490,
         desc="临湖而建的美术馆，李自健写实油画震撼人心，建筑本身即是风景。",
         scores=dict(culture=4, photo=4, family=3, nature=2, food=1, shopping=1, nightlife=1),
         style=["古韵文化", "潮玩都市"],
         hours=dict(open="09:30", close="17:30", note="周一闭馆"), ticket="免费"),
    dict(id="houhu-art", name="后湖国际艺术园", district="岳麓区", type="photo",
         tags=["艺术街区", "咖啡", "涂鸦"], duration_min=90, lat=28.1620, lon=112.9370,
         desc="大学城旁的艺术村落，厂房改造的画廊与咖啡馆散布湖边，青年气息浓厚。",
         scores=dict(photo=4, culture=3, food=3, nightlife=2, family=2, shopping=2, nature=2),
         style=["潮玩都市"],
         hours=dict(open="10:00", close="21:00", note="园区开放"), ticket="免费"),
    # ============ 天心区 +3 ============
    dict(id="baisha-well", name="白沙古井", district="天心区", type="culture",
         tags=["古井", "汲水", "市井"], duration_min=30, lat=28.1880, lon=112.9705,
         desc="长沙老城的一眼活井，历代文人题咏，至今仍有市民前来取水泡茶。",
         scores=dict(culture=4, photo=2, family=2, nature=1, food=1, shopping=1, nightlife=1),
         style=["古韵文化"],
         hours=dict(open="00:00", close="24:00", note="露天古井"), ticket="免费"),
    dict(id="nanmenkou", name="南门口", district="天心区", type="food",
         tags=["老巷", "糖油粑粑", "烟火"], duration_min=60, lat=28.1805, lon=112.9710,
         desc="老长沙的记忆坐标，巷口小摊的糖油粑粑与葱油粑粑冒着热气，从早到晚不断。",
         scores=dict(food=5, nightlife=3, photo=3, culture=2, shopping=2, family=3, nature=1),
         style=["美食烟火"],
         hours=dict(open="08:00", close="23:00", note="小吃摊营业"), ticket="免费"),
    dict(id="train-park", name="火车头公园", district="天心区", type="photo",
         tags=["绿皮车", "工业风", "打卡"], duration_min=45, lat=28.1650, lon=112.9730,
         desc="江畔停着退役的蒸汽机车头，锈色铁轨配江景，怀旧工业风的出片圣地。",
         scores=dict(photo=5, culture=3, family=3, nature=2, food=1, shopping=1, nightlife=2),
         style=["潮玩都市", "夜景打卡"],
         hours=dict(open="06:00", close="22:00", note="免费开放"), ticket="免费"),
    # ============ 芙蓉区 +8 ============
    dict(id="duzheng-street", name="都正街", district="芙蓉区", type="culture",
         tags=["老街", "市井", "烟火"], duration_min=60, lat=28.1860, lon=112.9750,
         desc="窄巷老屋修旧如旧，灯笼挂满檐角，茶楼与小吃铺混着长沙人的日常。",
         scores=dict(culture=4, food=4, photo=3, nightlife=2, family=3, shopping=2, nature=1),
         style=["古韵文化", "美食烟火"],
         hours=dict(open="10:00", close="23:00", note="街区开放"), ticket="免费"),
    dict(id="hualongchi", name="化龙池", district="芙蓉区", type="nightlife",
         tags=["酒吧", "清吧", "小巷"], duration_min=90, lat=28.1840, lon=112.9770,
         desc="白天的麻石小巷安静，入夜清吧亮起暖灯，音乐与低语漫过墙头。",
         scores=dict(nightlife=5, food=3, photo=3, culture=2, shopping=1, family=1, nature=1),
         style=["夜景打卡"],
         hours=dict(open="18:00", close="02:00", note="夜间酒吧街区"), ticket="免费"),
    dict(id="mifen-street", name="湖南米粉街", district="芙蓉区", type="food",
         tags=["米粉", "早餐", "嗦粉"], duration_min=45, lat=28.2000, lon=112.9860,
         desc="一街嗦遍湖南各地米粉，码子飘香，墙上涂鸦适合拍照发圈。",
         scores=dict(food=5, photo=3, family=3, nightlife=1, shopping=1, culture=1, nature=1),
         style=["美食烟火"],
         hours=dict(open="07:00", close="22:00", note="早餐最旺"), ticket="免费"),
    dict(id="baiguoyuan", name="白果园", district="芙蓉区", type="culture",
         tags=["老宅", "青砖", "静谧"], duration_min=45, lat=28.1930, lon=112.9680,
         desc="闹市中的一片民国老宅，青砖灰瓦间藏着长沙近现代史的脚印。",
         scores=dict(culture=4, photo=3, family=2, nature=1, food=2, shopping=1, nightlife=1),
         style=["古韵文化"],
         hours=dict(open="00:00", close="24:00", note="街区开放"), ticket="免费"),
    dict(id="dingwangtai", name="定王台", district="芙蓉区", type="culture",
         tags=["书市", "故址", "怀古"], duration_min=40, lat=28.1910, lon=112.9770,
         desc="汉长沙定王筑台望母之处，如今书市环绕，纸墨香与历史重叠。",
         scores=dict(culture=4, photo=2, family=2, food=2, shopping=2, nature=1, nightlife=1),
         style=["古韵文化"],
         hours=dict(open="00:00", close="24:00", note="书市白天营业"), ticket="免费"),
    dict(id="wanjiali", name="万家丽国际购物中心", district="芙蓉区", type="shopping",
         tags=["巨mall", "天台", "地标"], duration_min=120, lat=28.1980, lon=113.0350,
         desc="建筑体量惊人的一站式巨mall，顶层观景天台可俯瞰半个长沙。",
         scores=dict(shopping=5, food=4, photo=3, family=4, nightlife=2, culture=1, nature=1),
         style=["潮玩都市"],
         hours=dict(open="10:00", close="22:00", note="商场营业"), ticket="免费"),
    dict(id="hq-wedding-park", name="浏阳河婚庆文化园", district="芙蓉区", type="photo",
         tags=["欧式", "教堂", "夜景"], duration_min=60, lat=28.2050, lon=113.0250,
         desc="浏阳河畔的欧式建筑群，白色教堂与草坪是婚纱照圣地，入夜灯光温柔。",
         scores=dict(photo=5, family=3, nightlife=3, nature=2, food=2, shopping=2, culture=1),
         style=["夜景打卡", "亲子休闲"],
         hours=dict(open="00:00", close="24:00", note="园区开放"), ticket="免费"),
    dict(id="library", name="湖南省图书馆", district="芙蓉区", type="culture",
         tags=["老馆", "书香", "静谧"], duration_min=60, lat=28.1980, lon=112.9775,
         desc="百年老馆藏书百万册，中庭绿意掩映，是城中难得的安静角落。",
         scores=dict(culture=4, family=2, photo=2, nature=2, food=1, shopping=1, nightlife=1),
         style=["古韵文化"],
         hours=dict(open="08:30", close="17:30", note="周二闭馆"), ticket="免费"),
    # ============ 开福区 +9 ============
    dict(id="window-of-world", name="长沙世界之窗", district="开福区", type="family",
         tags=["主题乐园", "微缩景观", "游乐"], duration_min=240, lat=28.2530, lon=113.0500,
         desc="把世界名胜微缩到一处，过山车与摩天轮并举，适合全家玩上一整天。",
         scores=dict(family=5, photo=4, nightlife=2, food=3, shopping=2, culture=2, nature=1),
         style=["亲子休闲", "潮玩都市"],
         hours=dict(open="09:00", close="22:00", note="节假日延长"), ticket="¥200 起"),
    dict(id="underwater-world", name="长沙海底世界", district="开福区", type="family",
         tags=["海洋馆", "企鹅", "亲子"], duration_min=150, lat=28.2500, lon=113.0550,
         desc="蔚蓝隧道里鲨鱼从头顶游过，海豚表演让小朋友挪不开眼睛。",
         scores=dict(family=5, photo=4, nature=3, food=2, shopping=1, culture=1, nightlife=1),
         style=["亲子休闲"],
         hours=dict(open="09:00", close="18:00", note="周末延长"), ticket="¥160 起"),
    dict(id="martyrs-park", name="烈士公园", district="开福区", type="nature",
         tags=["湖心亭", "梧桐", "年嘉湖"], duration_min=120, lat=28.2160, lon=113.0050,
         desc="城央最大的绿肺，年嘉湖泛舟、梧桐大道漫步，四季都有不同的风景。",
         scores=dict(nature=4, family=4, photo=3, culture=2, food=2, shopping=1, nightlife=1),
         style=["自然山水", "亲子休闲"],
         hours=dict(open="06:00", close="22:00", note="免费入园"), ticket="免费"),
    dict(id="changsha-museum", name="长沙博物馆", district="开福区", type="culture",
         tags=["湖湘", "青铜", "新馆"], duration_min=120, lat=28.2300, lon=112.9890,
         desc="滨江文化园里的新馆，湖湘文明从炭河里青铜到长沙窑瓷器层层铺开。",
         scores=dict(culture=5, photo=3, family=4, nature=1, food=1, shopping=1, nightlife=1),
         style=["古韵文化"],
         hours=dict(open="09:00", close="17:00", note="周一闭馆，需预约"), ticket="免费预约"),
    dict(id="jiangtan-park", name="湘江江滩公园", district="开福区", type="nature",
         tags=["江滩", "晚霞", "风筝"], duration_min=90, lat=28.2570, lon=112.9770,
         desc="湘江北岸的滩涂公园，日落时分江面镀金，风筝与野餐的人群散落草坡。",
         scores=dict(nature=4, photo=4, family=4, nightlife=2, food=1, shopping=1, culture=1),
         style=["自然山水", "夜景打卡"],
         hours=dict(open="00:00", close="24:00", note="全天开放"), ticket="免费"),
    dict(id="chaozong-street", name="潮宗街", district="开福区", type="culture",
         tags=["麻石路", "教堂", "老街"], duration_min=60, lat=28.2010, lon=112.9700,
         desc="长沙最老的麻石街之一，老教堂与咖啡店并肩，历史和新潮在这里擦肩。",
         scores=dict(culture=4, photo=4, food=3, nightlife=2, family=2, shopping=2, nature=1),
         style=["古韵文化"],
         hours=dict(open="00:00", close="24:00", note="街区开放"), ticket="免费"),
    dict(id="binjiang-culture", name="滨江文化园", district="开福区", type="culture",
         tags=["三馆一厅", "江景", "地标"], duration_min=90, lat=28.2280, lon=112.9900,
         desc="博物馆、图书馆、规划馆与音乐厅沿江一字排开，夜色中灯光如带。",
         scores=dict(culture=4, photo=4, nightlife=3, family=3, nature=2, food=1, shopping=1),
         style=["古韵文化", "夜景打卡"],
         hours=dict(open="09:00", close="21:00", note="场馆开放"), ticket="免费"),
    dict(id="hunan-tv", name="湖南广电", district="开福区", type="photo",
         tags=["芒果台", "追星", "打卡"], duration_min=60, lat=28.2440, lon=113.0560,
         desc="“芒果台”大本营，马栏山上的地标建筑，偶遇明星的概率最高的地方。",
         scores=dict(photo=4, nightlife=2, shopping=2, food=2, culture=1, family=2, nature=1),
         style=["潮玩都市", "夜景打卡"],
         hours=dict(open="00:00", close="24:00", note="外观开放"), ticket="免费"),
    dict(id="yuehu-park", name="月湖公园", district="开福区", type="nature",
         tags=["湖景", "雕塑", "清幽"], duration_min=90, lat=28.2320, lon=113.0450,
         desc="一弯月形湖面环绕雕塑园，桥影与树影落进水里，散步骑行皆宜。",
         scores=dict(nature=4, family=4, photo=3, culture=2, food=1, shopping=1, nightlife=1),
         style=["自然山水", "亲子休闲"],
         hours=dict(open="06:00", close="22:00", note="免费入园"), ticket="免费"),
    # ============ 雨花区 +10 ============
    dict(id="botanical-garden", name="湖南省森林植物园", district="雨花区", type="nature",
         tags=["花海", "樱花园", "森林"], duration_min=180, lat=28.1220, lon=113.0130,
         desc="城郊的森林氧吧，樱花、杜鹃与郁金香按季盛放，徒步栈道穿林而过。",
         scores=dict(nature=5, family=5, photo=5, culture=1, food=2, shopping=1, nightlife=1),
         style=["自然山水", "亲子休闲"],
         hours=dict(open="07:00", close="18:00", note="花期收费"), ticket="¥20 起"),
    dict(id="guitang-river", name="圭塘河风光带", district="雨花区", type="nature",
         tags=["河畔", "绿道", "骑行"], duration_min=90, lat=28.1450, lon=113.0330,
         desc="穿城而过的生态河道，两岸绿道连成环线，晨跑夜骑都舒服。",
         scores=dict(nature=4, family=4, photo=3, culture=1, food=2, shopping=1, nightlife=2),
         style=["自然山水", "亲子休闲"],
         hours=dict(open="00:00", close="24:00", note="全天开放"), ticket="免费"),
    dict(id="desiqin", name="德思勤城市广场", district="雨花区", type="shopping",
         tags=["商圈", "24h书店", "影院"], duration_min=120, lat=28.1150, lon=113.0130,
         desc="南城人气商圈，24 小时书店与影院餐厅云集，是雨花区的夜生活中心。",
         scores=dict(shopping=5, food=4, nightlife=4, photo=3, family=3, culture=1, nature=1),
         style=["潮玩都市"],
         hours=dict(open="10:00", close="22:30", note="商场营业"), ticket="免费"),
    dict(id="hongxing-flowers", name="红星花卉市场", district="雨花区", type="shopping",
         tags=["鲜花", "绿植", "便宜"], duration_min=60, lat=28.0950, lon=113.0190,
         desc="整条街都是花档，十元一捧的浪漫，挑一束带走整个好心情。",
         scores=dict(shopping=4, photo=4, family=3, nature=2, food=1, culture=1, nightlife=1),
         style=["潮玩都市"],
         hours=dict(open="08:00", close="19:00", note="批发零售"), ticket="免费"),
    dict(id="dongtang", name="东塘商圈", district="雨花区", type="shopping",
         tags=["老商圈", "商场", "小吃"], duration_min=90, lat=28.1650, lon=112.9980,
         desc="长沙的老牌商圈，百货与地下小吃街并存，市井与潮流各占一半。",
         scores=dict(shopping=4, food=4, nightlife=3, photo=2, family=3, culture=1, nature=1),
         style=["潮玩都市", "美食烟火"],
         hours=dict(open="10:00", close="22:00", note="商场营业"), ticket="免费"),
    dict(id="yuhua-feiwei", name="雨花非遗馆", district="雨花区", type="culture",
         tags=["非遗", "手作", "体验"], duration_min=90, lat=28.1500, lon=113.0100,
         desc="湖南非遗技艺的集中展厅，湘绣、陶瓷、竹编可看可学可上手。",
         scores=dict(culture=4, family=4, photo=3, shopping=2, food=1, nature=1, nightlife=1),
         style=["古韵文化"],
         hours=dict(open="09:00", close="17:30", note="周一闭馆"), ticket="免费"),
    dict(id="xiangfu-park", name="湘府文化公园", district="雨花区", type="nature",
         tags=["湖园", "广场", "傍晚"], duration_min=60, lat=28.1110, lon=113.0170,
         desc="省府旁的宽阔湖园，傍晚喷泉与散步人流汇成南城的日常风景。",
         scores=dict(nature=4, family=4, photo=3, culture=1, food=1, shopping=1, nightlife=1),
         style=["自然山水"],
         hours=dict(open="06:00", close="22:00", note="免费入园"), ticket="免费"),
    dict(id="gaoqiao-market", name="高桥大市场", district="雨花区", type="shopping",
         tags=["批发", "淘货", "烟火"], duration_min=120, lat=28.1780, lon=113.0350,
         desc="中南地区最大的综合批发市场，从饰品到干货无所不有，淘货乐趣无穷。",
         scores=dict(shopping=5, food=3, nightlife=1, photo=2, family=2, culture=1, nature=1),
         style=["潮玩都市", "美食烟火"],
         hours=dict(open="08:00", close="18:00", note="批发为主"), ticket="免费"),
    dict(id="shawan-park", name="沙湾公园", district="雨花区", type="nature",
         tags=["山丘", "森林", "步道"], duration_min=90, lat=28.1550, lon=113.0520,
         desc="掩在城市里的绿丘，石阶步道穿林，山顶小亭可远眺万家灯火。",
         scores=dict(nature=4, family=4, photo=3, culture=1, food=1, shopping=1, nightlife=2),
         style=["自然山水", "亲子休闲"],
         hours=dict(open="06:00", close="22:00", note="免费入园"), ticket="免费"),
    dict(id="guihua-park", name="桂花公园", district="雨花区", type="nature",
         tags=["桂香", "晨练", "清静"], duration_min=60, lat=28.1480, lon=113.0030,
         desc="秋日满园桂花香，园子不大却安静整洁，是老城居民的日常散步地。",
         scores=dict(nature=4, family=4, photo=2, culture=1, food=1, shopping=1, nightlife=1),
         style=["自然山水", "亲子休闲"],
         hours=dict(open="06:00", close="22:00", note="免费入园"), ticket="免费"),
]

# ---- 既有 18 个 POI 的补充分配（style / hours / ticket）----
ENRICH = {
    "yuelu-mountain": dict(style=["自然山水"],
        hours=dict(open="06:00", close="22:00", note="免费入园，索道另计"), ticket="免费"),
    "yuelu-academy": dict(style=["古韵文化"],
        hours=dict(open="07:30", close="18:00", note="17:30 停止售票"), ticket="¥50"),
    "yuhu-wetland": dict(style=["自然山水", "亲子休闲"],
        hours=dict(open="07:00", close="21:00", note="湿地科普馆 9:00-17:00"), ticket="免费"),
    "juzizhou": dict(style=["自然山水", "夜景打卡"],
        hours=dict(open="07:00", close="22:00", note="观光小火车 8:00-21:00"), ticket="免费"),
    "xiangjiang-view": dict(style=["自然山水", "夜景打卡"],
        hours=dict(open="00:00", close="24:00", note="沿江步道全天开放"), ticket="免费"),
    "taiping-street": dict(style=["美食烟火", "古韵文化"],
        hours=dict(open="09:00", close="23:00", note="夜景最佳"), ticket="免费"),
    "pozi-street": dict(style=["美食烟火", "夜景打卡"],
        hours=dict(open="10:00", close="24:00", note="越夜越热闹"), ticket="免费"),
    "huogongdian": dict(style=["美食烟火"],
        hours=dict(open="11:00", close="22:00", note="早茶 7:00-10:30"), ticket="免费"),
    "wenheyou": dict(style=["潮玩都市", "美食烟火"],
        hours=dict(open="11:00", close="24:00", note="排队较久，建议提前取号"), ticket="免费"),
    "wuyi-square": dict(style=["潮玩都市"],
        hours=dict(open="00:00", close="24:00", note="商圈广场"), ticket="免费"),
    "ifs-changsha": dict(style=["潮玩都市"],
        hours=dict(open="10:00", close="22:00", note="观景台 10:00-22:00"), ticket="免费"),
    "huangxing-walk": dict(style=["潮玩都市", "夜景打卡"],
        hours=dict(open="10:00", close="24:00", note="步行街全天"), ticket="免费"),
    "jiayi-guju": dict(style=["古韵文化"],
        hours=dict(open="08:30", close="17:30", note="周一闭馆"), ticket="免费"),
    "hun-museum": dict(style=["古韵文化"],
        hours=dict(open="09:00", close="17:00", note="周一闭馆，需公众号预约"), ticket="免费预约"),
    "tianxin-pavilion": dict(style=["古韵文化"],
        hours=dict(open="08:00", close="17:30", note="17:00 停止入园"), ticket="¥32"),
    "dufu-jiangge": dict(style=["古韵文化", "夜景打卡"],
        hours=dict(open="09:00", close="22:00", note="夜间亮灯至 22:00"), ticket="¥11"),
    "jiefangxi": dict(style=["夜景打卡", "美食烟火"],
        hours=dict(open="18:00", close="04:00", note="越夜越疯狂"), ticket="免费"),
    "orange-ride": dict(style=["自然山水", "夜景打卡"],
        hours=dict(open="00:00", close="24:00", note="租车点白天营业"), ticket="免费"),
}

ALL = {
    "meixihu-island": "梅溪湖城市岛", "aiwanting": "爱晚亭", "hunan-university": "湖南大学",
    "yuren-pier": "渔人码头", "xihu-park": "西湖公园", "lizijian-gallery": "李自健美术馆",
    "houhu-art": "后湖国际艺术园", "baisha-well": "白沙古井", "nanmenkou": "南门口",
    "train-park": "火车头公园", "duzheng-street": "都正街", "hualongchi": "化龙池",
    "mifen-street": "湖南米粉街", "baiguoyuan": "白果园", "dingwangtai": "定王台",
    "wanjiali": "万家丽国际购物中心", "hq-wedding-park": "浏阳河婚庆文化园",
    "library": "湖南省图书馆", "window-of-world": "长沙世界之窗",
    "underwater-world": "长沙海底世界", "martyrs-park": "烈士公园",
    "changsha-museum": "长沙博物馆", "jiangtan-park": "湘江江滩公园",
    "chaozong-street": "潮宗街", "binjiang-culture": "滨江文化园",
    "hunan-tv": "湖南广电", "yuehu-park": "月湖公园", "botanical-garden": "湖南省森林植物园",
    "guitang-river": "圭塘河风光带", "desiqin": "德思勤城市广场",
    "hongxing-flowers": "红星花卉市场", "dongtang": "东塘商圈", "yuhua-feiwei": "雨花非遗馆",
    "xiangfu-park": "湘府文化公园", "gaoqiao-market": "高桥大市场",
    "shawan-park": "沙湾公园", "guihua-park": "桂花公园",
}


def enrich_poi(p):
    """给既有 POI 补充 style/hours/ticket/images，desc 保持原样。"""
    pid = p["id"]
    extra = ENRICH.get(pid, {})
    p["style"] = extra.get("style", ["古韵文化"] if p.get("type") == "culture" else ["潮玩都市"])
    p["hours"] = extra.get("hours", dict(open="09:00", close="18:00", note="以现场为准"))
    p["ticket"] = extra.get("ticket", "免费")
    p["images"] = images(p["name"], p.get("desc", ""))
    return p


def main():
    with open(POI_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)

    pois = doc["pois"]
    ids = {p["id"] for p in pois}
    dups = [n["id"] for n in NEW if n["id"] in ids]
    if dups:
        raise SystemExit("新增 POI id 重复: %s" % dups)

    for n in NEW:
        x, y = grid_xy(n["lon"], n["lat"])
        n["x"] = x
        n["y"] = y
        n["images"] = images(n["name"], n["desc"])
        if not (LON0 <= n["lon"] <= LON1 and LAT0 <= n["lat"] <= LAT1):
            raise SystemExit("坐标越界: %s" % n["id"])
        pois.append(n)

    pois = [enrich_poi(p) for p in pois]

    # 分区统计
    from collections import Counter
    dist = Counter(p["district"] for p in pois)
    print("分区统计:", dict(dist), "共", len(pois), "个")
    for d, n in dist.items():
        if n < 10:
            print("  警告: %s 不足 10 个（%d）" % (d, n))

    doc["pois"] = pois
    doc["note"] = ("POI 单一数据源（55 个，五区分散）。x/y 为 0-1000 抽象地图格坐标；"
                   "scores 为各偏好轴得分(0-5)；style 为 MBTI 风格分类；"
                   "images 为站内图床链接。")
    with open(POI_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("已写入", POI_FILE)


if __name__ == "__main__":
    main()
