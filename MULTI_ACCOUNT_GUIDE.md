# 多账号配置完全指南

## 🎯 快速开始

### **步骤 1: 准备多个账号**

确保你有多个 AgentRouter 或 AnyRouter 账号。

---

## 📱 获取多个账号信息的方法

### **方法 1: 使用不同浏览器（推荐）**

这是最简单的方法，不需要来回切换登录。

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Chrome    │  │    Edge     │  │  Firefox    │
│   账号 1    │  │   账号 2    │  │   账号 3    │
└─────────────┘  └─────────────┘  └─────────────┘
```

**操作步骤：**

1. **Chrome 浏览器**
   - 打开 https://agentrouter.org
   - 登录账号 1
   - F12 → Application → Cookies → 复制 `session`
   - F12 → Network → 任意请求 → Headers → 复制 `new-api-user`
   - 记录到文本文件

2. **Edge 浏览器**
   - 打开 https://agentrouter.org
   - 登录账号 2
   - 重复上述步骤
   - 记录到文本文件

3. **Firefox 浏览器**
   - 打开 https://agentrouter.org
   - 登录账号 3
   - 重复上述步骤
   - 记录到文本文件

---

### **方法 2: 使用无痕/隐私窗口**

如果你只有一个浏览器，可以使用无痕模式。

**操作步骤：**

1. **正常窗口** → 登录账号 1 → 获取信息 → 记录

2. **打开无痕窗口**（Ctrl+Shift+N / Cmd+Shift+N）
   - 登录账号 2 → 获取信息 → 记录
   - 关闭无痕窗口

3. **再次打开无痕窗口**
   - 登录账号 3 → 获取信息 → 记录

---

### **方法 3: 清除 Cookie 切换账号**

**操作步骤：**

1. 登录账号 1 → F12 获取信息 → 记录

2. F12 → Application → Storage → Clear site data
   - ✅ Cookies and site data
   - ✅ Cached images and files
   - 点击 "Clear site data"

3. 刷新页面 → 登录账号 2 → 获取信息 → 记录

4. 重复步骤 2-3 获取更多账号

---

### **方法 4: 使用浏览器配置文件（高级）**

**Chrome/Edge:**
```bash
# 创建多个配置文件
chrome.exe --user-data-dir="C:\ChromeProfile1"
chrome.exe --user-data-dir="C:\ChromeProfile2"
```

每个配置文件独立的 Cookie 存储。

---

## 📋 信息记录模板

建议创建一个 Excel 或文本文件记录：

```
账号1 - AgentRouter 主账号
├─ session: MTc2MTQwNjM2NHxEWDhF...
└─ api_user: 34877

账号2 - AgentRouter 备用账号
├─ session: MTc2MTQxMjM0NXxEWDhF...
└─ api_user: 35123

账号3 - AnyRouter 测试账号
├─ session: MTc2MTQyMzQ1NnxEWDhF...
└─ api_user: 12345
```

---

## 🛠️ 配置格式

### **JSON 格式（用于 GitHub Actions）**

```json
[
  {
    "name": "主账号",
    "provider": "agentrouter",
    "cookies": {
      "session": "MTc2MTQwNjM2NHxEWDhF..."
    },
    "api_user": "34877"
  },
  {
    "name": "备用账号",
    "provider": "agentrouter",
    "cookies": {
      "session": "MTc2MTQxMjM0NXxEWDhF..."
    },
    "api_user": "35123"
  },
  {
    "name": "测试账号 - AnyRouter",
    "provider": "anyrouter",
    "cookies": {
      "session": "MTc2MTQyMzQ1NnxEWDhF..."
    },
    "api_user": "12345"
  }
]
```

**⚠️ 注意事项：**
- JSON 必须是**单行格式**（用于 GitHub Secrets）
- 不能有换行符
- 使用在线工具压缩：https://jsonformatter.org/json-minify

**压缩后的格式：**
```json
[{"name":"主账号","provider":"agentrouter","cookies":{"session":"MTc2MTQw..."},"api_user":"34877"},{"name":"备用账号","provider":"agentrouter","cookies":{"session":"MTc2MTQx..."},"api_user":"35123"}]
```

---

## 🧪 本地测试多账号

### **方法 1: 使用测试脚本**

1. 编辑 `test_multi_accounts.py`：

```python
ACCOUNTS = [
    {
        "name": "主账号",
        "provider": "agentrouter",
        "cookies": {"session": "账号1的session"},
        "api_user": "账号1的user_id"
    },
    {
        "name": "备用账号",
        "provider": "agentrouter",
        "cookies": {"session": "账号2的session"},
        "api_user": "账号2的user_id"
    },
]
```

2. 运行测试：
```bash
uv run python test_multi_accounts.py
```

### **方法 2: 使用 .env 文件**

创建 `.env` 文件（会被 gitignore）：

```bash
ANYROUTER_ACCOUNTS=[{"name":"主账号","provider":"agentrouter","cookies":{"session":"xxx"},"api_user":"34877"},{"name":"备用账号","provider":"agentrouter","cookies":{"session":"yyy"},"api_user":"35123"}]
```

运行：
```bash
uv run python checkin.py
```

---

## 🚀 部署到 GitHub Actions

### **步骤 1: 准备配置**

将你的多账号配置转换为**单行 JSON**：

```json
[{"name":"主账号","provider":"agentrouter","cookies":{"session":"MTc2MTQwNjM2NHw..."},"api_user":"34877"},{"name":"备用账号","provider":"agentrouter","cookies":{"session":"MTc2MTQxMjM0NXw..."},"api_user":"35123"}]
```

### **步骤 2: 配置 GitHub Secret**

1. 进入你的 GitHub 仓库
2. `Settings` → `Environments` → 创建 `production` 环境
3. 点击 `Add environment secret`
4. **Name**: `ANYROUTER_ACCOUNTS`
5. **Value**: 粘贴你的单行 JSON
6. 点击 `Add secret`

### **步骤 3: 启用 Actions**

1. 点击 `Actions` 标签页
2. 如果提示启用，点击 `Enable workflow`
3. 找到 "AnyRouter 自动签到"
4. 点击 `Run workflow` 进行测试

---

## 📊 执行结果示例

```
[SYSTEM] AnyRouter.top multi-account auto check-in script started
[TIME] Execution time: 2025-10-25 23:45:00
[INFO] Found 3 account configurations

[PROCESSING] Starting to process 主账号
[INFO] 主账号: Using provider "agentrouter"
:money: Current balance: $325.0, Used: $0.0
[SUCCESS] 主账号: Check-in successful!

[PROCESSING] Starting to process 备用账号
[INFO] 备用账号: Using provider "agentrouter"
:money: Current balance: $150.0, Used: $25.0
[SUCCESS] 备用账号: Check-in successful!

[PROCESSING] Starting to process 测试账号 - AnyRouter
[INFO] 测试账号 - AnyRouter: Using provider "anyrouter"
[PROCESSING] Starting browser to get WAF cookies...
:money: Current balance: $100.0, Used: $50.0
[SUCCESS] 测试账号 - AnyRouter: Check-in successful!

[STATS] Check-in result statistics:
[SUCCESS] Success: 3/3
[SUCCESS] All accounts check-in successful!
```

---

## ⚠️ 常见问题

### **Q1: 某个账号失败会影响其他账号吗？**
**A:** 不会！脚本会继续处理其他账号，只要有一个成功就算成功。

### **Q2: 不同平台可以混用吗？**
**A:** 可以！支持 `anyrouter`、`agentrouter` 混合配置。

### **Q3: 账号配置顺序有影响吗？**
**A:** 没有影响，按数组顺序依次执行。

### **Q4: Session 过期怎么办？**
**A:** 脚本会报 401 错误，重新获取该账号的 session 更新配置即可。

### **Q5: 可以配置多少个账号？**
**A:** 理论上无限制，但建议不超过 10 个（GitHub Actions 执行时间限制）。

### **Q6: 账号之间会互相影响吗？**
**A:** 不会，每个账号独立处理，使用各自的 cookies。

---

## 🎯 最佳实践

### **1. 账号命名规范**
```json
{
  "name": "AgentRouter - 主账号",  // ✅ 清晰明确
  "name": "AnyRouter - 测试",     // ✅ 包含平台信息
  "name": "账号1"                 // ❌ 不够清晰
}
```

### **2. 定期检查**
- 每月检查一次 session 是否有效
- 建议在 session 过期前主动更新

### **3. 余额监控**
- 配置通知推送（钉钉、邮件等）
- 脚本会在余额变化时自动通知

### **4. 安全建议**
- 不要在公开场所分享你的配置
- session 相当于密码，妥善保管
- 定期更换 session（重新登录）

---

## 🔧 故障排除

### **问题：某个账号一直 401 错误**
**解决方案：**
1. 退出该账号
2. 清除浏览器 Cookie
3. 重新登录
4. 获取新的 session 和 api_user
5. 更新配置

### **问题：多个账号都失败**
**解决方案：**
1. 检查 JSON 格式是否正确
2. 检查是否是单行格式（GitHub Secrets）
3. 检查每个账号的 session 是否有效
4. 查看 Actions 日志详细错误信息

### **问题：部分账号成功，部分失败**
**解决方案：**
- 这是正常现象
- 检查失败账号的 session 是否过期
- 单独更新失败账号的配置

---

## 📚 参考资源

- [项目 README](./README.md)
- [流程分析文档](./FLOW_ANALYSIS.md)
- [单账号测试脚本](./test_local.py)
- [多账号测试脚本](./test_multi_accounts.py)

---

## 💡 小贴士

1. **使用不同浏览器获取信息最简单**
2. **记得压缩 JSON 为单行格式**
3. **先本地测试，再部署到 Actions**
4. **配置通知可以及时了解签到状态**
5. **Session 有效期约 30 天，提前更新**
