#!/usr/bin/env python3
"""
本地 Session 测试脚本
用于快速验证账号配置是否正确
"""

import json
import sys
from datetime import datetime

try:
	import httpx
	# 创建兼容 requests 的接口
	class RequestsCompat:
		@staticmethod
		def get(*args, **kwargs):
			with httpx.Client(verify=False, timeout=10.0) as client:
				return client.get(*args, **kwargs)

		class exceptions:
			Timeout = httpx.TimeoutException
			RequestException = httpx.HTTPError

	requests = RequestsCompat()
except ImportError:
	import requests


def test_single_account(account, index):
    """测试单个账号的 session 是否有效"""
    name = account.get("name", f"Account {index + 1}")
    provider = account.get("provider", "unknown")

    # 获取 session
    cookies = account.get("cookies", {})
    if isinstance(cookies, dict):
        session = cookies.get("session")
    else:
        print(f"❌ {name}: cookies 格式错误，应该是字典格式")
        return False

    api_user = account.get("api_user")

    if not session:
        print(f"❌ {name}: 未配置 session")
        return False

    if not api_user:
        print(f"⚠️  {name}: 未配置 api_user")

    # 选择 API 端点
    if provider == "agentrouter":
        url = "https://agentrouter.org/api/user/self"
        domain = "AgentRouter"
    elif provider == "anyrouter":
        url = "https://anyrouter.top/api/user/self"
        domain = "AnyRouter"
    else:
        print(f"❌ {name}: 未知的 provider: {provider}")
        return False

    # 从 name 中提取信息（格式：linuxdo_ID_username_email_platform）
    parts = name.split('_')
    if len(parts) >= 4:
        linuxdo_id = parts[1] if len(parts) > 1 else api_user
        username = parts[2] if len(parts) > 2 else "Unknown"
        email = parts[3] if len(parts) > 3 else "Unknown"
        display_name = f"linuxdo_{linuxdo_id}   {username}   {email} - {domain}"
    else:
        display_name = f"{name} - {domain}"

    print(f"\n{'='*80}")
    print(f"🔍 测试账号: {display_name}")
    print(f"👤 API User: {api_user}")
    print(f"🔑 Session: {session[:20]}...{session[-20:]}")
    print(f"{'='*80}")
    
    try:
        # 发送请求
        print(f"📡 发送请求到: {url}")
        response = requests.get(
            url,
            cookies={"session": session},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "new-api-user": str(api_user) if api_user else ""
            },
            timeout=10
        )
        
        print(f"📥 响应状态码: {response.status_code}")
        
        # 检查状态码
        if response.status_code != 200:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            print(f"📄 响应内容预览: {response.text[:200]}")
            return False
        
        # 尝试解析 JSON
        try:
            data = response.json()
            print(f"✅ JSON 解析成功")
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            print(f"📄 响应内容预览: {response.text[:200]}")
            return False
        
        # 检查 API 返回
        if data.get("success"):
            user_data = data.get("data", {})
            username = user_data.get("username", "Unknown")
            quota = user_data.get("quota", 0) / 500000
            used_quota = user_data.get("used_quota", 0) / 500000
            
            print(f"✅ Session 有效！")
            print(f"👤 用户名: {username}")
            print(f"💰 余额: ${quota:.2f}")
            print(f"📊 已使用: ${used_quota:.2f}")
            return True
        else:
            error_msg = data.get("message", "未知错误")
            print(f"❌ API 返回失败: {error_msg}")
            print(f"📄 完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("🧪 Session 本地测试工具")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 读取配置文件
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        # 尝试常见的配置文件名
        for filename in ["update_sessions.json", "accounts_config.json", "config.json"]:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config_file = filename
                    break
            except FileNotFoundError:
                continue
    
    if not config_file:
        print("\n❌ 未找到配置文件")
        print("\n使用方法:")
        print("  python test_session.py [配置文件路径]")
        print("\n或者将配置保存为以下文件名之一:")
        print("  - update_sessions.json")
        print("  - accounts_config.json")
        print("  - config.json")
        sys.exit(1)
    
    # 读取配置
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        sys.exit(1)
    
    if not isinstance(accounts, list):
        print("❌ 配置格式错误: 应该是数组格式 [...]")
        sys.exit(1)
    
    print(f"\n📋 找到 {len(accounts)} 个账号配置")
    print(f"📁 配置文件: {config_file}")
    
    # 测试所有账号
    results = []
    for i, account in enumerate(accounts):
        success = test_single_account(account, i)
        results.append(success)
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"✅ 成功: {success_count}/{total_count}")
    print(f"❌ 失败: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n🎉 所有账号测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️  部分账号测试失败，请检查上面的详细信息")
        print("\n💡 解决方案:")
        print("  1. 访问对应平台重新登录获取新的 session")
        print("  2. 使用 F12 开发者工具获取 session cookie")
        print("  3. 更新配置文件中的 session 值")
        print("\n📖 详细指南请查看: SESSION_TROUBLESHOOTING.md")
        sys.exit(1)


if __name__ == "__main__":
    main()

