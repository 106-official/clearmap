@echo off
chcp 65001 >nul
title ClearMap · 长沙
cd /d "%~dp0"
echo 启动 ClearMap —— 请等待浏览器打开 http://127.0.0.1:9100
start "" http://127.0.0.1:9100
python app.py 9100
pause