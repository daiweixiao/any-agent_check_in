@echo off
chcp 65001 >nul
echo ====================================
echo Git Push Script
echo ====================================
echo.

echo [1/4] Committing...
git commit -m "Initial commit"
if %errorlevel% neq 0 (
    echo Commit failed
    pause
    exit /b 1
)
echo Commit successful
echo.

echo [2/4] Setting branch to main...
git branch -M main
echo.

echo [3/4] Adding remote...
git remote add origin https://github.com/daiweixiao/any-agent_check_in.git
echo.

echo [4/4] Pushing to GitHub...
git push -u origin main
if %errorlevel% neq 0 (
    echo Push failed. You may need to login.
    echo.
    echo Please use Personal Access Token as password
    echo Get token at: https://github.com/settings/tokens
    pause
    exit /b 1
)

echo.
echo ====================================
echo Success! Code pushed to GitHub
echo ====================================
echo.
echo Repository: https://github.com/daiweixiao/any-agent_check_in
echo.
pause
