@echo off
REM 一键查看自动化状态 (Windows)

echo 🤖 多站点自动签到系统 - 快速状态
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 运行快速状态工具
python quick_status.py

echo.
echo 💡 更多命令:
echo   python check_status.py       - 详细状态检查
echo   python analyze_failures.py   - 失败分析
echo   python analyze_success.py    - 成功统计
echo   python multi_site_checkin.py - 运行签到
echo.
echo 📚 查看报告:
echo   type AUTOMATION_REPORT.md    - 完整分析报告
echo   type FAQ.md                  - 常见问题
echo   type SUMMARY.md              - 总结文档
echo.

pause
