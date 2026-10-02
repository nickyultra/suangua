@echo off
chcp 65001 >nul
title 易学占卜 Agent
cd /d "%~dp0"

set "CF=%LOCALAPPDATA%\cloudflared\cloudflared.exe"
set "PORT=8000"

if not exist "%CF%" (
    echo [错误] 找不到 cloudflared:
    echo   %CF%
    echo 只想起本地服务的话，直接跑:
    echo   python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   易学占卜 Agent
echo ============================================================
echo   [1/2] 本地服务  http://localhost:%PORT%   (另开一个窗口)
echo   [2/2] 公网隧道  就是这个窗口，稍后打印公网地址
echo ------------------------------------------------------------
echo   同一 Wi-Fi 下的人可访问  http://本机IP:%PORT%
echo   公网地址长得像  https://xxx.trycloudflare.com
echo   关掉本窗口 = 公网地址失效，下次重开会换成新地址
echo ============================================================
echo.

start "占卜-本地服务" cmd /k python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

echo 等待本地服务就绪...
timeout /t 4 /nobreak >nul
echo.

:loop
"%CF%" tunnel --url http://localhost:%PORT% --protocol http2 --no-autoupdate
echo.
echo ------------------------------------------------------------
echo 隧道已退出，公网地址失效。
echo 按任意键重新开一条隧道（会得到一个新地址），或直接关窗口。
echo ------------------------------------------------------------
pause >nul
goto loop
