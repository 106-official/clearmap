@echo off
chcp 65001 >nul
rem ============================================================
rem  ClearMap 后端 · 常开笔记本启动脚本
rem  监听 0.0.0.0，供局域网 / 路由器端口映射 / 公网访问。
rem  默认端口 9100；想换端口改下面 CLEARMAP_PORT。
rem  设置完 App 里的“服务器设置”→“保存并重连”即可。
rem ============================================================
set CLEARMAP_HOST=0.0.0.0
set CLEARMAP_PORT=9100
cd /d "%~dp0.."

echo.
echo  ClearMap 正在启动，监听 http://0.0.0.0:%CLEARMAP_PORT%
echo  本机访问:   http://127.0.0.1:%CLEARMAP_PORT%
echo  局域网/公网: http://<你的IP或外网地址>:%CLEARMAP_PORT%
echo  关闭本窗口或 Ctrl+C 即停止。
echo.

rem 优先使用当前 PATH 中的 python；找不到则用常见安装路径
where python >nul 2>nul
if %errorlevel%==0 (
    python app.py
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" app.py
) else if exist "C:\Python312\python.exe" (
    "C:\Python312\python.exe" app.py
) else (
    echo 未找到 Python，请安装 Python 3.8+ 并加入 PATH，或改本脚本里的 python 路径。
    pause
)