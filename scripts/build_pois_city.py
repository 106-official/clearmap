# -*- coding: utf-8 -*-
"""构建上海 / 北京两城的 POI 数据文件。

手写精选景点清单（含真实经纬度、偏好得分、风格、开放信息），
一次性生成：
  - data/poi/<city>.json      后端 /api/pois?city=<city> 读取
  - static/pois-<city>.json   APK 离线兜底读取
字段结构与长沙 data/poi/changsha.json 一致（scores 七个偏好轴 / style / hours / ticket / images）。
"""
import json
import os
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_DIR = os.path.join(BASE, "data", "poi")
STATIC_DIR = os.path.join(BASE, "static")

BBOX = {
    # city: (s, w, n, e)
    "shanghai": (31.14, 121.395, 31.31, 121.575),
    "beijing":  (39.72, 116.16, 40.06, 116.62),
}


def grid_xy(bbox, lon, lat):
    s, w, n, e = bbox
    x = round((lon - w) / (e - w) * 1000)
    y = round((n - lat) / (n - s) * 1000)
    return max(0, min(1000, x)), max(0, min(1000, y))


def img(city, name, desc, seed):
    prompt = ("%s实景旅游摄影，%s现场风貌，晴天自然光，高清摄影作品，构图精美" % (city, name + "，" + desc))
    return "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=" + \
        urllib.parse.quote(prompt) + "&image_size=landscape_16_9&seed=" + seed


def images(city, name, desc, n=2):
    return [{"src": img(city, name, desc, str(i + 1)), "alt": name + " 景致 " + str(i + 1)} for i in range(n)]


D = {a: 1 for a in ("nature", "culture", "food", "shopping", "nightlife", "family", "photo")}
def sc(nature=1, culture=1, food=1, shopping=1, nightlife=1, family=1, photo=1):
    return dict(nature=nature, culture=culture, food=food, shopping=shopping,
                nightlife=nightlife, family=family, photo=photo)


CATS = {
    "shanghai": "上海",
    "beijing": "北京",
}

POIS = {
# ---------------------------------------------------------------- 上海 ----
"shanghai": [
  dict(id="the-bund", name="外滩", district="黄浦区", type="nightlife",
       tags=["万国建筑", "江景", "夜色"], duration_min=90, lat=31.2397, lon=121.4900,
       desc="黄浦江畔的万国建筑博览群，对岸陆家嘴灯火如带，是魔都最经典的夜色封面。",
       scores=sc(culture=4, nightlife=5, photo=5, family=4, food=3, shopping=3, nature=2),
       style=["夜景打卡", "古韵文化"],
       hours=dict(open="00:00", close="24:00", note="滨水步道全天开放"), ticket="免费"),
  dict(id="yu-garden", name="豫园", district="黄浦区", type="culture",
       tags=["明代园林", "九曲桥", "点心"], duration_min=120, lat=31.2270, lon=121.4920,
       desc="四百年的江南园林，亭台错落、假山盘曲，园外老街满是南翔小笼与金银饰品。",
       scores=sc(culture=5, photo=4, family=4, food=4, shopping=3, nature=2, nightlife=1),
       style=["古韵文化", "美食烟火"],
       hours=dict(open="09:00", close="16:30", note="周一闭园"), ticket="¥40"),
  dict(id="nanjing-road", name="南京路步行街", district="黄浦区", type="shopping",
       tags=["步行街", "老字号", "人流"], duration_min=120, lat=31.2365, lon=121.4780,
       desc="十里洋场的商业老街，老字号与新潮店并肩，从早到晚人潮如织。",
       scores=sc(shopping=5, food=5, photo=4, nightlife=4, family=4, culture=3, nature=1),
       style=["潮玩都市", "美食烟火"],
       hours=dict(open="10:00", close="22:30", note="步行街全天"), ticket="免费"),
  dict(id="people-square", name="上海人民广场", district="黄浦区", type="shopping",
       tags=["城市客厅", "鸽群", "博物馆"], duration_min=90, lat=31.2317, lon=121.4679,
       desc="上海真正的城市客厅，广场鸽群与双层巴士相伴，四周是美术馆、大剧院与商业地标。",
       scores=sc(shopping=4, culture=4, family=4, photo=3, nightlife=2, food=3, nature=2),
       style=["潮玩都市"],
       hours=dict(open="00:00", close="24:00", note="广场开放"), ticket="免费"),
  dict(id="xintiandi", name="新天地", district="黄浦区", type="photo",
       tags=["石库门", "里弄", "潮店"], duration_min=120, lat=31.2167, lon=121.4760,
       desc="石库门老里弄改造成的时尚街区，青砖弄堂里藏着咖啡馆、买手店与餐厅。",
       scores=sc(photo=5, shopping=5, food=4, nightlife=4, culture=3, family=3, nature=1),
       style=["潮玩都市", "夜景打卡"],
       hours=dict(open="10:00", close="23:00", note="街区开放"), ticket="免费"),
  dict(id="tianzifang", name="田子坊", district="黄浦区", type="photo",
       tags=["弄堂", "手作", "涂鸦"], duration_min=90, lat=31.2080, lon=121.4680,
       desc="小弄堂里挤满画廊、首饰铺与创意小店，是文艺青年的淘宝与拍照天堂。",
       scores=sc(photo=5, shopping=4, food=3, nightlife=3, culture=3, family=2, nature=1),
       style=["潮玩都市"],
       hours=dict(open="10:00", close="21:00", note="街区开放"), ticket="免费"),
  dict(id="jingan-temple", name="静安寺", district="静安区", type="culture",
       tags=["千年古刹", "金顶", "闹中取静"], duration_min=60, lat=31.2230, lon=121.4450,
       desc="繁华商圈中心的一座千年古刹，金顶在玻璃幕墙间闪着光，钟声与车流交织。",
       scores=sc(culture=4, photo=4, nightlife=2, shopping=3, food=2, family=2, nature=2),
       style=["古韵文化"],
       hours=dict(open="07:00", close="17:00", note="香火时段"), ticket="¥50"),
  dict(id="wukang-building", name="武康大楼", district="徐汇区", type="photo",
       tags=["老洋房", "楔形楼", "打卡"], duration_min=45, lat=31.2100, lon=121.4410,
       desc="路口的一幢楔形老公寓，红砖立面与梧桐光影，是上海最出片的街角。",
       scores=sc(photo=5, culture=3, food=3, shopping=3, nightlife=2, family=2, nature=2),
       style=["古韵文化", "夜景打卡"],
       hours=dict(open="00:00", close="24:00", note="街角外观"), ticket="免费"),
  dict(id="hengshan-road", name="衡山路", district="徐汇区", type="photo",
       tags=["梧桐大道", "酒吧", "老洋房"], duration_min=90, lat=31.2040, lon=121.4450,
       desc="法国梧桐夹道的林荫老路，旧洋房与新酒吧错落，夜生活从黄昏开始。",
       scores=sc(photo=4, nightlife=5, food=4, shopping=3, culture=3, nature=3, family=2),
       style=["夜景打卡", "古韵文化"],
       hours=dict(open="00:00", close="24:00", note="酒吧街入夜最旺"), ticket="免费"),
  dict(id="century-park", name="世纪公园", district="浦东新区", type="nature",
       tags=["大草坪", "镜天湖", "亲子"], duration_min=150, lat=31.2200, lon=121.5450,
       desc="浦东中心最大的绿地，镜天湖畔草坪开阔，适合野餐、骑行与放风筝。",
       scores=sc(nature=5, family=5, photo=4, food=2, shopping=1, culture=1, nightlife=1),
       style=["自然山水", "亲子休闲"],
       hours=dict(open="07:00", close="18:00", note="免费入园"), ticket="免费"),
  dict(id="oriental-pearl", name="东方明珠塔", district="浦东新区", type="photo",
       tags=["观景", "玻璃廊", "夜景"], duration_min=120, lat=31.2396, lon=121.4998,
       desc="黄浦江畔的球形电视塔，高空玻璃廊与旋转餐厅可俯瞰整座魔都夜色。",
       scores=sc(photo=5, nightlife=5, culture=3, family=4, shopping=2, nature=1, food=3),
       style=["夜景打卡", "潮玩都市"],
       hours=dict(open="09:00", close="21:00", note="观景最晚入场 21:00"), ticket="¥199 起"),
  dict(id="lujiazui", name="陆家嘴金融城", district="浦东新区", type="shopping",
       tags=["三件套", "摩天楼", "CBD"], duration_min=90, lat=31.2390, lon=121.5010,
       desc="摩天大楼的森林，环球金融、金茂与上海中心三足鼎立，走在地下连廊感受都市脉搏。",
       scores=sc(shopping=4, photo=5, nightlife=4, food=4, culture=2, family=3, nature=1),
       style=["潮玩都市", "夜景打卡"],
       hours=dict(open="00:00", close="24:00", note="连廊与步道全天"), ticket="免费"),
  dict(id="xuhui-bible", name="徐家汇天主堂", district="徐汇区", type="culture",
       tags=["哥特式", "双塔", "礼拜"], duration_min=45, lat=31.1910, lon=121.4400,
       desc="尖顶哥特式的百年教堂，双塔直插天际，是徐家汇最醒目的地标建筑。",
       scores=sc(culture=4, photo=4, shopping=2, family=2, food=1, nightlife=1, nature=1),
       style=["古韵文化"],
       hours=dict(open="09:00", close="16:00", note="弥撒期间不对游客开放"), ticket="免费"),
  dict(id="m50-art", name="M50 创意园", district="普陀区", type="photo",
       tags=["艺术仓库", "画廊", "涂鸦"], duration_min=90, lat=31.2400, lon=121.4060,
       desc="苏州河边的老厂房改成艺术仓库，一间间画廊堆放当代艺术与先锋装置。",
       scores=sc(photo=5, culture=4, shopping=3, nightlife=2, food=2, family=2, nature=1),
       style=["潮玩都市"],
       hours=dict(open="09:00", close="18:00", note="个展按展期"), ticket="免费"),
  dict(id="changfeng-park", name="长风公园", district="普陀区", type="family",
       tags=["海洋世界", "湖山", "亲子"], duration_min=150, lat=31.2250, lon=121.4020,
       desc="山水园林与海洋馆并存的亲子乐园，白鲸与海豚表演让小朋友流连忘返。",
       scores=sc(family=5, nature=4, photo=4, food=3, shopping=1, culture=1, nightlife=1),
       style=["亲子休闲", "自然山水"],
       hours=dict(open="08:00", close="17:30", note="海洋馆另售票"), ticket="¥180 起"),
],

# ---------------------------------------------------------------- 北京 ----
"beijing": [
  dict(id="forbidden-city", name="故宫博物院", district="东城区", type="culture",
       tags=["紫禁城", "宫殿", "六百载"], duration_min=240, lat=39.9163, lon=116.3972,
       desc="世界上现存最大的宫殿建筑群，红墙黄瓦与飞檐斗拱，走进它就像走进历史本身。",
       scores=sc(culture=5, photo=5, family=4, shopping=1, food=2, nature=1, nightlife=1),
       style=["古韵文化"],
       hours=dict(open="08:30", close="17:00", note="周一闭馆，需预约"), ticket="¥60"),
  dict(id="tiananmen", name="天安门广场", district="东城区", type="culture",
       tags=["国门", "广场", "升旗"], duration_min=90, lat=39.9055, lon=116.3976,
       desc="世界上最大的城市广场，正阳门与人民英雄纪念碑相望，升旗仪式庄严而动人。",
       scores=sc(culture=5, photo=4, family=4, nature=2, shopping=1, food=1, nightlife=1),
       style=["古韵文化"],
       hours=dict(open="05:00", close="22:00", note="安检进入"), ticket="免费"),
  dict(id="temple-of-heaven", name="天坛公园", district="东城区", type="culture",
       tags=["祈年殿", "回音壁", "古柏"], duration_min=120, lat=39.8822, lon=116.4066,
       desc="明清皇帝祭天的圜丘与祈年殿，蓝瓦圆殿配松柏，晨练人群与古意相映。",
       scores=sc(culture=5, nature=4, photo=4, family=4, food=2, shopping=1, nightlife=1),
       style=["古韵文化", "自然山水"],
       hours=dict(open="06:00", close="22:00", note="园内景点 17:30 止"), ticket="¥34"),
  dict(id="jingshan-park", name="景山公园", district="西城区", type="nature",
       tags=["万春亭", "俯瞰故宫", "牡丹"], duration_min=90, lat=39.9230, lon=116.3960,
       desc="故宫北侧的小山，万春亭顶可俯瞰整片紫禁城金瓦，是绝佳的拍摄机位。",
       scores=sc(nature=5, photo=5, culture=4, family=4, food=2, shopping=1, nightlife=1),
       style=["自然山水", "古韵文化"],
       hours=dict(open="06:30", close="21:00", note="登山步道"), ticket="¥2"),
  dict(id="beihai-park", name="北海公园", district="西城区", type="nature",
       tags=["白塔", "太液池", "九龙壁"], duration_min=120, lat=39.9250, lon=116.3830,
       desc="清代皇家园林，琼华岛上的白塔倒映太液池，荡舟湖上可看天上夕阳染金。",
       scores=sc(nature=5, culture=4, photo=4, family=4, food=2, shopping=1, nightlife=1),
       style=["自然山水", "古韵文化"],
       hours=dict(open="06:30", close="21:00", note="含团城"), ticket="¥10"),
  dict(id="huofang-hutong", name="南锣鼓巷", district="东城区", type="food",
       tags=["胡同", "小吃", "文艺"], duration_min=90, lat=39.9360, lon=116.4040,
       desc="一条主巷八条鱼骨胡同，串起老北京的门墩、糖葫芦与文创小店，越夜越热闹。",
       scores=sc(food=5, photo=4, shopping=4, nightlife=3, culture=3, family=3, nature=1),
       style=["美食烟火", "潮玩都市"],
       hours=dict(open="10:00", close="22:30", note="周末人流最挤"), ticket="免费"),
  dict(id="shichahai", name="什刹海", district="西城区", type="nightlife",
       tags=["后海", "酒吧", "划船"], duration_min=120, lat=39.9400, lon=116.3820,
       desc="三海相连的老城水域，白天看杨柳拂堤、蹬船戏水，夜里沿湖酒吧灯火通明。",
       scores=sc(nightlife=5, nature=4, photo=4, food=4, family=3, culture=3, shopping=2),
       style=["夜景打卡", "自然山水"],
       hours=dict(open="00:00", close="24:00", note="酒吧街入夜开业"), ticket="免费"),
  dict(id="wangfujing", name="王府井步行街", district="东城区", type="shopping",
       tags=["百年商街", "小吃街", "地标"], duration_min=120, lat=39.9140, lon=116.4110,
       desc="老北京最负盛名的商业街，百货、老字号与美食一条街从早旺到晚。",
       scores=sc(shopping=5, food=5, photo=3, nightlife=3, family=4, culture=2, nature=1),
       style=["潮玩都市", "美食烟火"],
       hours=dict(open="10:00", close="22:00", note="步行街全天"), ticket="免费"),
  dict(id="summer-palace", name="颐和园", district="海淀区", type="nature",
       tags=["昆明湖", "万寿山", "长廊"], duration_min=240, lat=39.9990, lon=116.2750,
       desc="中国现存最大的皇家园林，昆明湖烟波 + 万寿山亭台，移步换景处处入画。",
       scores=sc(nature=5, culture=5, photo=5, family=4, food=2, shopping=1, nightlife=1),
       style=["自然山水", "古韵文化"],
       hours=dict(open="06:30", close="18:00", note="联票含园中园"), ticket="¥30 起"),
  dict(id="olympic-park", name="奥林匹克公园", district="朝阳区", type="photo",
       tags=["鸟巢", "水立方", "夜景"], duration_min=150, lat=39.9920, lon=116.3970,
       desc="鸟巢与水立方并肩的奥运主场馆区，入夜灯光璀璨，是北京最现代的打卡地。",
       scores=sc(photo=5, nightlife=5, family=5, shopping=3, food=3, culture=2, nature=2),
       style=["夜景打卡", "潮玩都市"],
       hours=dict(open="00:00", close="24:00", note="外场开放，场馆另售票"), ticket="免费"),
  dict(id="798-art", name="798 艺术区", district="朝阳区", type="photo",
       tags=["厂房loft", "画廊", "涂鸦"], duration_min=150, lat=39.9830, lon=116.4970,
       desc="国营电子厂厂房改造成的艺术区，巨型涂鸦与先锋画廊并存，文艺浓度极高。",
       scores=sc(photo=5, culture=4, shopping=3, nightlife=3, food=3, family=2, nature=1),
       style=["潮玩都市"],
       hours=dict(open="10:00", close="19:00", note="各展馆时间不一"), ticket="免费"),
  dict(id="yuyuantan", name="玉渊潭公园", district="海淀区", type="nature",
       tags=["樱花园", "西湖", "中央电视塔"], duration_min=150, lat=39.9180, lon=116.3120,
       desc="城中湖园，春天樱花开满半个湖岸，借景中央电视塔，是摄影与亲子好去处。",
       scores=sc(nature=5, family=5, photo=5, food=2, shopping=1, culture=1, nightlife=1),
       style=["自然山水", "亲子休闲"],
       hours=dict(open="06:00", close="21:00", note="樱花季人流量大"), ticket="¥2"),
  dict(id="beijing-zoo", name="北京动物园", district="西城区", type="family",
       tags=["大熊猫", "海洋馆", "亲子"], duration_min=180, lat=39.9380, lon=116.3330,
       desc="百年动物园，看大熊猫啃竹子、长颈鹿踱步，是带娃看动物世界的首选。",
       scores=sc(family=5, nature=4, photo=4, food=2, shopping=1, culture=1, nightlife=1),
       style=["亲子休闲", "自然山水"],
       hours=dict(open="07:30", close="18:00", note="海洋馆另售票"), ticket="¥15 起"),
  dict(id="yao-zhongzhou", name="钟鼓楼·时空胡同", district="东城区", type="culture",
       tags=["钟楼", "鼓楼", "老城"], duration_min=60, lat=39.9400, lon=116.3960,
       desc="北京城中轴线上的一对老建筑，登上鼓楼看灰瓦胡同向四面蔓延。",
       scores=sc(culture=5, photo=4, food=3, nightlife=2, family=3, shopping=2, nature=1),
       style=["古韵文化"],
       hours=dict(open="09:00", close="17:00", note="周一闭馆"), ticket="¥30"),
],
}


def main():
    os.makedirs(POI_DIR, exist_ok=True)
    for city, raw in POIS.items():
        bbox = BBOX[city]
        pois = []
        for p in raw:
            p = dict(p)
            x, y = grid_xy(bbox, p["lon"], p["lat"])
            p["x"] = x
            p["y"] = y
            p["images"] = images(CATS[city], p["name"], p.get("desc", ""))
            if not p.get("scores"):
                p["scores"] = sc()
            pois.append(p)
        doc = {
            "pois": pois,
            "note": "城市精选景点（%d 个）。scores 为七个偏好轴得分(0-5)；style 为 MBTI 风格分类；images 为站内图床链接。" % len(pois),
        }
        data_path = os.path.join(POI_DIR, city + ".json")
        static_path = os.path.join(STATIC_DIR, "pois-" + city + ".json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        # 离线包：去掉服务端附加字段（保留与渲染相关的字段即可），直接同构写入
        with open(static_path, "w", encoding="utf-8") as f:
            json.dump({"pois": pois}, f, ensure_ascii=False, indent=2)
        print("%s: %d 个 -> %s / %s" % (city, len(pois), data_path, static_path))


if __name__ == "__main__":
    main()