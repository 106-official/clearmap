# ClearMap 更新日志

记录每次功能迭代的详细内容。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [1.04 修复] · 2026-09-17（不升级版本号，覆盖 cloud-app-preview-1.04）

### 修复

- **行程「相册/邮戳」打卡照片仍不显示**：`renderAlbum` 的打卡照片 `c.img` 由后端返回 `/api/media?...` 相对路径，之前未拼 `API_BASE` 导致 WebView 相对本地资源 404。已改经 `avatarUrl()` 统一补全，行程相册/邮戳卡片照片恢复显示；随笔配图、发现流他人配图与头像沿用同一归一化逻辑，一并确认可用。

### 精简

- **后端无用代码整理**：按「前端已不再调用」为据审慎清理已死的端点与函数——
  - `api.py`：移除 `GET /api/meta`、`GET /api/recommend`、`GET /api/itinerary/{budget}`、`GET /api/transit`、`POST /api/profile`、`POST /api/plan` 六条路由及其函数 `meta / recommend_api / itinerary / save_plan / update_profile / transit_meta`；`GET /api/profile`（读偏好）、`POST /api/route-plan`、`/api/essay`、`/api/feed` 等仍被前端使用的接口原样保留。
  - `data.py`：删除仅为上述死接口服务的 `update_profile`、`add_plan`。
  - `store.js`：删除无调用的 `meta / itinerary / savePlan / saveProfile / transit` 方法（保留 `profile` 读、`me`、`health`、`auth`、`essay`、`feed` 等）。
  - `app.js`：删除死函数 `generateItinerary` / `savePlan` 及闲置变量 `currentItinerary` / `currentBudget`；保留仍在用的 `loadProfile`。

### 核验（无损害）

- `api.py`、`data.py` 通过 `python -m py_compile`；`tests/selftest.py` 已同步移除对已删端点的用例（改为断言 404）、token 鉴权改测存活接口，整跑 `ALL GREEN — 验收通过`。
- `store.js / app.js / render.js / map.js` 通过 `node --check`；全库检索确认已删端点/函数无残留引用。
- `docs/API.md`、`README.md` 接口速查表同步移除已删端点。
- `assembleRelease`（`-x lint`）构建成功，内置云后端 `http://47.99.131.169:9100/`、签名 `clearmap2026`。
- 成品：`dist/ClearMap-cloud-preview-1.04.apk`（覆盖旧 1.04，版本号不变）。

## [cloud-app-preview-1.04] · 2026-09-16

### 修复

- **随笔/发现配图无法显示**：随笔图片与发现流里的配图、作者头像由后端返回 `/api/media?...` 相对路径，在 APK（WebView 相对本地资源解析）中会 404 空图。`render.js` 的 `renderMyEssays / renderFeed / restore` 改经 `avatarUrl()` 统一把相对路径自动拼上 `API_BASE`，我的随笔配图、发现流他人配图与头像均可正常显示。
- **选点详情全屏展示**：`.poi-pop` 由居中悬浮小卡片改为真正的全屏独立页面（透明虚化 → 整页纸色 + 右上 sticky 关闭按钮 + 内容内滚 `overscroll-behavior:contain`），点击红绿景点后整屏呈现，不再是小卡片。
- **行程页删除景点选择**：打卡表单移除景点下拉「选择区」，打卡地点由地图「在此打卡」自动确定；随按钮收起详情页并跳转行程。
- **「关联的景点不存在」修复**：打卡原来从可能为空的 `checkinPoi` 下拉取值导致 `poi_id` 为空/不匹配；现在直接使用地图传来的 `pendingCheckinPoi`（必为真实景点 id），并校验 `state.pois` 命中，未选景点时给出明确提示。

### 验证
- `app.js / render.js / map.js` 通过 `node --check`；`assembleRelease` 构建成功（`-x lint`），内置云后端 `http://47.99.131.169:9100/`、签名 `clearmap2026`。
- 成品：`dist/ClearMap-cloud-preview-1.04.apk`。

## [cloud-app-preview-1.03] · 2026-09-16

### 地图（顺滑 / 景点分层 / 选点详情）

- **进一步消除卡顿与延迟**：`setTransform` 由逐帧设置 SVG `transform` 属性 + 刷新 `--unit` 自定义属性，改为走 CSS `transform`（配合 `.map-view` 的 `will-change` 走 GPU 合成），并把道路宽度用的 `--unit` 移到全量重建时才更新——拖拽、双指捏合与按钮缩放不再每帧触发样式重算/回流，缩放平移更跟手、低延迟。
- **红绿景点分层显示**：整城视野默认只显示红色重点（高契合）且自动“抽稀拉开间距”避免拥挤成团；绿色常规点需放大到街区级 `allUpx=2` 才浮现；选中点始终可见（`renderMarkers` 增加抗拥挤的 `kept` 间距过滤）。
- **选点详情改为虚化独立页面**：不再以底部栏弹出，改为全屏居中悬浮卡片（`blur(10px)` 虚化背景 + `fadeIn/rise` 动效），关闭按钮在右上，操作按钮在卡片内、四周留白，`z-index:80` 盖过底部标签栏，不再被遮挡。

### 个人（默认头像 / 头像保存 / 随笔版面）

- **默认头像 SVG**：无头像时显示简约人物剪影（内联 SVG）+ 右下“＋”，不再出现“损坏图片方框”；图片加载失败也会自动回退到剪影。
- **头像上传更新修复**：`renderProfile` 新增 `avatarUrl()`，把云端返回的相对路径自动拼接上 `API_BASE`（绝对 URL / data 原样保留），上传后头像即时刷新显示；登录态经 `localStorage` 持久化，覆盖安装（同签名）更新不丢用户信息。
- **发布随笔版面重设计**：去掉简单按钮/输入框，改为深绿色水墨渐变 Hero（卷角牌匾质感）+ 衬线大字标题 + 仿纸笺书写区（无框大号手写输入 + 卡片化配图预览）+ 底部虚线分隔的发布底栏。

### 验证
- `app.js / render.js / map.js` 通过 `node --check`；`assembleRelease` 构建成功（`-x lint`），内置云后端 `http://47.99.131.169:9100/`、签名 `clearmap2026`。
- 成品：`dist/ClearMap-cloud-preview-1.03.apk`。

## [cloud-app-preview-1.02] · 2026-09-16

### 变更（地图 / 行程 / 个人页面重构）

- **道路分层分级显示（LOD）**：`map.js` 各档道路由“整城视野全显”改为分级——默认整城视野只显示最深的干道 `road-t1`，较浅的 `road-t2` 需放大后才浮现，更细的 `road-t3/t4` 依次在更高放大倍数才出现，避免初始视野道路堆叠。
- **定位按钮避开底部栏**：`.map-controls` 由 `bottom:14px` 上移至 `bottom:104px`，不再被固定底栏遮挡；修复定位按钮“点不到/点击后无反应”。
- **行程页重构为相册/邮戳卡片墙**：`view-plan` 重构为单屏布局——顶部「开始记录行程 / ＋加一张打卡」工具条 + 打卡小表单（默认收起，可展开/随「在此打卡」自动弹出）+ 打卡照片卡与足迹路线卡**交叉排列**成 2 列卡片网格（`render.renderAlbum`），整页不滚动，卡片溢出时仅在卡片区内滚动；删除原「记录一段足迹、打卡一处风景…」文案。
- **修复「开始记录行程」无响应**：点击即弹 toast 引导并切到地图开始 GPS 记录，避免按钮处于底栏遮挡区。
- **个人页改为 O= 形布局**：左侧滑圆头像（整体左移），右侧为无边框铺底文字——名称行（名称输入 + 右侧 MBTI 小徽标）+ 个性签名，均为直接显示在背景上的透明输入，不再是按钮/卡片；删除 MBTI 大按钮块与「写一篇随笔」按钮；「写一篇随笔」迁入「我的随笔」表头右侧。
- **删除按钮蓝色聚焦框**：全局 `:focus / :focus-visible { outline: none }` + `-webkit-tap-highlight-color: transparent`，移除点击出现的蓝色矩阵框。
- **地图进一步顺滑**：`needFullRender` 平移重建阈值放宽至 160px、缩放档位宽容至 0.12，减少平移/缩放过程中不必要的全量重绘，配合既有 `will-change: transform` 让拖拽/缩放更跟手。

### 修复（资料 / 图片 / MBTI / 随笔保存）

- **头像上传失效根因修复**：个人页重构时补回缺失的隐藏文件输入 `#avatarFile`，修复上传头像无反应/无法保存。
- **保存操作统一加固**：`uploadAvatar / saveMe / saveMbti / publishEssay` 均补 `.catch` 与 `!r.ok` 分支的可视化 toast（含网络异常），不再静默失败；`saveMe` 保存后同步刷新底部个人标题。
- 修复个人页重构后 `#mbtiRecsMe` 空引用导致的启动风险（改为判空绑定）。

### 验证

- 前端 `app.js / render.js / map.js` 通过 `node --check`；Android 构建 `assembleRelease` 成功（`-x lint`）；APK 内置云地址、签名别名 `clearmap2026` 核验入包。
- 成品：`dist/ClearMap-cloud-preview-1.02.apk`。

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