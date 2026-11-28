@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo   MAISON L'ATELIER - Build ^& Deploy to Ubuntu (192.168.118.128)
echo ========================================================
echo.

echo [1/2] 编译最新静态页面并生成 Ubuntu 发布包...
.\.venv\Scripts\python.exe build_release.py
if errorlevel 1 (
    echo [ERROR] 编译打包失败。
    pause
    exit /b 1
)

echo.
echo [2/2] 上传并部署至 Ubuntu (xh@192.168.118.128)...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\deploy\upload_and_deploy.ps1" -ServerIp 192.168.118.128 -User xh
if errorlevel 1 (
    echo.
    echo [FAILED] 远程部署未完成，请检查上方提示。
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   [SUCCESS] Ubuntu (http://192.168.118.128) 已同步为最新版本！
echo ========================================================
pause
