#!/usr/bin/env python3
"""
本地测试脚本
"""
import os
import sys

# 设置测试环境变量
# 最新配置（2025-10-25 23:32 更新）
TEST_SESSION = "MTc2MTQwNjM2NHxEWDhFQVFMX2dBQUJFQUVRQUFEXzRfLUFBQWNHYzNSeWFXNW5EQW9BQ0hWelpYSnVZVzFsQm5OMGNtbHVad3dQQUExc2FXNTFlR1J2WHpNME9EYzNCbk4wY21sdVp3d0dBQVJ5YjJ4bEEybHVkQVFDQUFJR2MzUnlhVzVuREFnQUJuTjBZWFIxY3dOcGJuUUVBZ0FDQm5OMGNtbHVad3dIQUFWbmNtOTFjQVp6ZEhKcGJtY01DUUFIWkdWbVlYVnNkQVp6ZEhKcGJtY01CUUFEWVdabUJuTjBjbWx1Wnd3R0FBUTBNVGxGQm5OMGNtbHVad3dOQUF0dllYVjBhRjl6ZEdGMFpRWnpkSEpwYm1jTURnQU1Vemd6VW1WbGFrOU9aa1p4Qm5OMGNtbHVad3dFQUFKcFpBTnBiblFFQlFEOUFSQjZ8JIfapZbxzSc9wHcoiPG4f8CPG5bJx1y_ok3MiqQbcoI="
TEST_API_USER = "34877"

# 构建账号配置
accounts_config = [
    {
        "name": "测试账号 - AgentRouter",
        "provider": "agentrouter",
        "cookies": {
            "session": TEST_SESSION
        },
        "api_user": TEST_API_USER
    }
]

# 设置环境变量
import json
os.environ['ANYROUTER_ACCOUNTS'] = json.dumps(accounts_config)

print("=" * 60)
print("🧪 开始本地测试")
print("=" * 60)
print(f"📋 配置信息:")
print(f"   - Provider: agentrouter")
print(f"   - API User: {TEST_API_USER}")
print(f"   - Session: {TEST_SESSION[:30]}...")
print("=" * 60)
print()

# 导入并运行主程序
from checkin import run_main

if __name__ == '__main__':
    try:
        run_main()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
