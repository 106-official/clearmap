# ClearMap 更新日志

记录每次功能迭代的详细内容。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [ClearMap-cloud-preview-1.06] · 2026-09-17

### 修复

- **随笔配图显示恢复正常**：随笔配图（个人页「我的随笔」与「发现」流）与头像一致改用 `fetch→Blob→对象URL` 通道加载，规避 WebView 直连 http 图片偶发失败；失败时移除破图，不再显示损坏框。
- **POI 景点图不再空白**：上海 15 个、北京 13 个景点（天安门因内容合规限制无法生成）新增实景风配图，随 APK 内置离线加载；长沙 3 个无图景点保持原样。所有景点图引用统一改为**相对路径**（`media/pois/<id>/img1.jpg`），Web 预览与 APK 内 `file://` 环境均可正确解析（此前 `/media/pois/...` 前导斜杠在 APK 内会解析到错误位置）。

### 界面

- **地图左上角布局互换**：城市选择胶囊与 MBTI 推荐条互换位置——MBTI 条移至地图顶部（`top:8px`），城市选择器下移（`top:64px`），展开的城市列表不再与 MBTI 互叠；地图视图隐藏顶部标题栏实现全屏沉浸。
- **提示风格统一（告别黑框）**：Toast 从深黑底改为纸墨风浅色毛玻璃卡（河绿描边、柔和投影、衬线排版），支持多行；MBTI 认证成功提示改为两行「已认证 MBTI / 系统为你换了一批风景」；发布随笔提示改为「发布成功^-^」。
- **行程按钮排版**：「开始记录行程 / 加一张打卡」并排等宽、不换行，小屏不再中间折行。

### 核验

- `app.js / render.js / store.js` 通过 `node --check`；后端 `py_compile` 通过。
- 图片清单核验：上海 15 张、北京 13 张、长沙 234 处引用已相对化；JSON 全部有效。
- 成品：`dist/ClearMap-cloud-preview-1.06.apk`（116.5MB，`versionCode 2 / versionName 1.06`，签名 `clearmap2026`，证书 SHA-256 `e0a3fbbc…`）。

## [1.05 二次修复] · 2026-09-17（不升级版本号，覆盖 ClearMap-cloud-preview-1.05）

### 界面

- **地图城市选择器重构为自定义动效控件**：将左上角原生 `<select>`（长沙/上海/北京）替换为「胶囊按钮 + 展开列表」样式，贴合纸墨/河绿设计语言：
  - 胶囊：河绿圆点 + 城市名 + 可旋转箭头，hover 徽标变色浮起；
  - 展开列表：半透明毛玻璃、纸色底、带 `cityIn` 入场动画（淡入 + 位移 + 缩放）、选中项高亮，点击外部自动收起。
- **地图缩放/定位按钮不再被底栏遮挡**：`.map-controls` 在固定底栏与安全区之上抬升（`bottom: calc(116px + env(safe-area-inset-bottom))`），最下方按钮（定位）完整可见。

### 修复

- **POI 景点图显示「The Image is generating…」占位**：部分景点 `images` 里的 `src` 指向 AI 生成占位地址（`trae-api-cn.mchost.guru/.../text_to_image?...`），无法渲染为真实图片，被内部提示文案占位。已从全部 POI 数据（前端 `static/pois*.json` 离线包 + 后端 `data/poi/*.json`）移除这类占位项：
  - 长沙：移除 18 处占位，本地真实图片 234 张保留，地图详情照常显示实景照片；
  - 上海 / 北京：移除 30 / 28 处占位（该两城未捆绑本地大图，移除后对应景点不再显示图集，避免坏占位）。
- **头像显示排查（二次确认）**：逐链路实测——后端 ECS 分别以 guest 与**真实登录态**（注册手机号→登录→token→上传→/api/me→/api/media）完整走通，全部 200 且返回 `image/png`；APK 内 `CLEARMAP_API_BASE` 注入与 `avatarUrl()` 拼接验证无误；`usesCleartextTraffic` 已开。确认后端与传输无问题后，针对「上传成功但 `<img>` 加载失败回退剪影」的残余现象，将头像与发现流头像改为 **fetch→Blob→对象URL 通道**加载（与上传接口同通道），并新增**服务器地址自检**（`api.bootstrapServerBase()` 探测本地残留地址，失效自动回退内置云后端），从加载通道与地址可靠性两侧彻底解决。

### 核验

- `app.js / render.js / store.js` 通过 `node --check`。
- 4 份 POI JSON 过滤后移除数量核验：长沙 18、上海 30、北京 28。
- APK 内 `index.html` 注入、`store.js` 自检回退逻辑实测存在。
- 成品：`dist/ClearMap-cloud-preview-1.05.apk`（覆盖同名文件，内置云后端 `http://47.99.131.169:9100/`，签名 `clearmap2026`）。

## [cloud-app-preview-1.05] · 2026-09-17

### 界面

- **地图城市选择器改置左上角**：将原来挤在右下缩放控件列的 `<select>`（长沙/上海/北京）独立为左上角固定胶囊，避免与缩放/定位按钮堆叠。

### 排查结论 · 头像与相册显示

逐一核对图像上传→落盘→回读→展示整条链路后确认**当前代码本身已可用**（对本地模块与线上 ECS `47.99.131.169:9100` 均实测验证）：

- 后端 `_save_image` 落盘 `data/uploads/<user>/avatar-xxxx.png` → `media()` 回读成功；
- 线上 ECS `POST /api/avatar` 返回 `/api/media?...` 且该 URL `200` 可取回图片字节；
- 前端上传后更新 `state.me.avatar` 并重渲染，`avatarUrl()` 自动把相对 `/api/media` 拼上 `API_BASE`；
- WebView `allowMixedContent:true` 允许 http 图片加载。

**此前「仍无法显示」的根因是已装的旧 APK 未包含 `compressImage` / `avatarUrl` 修复**，本次重新 `cap sync` 并注入云后端 `http://47.99.131.169:9100/` 后重建，确保修复真正进入安装包。

### 修复

- **随笔多图发布触碰 1MB 请求体上限**：`/api/essay` 最多可带 6 张图，单张 base64 最长约 0.9MB，合计常超后端默认 1MB 上限被拒（表现为「随笔配图无法上传/显示」）。已将 `/api/essay` 的请求体上限放宽到 7MB，其余接口仍保持 1MB。

### 核验

- `api.py / data.py / server.py / config.py` 通过 `python -m py_compile`。
- `app.js / render.js / store.js / map.js` 通过 `node --check`。
- 线上 ECS 完成头像上传→media 回读实测（`200`）。
- 成品：`dist/ClearMap-cloud-preview-1.05.apk`（内置云后端 `http://47.99.131.169:9100/`，签名 `clearmap2026`）。

## [1.04 修复] · 2026-09-17（不升级版本号，覆盖 cloud-app-preview-1.04）

### 地图流畅度 · 近零延迟

采用「静态层 / 动态层」彻底解耦，把平移/缩放中的同步重建降到最低：

- **静态底图只构建一次**：区界、水系、主干道 tier1（泸 6738 条）与所在视野无关，构建一次后常驻，之后平移/缩放全靠 `.map-view` 的 CSS transform（GPU 合成）驱动，**不再每 160px 平移就同步整组重塞**，消除主要抖动源。
- **细分路由单独随缩放加载**：`renderRoads` 仅处理 tier2/3/4，且只在跨越 LOD 档位时按可见区重建。
- **建筑按单元格缓存**：建筑元数据（包围盒 + path）按网格单元格缓存、只用一次，平移时仅做数值剔除，不再整城 35035 幢重复扫描。
- **切城市清空缓存**：`setCity` 复位道路 / 建筑 / 区界 / 静态层缓存，跨城市不串用。
- 首帧渲染主干道直接用原始 path（无需逐条算 bbox），缩短启动期开销。

### 修复

- **相册/头像大图无法上传**：之前前端对头像、打卡、随笔配图均做了 `>4MB` 硬拒，而后端请求体上限是 1MB（base64 膨胀后更严）；正常相机原图（动辄 3–8MB）必然失败，表现为「实拍图无法上传 / 头像无法上传」。改为**前端 canvas 压缩**：大于 600KB 的图先等比缩到 `maxW`（头像 512 / 图与随笔 1600）并转 JPEG（质量自适应探底），把编码长度压到 0.9MB 内、远小于后端 1MB 上限，GIF/SVG/小图原样直传。头像、打卡、随笔三处上传现已统一走 `compressImage`，大图可正常上传。
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