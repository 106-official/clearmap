# ClearMap · 长沙

> 把一座城市，走成自己的样子。

ClearMap 是一个基于 OpenStreetMap 数据的城市地图与个性化行程推荐 Web 应用。以长沙为首座城市，提供真实地理坐标的 SVG 交互地图、基于偏好的景点推荐、MBTI 性格匹配、贪心行程编排、公交地铁换乘规划，以及 GPS 轨迹记录与旅行打卡等功能。

后端使用 Python 标准库零第三方依赖实现，前端为原生 HTML/CSS/JavaScript，开箱即用。

## 版本历史

```
## cloud-app-preview-1.01 (2026-09-15)
- 云端部署：后端正式上线阿里云 ECS（47.99.131.169:9100，systemd 自启），真实短信验证码登录端到端通过
- 修复：WebView 跨域请求被后端 CORS 拦导致「获取验证码」无反应（补 CORS 头 + OPTIONS 预检）
- 地图：红绿景点恢复（离线 POI 空数组回退 + 补算 affinity 分层）；新增「定位到我的位置」按钮（设备定位权限）
- 移除：地图「选起点」起点条；纸飞机路线改为自动取「我的位置」
- 个人：资料改为无边框背景文字区块；标题变「[昵称]的旅行志」；删副标题
- 优化：拖拽顺滑（will-change / 平移重建阈值 120px / 潜带加宽）
- 产出：dist/ClearMap-cloud-1.0.apk 与 dist/ClearMap-cloud-preview-1.01.apk（签名 clearmap2026，内置云后端地址）

## preview-1.23 (2026-09-14)
- 登录策略：首页移除「检测登录状态」按钮；未登录点「进入地图」直接弹手机验证码注册/登录（不可跳过）
- 修复：地图视图 hidden 状态下 SVG 底图尺寸为 0 导致切换后不显示（ResizeObserver + showView 时重算视口复位视野）
- 地图：移除“实时 GPS 记录你的足迹…”默认文案；GPS 记录入口迁到「行程」页，记录中才显示悬浮记录浮层
- 个人：移除「服务器/后端连接」「我的偏好」「账号」三张卡片，仅保留个人资料卡
- 随笔发布改为按钮 → 跳转独立发布页（文字 + 相册配图）；「我的随笔」改为嵌入式展示在个人资料卡下方
- 修复：随笔页导航按钮/记录浮层此前未绑定、以及残留的 refreshAuthUi 调用，均会导致启动抛错
- 文档：README / CHANGELOG / docs/LOCAL_SERVER 同步更新

## preview-1.22 (2026-09-14)
- 新增：地图双指缩放 / 全屏沉浸（非卡片，覆盖上下栏以外全区域）
- 新增：底部「发现」栏（指南针图标）+ 旅游随笔发布 / 发现流
- 修复：点击地图红/绿点无法弹出景点详情
- 更新：底部「个人中心」更名「个人」
- 移除：行程半日/全天/慢游预算按钮，改为打卡 + 路线记录归档
- 文档：新增 docs/LOCAL_SERVER.md 详细部署、docs/DOC_STANDARD.md 维护标准
```

## 功能特性

- **移动端 App** — Capacitor 封装为安卓 APK；底部四栏导航（地图 / 行程 / 发现 / 个人），打开先见**首页落地页**（品牌引言 + 登录状态），无需云服务器、可离线浏览地图
- **真实城市地图** — 基于 OSM 数据的 SVG 矢量地图，Web Mercator 投影，全屏沉浸，支持单指拖拽平移、滚轮 / **双指**缩放、LOD 分层渲染（道路 4 级细节、建筑网格分块惰性加载），交互丝滑、GPU 加速
- **旅游随笔 / 发现** — 「个人」页发布随笔（文字 + 可选相册配图），聚合到「发现」页按时间流展示，可删除自己的随笔
- **7 维偏好推荐** — 自然山水 / 历史人文 / 美食风味 / 逛街购物 / 夜生活 / 亲子休闲 / 网红打卡，加权打分排序
- **MBTI 性格推荐** — 16 型人格与景点风格匹配，按性格画像推荐契合去处
- **行程打卡 / 记录归档** — 「行程」页保留打卡与 GPS 路线记录，可在行程界面查看归档（记录路线 + 打卡景点）
- **换乘路线规划** — 步行-公交-地铁混合 Dijkstra 最短路径，大圆距离 + 换乘惩罚 + 步行接驳建模
- **GPS 轨迹记录** — 实时 `watchPosition` 记录足迹，GPS 不可用时降级为地图点选模式
- **旅行打卡** — 照片上传 + GPS 定位 + 关联景点，支持删除管理
- **个人中心** — 头像、昵称、签名、MBTI 认证、收藏、随笔发布（进入「个人」栏）
- **数据本地持久化** — JSON 文件原子写入，防御式异常处理，无外部数据库

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Python 3 标准库 | `http.server` / `json` / `heapq` / `math` / `uuid` / `base64`，零第三方依赖 |
| 前端 | 原生 HTML / CSS / JS | 无框架，4 个 JS 模块（store / map / render / app） |
| 地图引擎 | 自研 SVG | Web Mercator 投影，LOD 分层渲染，建筑网格分块 |
| 路径规划 | Dijkstra | 大圆距离 + 换乘惩罚 + 步行接驳 |
| 数据存储 | JSON 文件 | 原子写入（先写 .tmp 再 rename），防御式异常 |
| 地图数据源 | OpenStreetMap | 由 `scripts/build_map.py` 构建为 `<city>.json`（长沙/上海/北京） |

## 项目结构

```
clearmap/
├── app.py                 # 入口：python app.py [端口]
├── 启动.bat                # Windows 一键启动脚本
├── server.py              # HTTP 服务层（路由分发 + 静态资源服务）
├── api.py                 # REST API 业务处理
├── config.py              # 全局配置（路径、偏好维度、行程参数、MBTI 定义、短信/云同步）
├── auth.py                # 认证层：短信验证码 + 注册登录 + token 会话
├── cloud.py               # 云同步层：个人信息推送/拉取阿里云
├── data.py                # 数据层：POI 单一数据源 + 用户 JSON 持久化
├── recommend.py           # 推荐引擎：加权打分 + 贪心行程编排
├── route.py                # 换乘路线引擎：Dijkstra 最短路径
├── deploy/
│   ├── cloud_server.py     # 云同步服务端（部署到远端主机，零依赖）
│   └── start_laptop.bat    # 常开笔记本启动脚本（监听 0.0.0.0，供局域网/端口映射访问）
├── docs/
│   ├── API.md               # 完整的接口方案（请求/响应/认证/状态码）
│   ├── LOCAL_SERVER.md      # 本地/常开笔记本部署 & App 配置后端的详细步骤
│   └── DOC_STANDARD.md      # 项目文档维护规范（后续完善文档必须遵守）
├── data/
│   ├── poi/changsha.json  # POI 景点数据（50+ 景点）
│   ├── users/             # 用户数据（JSON 持久化）
│   ├── accounts.json      # 手机号 -> user_id 映射
│   └── sessions.json      # token -> user_id 会话（持久化）
├── scripts/
│   ├── build_map.py       # 从 OSM 生成地图矢量数据
│   ├── build_pois.py      # 构建 POI 数据
│   ├── build_transit.py   # 构建公交/地铁站点线路数据
│   ├── fetch_poi_photos.py # 获取景点照片
│   └── geocode_pois.py    # 地理编码 POI
├── static/
│   ├── index.html         # 主页面（首页 + 地图 / 行程 / 我的 三视图）
│   ├── css/style.css      # 样式
│   ├── js/
│   │   ├── store.js       # API 客户端 + 全局状态
│   │   ├── map.js         # SVG 地图引擎
│   │   ├── render.js      # DOM 渲染层
│   │   └── app.js         # 事件编排 + 视图切换
│   ├── map/
│   │   ├── changsha.json  # 地图矢量数据（长沙 · 道路/建筑/水系/区界）
│   │   ├── shanghai.json  # 地图矢量数据（上海 · 核心城区）
│   │   ├── beijing.json   # 地图矢量数据（北京 · 城六区）
│   │   └── transit.json   # 公交/地铁数据
│   └── media/pois/        # 景点照片
├── mobile/
│   ├── package.json       # Capacitor 安卓封装
│   ├── capacitor.config.json
│   └── README.md          # APK 打包步骤
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
git clone https://github.com/106-official/clearmap.git
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

### 部署到"常开笔记本"（替代云服务器）

如果你的那台笔记本常开、且开启了**路由器端口映射 / 公网访问**，可直接把它当后端主机：

1. 在笔记本上安装 Python 3.8+（或直接使用本项目所在机器的 Python 环境）。
2. 双击 `deploy/start_laptop.bat`——它会以 `0.0.0.0` 监听（默认端口 `9100`），局域网 / 端口映射后的公网均可访问。
3. 放行 Windows 防火墙入站 `9100` TCP；在路由器设置"端口映射"（公网端口 → 笔记本内网 IP:9100）。
4. 手机 App 对接后端：preview-1.23 起，「个人」页已精简**不再显示「服务器 / 后端连接」设置卡片**。后端地址改由打包期指定（`store.js` 的 `clearmap_api_base`）并持久化于 `localStorage`；未配置时 App 以离线模式运行（底图/景点可用，登录/打卡/随笔等需后端的功能停用）。

> 备份该笔记本数据目录 `data/` 即可实现账号 / 打卡 / 路线等数据迁移。

### 部署到阿里云 ECS（云端正式版）

当前 `dist/ClearMap-cloud-*.apk` 已内置云端后端地址 `http://47.99.131.169:9100/`，后端即在阿里云 ECS 上运行：

1. 上传 `server.py / api.py / auth.py / data.py / recommend.py / cloud.py / config.py` 等后端源码到服务器（如 `/opt/clearmap/`）。
2. 服务器 `config.py` 设 `HOST=0.0.0.0`（监听所有网卡，默认 `9100`），并填齐 `SMS_ALIYUN` 四项启用真实短信。
3. 用 `systemd` 托管常驻（开机自启、崩溃自动拉起）：见服务器 `/etc/systemd/system/clearmap.service`（ExecStart 指向 `python3 server.py`）。
4. **阿里云安全组**放行入方向 TCP `9100`（`0.0.0.0/0`）；后端已带 CORS 头，WebView/浏览器跨域可正常调用。
5. 校验 `curl http://47.99.131.169:9100/api/health` 返回 `{"ok": true, ...}`。
6. 用户数据（账号/随笔/打卡/行程）落盘服务器本地 `data/`，建议配置每日备份。

### 运行测试

```bash
python tests/selftest.py
```

自检脚本验证：POI 数据完整性、推荐引擎排序、行程预算约束、全部 API 路由、换乘数据可用性、地图数据结构与投影正确性。

## 使用说明

### 地图视图

- 滚轮缩放、拖拽（单指）平移、双指缩放
- 右上角切换城市底图（长沙 / 上海 / 北京）
- 点击景点图钉查看详情（图片、描述、开放时间、门票、契合度）
- 点击「纸飞机」图标规划前往该景点的换乘路线
- 底部工具栏「选起点」（地图点选 ◎ 或 GPS 定位），用于纸飞机路线规划

### 行程页（打卡 + 足迹）

- 「足迹路线」卡点击「开始记录行程」→ 自动切到地图并用 GPS 画下足迹，点「停止并保存」结束，回到行程页查看归档
- GPS 不可用时自动降级为地图点选模式
- 「行程打卡」关联景点上传照片，点亮旅程

### 个人

- 上传头像、设置昵称与签名、选择 MBTI 性格
- 点「写一篇随笔 →」进入独立发布页（文字 + 相册配图），发布后聚合到「发现」页
- 个人资料卡下方嵌入式展示「我的随笔」，可删除自己发布的随笔

## API 接口

> 完整接口方案（含请求/响应示例、认证、状态码、安全说明）见 **[docs/API.md](docs/API.md)**。下表为速查。

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
| POST | `/api/sms` | 发送手机验证码 |
| POST | `/api/auth/login` | 手机号验证码登录/注册 |
| POST | `/api/auth/logout` | 退出登录 |
| GET | `/api/auth/me` | 当前登录用户信息 |

所有接口返回 `{"ok": true/false, ...}` 结构，异常不会 500 裸奔。

### 账号与云同步

- **登录（强制进入地图前完成）**：打开 App 先落在**首页**，首页仅一个「进入地图」按钮（无登录态检测按钮）。未登录点「进入地图」会直接弹**手机验证码注册/登录**，且**不可跳过**——只有登录成功才能进入地图；已登录状态由 `localStorage` 的 token 自动保持，直接放行。
- **本地持久化**：登录 token 存于 `localStorage("clearmap_token")`，有效 30 天，无需频繁重复登录；账号、打卡、路线等数据由笔记本后端 `data/` 目录持久化。
- **短信**：未配置阿里云短信时验证码为固定调试码 `123456`（仅联调）；在 `config.py` 的 `SMS_ALIYUN` 填齐 **AccessKeyId / AccessKeySecret / 短信签名 / 模板 Code** 后即启用真实短信（阿里云短信接口已在 `auth.py` 实现）。
- **云同步（可选）**：把 `deploy/cloud_server.py` 部署到远端主机并设强密钥 `CLEARMAP_CLOUD_KEY`，然后在 `config.py` 填 `CLOUD_SYNC_URL` 与 `CLOUD_SYNC_KEY`。配置生效后个人数据可推送/恢复（尽力而为，不阻塞本地写）。若直接用常开笔记本后端，则无需云同步。

## 数据来源

- **地图矢量数据**：[OpenStreetMap](https://www.openstreetmap.org/) — 道路、建筑、水系、行政区划，由 `scripts/build_map.py` 投影为局部坐标后落盘
- **公交/地铁数据**：站点与线路信息，由 `scripts/build_transit.py` 构建
- **景点数据**：50+ 个长沙景点，含坐标、描述、风格标签、偏好评分、开放时间、门票等
- **景点照片**：由 `scripts/fetch_poi_photos.py` 获取，存储于 `static/media/pois/`

## License

[MIT](LICENSE)
