@echo off
chcp 65001 >nul
echo ====================================
echo Git Update Script
echo ====================================
echo.

echo [1/3] Committing changes...
git commit -m "Fix: Remove urllib3 dependency"
if %errorlevel% neq 0 (
    echo Commit failed
    pause
    exit /b 1
)
echo Commit successful
echo.

echo [2/3] Pushing to GitHub...
git push
if %errorlevel% neq 0 (
    echo Push failed
    pause
    exit /b 1
)
echo Push successful
echo.

echo ====================================
echo Success! Code updated on GitHub
echo ====================================
echo.
pause
