#!/usr/bin/env python3
"""
自动刷新 Session 脚本
当检测到 session 即将过期时，自动重新登录并更新配置
"""

import requests
import json
import time
from datetime import datetime, timedelta

# ==================== 配置 ====================

# LinuxDO OAuth 配置
LINUXDO_CLIENT_ID = "KZUecGfhhDZMVnv8UtEdhOhf9sNOhqVX"  # AgentRouter 的 client_id
LINUXDO_USERNAME = "你的LinuxDO用户名"
LINUXDO_PASSWORD = "你的LinuxDO密码"

# 推广码（可选）
AFF_CODE = "419E"

# Session 有效期（天）
SESSION_VALIDITY_DAYS = 30

# 配置文件路径
CONFIG_FILE = "accounts_config.json"

# ==================== 函数定义 ====================

def check_session_validity(session_cookie):
    """
    检查 session 是否有效
    
    Args:
        session_cookie: session cookie 值
        
    Returns:
        bool: True 表示有效，False 表示无效或即将过期
    """
    try:
        # 尝试访问用户信息接口
        response = requests.get(
            "https://agentrouter.org/api/user/self",
            cookies={"session": session_cookie},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✅ Session 有效，用户: {data.get('data', {}).get('username', 'Unknown')}")
                return True
        
        print("⚠️ Session 无效或即将过期")
        return False
        
    except Exception as e:
        print(f"❌ 检查 session 失败: {e}")
        return False


def get_oauth_state(aff_code=None):
    """
    获取 OAuth state
    
    Args:
        aff_code: 推广码（可选）
        
    Returns:
        str: state 值，失败返回 None
    """
    try:
        url = "https://agentrouter.org/api/oauth/state"
        params = {"aff": aff_code} if aff_code else {}
        
        response = requests.get(
            url,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                state = data.get("data")
                print(f"✅ 获取 state 成功: {state}")
                return state
        
        print(f"❌ 获取 state 失败: {response.text}")
        return None
        
    except Exception as e:
        print(f"❌ 获取 state 异常: {e}")
        return None


def simulate_linuxdo_login(username, password, client_id, state):
    """
    模拟 LinuxDO OAuth 登录流程
    
    注意：这需要 LinuxDO 的自动化登录支持
    实际可能需要使用 Selenium 或 Playwright
    
    Args:
        username: LinuxDO 用户名
        password: LinuxDO 密码
        client_id: OAuth client_id
        state: OAuth state
        
    Returns:
        str: OAuth code，失败返回 None
    """
    print("⚠️ 自动登录 LinuxDO 需要浏览器自动化工具")
    print("💡 建议使用 Playwright 实现自动授权")
    
    # TODO: 实现 LinuxDO 自动登录
    # 这里需要使用 Playwright 或 Selenium
    # 1. 访问授权页面
    # 2. 填写用户名密码
    # 3. 点击"允许"按钮
    # 4. 获取回调 URL 中的 code
    
    return None


def exchange_code_for_session(code, state):
    """
    用 OAuth code 交换 session
    
    Args:
        code: OAuth code
        state: OAuth state
        
    Returns:
        str: session cookie 值，失败返回 None
    """
    try:
        response = requests.get(
            "https://agentrouter.org/api/oauth/linuxdo",
            params={"code": code, "state": state},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            allow_redirects=False,
            timeout=10
        )
        
        # 检查是否设置了 session cookie
        if "session" in response.cookies:
            session = response.cookies["session"]
            print(f"✅ 成功获取新 session")
            return session
        
        # 检查响应
        data = response.json()
        if not data.get("success"):
            print(f"❌ 登录失败: {data.get('message', 'Unknown error')}")
        
        return None
        
    except Exception as e:
        print(f"❌ 交换 session 失败: {e}")
        return None


def update_config_file(config_file, account_name, new_session):
    """
    更新配置文件中的 session
    
    Args:
        config_file: 配置文件路径
        account_name: 账号名称
        new_session: 新的 session 值
        
    Returns:
        bool: 成功返回 True
    """
    try:
        # 读取现有配置
        with open(config_file, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        
        # 查找并更新账号
        updated = False
        for account in accounts:
            if account.get("name") == account_name:
                account["cookies"]["session"] = new_session
                account["last_refresh"] = datetime.now().isoformat()
                updated = True
                break
        
        if not updated:
            print(f"⚠️ 未找到账号: {account_name}")
            return False
        
        # 保存配置
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 配置文件已更新: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        return False


def auto_refresh_if_needed():
    """
    检查并自动刷新即将过期的 session
    """
    print("=" * 70)
    print("🔄 Session 自动刷新检查")
    print("=" * 70)
    print()
    
    try:
        # 读取配置
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        
        for account in accounts:
            name = account.get("name", "Unknown")
            session = account.get("cookies", {}).get("session")
            
            if not session:
                print(f"⚠️ {name}: 未配置 session")
                continue
            
            print(f"\n📋 检查账号: {name}")
            
            # 检查 session 是否有效
            if check_session_validity(session):
                print(f"✅ {name}: Session 仍然有效，无需刷新")
                continue
            
            print(f"🔄 {name}: 需要刷新 session")
            
            # 获取 state
            state = get_oauth_state(AFF_CODE)
            if not state:
                print(f"❌ {name}: 无法获取 OAuth state")
                continue
            
            # TODO: 实现自动登录
            print(f"⚠️ {name}: 需要手动登录获取新 session")
            print(f"   请访问: https://agentrouter.org/oauth")
            
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ 处理失败: {e}")


# ==================== 方案 2: 使用 Playwright 自动登录 ====================

def auto_refresh_with_playwright(account):
    """
    使用 Playwright 自动刷新 session
    
    Args:
        account: 账号配置字典
        
    Returns:
        str: 新的 session，失败返回 None
    """
    print(f"\n🤖 使用浏览器自动化刷新: {account.get('name')}")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=False)  # 设为 True 可后台运行
            context = browser.new_context()
            page = context.new_page()
            
            # 1. 访问登录页面
            print("📍 访问登录页面...")
            page.goto("https://agentrouter.org/oauth")
            
            # 2. 点击 LinuxDO 登录按钮
            print("🔘 点击 LinuxDO 登录...")
            page.click("text=Linux DO")  # 根据实际按钮文本调整
            
            # 3. 等待跳转到 LinuxDO 授权页
            print("⏳ 等待授权页面...")
            page.wait_for_url("**/connect.linux.do/**", timeout=10000)
            
            # 4. 填写 LinuxDO 登录信息（如果需要）
            if page.url.find("login") != -1:
                print("📝 填写登录信息...")
                page.fill("input[name='login']", LINUXDO_USERNAME)
                page.fill("input[name='password']", LINUXDO_PASSWORD)
                page.click("button[type='submit']")
                time.sleep(2)
            
            # 5. 点击"允许"按钮
            print("✅ 点击授权按钮...")
            page.click("button:has-text('允许')")  # 根据实际按钮文本调整
            
            # 6. 等待回调完成
            print("⏳ 等待回调完成...")
            page.wait_for_url("**/agentrouter.org/**", timeout=10000)
            
            # 7. 获取 session cookie
            cookies = context.cookies()
            session_cookie = None
            for cookie in cookies:
                if cookie["name"] == "session":
                    session_cookie = cookie["value"]
                    break
            
            browser.close()
            
            if session_cookie:
                print(f"✅ 成功获取新 session")
                return session_cookie
            else:
                print(f"❌ 未找到 session cookie")
                return None
            
    except ImportError:
        print("❌ 未安装 Playwright，请运行: pip install playwright")
        print("   然后运行: playwright install chromium")
        return None
    except Exception as e:
        print(f"❌ 自动刷新失败: {e}")
        return None


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║           Session 自动刷新工具                             ║
║                                                            ║
║  功能: 检测并自动刷新即将过期的 session                    ║
║  建议: 配合定时任务（如每周运行一次）使用                  ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # 运行自动刷新检查
    auto_refresh_if_needed()
    
    print("\n" + "=" * 70)
    print("✨ 检查完成")
    print("=" * 70)
