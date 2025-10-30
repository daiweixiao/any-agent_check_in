@echo off
echo ====================================
echo Documentation Cleanup
echo ====================================
echo.

echo [1/4] Backup old README...
if exist README.md (
    move README.md docs\README_OLD.md >nul
    echo Backed up to docs\README_OLD.md
)
echo.

echo [2/4] Use new README...
move README_NEW.md README.md >nul
echo New README.md created
echo.

echo [3/4] Delete duplicate docs...
del /Q ADD_ACCOUNT_GUIDE.md 2>nul
del /Q AUTO_LOGIN_README.md 2>nul
del /Q AUTO_LOGIN_SECURITY_GUIDE.md 2>nul
del /Q FLOW_ANALYSIS.md 2>nul
del /Q MULTI_ACCOUNT_GUIDE.md 2>nul
del /Q REFRESH_SESSION_GUIDE.md 2>nul
del /Q WAF_CACHE_OPTIMIZATION.md 2>nul
echo Deleted 7 documents
echo.

echo [4/4] Move reference docs...
if exist QUICK_START.md move QUICK_START.md docs\ >nul
if exist GITHUB_ACTIONS_SETUP.md move GITHUB_ACTIONS_SETUP.md docs\ >nul
if exist PASSWORD_ENCRYPTION_GUIDE.md move PASSWORD_ENCRYPTION_GUIDE.md docs\ >nul
echo Moved to docs/
echo.

echo ====================================
echo Cleanup Complete!
echo ====================================
echo.
echo Project structure:
echo   - README.md          Main doc
echo   - docs/              Reference docs
echo.
pause
