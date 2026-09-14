# ClearMap 安卓 App 封装（Capacitor）

把既有 Web 前端打包为安卓 App。核心是**完整的 Web 前端当作 App 壳内资源**、**后端数据既可用内嵌离线包，也可指向任一本机 / 局域网 / 公网后端**。

> 说明：本方案是标准 Capacitor 封装。Web 页面/地图矢量数据随 APK 内置（从 `../static` 打包）。地图数据完全离线；`/api/*` 业务接口的后端地址默认同源（空），可在 App 内「个人中心 → 服务器 / 后端连接」修改并本地保存——不必为换地址重新打包。

## 前置（一次性安装）

1. 安装 **Android Studio**（自带 JDK + Android SDK）。装好后在 `Settings → SDK Manager` 勾选任一系统镜像，并记录 SDK 路径。
2. 本目录安装依赖：

   ```bash
   cd 工作台/projects/clearmap/mobile
   npm install @capacitor/core @capacitor/cli @capacitor/android
   ```

## 首次生成安卓工程

```bash
npx cap add android
```

> 若提示 SDK 相关，确认 `local.properties` 写好 sdk.dir（或用 `sdkmanager`/Android Studio 同步）。

## 每次改完前端后同步并打包

```bash
npx cap sync android
# 用 Android Studio 打开 mobile/android，等 Gradle 同步后  Build → Build APK
```
或命令行出包（需已配置 Android SDK）：
```bash
cd mobile/android
./gradlew assembleDebug
# 产物：mobile/android/app/build/outputs/apk/debug/app-debug.apk
```

## 后端地址（关键）

App 内的接口默认走同源（WebView 内置资源 + 离线 POI 兜底）。要让 App 连上你的后端，任选其一（**无需重新打包**）：

1. **App 内设置（推荐）**：打开 App →「个人中心」→「服务器 / 后端连接」→ 填后端地址（末尾带 `/`，如 `http://192.168.1.20:9100/` 或 `http://公网IP:9100/`）→「保存并重连」。地址存于本地，可随时改。
2. **编译期默认（可选）**：在 `../static/index.html` 的 `<head>`、`store.js` 之前加一行 `window.CLEARMAP_API_BASE = "https://你的后端/";` 作为默认值，再 `npx cap sync android` 重新打包。App 内设置会覆盖此默认值。

### 部署到"常开笔记本"（替代云服务器，含公网端口映射路径）

以手机通过**路由器端口映射 + 公网 IP** 访问常开笔记本为例：

1. **笔记本**装 Python 3.8+，双击 `../deploy/start_laptop.bat`（以 `0.0.0.0` 监听，默认端口 `9100`，可用 `CLEARMAP_PORT` 环境变量改端口）。
2. **Windows 防火墙**放行入站 `9100` TCP（或用的端口）。
3. **路由器**做端口映射：公网端口 → 笔记本内网 IP:9100；若家庭宽带是动态公网 IP，建议配合 DDNS 绑定固定域名。
4. **手机**在「服务器 / 后端连接」填 `http://<公网IP或域名>:端口/`，保存重连即可。
5. 以后笔记本搬新位置 / IP 变，**只需在 App 内改地址**，无需重装。

> 注意：后端是标准库 HTTP（非 HTTPS），App 已在 `AndroidManifest.xml` 开启 `usesCleartextTraffic="true"` 以支持 `http://`；如需严肃公网使用建议置于 Nginx + HTTPS 反向代理后。

## 注意

- 手机需能访问该后端（同局域网 / 公网 / 端口映射可通）。
- 若后端不可用，App 仍能打开并**离线浏览地图与内置 POI**；业务接口不可用。