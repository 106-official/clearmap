# ClearMap · 长沙

> 把一座城市，走成自己的样子。

ClearMap 是一个基于 OpenStreetMap 数据的城市地图与个性化行程推荐 Web 应用。以长沙为首座城市，提供真实地理坐标的 SVG 交互地图、基于偏好的景点推荐、MBTI 性格匹配、贪心行程编排、公交地铁换乘规划，以及 GPS 轨迹记录与旅行打卡等功能。

后端使用 Python 标准库零第三方依赖实现，前端为原生 HTML/CSS/JavaScript，开箱即用。

## 功能特性

- **真实城市地图** — 基于 OSM 数据的 SVG 矢量地图，Web Mercator 投影，支持拖拽平移、滚轮缩放、LOD 分层渲染（道路 4 级细节、建筑网格分块惰性加载）
- **7 维偏好推荐** — 自然山水 / 历史人文 / 美食风味 / 逛街购物 / 夜生活 / 亲子休闲 / 网红打卡，加权打分排序
- **MBTI 性格推荐** — 16 型人格与景点风格匹配，按性格画像推荐契合去处
- **行程编排** — 贪心算法按时长预算（半日 4h / 全天 8h / 慢游 12h）编排，最近邻重排成顺路路线
- **换乘路线规划** — 步行-公交-地铁混合 Dijkstra 最短路径，大圆距离 + 换乘惩罚 + 步行接驳建模
- **GPS 轨迹记录** — 实时 `watchPosition` 记录足迹，GPS 不可用时降级为地图点选模式
- **旅行打卡** — 照片上传 + GPS 定位 + 关联景点，支持删除管理
- **个人中心** — 头像、昵称、签名、MBTI 认证、收藏、行程保存
- **数据本地持久化** — JSON 文件原子写入，防御式异常处理，无外部数据库

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Python 3 标准库 | `http.server` / `json` / `heapq` / `math` / `uuid` / `base64`，零第三方依赖 |
| 前端 | 原生 HTML / CSS / JS | 无框架，4 个 JS 模块（store / map / render / app） |
| 地图引擎 | 自研 SVG | Web Mercator 投影，LOD 分层渲染，建筑网格分块 |
| 路径规划 | Dijkstra | 大圆距离 + 换乘惩罚 + 步行接驳 |
| 数据存储 | JSON 文件 | 原子写入（先写 .tmp 再 rename），防御式异常 |
| 地图数据源 | OpenStreetMap | 由 `scripts/build_map.py` 构建为 `changsha.json` |

## 项目结构

```
clearmap/
├── app.py                 # 入口：python app.py [端口]
├── 启动.bat                # Windows 一键启动脚本
├── server.py              # HTTP 服务层（路由分发 + 静态资源服务）
├── api.py                 # REST API 业务处理
├── config.py              # 全局配置（路径、偏好维度、行程参数、MBTI 定义）
├── data.py                # 数据层：POI 单一数据源 + 用户 JSON 持久化
├── recommend.py           # 推荐引擎：加权打分 + 贪心行程编排
├── route.py                # 换乘路线引擎：Dijkstra 最短路径
├── data/
│   ├── poi/changsha.json  # POI 景点数据（50+ 景点）
│   └── users/             # 用户数据（JSON 持久化）
├── scripts/
│   ├── build_map.py       # 从 OSM 生成地图矢量数据
│   ├── build_pois.py      # 构建 POI 数据
│   ├── build_transit.py   # 构建公交/地铁站点线路数据
│   ├── fetch_poi_photos.py # 获取景点照片
│   └── geocode_pois.py    # 地理编码 POI
├── static/
│   ├── index.html         # 主页面（地图 / 偏好 / 行程 / 我的 四视图）
│   ├── css/style.css      # 样式
│   ├── js/
│   │   ├── store.js       # API 客户端 + 全局状态
│   │   ├── map.js         # SVG 地图引擎
│   │   ├── render.js      # DOM 渲染层
│   │   └── app.js         # 事件编排 + 视图切换
│   ├── map/
│   │   ├── changsha.json  # 地图矢量数据（道路/建筑/水系/区界）
│   │   └── transit.json   # 公交/地铁数据
│   └── media/pois/        # 景点照片
└── tests/
    └── selftest.py        # 接受性自检（数据完整性 + 推荐引擎 + API 路由）
```

## 快速开始

### 环境要求

- Python 3.8+
- 现代浏览器（Chrome / Edge / Firefox）

### 安装

无需安装任何第三方依赖，克隆后直接运行：

```bash
git clone https://github.com/Kaiibye/clearmap.git
cd clearmap
```

### 启动

**方式一：命令行**

```bash
python app.py          # 默认端口 9100
python app.py 8080     # 指定端口
```

**方式二：Windows 双击**

双击 `启动.bat`，浏览器会自动打开 `http://127.0.0.1:9100`。

启动后在浏览器访问 `http://127.0.0.1:9100` 即可使用。

### 运行测试

```bash
python tests/selftest.py
```

自检脚本验证：POI 数据完整性、推荐引擎排序、行程预算约束、全部 API 路由、换乘数据可用性、地图数据结构与投影正确性。

## 使用说明

### 地图视图

- 滚轮缩放、拖拽平移地图
- 点击景点图钉查看详情（图片、描述、开放时间、门票、契合度）
- 点击「纸飞机」图标规划前往该景点的换乘路线
- 在底部工具栏选择起点（地图点选或 GPS 定位），开始/结束 GPS 轨迹记录

### 偏好设置

- 拖动 7 条标尺设置偏好权重（0-5），地图推荐实时刷新

### 行程编排

- 选择时长档位（半日 / 全天 / 慢游），点击「编排行程」
- 系统按偏好打分贪心装入，再用最近邻重排成顺路路线
- 可保存行程到个人中心

### 个人中心

- 上传头像、设置昵称与签名
- 选择 MBTI 性格类型，获得专属推荐
- 上传旅行打卡照片（关联景点 + GPS 定位）
- 查看与删除已记录的 GPS 轨迹路线

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET | `/api/meta` | 城市元信息 |
| GET | `/api/pois` | 全部景点（含推荐打分） |
| GET | `/api/recommend` | 推荐景点 |
| GET | `/api/itinerary/{budget}` | 行程编排 |
| GET | `/api/profile` | 用户偏好 |
| POST | `/api/profile` | 更新偏好 |
| GET | `/api/me` | 个人资料 |
| POST | `/api/me` | 更新资料 |
| POST | `/api/avatar` | 上传头像 |
| POST | `/api/checkin` | 旅行打卡 |
| DELETE | `/api/checkin/{id}` | 删除打卡 |
| POST | `/api/route` | 保存 GPS 路线 |
| DELETE | `/api/route/{id}` | 删除路线 |
| POST | `/api/plan` | 保存行程 |
| POST | `/api/favorite/{poi_id}` | 收藏/取消收藏 |
| GET | `/api/mbti-recs` | MBTI 专属推荐 |
| GET | `/api/transit` | 公交/地铁数据概况 |
| POST | `/api/route-plan` | 换乘路线规划 |

所有接口返回 `{"ok": true/false, ...}` 结构，异常不会 500 裸奔。

## 数据来源

- **地图矢量数据**：[OpenStreetMap](https://www.openstreetmap.org/) — 道路、建筑、水系、行政区划，由 `scripts/build_map.py` 投影为局部坐标后落盘
- **公交/地铁数据**：站点与线路信息，由 `scripts/build_transit.py` 构建
- **景点数据**：50+ 个长沙景点，含坐标、描述、风格标签、偏好评分、开放时间、门票等
- **景点照片**：由 `scripts/fetch_poi_photos.py` 获取，存储于 `static/media/pois/`

## License

[MIT](LICENSE)
