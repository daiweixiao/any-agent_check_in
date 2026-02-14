@echo off
chcp 65001 >nul
echo ========================================
echo Session 测试工具
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查配置文件
if exist "update_sessions.json" (
    set CONFIG_FILE=update_sessions.json
) else if exist "accounts_config.json" (
    set CONFIG_FILE=accounts_config.json
) else if exist "config.json" (
    set CONFIG_FILE=config.json
) else (
    echo ❌ 未找到配置文件
    echo.
    echo 请创建以下文件之一:
    echo   - update_sessions.json
    echo   - accounts_config.json
    echo   - config.json
    echo.
    pause
    exit /b 1
)

echo 📁 使用配置文件: %CONFIG_FILE%
echo.

REM 安装依赖
echo 📦 检查依赖...
pip show requests >nul 2>&1
if errorlevel 1 (
    echo 📥 安装 requests...
    pip install requests
)

echo.
echo 🧪 开始测试...
echo.

REM 运行测试
python test_session.py %CONFIG_FILE%

echo.
pause

