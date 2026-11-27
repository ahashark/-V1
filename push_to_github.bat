@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo   MAISON L'ATELIER - 构建静态页面并推送至 GitHub Pages
echo   目标仓库: https://github.com/ahashark/-V1.git
echo   绑定域名: https://sxy.ink
echo ========================================================
echo.

echo [1/3] 正在运行 Python 静态站点构建器 (build_static.py)...
.\.venv\Scripts\python.exe build_static.py
if errorlevel 1 (
    echo [错误] 静态构建失败，请检查上方报错信息。
    pause
    exit /b 1
)

echo.
echo [2/3] 检查并提交最新网页更改...
git add .
git diff --cached --quiet
if not errorlevel 1 (
    echo 当前所有文件已是最新提交状态。
) else (
    git commit -m "Update static site for sxy.ink"
)

echo.
echo [3/3] 正在推送至 GitHub (首次运行请在弹出的窗口点击 Sign in with your browser 授权)...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [提示] 推送未完成，请确认已完成 GitHub 登录授权后重试。
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   [成功] 代码与 docs/ 静态页面已成功上传至 GitHub！
echo   请前往 https://github.com/ahashark/-V1/settings/pages 开启 Pages。
echo ========================================================
pause
