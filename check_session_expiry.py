#!/usr/bin/env python3
"""
Session 过期检测脚本
检测 session 是否即将过期，如果是则发送通知
建议每天运行一次（通过 GitHub Actions）
"""

import requests
import json
import sys
import os
from datetime import datetime

def check_account_session(account):
    """
    检查单个账号的 session 是否有效
    
    Returns:
        dict: {"valid": bool, "message": str}
    """
    name = account.get("name", "Unknown")
    provider = account.get("provider", "unknown")
    session = account.get("cookies", {}).get("session")
    api_user = account.get("api_user")
    
    if not session:
        return {
            "valid": False,
            "account": name,
            "message": "❌ 未配置 session"
        }
    
    # 根据 provider 选择 API 端点
    if provider == "agentrouter":
        url = "https://agentrouter.org/api/user/self"
    elif provider == "anyrouter":
        url = "https://anyrouter.top/api/user/self"
    else:
        return {
            "valid": False,
            "account": name,
            "message": f"❌ 未知的 provider: {provider}"
        }
    
    try:
        response = requests.get(
            url,
            cookies={"session": session},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "new-api-user": str(api_user) if api_user else ""
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                username = data.get("data", {}).get("username", "Unknown")
                balance = data.get("data", {}).get("quota", 0) / 100
                return {
                    "valid": True,
                    "account": name,
                    "message": f"✅ Session 有效 | 用户: {username} | 余额: ${balance}",
                    "balance": balance
                }
        
        return {
            "valid": False,
            "account": name,
            "message": f"⚠️ Session 无效或过期 | Status: {response.status_code}"
        }
        
    except Exception as e:
        return {
            "valid": False,
            "account": name,
            "message": f"❌ 检查失败: {str(e)}"
        }


def main():
    """主函数"""
    print("=" * 70)
    print("🔍 Session 有效性检查")
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # 从环境变量或命令行参数读取账号配置
    accounts_json = os.environ.get('ANYROUTER_ACCOUNTS')

    # 如果环境变量不存在，尝试从命令行参数读取
    if not accounts_json and len(sys.argv) > 1:
        accounts_json = sys.argv[1]

    if not accounts_json:
        print("❌ 错误: 请提供账号配置 JSON")
        print("用法: python check_session_expiry.py '<ACCOUNTS_JSON>'")
        print("或设置环境变量: ANYROUTER_ACCOUNTS")
        sys.exit(1)

    try:
        accounts = json.loads(accounts_json)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)
    
    # 检查所有账号
    results = []
    invalid_accounts = []
    
    for account in accounts:
        result = check_account_session(account)
        results.append(result)
        print(f"📋 {result['message']}")
        
        if not result["valid"]:
            invalid_accounts.append(result["account"])
    
    print()
    print("=" * 70)
    print("📊 检查结果汇总")
    print("=" * 70)
    
    valid_count = sum(1 for r in results if r["valid"])
    total_count = len(results)
    
    print(f"✅ 有效: {valid_count}/{total_count}")
    print(f"❌ 无效: {len(invalid_accounts)}/{total_count}")
    
    if invalid_accounts:
        print()
        print("⚠️ 以下账号需要更新 Session:")
        for acc in invalid_accounts:
            print(f"   - {acc}")
        print()
        print("🔧 请访问以下页面重新登录:")
        print("   AgentRouter: https://agentrouter.org/oauth")
        print("   AnyRouter: https://anyrouter.top/oauth")
        
        # 返回非零退出码，触发 GitHub Actions 通知
        sys.exit(1)
    else:
        print()
        print("✅ 所有账号 Session 均有效！")
        sys.exit(0)


if __name__ == "__main__":
    main()
