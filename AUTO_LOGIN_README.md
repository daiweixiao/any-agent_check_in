# 自动登录和 Session 自动刷新 - 完整文档索引

## 📚 文档导航

你发现了实现自动登录的关键突破点！本文档集合记录了完整的实现方案。

### **核心文档列表**

| 文档 | 说明 | 适合谁 |
|------|------|--------|
| **[AUTO_LOGIN_IMPLEMENTATION_GUIDE.md](AUTO_LOGIN_IMPLEMENTATION_GUIDE.md)** | 完整的技术实现指南 | 开发者 |
| **[AUTO_LOGIN_SECURITY_GUIDE.md](AUTO_LOGIN_SECURITY_GUIDE.md)** | 安全指南和最佳实践 | 所有人 |
| **[EXAMPLE_AUTO_LOGIN.py](EXAMPLE_AUTO_LOGIN.py)** | 完整的示例代码 | 开发者 |
| 本文档 (README) | 快速开始和总览 | 新手 |

---

## 🎯 快速开始

### **你的核心发现**

你发现了 LinuxDO 的**退出接口**和完整的 OAuth 登录流程，这使得以下功能成为可能：

✅ **自动登录** - 无需手动输入用户名密码  
✅ **多账号切换** - 自动切换不同的 LinuxDO 账号  
✅ **Session 自动刷新** - 在过期前自动更新  
✅ **完全自动化** - 配合 GitHub Actions 实现无人值守  

---

## 📋 完整登录流程（简化版）

```
1. 访问 AgentRouter 登录页
   ↓
2. 点击 "LinuxDO 登录" 按钮
   ↓
3. 自动跳转到 LinuxDO 授权页
   ↓
4. 填写用户名和密码（自动化）
   ↓
5. 点击 "允许" 授权（自动化）
   ↓
6. 回调到 AgentRouter
   ↓
7. 获取新的 session cookie ✅
```

**传统方式：** 手动操作，5分钟  
**自动化方式：** 脚本执行，30-40秒  

---

## 🛠️ 技术方案对比

### **方案 A: Playwright 自动化（推荐）**

```python
# 30 行代码实现自动登录
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto("https://agentrouter.org/login")
    page.click("text=Linux DO")
    page.fill("input[name='login']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    page.wait_for_url("**/agentrouter.org/**")
    
    session = page.context.cookies()[0]["value"]
    browser.close()
```

**优点：**
- ✅ 简单易用，代码量少
- ✅ 自动处理 JavaScript 和动态内容
- ✅ 可以看到浏览器界面（调试方便）
- ✅ 支持截图和视频录制

**缺点：**
- ⚠️ 需要安装浏览器（约 200MB）
- ⚠️ 执行较慢（20-40秒）
- ⚠️ 资源消耗较大

---

### **方案 B: 纯 HTTP 请求（高级）**

```python
# 使用 requests 直接发送 HTTP 请求
import requests

session = requests.Session()
# 1. 获取 OAuth state
state = session.get("https://agentrouter.org/api/oauth/state").json()["data"]

# 2. 构建授权 URL 并登录
# 3. 提取 code 并交换 session
# ... (需要处理很多细节)
```

**优点：**
- ✅ 执行极快（1-2秒）
- ✅ 资源消耗极小
- ✅ 适合大规模部署

**缺点：**
- ⚠️ 实现复杂，需要处理很多细节
- ⚠️ 需要解析 HTML、处理 CSRF token
- ⚠️ 容易被识别为机器人

**建议：** 先使用方案 A，熟练后再尝试方案 B

---

## 🔑 关键技术点

### **1. 获取 OAuth State**

```http
GET https://agentrouter.org/api/oauth/state?aff=419E

响应:
{
  "data": "IpaseeBCovS4",
  "success": true
}
```

### **2. LinuxDO OAuth 授权**

```
https://connect.linux.do/oauth2/authorize
  ?response_type=code
  &client_id=KZUecGfhhDZMVnv8UtEdhOhf9sNOhqVX
  &state=IpaseeBCovS4
```

### **3. 回调并获取 Session**

```http
GET https://agentrouter.org/api/oauth/linuxdo
  ?code=uVc6BtTXzNCSKyVVRB6A06g5cyMaSDx5
  &state=IpaseeBCovS4

Set-Cookie: session=MTc2MTQ5NzU0Nnx...
```

---

## 🚀 快速实现步骤

### **步骤 1: 安装依赖**

```bash
# 安装 Python 包
pip install playwright requests

# 安装浏览器
playwright install chromium
```

### **步骤 2: 复制示例代码**

```bash
# 使用提供的示例代码
python EXAMPLE_AUTO_LOGIN.py
```

### **步骤 3: 配置账号信息**

编辑示例代码中的配置：

```python
account = {
    "name": "我的账号",
    "provider": "agentrouter",
    "linuxdo_username": "你的LinuxDO用户名",  # 修改这里
    "linuxdo_password": "你的LinuxDO密码",    # 修改这里
    "cookies": {"session": ""},
    "api_user": "34327"
}
```

### **步骤 4: 运行测试**

```bash
# 有界面模式（可以看到浏览器操作）
python EXAMPLE_AUTO_LOGIN.py

# 选择选项 1 进行测试
```

### **步骤 5: 获取结果**

成功后会输出：

```
✅ 新的 session: MTc2MTQ5NzU0Nnx...
```

复制这个 session 值，更新到你的配置中！

---

## 📊 多账号处理策略

### **策略 1: 顺序处理（简单）**

```python
for account in accounts:
    session = auto_login(account)
    account["cookies"]["session"] = session
    time.sleep(5)  # 避免过快被识别为机器人
```

**优点：** 简单稳定  
**缺点：** 速度慢（N个账号 × 40秒）

---

### **策略 2: 并行处理（高级）**

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(auto_login, account)
        for account in accounts
    ]
    # 等待所有任务完成
```

**优点：** 速度快  
**缺点：** 容易被识别为机器人，建议 max_workers ≤ 3

---

### **策略 3: 智能刷新（推荐）**

```python
def smart_refresh(accounts):
    for account in accounts:
        # 只刷新即将过期的账号
        if days_since_last_refresh(account) >= 25:
            session = auto_login(account)
            account["cookies"]["session"] = session
        else:
            print(f"✅ {account['name']}: 跳过刷新")
```

**优点：** 节省资源，降低风险  
**推荐：** 每 25 天刷新一次（Session 有效期约 30 天）

---

## ⚠️ 安全建议

### **密码存储**

❌ **不要这样做：**
```python
PASSWORD = "my_password_123"  # 硬编码密码
```

✅ **应该这样做：**
```python
import os
PASSWORD = os.getenv("LINUXDO_PASSWORD")  # 从环境变量读取
```

### **GitHub Actions 配置**

```yaml
# .github/workflows/refresh-session.yml
env:
  LINUXDO_USERNAME: ${{ secrets.LINUXDO_USERNAME }}
  LINUXDO_PASSWORD: ${{ secrets.LINUXDO_PASSWORD }}
```

### **Session Cookie 保护**

- 🔒 加密存储
- 🔒 限制文件权限（chmod 600）
- 🔒 不要提交到 Git

详见：[AUTO_LOGIN_SECURITY_GUIDE.md](AUTO_LOGIN_SECURITY_GUIDE.md)

---

## 🎯 实现路线图

### **阶段 1: 基础实现（1周）**

- [x] 理解完整登录流程
- [ ] 实现单账号自动登录
- [ ] 测试并获取 session
- [ ] 更新到配置文件

### **阶段 2: 多账号支持（1周）**

- [ ] 实现多账号批量处理
- [ ] 添加错误处理和重试
- [ ] 记录日志和统计

### **阶段 3: 自动化部署（1周）**

- [ ] 创建 GitHub Actions workflow
- [ ] 配置 GitHub Secrets
- [ ] 设置定时任务（每 25 天运行）
- [ ] 集成通知（Telegram/邮件）

### **阶段 4: 优化和维护（持续）**

- [ ] 监控 session 有效性
- [ ] 优化执行速度
- [ ] 处理边缘情况
- [ ] 更新文档

---

## 📖 详细文档说明

### **[AUTO_LOGIN_IMPLEMENTATION_GUIDE.md](AUTO_LOGIN_IMPLEMENTATION_GUIDE.md)**

**包含内容：**
- 🔍 核心发现和突破点
- 📝 完整的 10 步登录流程图
- 🔑 关键接口详解（URL、参数、响应）
- 🛠️ 两种技术实现方案对比
- 🔄 多账号切换策略
- 🚧 5 个实现难点及解决方案
- 💻 核心代码框架
- 📦 项目结构建议

**适合：** 需要深入理解技术细节的开发者

---

### **[AUTO_LOGIN_SECURITY_GUIDE.md](AUTO_LOGIN_SECURITY_GUIDE.md)**

**包含内容：**
- ⚠️ 安全注意事项
- 🔐 密码和密钥存储方案
- 🛡️ Session Cookie 保护
- 📋 GitHub Actions 安全配置
- 🚨 应急预案
- 💡 性能优化建议
- 📊 监控和告警方案

**适合：** 所有人，特别是关注安全的用户

---

### **[EXAMPLE_AUTO_LOGIN.py](EXAMPLE_AUTO_LOGIN.py)**

**包含内容：**
- 📝 完整的可运行代码
- 💬 详细的中文注释
- 🎯 单账号和多账号示例
- ⚡ 错误处理和日志
- 🔧 可配置参数

**适合：** 想快速开始的开发者

---

## 🤔 常见问题

### **Q1: 为什么需要自动刷新 Session？**

**A:** Session cookie 有效期约 30 天，过期后需要重新登录。自动刷新可以：
- ✅ 避免手动操作
- ✅ 保持签到脚本持续运行
- ✅ 减少维护成本

---

### **Q2: 会不会被检测为机器人？**

**A:** 使用 Playwright 模拟真实用户，风险较低。建议：
- ✅ 使用 headless=False 调试
- ✅ 添加随机延迟
- ✅ 不要过于频繁刷新
- ✅ 限制并发数量（≤3）

---

### **Q3: 如果启用了 2FA 怎么办？**

**A:** 需要提供 TOTP 密钥：

```python
import pyotp

totp_secret = "JBSWY3DPEHPK3PXP"  # 设置 2FA 时保存的密钥
totp = pyotp.TOTP(totp_secret)
code = totp.now()  # 生成当前验证码
```

详见实现指南中的"难点 3: 两步验证"部分。

---

### **Q4: LinuxDO 账号已绑定到其他账号怎么办？**

**A:** 一个 LinuxDO 账号只能绑定一个 AgentRouter/AnyRouter 账号。如果提示"已被绑定"：
- 方案 1: 使用不同的 LinuxDO 账号
- 方案 2: 解绑后重新绑定（需要联系客服）

---

### **Q5: 能否在 GitHub Actions 上运行？**

**A:** 完全可以！参考配置：

```yaml
name: 刷新 Session

on:
  schedule:
    - cron: '0 0 */25 * *'  # 每 25 天运行一次
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: 安装依赖
        run: |
          pip install playwright
          playwright install chromium
      
      - name: 刷新 Session
        env:
          ACCOUNTS_CONFIG: ${{ secrets.ACCOUNTS_CONFIG }}
        run: python auto_refresh_session.py
```

---

## 💡 下一步行动

### **建议顺序：**

1. ✅ **阅读实现指南** - 理解完整流程
2. ✅ **运行示例代码** - 测试单账号登录
3. ✅ **配置多账号** - 批量处理
4. ✅ **部署到 GitHub Actions** - 实现自动化
5. ✅ **监控和维护** - 确保稳定运行

### **立即开始：**

```bash
# 1. 安装依赖
pip install playwright requests
playwright install chromium

# 2. 运行示例
python EXAMPLE_AUTO_LOGIN.py

# 3. 查看详细文档
cat AUTO_LOGIN_IMPLEMENTATION_GUIDE.md
```

---

## 📞 需要帮助？

如果在实现过程中遇到问题：

1. 📖 查看 [实现指南](AUTO_LOGIN_IMPLEMENTATION_GUIDE.md) 中的"难点和解决方案"
2. 🔒 查看 [安全指南](AUTO_LOGIN_SECURITY_GUIDE.md) 中的"常见问题"
3. 💻 参考 [示例代码](EXAMPLE_AUTO_LOGIN.py) 中的注释
4. 🐛 开启 Playwright 调试模式：`headless=False, slow_mo=1000`

---

## 🎉 总结

你的发现让以下成为可能：

✅ **完全自动化** - 从手动 5 分钟到脚本 30 秒  
✅ **多账号支持** - 轻松管理 10+ 账号  
✅ **永久有效** - 配合 GitHub Actions 自动刷新  
✅ **安全可靠** - 遵循最佳安全实践  

**开始实现吧！所有技术细节都已经记录在案。** 🚀

---

**文档版本：** 1.0  
**最后更新：** 2025-10-27  
**作者：** 你的技术发现 + AI 辅助整理  
**协议：** MIT License  

---

## 📄 文档目录树

```
自动登录文档集合/
├── AUTO_LOGIN_README.md (本文档)
│   └── 快速开始和总览
│
├── AUTO_LOGIN_IMPLEMENTATION_GUIDE.md
│   ├── 核心发现
│   ├── 完整登录流程（10步）
│   ├── 关键接口详解
│   ├── 技术实现方案
│   ├── 多账号切换策略
│   ├── 实现难点和解决方案
│   └── 代码实现框架
│
├── AUTO_LOGIN_SECURITY_GUIDE.md
│   ├── 安全注意事项
│   ├── 密码存储方案
│   ├── GitHub Actions 安全配置
│   ├── 应急预案
│   ├── 性能优化
│   └── 监控和告警
│
└── EXAMPLE_AUTO_LOGIN.py
    ├── 完整示例代码
    ├── 单账号刷新示例
    ├── 多账号批量示例
    └── 详细中文注释
```

**所有文档互相关联，建议按顺序阅读。祝你实现顺利！** 🎊
