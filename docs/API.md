# ClearMap 接口方案（API Reference）

前后端通信采用 **HTTP JSON**。顶层统一容器 `{ "ok": true/false, ... }`：
- `ok: true` → 成功，携带业务字段。
- `ok: false` → 失败，携带 `error`（简要中文错误信息）或 `msg`。
- 任何未预期异常都会被捕获并归一化为 `{ "ok": false, "error": "服务异常: ..." }`，**永不裸奔 500**。

## 认证与会话

采用 **手机号 + 短信验证码** 登录，登录后下发持久化会话 `token`（有效期 30 天，服务端 JSON 落盘，重启不丢）。

### 携带身份的方式
除下列"无需身份"接口外，绝大多数接口通过 **查询串** 携带身份：
- 已登录：`?token=<token>`
- 未登录：`?user=guest`（默认行为，不带即可）
服务端 `resolve(token)` 校验会话；失效/过期自动回退为游客 `guest`，不报错。

### 哪些接口"无需身份"（不认 token/user）
`POST /api/sms`、`POST /api/auth/login`、`POST /api/auth/logout`（token 在 body）、`GET /api/auth/me`、`GET /api/health`。

## 认证接口

### POST `/api/sms`
发送验证码（阿里云短信；未配置短信时为调试码 `123456`）。

请求体：
```json
{ "phone": "13800138000" }
```
响应 `200`：
```json
{ "ok": true, "msg": "验证码已发送" }
```
调试模式下额外返回 `dev_code`（前端自动填入输入框）：
```json
{ "ok": true, "msg": "验证码已发送（当前为调试模式，固定为 123456）", "dev_code": "123456" }
```
节流：同一手机号 60 秒内不可重发；验证码 5 分钟有效、最多尝试 5 次。

### POST `/api/auth/login`
校验验证码并登录 / 注册（首次登录自动建号）。

请求体：
```json
{ "phone": "13800138000", "code": "123456" }
```
成功 `200`：
```json
{ "ok": true, "msg": "登录成功", "session": { "token": "<hex>", "user_id": "u...", "phone": "+8613800138000", "nickname": "", "is_new": 1 } }
```
失败 `400`：`{ "ok": false, "error": "验证码不正确" }`

前端登录后应把 `session.token` 存进 `localStorage.key = "clearmap_token"`。

### POST `/api/auth/logout`
登出，废除当前会话。
```json
{ "token": "<token>" }
```
响应：`{ "ok": true }`

### GET `/api/auth/me?token=`
校验当前登录态。
```json
{ "ok": true, "me": { "user_id": "u...", "phone": "+86...", "nickname": "", "avatar": "", "is_new": 1, "signed_in": true } }
```
未登录时 `me.signed_in` 为 `false`、`phone` 为空。App 首页启动时调用它做登录状态检测。

## 通用业务接口（除认证外均需 user/token）

### GET `/api/health`
```json
{ "ok": true, "status": "up" }
```
「服务器设置」用它检测后端连通性。

### GET `/api/pois?city=changsha&`
返回按偏好与 MBTI 排序的景点（含地理坐标 `x/y` 为 Web Mercator 局部坐标）。
```json
{ "ok": true, "pois": [ { "id": "...", "name": "...", "district": "", "type": "", "tags": [], "duration_min": 60, "desc": "", "x": ..., "y": ..., "lat": ..., "lon": ..., "affinity": 0.9, "mbti_affinity": null, "style": [], "hours": {}, "ticket": "", "images": [] } ] }
```

### GET `/api/profile?`
```json
{ "ok": true, "profile": { "nature": 3, "culture": 3, ... }, "favorites": [], "plans": [] }
```

### GET `/api/me?`
个人中心聚合：资料、偏好、收藏、行程、打卡、路线。
```json
{ "ok": true, "me": { "id": "guest", "nickname": "", "signature": "", "avatar": "", "mbti": null, "mbti_name": "", "created": null }, "profile": {...}, "favorites": [], "plans": [], "checkins": [], "routes": [], "essays": [] }
```

### POST `/api/me?`
更新资料。请求体：`{ "nickname": "", "signature": "" }` 或 `{ "mbti": "INFJ" }`。

### POST `/api/avatar?`
上传头像（data URL，≤4MB，`image/png|jpeg|gif|webp`）。请求体：`{ "data": "data:image/..." }`
响应：`{ "ok": true, "avatar": "/api/media?user=...&file=..." }`

### POST `/api/checkin?`
旅行打卡。请求体：`{ "img": "<data URL>", "lat": 28, "lon": 113, "poi_id": "", "caption": "" }`（`img` 可省）。

### DELETE `/api/checkin/{id}?`

### POST `/api/route?`
保存 GPS 轨迹。请求体：`{ "title": "", "start": 0, "end": 0, "points": [[lat,lon], ...] }`（至少 2 点）。

### DELETE `/api/route/{id}?`

### POST `/api/favorite/{poi_id}?`
切换收藏。响应：`{ "ok": true, "action": "added"|"removed", "favorites": [...] }`

### GET `/api/mbti-recs?city=&limit=`
未认证 MBTI 时返回空 `recommended`；已认证返回风格推荐。

### POST `/api/route-plan?`
换乘路线规划（公交/地铁）。请求体：
```json
{ "from": { "lat": 28.2, "lon": 113.0, "name": "起点" }, "to": { "poi_id": "xxx" } }
```
`to` 也可为 `{ "lat", "lon", "name" }`。响应含 `total_min`、`transfers`、`legs[]`、`coords[]`。

## 旅游随笔 / 发现（preview-1.22）

随笔由「个人」页发布（文字 + 可选相册配图，最多 6 张），聚合到「发现」页供所有人查看。图片以 data URL 上传，存到用户 `uploads/<user>/essay-*.jpg`，随笔导出时替换为 `/api/media` URL。

### POST `/api/essay?`
发布/追加一篇随笔。**仅登录用户可发布**（游客调用返回 400「请先登录后再发布随笔」）。
```json
{ "text": "湘江边入夜后的晚风", "imgs": ["data:image/jpeg;base64,..."] }
```
`text` 必填、≤2000 字；`imgs` 可空、≤6 张、单张 ≤4MB。
响应 `200`：`{ "ok": true, "essay": { "id", "created", "text", "imgs": ["/api/media?..."] } }`

### DELETE `/api/essay/{id}?`
删除自己的随笔。响应：`{ "ok": true, "id": "..." }`

### GET `/api/feed?limit=30&`
发现流：聚合所有账号（含游客）的随笔，按时间倒序。`limit`（默认 30，≤60 可调）。
```json
{ "ok": true, "essays": [ { "id", "text", "imgs": [], "created", "author_id", "author": "昵称/旅人", "avatar" } ] }
```

> 个人页的「我的随笔」列表来自 `GET /api/me?` 返回的 `essays` 字段（原样附带作者信息）。

## 图片访问

### GET `/api/media?user=<user_id>&file=<filename>`
读取用户上传的图片（头像/打卡）。`file` 仅允许文件名本身，防目录穿越。

## 状态码约定
- `200` 成功
- `400` 业务错误（如验证码错误、参数非法）
- `404` 接口/资源不存在
- `403` 无权限（如访问 `/data/`）

## 数据目录
- `data/users/<user_id>.json` — 用户资料
- `data/accounts.json` — 手机号 → user_id
- `data/sessions.json` — token → 会话
- `data/uploads/<user>/` — 上传图片
- `data/poi/<city>.json` — 各城市 POI

## 安全说明
- 手机号入参会规范化并至少 8 位数字；验证码随机 6 位、5 分钟有效、5 次上限、60 秒节流。
- 上传图片限 4MB 且白名单格式；文件名防目录穿越。
- 后端为标准库 `http.server`，生产建议置于 Nginx 反向代理后启用 HTTPS。