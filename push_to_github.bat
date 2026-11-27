@echo off
cd /d "%~dp0"

echo ========================================================
echo   MAISON L'ATELIER - Deploy to GitHub Pages (sxy.ink)
echo   Repository: https://github.com/ahashark/-V1.git
echo ========================================================
echo.

echo [1/3] Building static pages into docs/ ...
.\.venv\Scripts\python.exe build_static.py
if errorlevel 1 (
    echo [ERROR] Static build failed.
    pause
    exit /b 1
)

echo.
echo [2/3] Checking git status ...
git add .
git commit -m "Update static site for sxy.ink" >nul 2>nul

echo.
echo [3/3] Pushing to GitHub (please complete browser sign-in if prompted) ...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [FAILED] Push did not complete. Please sign in when GitHub prompts.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   [SUCCESS] Uploaded to https://github.com/ahashark/-V1
echo   Next: Open https://github.com/ahashark/-V1/settings/pages
echo ========================================================
pause
