#!/usr/bin/env python3
"""
自动登录示例代码
这是一个完整的实现示例，展示如何使用 Playwright 自动登录 AgentRouter

⚠️ 注意：这只是示例代码，实际使用时需要根据具体情况调整
"""

from playwright.sync_api import sync_playwright, Page
import time
import json
from datetime import datetime

# ==================== 配置示例 ====================

EXAMPLE_CONFIG = {
    "accounts": [
        {
            "name": "示例账号1",
            "provider": "agentrouter",
            "linuxdo_username": "your_username",  # 替换为实际用户名
            "linuxdo_password": "your_password",  # 替换为实际密码
            "totp_secret": None,  # 如果启用 2FA，填入 TOTP 密钥
            "aff_code": "419E",
            "cookies": {
                "session": ""  # 将被自动填充
            },
            "api_user": "34327"
        }
    ]
}

# ==================== 核心函数 ====================

def auto_login_agentrouter(
    page: Page,
    username: str,
    password: str,
    totp_secret: str = None
) -> str:
    """
    自动登录 AgentRouter 并获取 session cookie
    
    Args:
        page: Playwright Page 对象
        username: LinuxDO 用户名或邮箱
        password: LinuxDO 密码
        totp_secret: 可选的 TOTP 密钥（用于 2FA）
    
    Returns:
        str: session cookie 值，失败返回 None
    """
    try:
        print(f"\n{'='*60}")
        print(f"🔐 开始自动登录流程")
        print(f"   用户名: {username}")
        print(f"{'='*60}\n")
        
        # 步骤 1: 访问 AgentRouter 登录页
        print("📍 步骤 1/7: 访问 AgentRouter 登录页...")
        page.goto("https://agentrouter.org/login", wait_until="networkidle")
        time.sleep(2)
        
        # 步骤 2: 点击 LinuxDO 登录按钮
        print("🔘 步骤 2/7: 点击 LinuxDO 登录按钮...")
        
        # 尝试多种可能的选择器
        selectors = [
            "text=Linux DO",
            "button:has-text('Linux DO')",
            "a:has-text('Linux DO')",
            "[href*='oauth']"
        ]
        
        button_clicked = False
        for selector in selectors:
            try:
                page.click(selector, timeout=3000)
                button_clicked = True
                print(f"   ✅ 使用选择器成功: {selector}")
                break
            except:
                continue
        
        if not button_clicked:
            print("   ❌ 无法找到 LinuxDO 登录按钮")
            return None
        
        # 步骤 3: 等待跳转到 LinuxDO
        print("⏳ 步骤 3/7: 等待跳转到 LinuxDO...")
        try:
            page.wait_for_url("**/connect.linux.do/**", timeout=10000)
            print(f"   ✅ 已跳转到: {page.url}")
        except:
            print(f"   ⚠️ 未检测到 LinuxDO URL，当前: {page.url}")
        
        time.sleep(2)
        
        # 步骤 4: 检查是否需要登录
        current_url = page.url
        if "login" in current_url.lower() or "session" in current_url.lower():
            print("📝 步骤 4/7: 检测到登录页面，填写登录信息...")
            
            # 填写用户名
            try:
                page.fill("input[name='login']", username, timeout=5000)
                print(f"   ✅ 已填写用户名: {username}")
            except:
                print("   ❌ 无法找到用户名输入框")
                return None
            
            # 填写密码
            try:
                page.fill("input[name='password']", password, timeout=5000)
                print("   ✅ 已填写密码")
            except:
                print("   ❌ 无法找到密码输入框")
                return None
            
            # 提交登录表单
            try:
                page.click("button[type='submit']", timeout=5000)
                print("   ✅ 已提交登录表单")
            except:
                try:
                    page.press("input[name='password']", "Enter")
                    print("   ✅ 使用回车键提交")
                except:
                    print("   ❌ 无法提交登录表单")
                    return None
            
            time.sleep(3)
            
            # 处理 2FA（如果需要）
            if totp_secret:
                print("🔐 检测到 2FA 配置，生成验证码...")
                try:
                    import pyotp
                    totp = pyotp.TOTP(totp_secret)
                    verification_code = totp.now()
                    
                    # 查找 2FA 输入框
                    page.fill("input[name='second_factor']", verification_code, timeout=5000)
                    page.click("button[type='submit']")
                    print(f"   ✅ 已填写 2FA 验证码")
                    time.sleep(3)
                except ImportError:
                    print("   ⚠️ 未安装 pyotp 库，无法生成 2FA 验证码")
                    print("   💡 安装命令: pip install pyotp")
                except Exception as e:
                    print(f"   ⚠️ 2FA 验证失败: {str(e)}")
        else:
            print("📝 步骤 4/7: 已登录 LinuxDO，跳过登录步骤")
        
        # 步骤 5: 等待授权页面或自动授权
        print("⏳ 步骤 5/7: 等待授权页面...")
        time.sleep(3)
        
        current_url = page.url
        if "authorize" in current_url.lower():
            print("   ✅ 检测到授权页面")
            
            # 步骤 6: 点击"允许"按钮
            print("✅ 步骤 6/7: 点击授权按钮...")
            try:
                # 尝试多种可能的选择器
                allow_selectors = [
                    "button:has-text('允许')",
                    "button:has-text('Allow')",
                    "button:has-text('Authorize')",
                    "button[type='submit']"
                ]
                
                for selector in allow_selectors:
                    try:
                        page.click(selector, timeout=3000)
                        print(f"   ✅ 已点击授权: {selector}")
                        break
                    except:
                        continue
            except Exception as e:
                print(f"   ⚠️ 点击授权按钮失败: {str(e)}")
        else:
            print("   ✅ 已自动授权，无需手动点击")
        
        # 步骤 7: 等待回调完成
        print("⏳ 步骤 7/7: 等待回调完成...")
        try:
            page.wait_for_url("**/agentrouter.org/**", timeout=15000)
            print(f"   ✅ 回调成功，当前页面: {page.url}")
        except:
            print(f"   ⚠️ 回调超时，当前页面: {page.url}")
        
        time.sleep(3)
        
        # 获取 session cookie
        print("\n🍪 提取 session cookie...")
        cookies = page.context.cookies()
        
        session_cookie = None
        for cookie in cookies:
            if cookie["name"] == "session" and "agentrouter.org" in cookie["domain"]:
                session_cookie = cookie["value"]
                print(f"   ✅ 成功获取 session")
                print(f"   📋 Session 前缀: {session_cookie[:30]}...")
                break
        
        if not session_cookie:
            print("   ❌ 未找到 session cookie")
            print("\n   📋 所有 cookies:")
            for cookie in cookies:
                print(f"      - {cookie['name']}: {cookie['domain']}")
        
        return session_cookie
        
    except Exception as e:
        print(f"\n❌ 登录过程发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def auto_login_anyrouter(
    page: Page,
    username: str,
    password: str,
    totp_secret: str = None
) -> str:
    """
    自动登录 AnyRouter 并获取 session cookie
    
    流程与 AgentRouter 类似，只是 URL 不同
    """
    print(f"\n{'='*60}")
    print(f"🔐 开始自动登录 AnyRouter")
    print(f"{'='*60}\n")
    
    try:
        # 1. 访问 AnyRouter 登录页
        print("📍 访问 AnyRouter 登录页...")
        page.goto("https://anyrouter.top/login", wait_until="networkidle")
        time.sleep(2)
        
        # 2-7 步骤与 AgentRouter 类似
        # ... (省略重复代码)
        
        # 获取 session cookie（注意域名是 anyrouter.top）
        cookies = page.context.cookies()
        session_cookie = None
        for cookie in cookies:
            if cookie["name"] == "session" and "anyrouter.top" in cookie["domain"]:
                session_cookie = cookie["value"]
                break
        
        return session_cookie
        
    except Exception as e:
        print(f"❌ AnyRouter 登录异常: {str(e)}")
        return None


def refresh_account_session(account: dict, headless: bool = True) -> bool:
    """
    刷新单个账号的 session
    
    Args:
        account: 账号配置字典
        headless: 是否使用无头模式
    
    Returns:
        bool: 成功返回 True
    """
    print(f"\n{'='*70}")
    print(f"🔄 刷新账号: {account['name']}")
    print(f"{'='*70}")
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=500 if not headless else 0  # 非无头模式时放慢速度便于观察
        )
        
        # 创建新的浏览器上下文
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )
        
        # 创建新页面
        page = context.new_page()
        
        try:
            # 根据 provider 调用相应的登录函数
            provider = account.get("provider", "agentrouter")
            username = account["linuxdo_username"]
            password = account["linuxdo_password"]
            totp_secret = account.get("totp_secret")
            
            if provider == "agentrouter":
                session = auto_login_agentrouter(page, username, password, totp_secret)
            elif provider == "anyrouter":
                session = auto_login_anyrouter(page, username, password, totp_secret)
            else:
                print(f"❌ 未知的 provider: {provider}")
                return False
            
            # 更新账号配置
            if session:
                account["cookies"]["session"] = session
                account["last_refresh"] = datetime.now().isoformat()
                print(f"\n✅ 账号 {account['name']} session 刷新成功！")
                return True
            else:
                print(f"\n❌ 账号 {account['name']} session 刷新失败！")
                return False
                
        finally:
            # 清理资源
            context.close()
            browser.close()


def refresh_multiple_accounts(accounts: list, headless: bool = True) -> dict:
    """
    批量刷新多个账号的 session
    
    Args:
        accounts: 账号列表
        headless: 是否使用无头模式
    
    Returns:
        dict: 刷新结果统计
    """
    print(f"\n{'='*70}")
    print(f"🚀 开始批量刷新 {len(accounts)} 个账号")
    print(f"{'='*70}\n")
    
    results = {
        "total": len(accounts),
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for i, account in enumerate(accounts, 1):
        print(f"\n[{i}/{len(accounts)}] 处理账号: {account['name']}")
        
        try:
            success = refresh_account_session(account, headless=headless)
            
            if success:
                results["success"] += 1
                results["details"].append({
                    "name": account["name"],
                    "status": "success"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "name": account["name"],
                    "status": "failed"
                })
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "name": account["name"],
                "status": "error",
                "error": str(e)
            })
            print(f"❌ 处理账号时发生异常: {str(e)}")
        
        # 账号之间添加延迟，避免被识别为机器人
        if i < len(accounts):
            print("\n⏳ 等待 5 秒后处理下一个账号...")
            time.sleep(5)
    
    # 打印统计结果
    print(f"\n\n{'='*70}")
    print("📊 批量刷新结果统计")
    print(f"{'='*70}")
    print(f"✅ 成功: {results['success']}/{results['total']}")
    print(f"❌ 失败: {results['failed']}/{results['total']}")
    print(f"{'='*70}\n")
    
    return results


# ==================== 使用示例 ====================

def example_single_account():
    """示例：刷新单个账号"""
    account = {
        "name": "测试账号",
        "provider": "agentrouter",
        "linuxdo_username": "your_username",  # 替换为实际用户名
        "linuxdo_password": "your_password",  # 替换为实际密码
        "cookies": {"session": ""},
        "api_user": "34327"
    }
    
    # 刷新 session（使用有界面模式便于观察）
    success = refresh_account_session(account, headless=False)
    
    if success:
        print(f"\n✅ 新的 session: {account['cookies']['session'][:50]}...")
    else:
        print("\n❌ Session 刷新失败")


def example_multiple_accounts():
    """示例：批量刷新多个账号"""
    accounts = [
        {
            "name": "账号1",
            "provider": "agentrouter",
            "linuxdo_username": "username1",
            "linuxdo_password": "password1",
            "cookies": {"session": ""},
            "api_user": "34327"
        },
        {
            "name": "账号2",
            "provider": "anyrouter",
            "linuxdo_username": "username2",
            "linuxdo_password": "password2",
            "cookies": {"session": ""},
            "api_user": "87260"
        }
    ]
    
    # 批量刷新（使用无头模式）
    results = refresh_multiple_accounts(accounts, headless=True)
    
    # 保存更新后的配置
    with open("accounts_updated.json", "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2, ensure_ascii=False)
    
    print("✅ 配置已保存到 accounts_updated.json")


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                    自动登录示例程序                                ║
║                                                                   ║
║  功能: 自动登录 AgentRouter/AnyRouter 并获取 session cookie      ║
║  技术: Playwright                                                 ║
║                                                                   ║
║  ⚠️ 注意: 这是示例代码，请根据实际情况修改配置                    ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n请选择操作：")
    print("1. 刷新单个账号（有界面模式）")
    print("2. 批量刷新多个账号（无头模式）")
    print("3. 退出")
    
    choice = input("\n请输入选择 (1-3): ").strip()
    
    if choice == "1":
        print("\n⚠️ 请先编辑代码中的账号信息（用户名和密码）")
        input("按回车继续...")
        example_single_account()
    
    elif choice == "2":
        print("\n⚠️ 请先编辑代码中的账号列表（用户名和密码）")
        input("按回车继续...")
        example_multiple_accounts()
    
    elif choice == "3":
        print("\n👋 再见！")
    
    else:
        print("\n❌ 无效的选择")
