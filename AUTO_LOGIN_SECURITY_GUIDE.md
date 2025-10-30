# 自动登录安全指南

## ⚠️ 安全注意事项

### **1. 密码存储**

#### ❌ 错误做法
```python
# 不要硬编码密码
PASSWORD = "my_password_123"
ACCOUNTS = [
    {"username": "user1", "password": "pass123"}
]
```

#### ✅ 正确做法

**方案A: 使用环境变量**
```python
import os

PASSWORD = os.getenv("LINUXDO_PASSWORD")
TOTP_SECRET = os.getenv("LINUXDO_TOTP_SECRET")
```

**方案B: 使用 GitHub Secrets（推荐）**
```yaml
# .github/workflows/refresh-session.yml
env:
  LINUXDO_PASSWORD: ${{ secrets.LINUXDO_PASSWORD }}
  LINUXDO_TOTP_SECRET: ${{ secrets.LINUXDO_TOTP_SECRET }}
```

**方案C: 使用加密配置文件**
```python
from cryptography.fernet import Fernet

# 加密配置
def encrypt_config(config, key):
    f = Fernet(key)
    encrypted = f.encrypt(json.dumps(config).encode())
    return encrypted

# 解密配置
def decrypt_config(encrypted_config, key):
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_config)
    return json.loads(decrypted)

# 使用
KEY = os.getenv("ENCRYPTION_KEY")  # 密钥存储在环境变量
config = decrypt_config(encrypted_config, KEY)
```

---

### **2. 2FA 密钥保护**

#### ❌ 不要提交到 Git
```bash
# .gitignore
accounts_config.json
*.secret
.env
```

#### ✅ 安全存储 TOTP Secret
```python
# 从环境变量读取
totp_secret = os.getenv(f"LINUXDO_TOTP_{account_id}")

# 或使用密钥管理服务（AWS Secrets Manager、Azure Key Vault等）
from azure.keyvault.secrets import SecretClient
secret = key_vault_client.get_secret("linuxdo-totp-secret")
```

---

### **3. Session Cookie 安全**

#### 风险点
- Session cookie 可以完全控制账号
- 泄露 = 账号被盗

#### 防护措施
```python
# 1. 最小权限原则
# 只在需要时才刷新 session，不要频繁刷新

# 2. Session 加密存储
def save_session_encrypted(session, key):
    f = Fernet(key)
    encrypted = f.encrypt(session.encode())
    with open("session.enc", "wb") as file:
        file.write(encrypted)

# 3. 限制 Session 访问权限
os.chmod("accounts_config.json", 0o600)  # 只有所有者可读写
```

---

### **4. GitHub Actions 安全配置**

#### 使用 Environment Secrets
```yaml
name: 刷新 Session

on:
  schedule:
    - cron: '0 0 */25 * *'  # 每 25 天运行一次

jobs:
  refresh:
    runs-on: ubuntu-latest
    environment: production  # 使用 environment secrets
    
    steps:
      - uses: actions/checkout@v4
      
      - name: 刷新 Session
        env:
          # 从 environment secrets 读取
          ACCOUNTS_CONFIG: ${{ secrets.ACCOUNTS_CONFIG }}
          ENCRYPTION_KEY: ${{ secrets.ENCRYPTION_KEY }}
        run: |
          python auto_refresh_session.py
```

#### 限制权限
```yaml
permissions:
  contents: read  # 只读代码
  issues: write   # 可以创建 issue（用于通知）
```

---

## 🔐 最佳实践

### **配置分离策略**

```
生产环境（GitHub Actions）
├── 敏感信息 → GitHub Secrets
├── 配置文件 → 从 secrets 动态生成
└── 运行环境 → 隔离的 runner

开发环境（本地）
├── 敏感信息 → .env 文件（不提交到 Git）
├── 配置文件 → 从 .env 读取
└── 运行环境 → 本地机器
```

---

### **双因素认证处理**

如果 LinuxDO 账号启用了 2FA：

```python
import pyotp

# 保存 TOTP secret 时记录
# 在设置 2FA 时，LinuxDO 会显示一个二维码和密钥
# 密钥格式类似: JBSWY3DPEHPK3PXP
# 保存这个密钥，不要分享给任何人

def generate_totp_code(secret):
    """生成 6 位验证码"""
    totp = pyotp.TOTP(secret)
    return totp.now()  # 当前时间的验证码

# 使用
verification_code = generate_totp_code(totp_secret)
page.fill("input[name='second_factor']", verification_code)
```

---

### **错误处理和日志**

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_login.log'),
        logging.StreamHandler()
    ]
)

def auto_login_with_logging(username, password):
    try:
        logging.info(f"开始登录账号: {username}")
        
        # 执行登录
        session = auto_login(username, password)
        
        if session:
            logging.info(f"✅ 登录成功: {username}")
            # 不要记录完整的 session！
            logging.info(f"Session 前缀: {session[:20]}...")
        else:
            logging.error(f"❌ 登录失败: {username}")
        
        return session
        
    except Exception as e:
        logging.error(f"❌ 登录异常: {username} - {str(e)}")
        # 不要记录密码或敏感信息！
        return None
```

---

## 📋 部署检查清单

### **部署前检查**

- [ ] ✅ 所有敏感信息已移至环境变量或 Secrets
- [ ] ✅ `.gitignore` 包含所有敏感文件
- [ ] ✅ 本地测试通过
- [ ] ✅ 错误处理完善
- [ ] ✅ 日志不包含敏感信息
- [ ] ✅ GitHub Secrets 已正确配置
- [ ] ✅ Workflow 权限最小化
- [ ] ✅ 备份现有 session（防止刷新失败）

### **部署后监控**

- [ ] ✅ 定期检查 Actions 运行日志
- [ ] ✅ 监控 session 有效性
- [ ] ✅ 设置失败通知（邮件/Telegram）
- [ ] ✅ 定期更新依赖包
- [ ] ✅ 审查安全漏洞

---

## 🚨 应急预案

### **场景 1: Session 刷新失败**

**症状：**
- 自动刷新脚本运行失败
- 所有账号无法签到

**应急措施：**
```bash
# 1. 使用备份的 session
cp accounts_config.backup.json accounts_config.json

# 2. 手动获取新 session
# 访问网站 → F12 → 复制 session → 更新配置

# 3. 回滚到上一个工作版本
git revert HEAD
```

---

### **场景 2: 账号被锁定**

**症状：**
- 登录提示"账号已锁定"
- 需要邮箱验证

**应急措施：**
1. 停止自动登录脚本
2. 检查邮箱，完成验证
3. 手动登录确认账号正常
4. 降低刷新频率（延长刷新周期）

---

### **场景 3: LinuxDO 接口变更**

**症状：**
- 登录流程失败
- 返回意外的错误

**应急措施：**
1. 暂停自动刷新
2. 手动登录测试新流程
3. 使用浏览器 F12 查看新的请求
4. 更新脚本逻辑
5. 本地测试后重新部署

---

## 💡 性能优化建议

### **1. 并行处理多账号**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def refresh_accounts_parallel(accounts, max_workers=3):
    """并行刷新多个账号"""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_account = {
            executor.submit(auto_login, acc["username"], acc["password"]): acc
            for acc in accounts
        }
        
        # 获取结果
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                session = future.result()
                account["cookies"]["session"] = session
                results.append({"account": account["name"], "success": True})
            except Exception as e:
                results.append({"account": account["name"], "success": False, "error": str(e)})
    
    return results
```

**注意：**
- 不要设置太多 workers（容易被识别为攻击）
- 建议 max_workers=2-3

---

### **2. 浏览器实例复用**

```python
def refresh_accounts_reuse_browser(accounts):
    """复用浏览器实例"""
    with sync_playwright() as p:
        # 只启动一次浏览器
        browser = p.chromium.launch(headless=True)
        
        for account in accounts:
            # 每个账号使用新 context
            context = browser.new_context()
            page = context.new_page()
            
            session = auto_login(page, account["username"], account["password"])
            account["cookies"]["session"] = session
            
            # 关闭 context 释放资源
            context.close()
        
        # 最后关闭浏览器
        browser.close()
```

---

### **3. 智能刷新策略**

```python
def smart_refresh_strategy(accounts):
    """智能决定是否需要刷新"""
    for account in accounts:
        # 检查 session 是否仍然有效
        if check_session_validity(account):
            print(f"✅ {account['name']}: Session 仍然有效，跳过刷新")
            continue
        
        # 检查距离上次刷新的天数
        days_since_refresh = get_days_since_refresh(account)
        if days_since_refresh < 20:
            print(f"✅ {account['name']}: 距离上次刷新仅 {days_since_refresh} 天，跳过刷新")
            continue
        
        # 需要刷新
        print(f"🔄 {account['name']}: 需要刷新 session")
        session = auto_login(account["username"], account["password"])
        account["cookies"]["session"] = session
        account["last_refresh"] = datetime.now().isoformat()
```

---

## 📊 监控和告警

### **实现健康检查**

```python
def health_check():
    """检查系统健康状态"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_accounts": len(accounts),
        "valid_sessions": 0,
        "invalid_sessions": 0,
        "warnings": []
    }
    
    for account in accounts:
        if check_session_validity(account):
            report["valid_sessions"] += 1
        else:
            report["invalid_sessions"] += 1
            report["warnings"].append(f"{account['name']}: Session 无效")
    
    # 如果超过 50% 的账号 session 无效，发送警报
    if report["invalid_sessions"] / report["total_accounts"] > 0.5:
        send_alert(f"⚠️ 警告：{report['invalid_sessions']} 个账号 session 无效")
    
    return report
```

---

### **集成通知服务**

```python
# 示例：Telegram 通知
import requests

def send_telegram_notification(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    })

# 使用
try:
    result = refresh_sessions(accounts)
    if all(r["success"] for r in result):
        send_telegram_notification("✅ 所有账号 session 刷新成功！")
    else:
        failed = [r for r in result if not r["success"]]
        send_telegram_notification(f"⚠️ {len(failed)} 个账号刷新失败")
except Exception as e:
    send_telegram_notification(f"❌ Session 刷新异常: {str(e)}")
```

---

## 🎓 学习资源

### **相关技术文档**

- **Playwright 官方文档**: https://playwright.dev/python/
- **OAuth 2.0 RFC**: https://datatracker.ietf.org/doc/html/rfc6749
- **TOTP RFC**: https://datatracker.ietf.org/doc/html/rfc6238
- **GitHub Actions 文档**: https://docs.github.com/en/actions

### **推荐阅读**

1. **Web 自动化最佳实践**
   - 如何绕过常见的反爬虫机制
   - Playwright vs Selenium 选择指南

2. **OAuth 安全**
   - CSRF 攻击防护
   - State 参数的作用

3. **密钥管理**
   - 不要在代码中硬编码密钥
   - 使用密钥管理服务（KMS）

---

## 📝 后续优化方向

### **短期目标（1-2周）**

1. ✅ 实现基础的 Playwright 自动登录
2. ✅ 支持单账号 session 刷新
3. ✅ 添加基本错误处理

### **中期目标（1个月）**

1. 🔄 支持多账号批量刷新
2. 🔄 集成到 GitHub Actions
3. 🔄 添加监控和通知
4. 🔄 完善错误重试机制

### **长期目标（3个月）**

1. 🎯 实现纯 HTTP 方案（无需浏览器）
2. 🎯 支持更多平台（AnyRouter 等）
3. 🎯 开发 Web UI 管理界面
4. 🎯 添加详细的统计和分析

---

## 🤝 贡献指南

如果你优化了这个方案，欢迎分享：

1. **提交 Issue** 描述你的改进
2. **创建 PR** 提交代码改进
3. **更新文档** 补充实现细节
4. **分享经验** 帮助其他开发者

---

## ⚖️ 免责声明

本文档仅供学习和研究使用。使用自动化脚本时请：

1. ✅ 遵守网站的服务条款
2. ✅ 不要进行恶意攻击或滥用
3. ✅ 保护好自己的账号安全
4. ✅ 尊重网站的 robots.txt 和 API 限制

**使用自动化脚本的风险由你自己承担。**

---

## 📞 技术支持

如果在实现过程中遇到问题：

1. 查看 [主实现指南](AUTO_LOGIN_IMPLEMENTATION_GUIDE.md)
2. 检查 GitHub Actions 日志
3. 使用 Playwright 的调试模式：
   ```python
   browser = p.chromium.launch(headless=False, slow_mo=1000)
   ```
4. 查看完整的错误堆栈信息

---

**最后更新：2025-10-27**
**文档版本：1.0**
