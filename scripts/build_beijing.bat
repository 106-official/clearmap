@echo off
cd /d "C:\Users\26516\Desktop\工作台\projects\clearmap"
set PYTHONUNBUFFERED=1
set ROUND=0
:loop
set /a ROUND+=1
echo [%time%] Round %ROUND% starting...
python -u scripts\build_map.py beijing >> build_cache\beijing_batch.log 2>&1
echo [%time%] Round %ROUND% exited with code %errorlevel%
if exist "build_cache\beijing_buildings.json" (
    echo [%time%] Buildings cache complete!
    goto done
)
if %ROUND% GEQ 50 goto done
timeout /t 5 /nobreak >nul
goto loop
:done
echo [%time%] Batch complete after %ROUND% rounds.
