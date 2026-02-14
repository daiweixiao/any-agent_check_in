#!/usr/bin/env python3
"""
从 test_multi_accounts.py 生成 accounts_config.json
"""
import json

# 从 test_multi_accounts.py 导入账号配置
from test_multi_accounts import ACCOUNTS

# 转换为 accounts_config.json 格式
config_accounts = []
for account in ACCOUNTS:
    config_accounts.append({
        "name": account["name"],
        "provider": account["provider"],
        "cookies": account["cookies"],
        "api_user": account["api_user"]
    })

# 保存到 accounts_config.json
with open("accounts_config.json", "w", encoding="utf-8") as f:
    json.dump(config_accounts, f, indent=2, ensure_ascii=False)

print("✅ 成功生成 accounts_config.json")
print(f"📋 包含 {len(config_accounts)} 个账号配置")
