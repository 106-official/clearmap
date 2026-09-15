# ClearMap 更新日志

记录每次功能迭代的详细内容。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [cloud-app-preview-1.01] · 2026-09-15

### 新增（云端部署 + 设备定位）

- **后端正式部署到阿里云 ECS**：`47.99.131.169:9100`，托管服务 `systemd` 自启、崩溃自动拉起；`/api/health` 公网可达。存细分两个独立 service（`clearmap` 主 API），数据落盘服务器本地 `data/`。
- **真实短信验证码上线**：配置阿里云 RAM 子账号（仅 `AliyunDysmsFullAccess`）+ 短信认证产品（免资质签名/模板），手机号 `13****9756` 端到端验证码登录通过；未配置时仍回退调试码 `123456`。
- **跨域（CORS）修复**：打包 App/WebView 跨域请求云后端会被卡（`POST application/json` 触发预检），`api.py`/`server.py` 统一补 `Access-Control-Allow-Origin:*` 等头 + `do_OPTIONS` 预检处理；前端 `sendCode` 增 `.catch` 让网络异常改为可见提示而非静默无反应。
- **离线/内置 POI 兜底增强**：`/api/pois` 返回 `ok:true` 但空数组时同样回退随包内置 `pois-<city>.json`，并给无 `affinity` 的离线 POI 按 `scores` 均值补算，恢复地图「红=高契合 / 绿=常规」红绿圆点分层。
- **设备位置定位**：AndroidManifest 声明 `ACCESS_FINE/COARSE_LOCATION`；地图控件新增「定位到我的位置」按钮，`map.locate()` 把相机移到当前坐标并放大至街区级。
- 产出云端版成品：`dist/ClearMap-cloud-1.0.apk`（修复版）与 `dist/ClearMap-cloud-preview-1.01.apk`（本轮功能版），均签名 `clearmap2026`、内置云后端地址 `http://47.99.131.169:9100/`。

### 变更（地图 / 个人交互）

- **移除地图「选起点」**：删除地图下方起点条（`选起点` / `用我的位置` / 起点名）；纸飞机路线改为自动取「我的位置」作起点。
- **个人页改为非卡片资料**：资料从带边框卡片改为直接铺在背景上的文字区块（`.me-profile`，无边框）；标题变为动态「`[昵称]的旅行志`」（`meTitle`）；删除副标题「资料与随笔记事，都收在这」。

### 优化（拖拽顺滑度）

- `.map-view` 加 `will-change: transform`（已有 `touch-action:none`）；平移重建阈值 150→120px，建筑/道路潜带加宽，减少快速拖拽时边缘空白观感。

### 验证

- 前端 `app.js / map.js / render.js / store.js` 均通过 `node --check`；APK 内云端地址、affinity 逻辑、定位、GPS 权限均核验入包；签名 CN=ClearMap。

## [preview-1.23] · 2026-09-14

### 变更（登录策略与界面精简）

- **登录改为进入地图前的硬门槛**：首页移除「检测登录状态」按钮，仅保留「进入地图」；未登录点「进入地图」直接弹手机验证码注册/登录，且**不可跳过**（`openAuthModal(true)` 隐藏取消按钮、禁止点背景关闭）；登录成功后跳回地图。已登录态由 `localStorage` token 自动放行。
- **个人页精简**：移除「服务器 / 后端连接」「我的偏好」「账号」三张卡片，仅保留个人资料卡（头像 / 昵称 / 签名 / MBTI / 修改资料）。
- **随笔发布改独立页**：「写一篇随笔」变为按钮 → 跳转 `view-essay` 专注写作（文字 + 可选相册配图，最多 6 张），发布后返回个人；「我的随笔」改为嵌入式展示在个人资料卡下方（不单独成卡片）。
- **GPS 记录迁到行程页**：地图移除“实时 GPS 记录你的足迹…”默认文案；「行程」页新增「开始记录行程」按钮，点击自动切到地图开始 GPS 记录，记录中才显示地图下方的悬浮记录浮层（红点脉冲 + 采样数 + 停止保存）。

### 修复

- **SVG 底图切换后不显示**：地图视图 hidden 状态下面板尺寸为 0，渲染时 W/H 落最小值导致切到地图后视野错乱/空白；新增 `watchResize()`（ResizeObserver）在面板 0 → 实际尺寸变化时重算视口并 `fitToBox()` 复位，`showView("map")` 时另调 `map.refreshSize()` 兜底。
- **启动抛错导致功能失效**：修复 `essayGoBtn` / `essayBack`（随笔页导航）与 `recHud`（记录浮层显隐）原先未绑定的问题；移除 boot 中已不存在的 `refreshAuthUi()` 调用与失效的 `goRecord` 绑定，避免 `ReferenceError` / `TypeError` 中断初始化。
- **记录浮层无样式**：新增 `.rec-hud` 悬浮条样式（含记录脉冲动画），并补 `.btn-essay-go` / `.me-myessays` 嵌入式随笔样式。

### 文档

- `README.md`：版本历史、登录策略、部署（「服务器/后端连接」卡已移除）、使用说明同步更新。
- `docs/LOCAL_SERVER.md`：第 6 步改为「打包期指定后端地址」，说明离线模式行为。
- `CHANGELOG.md`：新增本条。

### 验证

- 前端四模块 `node --check` 语法校验通过；`Git` 已同步。

## [1.7.0] · 2026-09-14

### 新增（多城市 + 安卓封装准备）

- **多城市地图支持**：`scripts/build_map.py` 重构为城市参数化，`python build_map.py <city>` 可选 `changsha / shanghai / beijing`，内置各自 BBOX、行政区、分块与输出名；道路/建筑抓取改为**分块**（避免超大单次请求被 Overpass 截断），并新增 `build_cache/` 磁盘缓存（中断后可复用已抓取数据），`fetch()` 对 `IncompleteRead`/`504` 自动换镜像 + 指数退避重试。
- 前端**城市切换器**：[map.js](static/js/map.js) 新增 `setCity()`/`getCity()` 按城市缓存加载 `/map/<city>.json`；[app.js](static/js/app.js)+[index.html](static/index.html) 地图右上角新增城市下拉（长沙/上海/北京）；[style.css](static/css/style.css) 新增城市选择器样式。
- **安卓封装（Capacitor）**：新增 `mobile/` 工程，可用 `gradlew assembleRelease` 产出**签名 Release APK**（`com.clearmap.app`，minSdk 24 / targetSdk 36，签名 `clearmap-release.keystore`，密码见 `mobile/README.md`）；[store.js](static/js/store.js) 新增 `CLEARMAP_API_BASE` 后端地址开关（Web 同源不动，APK 时指向线上后端）；[app.js](static/js/app.js) 新增**离线兜底**：后端不可达时自动读取随包内置的 `static/pois.json`（由 `data/poi/changsha.json` 导出 55 个景点），保证无后端时地图仍显示景点。已产出成品 APK 至 `dist/ClearMap-v1.0-release.apk`（84.8MB，签名校验通过）。
- 状态：上海/北京核心城区矢量底图后台构建中（上海道路 34,902 条已抓取）。

## [1.6.1] · 2026-09-13

### 调整（界面打磨）

- **景点红绿圆点换用「水墨纸感柔和版」配色**：常规点由亮绿改为柔和青玉 `#5b8570`，高契合点由亮红改为柔和赭红 `#a8584a`；虚线环与圆点降低透明度更添水墨质感（仍保留「虚线圆环 + 实心圆点」设计，选中态转白实线 + 深河绿）。
- **红绿圆点增加「按契合度分层」显示**：地图拉远（`upx > 12`）时只显示红色(高契合/重点)圆点，放大到 `upx ≤ 12` 后绿色(常规)圆点才出现，与道路/建筑的分层 LOD 风格一致。
- **修复道路名重复显示并重叠**：根因是同一道路的几何在 tier1/tier2 及各分段中重复出现，之前会对同一路名标注多条、近处文字彼此重叠（实测存在 1081 组 midpoint 接近的重复标注）。现按**路名去重**，每个路名仅标注一次，消除叠加文字。

### 移除

- 删除底部栏 `<footer class="colophon">` 及其文案「ClearMap · 城市地图与个性化行程推荐 —— POI 单一数据源 · 推荐引擎 · 数据本地存储」，并移除对应 `.colophon` 样式。

### 验证

- `tests/selftest.py`：646 项检查，失败 0，ALL GREEN。
- 四个前端 JS（map.js / app.js / store.js / render.js）均通过 `node --check` 语法校验；HTTP 服务实时返回更新后的静态资源（页脚已无、配色/分层/路名去重均已生效）。

## [1.6.0] · 2026-09-13

本次更新包含三大改动：地图标识还原、点击侧栏修复、手机号登录 + 阿里云云同步。

### 新增

- **手机号验证码登录 / 注册**
  - `auth.py`：验证码生成（6 位）、发送节流（60 秒/次）、有效期 5 分钟（TTL）、最多尝试 5 次；注册/登录复用账号映射；token 会话持久化（默认 30 天）。
  - 阿里云短信接入（`dysmsapi.aliyuncs.com` RPC 签名）：未配置时回退为固定调试码 `123456`，便于本地联调。
  - 新接口：`POST /api/sms`、`POST /api/auth/login`、`POST /api/auth/logout`、`GET /api/auth/me`。
  - token 鉴权：所有参考接口支持用 `?token=` 取代 `?user=` 定位当前用户，未带 token 时退回 guest。
  - 前端：顶栏「登录」按钮 + 手机号验证码弹窗、60s 倒计时、登录后显示脱敏手机号、点击退出；登录状态用 `localStorage` 持久化。

- **阿里云云同步（个人信息存云端）**
  - `cloud.py`：`push()` 每次落盘后推送用户数据到远端，`pull()` 本地缺失时从云端恢复；网络异常静默降级，绝不阻塞本地写。
  - `deploy/cloud_server.py`：零依赖、标准库实现的云同步服务端，可部署到阿里云 ECS（`GET/POST ?token=KEY&user_id=` 拉取/推送，密钥不符 403）。
  - 配置：`config.py` 新增 `SMS_ALIYUN`、`SMS_*`、`CLOUD_SYNC_URL`、`CLOUD_SYNC_KEY`、`SESSION_TTL`，均为可开关项。

### 修复

- **地图景点标识还原**：把缩放后变成的「定位图钉」还原为原设计——绿/红圆点 + 虚线包围（红色用于高契合推荐景点、绿色用于常规），选中态圆点转白色实线，恒定屏幕尺寸。
- **点击景点无侧栏**：根因是 `setPointerCapture` 把派生的 click 事件目标夺到容器导致子级点击监听失效；改用 `elementFromPoint` + `closest(".poi-marker")` 拾取命中点，非拖拽点击景点即触发 `onClick`，侧栏（图片 + 介绍）正常弹出。

### 变更

- `store.js`：API 客户端重构为 token 优先（`qs()` 生成认证查询串），新增 `sms` / `login` / `logout` / `authMe` 方法。
- `api.py`：新增认证处理函数与路由；`query_id()` 支持 token 解析。
- `server.py`：无需改动（`do_POST` 已透传 body 到 `api.route`）。
- `data.py`：`ensure_user` 支持云端恢复，`save_user` 落盘后调用 `cloud.push`。
- `README.md`：项目结构、API 表、账号与云同步使用说明同步更新。

### 测试

- `tests/selftest.py` 新增「认证 / 账号」小节（10 项）：发送验证码、登录返回 token、会话绑定手机号、token 解析登录用户、token 鉴权写资料、错误验证码拒绝、超次数拒绝、退出登录、退出后 token 失效、非法手机号拒绝。
- 自检结果：**646 项检查，失败 0，ALL GREEN**。

### 待办（尚未配置）

- [ ] 用户提供阿里云 ECS 公网地址后，将 `CLOUD_SYNC_URL` 与 `CLOUD_SYNC_KEY` 填入 `config.py`。
- [ ] 将 `deploy/cloud_server.py` 部署到阿里云 ECS（设置强密钥 `CLEARMAP_CLOUD_KEY`，建议配 HTTPS 反代），并做连通验证。
- [ ] 暂用调试码 `123456` 联调；用户提供阿里云短信凭证（AccessKeyId/Secret、签名、模板 Code）后再开启真实短信。